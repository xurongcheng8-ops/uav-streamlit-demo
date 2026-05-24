from __future__ import annotations

import math
import time
from copy import deepcopy
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from .data_generator import normalize_nest_dataframe, normalize_task_dataframe, normalize_uav_dataframe


ALGORITHMS = {
    "nearest_neighbor": "Nearest Neighbor",
    "priority_first": "Priority First",
    "weighted": "Weighted Heuristic",
}


def run_dispatch_algorithm(
    algorithm: str,
    tasks: pd.DataFrame,
    nests: pd.DataFrame,
    uavs: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> dict:
    start = time.perf_counter()
    algorithm_key = _normalize_algorithm_key(algorithm)
    weights = weights or {"w1": 0.35, "w2": 0.25, "w3": 0.25, "w4": 0.15}

    tasks_df = normalize_task_dataframe(tasks)
    nests_df = normalize_nest_dataframe(nests)
    uavs_df = normalize_uav_dataframe(uavs)

    task_records = _records_by_id(tasks_df, "task_id")
    unserved = dict(task_records)
    nests_by_id = _records_by_id(nests_df, "nest_id")

    routes: dict[str, dict] = {}
    served_tasks: dict[str, dict] = {}

    for _, uav_row in uavs_df.sort_values("uav_id").iterrows():
        uav = _row_to_dict(uav_row)
        nest = nests_by_id.get(str(uav["nest_id"]))
        if nest is None:
            continue
        route = _empty_route(uav, nest)
        current_pos = (float(nest["x"]), float(nest["y"]))
        current_time = 0.0
        distance_used = 0.0

        while unserved:
            candidates = []
            for task_id, task in unserved.items():
                evaluation = evaluate_candidate(uav, nest, task, current_pos, current_time, distance_used)
                if evaluation["feasible"]:
                    candidates.append((task_id, task, evaluation))
            if not candidates:
                break

            task_id, task, evaluation = _select_candidate(algorithm_key, candidates, weights)
            _append_stop(route, task, evaluation)
            served_tasks[task_id] = {
                "task_id": task_id,
                "uav_id": str(uav["uav_id"]),
                "start_service_time": evaluation["start_service_time"],
                "arrival_time": evaluation["arrival_time"],
                "finish_time": evaluation["finish_time"],
                "on_time": evaluation["finish_time"] <= float(task["latest_finish"]) + 1e-9,
            }
            current_pos = (float(task["x"]), float(task["y"]))
            current_time = evaluation["finish_time"]
            distance_used += evaluation["travel_distance"]
            unserved.pop(task_id)

        _return_to_nest(route, uav, nest, current_pos, distance_used)
        routes[str(uav["uav_id"])] = route

    runtime = time.perf_counter() - start
    return {
        "algorithm": ALGORITHMS[algorithm_key],
        "algorithm_key": algorithm_key,
        "routes": routes,
        "served_tasks": served_tasks,
        "unserved_tasks": sorted(unserved.keys()),
        "runtime": runtime,
    }


def run_all_algorithms(
    tasks: pd.DataFrame,
    nests: pd.DataFrame,
    uavs: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> dict[str, dict]:
    return {
        key: run_dispatch_algorithm(key, tasks, nests, uavs, weights=weights)
        for key in ["nearest_neighbor", "priority_first", "weighted"]
    }


def evaluate_candidate(
    uav: dict,
    nest: dict,
    task: dict,
    current_pos: tuple[float, float],
    current_time: float,
    distance_used: float,
) -> dict:
    if float(task["payload_required"]) > float(uav["payload_capacity"]):
        return {"feasible": False, "reason": "payload"}

    task_pos = (float(task["x"]), float(task["y"]))
    nest_pos = (float(nest["x"]), float(nest["y"]))
    travel_distance = euclidean(current_pos, task_pos)
    return_distance = euclidean(task_pos, nest_pos)
    speed = max(float(uav["speed"]), 1e-6)
    arrival_time = current_time + travel_distance / speed
    start_service_time = max(arrival_time, float(task["earliest_start"]))
    finish_time = start_service_time + float(task["service_time"])

    if finish_time > float(task["latest_finish"]) + 1e-9:
        return {"feasible": False, "reason": "time_window"}

    allowed_distance = max(
        0.0,
        min(float(uav["max_range"]), float(uav["battery_capacity"]) - float(uav["safety_battery"])),
    )
    if distance_used + travel_distance + return_distance > allowed_distance + 1e-9:
        return {"feasible": False, "reason": "battery_range"}

    return {
        "feasible": True,
        "travel_distance": travel_distance,
        "return_distance": return_distance,
        "arrival_time": arrival_time,
        "start_service_time": start_service_time,
        "finish_time": finish_time,
        "slack_after_finish": float(task["latest_finish"]) - finish_time,
    }


def evaluate_fixed_route_sequence(
    uav: dict,
    nest: dict,
    tasks_by_id: dict[str, dict],
    task_sequence: Iterable[str],
) -> dict:
    route = _empty_route(uav, nest)
    current_pos = (float(nest["x"]), float(nest["y"]))
    current_time = 0.0
    distance_used = 0.0
    served_updates = {}

    for task_id in task_sequence:
        task = tasks_by_id.get(str(task_id))
        if task is None:
            return {"feasible": False, "reason": f"missing task {task_id}"}
        evaluation = evaluate_candidate(uav, nest, task, current_pos, current_time, distance_used)
        if not evaluation["feasible"]:
            return {"feasible": False, "reason": evaluation.get("reason", "infeasible")}
        _append_stop(route, task, evaluation)
        served_updates[str(task_id)] = {
            "task_id": str(task_id),
            "uav_id": str(uav["uav_id"]),
            "start_service_time": evaluation["start_service_time"],
            "arrival_time": evaluation["arrival_time"],
            "finish_time": evaluation["finish_time"],
            "on_time": evaluation["finish_time"] <= float(task["latest_finish"]) + 1e-9,
        }
        current_pos = (float(task["x"]), float(task["y"]))
        current_time = evaluation["finish_time"]
        distance_used += evaluation["travel_distance"]

    _return_to_nest(route, uav, nest, current_pos, distance_used)
    return {
        "feasible": True,
        "route": route,
        "served_updates": served_updates,
    }


def routes_to_dataframe(result: dict) -> pd.DataFrame:
    rows = []
    for route in result.get("routes", {}).values():
        rows.append(
            {
                "uav_id": route["uav_id"],
                "nest_id": route["nest_id"],
                "task_sequence": " -> ".join(route["task_sequence"]) if route["task_sequence"] else "(return only)",
                "task_count": len(route["task_sequence"]),
                "total_distance": round(route["total_distance"], 2),
                "total_service_time": round(route["total_service_time"], 2),
                "remaining_battery": round(route["remaining_battery"], 2),
            }
        )
    return pd.DataFrame(rows)


def stops_to_dataframe(result: dict) -> pd.DataFrame:
    rows = []
    for route in result.get("routes", {}).values():
        for stop in route.get("stops", []):
            rows.append(
                {
                    "uav_id": route["uav_id"],
                    "task_id": stop["task_id"],
                    "arrival_time": round(stop["arrival_time"], 2),
                    "start_service_time": round(stop["start_service_time"], 2),
                    "finish_time": round(stop["finish_time"], 2),
                    "x": round(stop["x"], 2),
                    "y": round(stop["y"], 2),
                }
            )
    return pd.DataFrame(rows)


def clone_result(result: dict) -> dict:
    return deepcopy(result)


def euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _select_candidate(
    algorithm_key: str,
    candidates: list[tuple[str, dict, dict]],
    weights: dict[str, float],
) -> tuple[str, dict, dict]:
    if algorithm_key == "nearest_neighbor":
        return min(candidates, key=lambda item: (item[2]["travel_distance"], item[1]["latest_finish"]))
    if algorithm_key == "priority_first":
        return min(
            candidates,
            key=lambda item: (
                -int(item[1]["priority"]),
                float(item[1]["latest_finish"]) - float(item[1]["earliest_start"]),
                item[2]["travel_distance"],
            ),
        )

    distances = [item[2]["travel_distance"] for item in candidates]
    slack_values = [max(0.0, item[2]["slack_after_finish"]) for item in candidates]
    energy_values = [item[2]["travel_distance"] + item[2]["return_distance"] for item in candidates]
    priorities = [float(item[1]["priority"]) for item in candidates]

    distance_norm = _normalize(distances)
    slack_norm = _normalize(slack_values)
    energy_norm = _normalize(energy_values)
    priority_norm = [value / 5.0 for value in priorities]

    scored = []
    for index, item in enumerate(candidates):
        score = (
            float(weights.get("w1", 0.35)) * distance_norm[index]
            + float(weights.get("w2", 0.25)) * slack_norm[index]
            - float(weights.get("w3", 0.25)) * priority_norm[index]
            + float(weights.get("w4", 0.15)) * energy_norm[index]
        )
        scored.append((score, item))
    return min(scored, key=lambda item: item[0])[1]


def _append_stop(route: dict, task: dict, evaluation: dict) -> None:
    route["task_sequence"].append(str(task["task_id"]))
    route["path"].append((float(task["x"]), float(task["y"])))
    route["stops"].append(
        {
            "task_id": str(task["task_id"]),
            "x": float(task["x"]),
            "y": float(task["y"]),
            "arrival_time": evaluation["arrival_time"],
            "start_service_time": evaluation["start_service_time"],
            "finish_time": evaluation["finish_time"],
            "travel_distance": evaluation["travel_distance"],
        }
    )
    route["total_service_time"] += float(task["service_time"])


def _return_to_nest(
    route: dict,
    uav: dict,
    nest: dict,
    current_pos: tuple[float, float],
    distance_used: float,
) -> None:
    nest_pos = (float(nest["x"]), float(nest["y"]))
    return_distance = euclidean(current_pos, nest_pos)
    route["total_distance"] = distance_used + return_distance
    route["remaining_battery"] = float(uav["battery_capacity"]) - route["total_distance"]
    if not route["path"] or route["path"][-1] != nest_pos:
        route["path"].append(nest_pos)


def _empty_route(uav: dict, nest: dict) -> dict:
    nest_pos = (float(nest["x"]), float(nest["y"]))
    return {
        "uav_id": str(uav["uav_id"]),
        "nest_id": str(uav["nest_id"]),
        "task_sequence": [],
        "path": [nest_pos],
        "stops": [],
        "total_distance": 0.0,
        "total_service_time": 0.0,
        "remaining_battery": float(uav["battery_capacity"]),
    }


def _records_by_id(df: pd.DataFrame, id_column: str) -> dict[str, dict]:
    return {str(row[id_column]): _row_to_dict(row) for _, row in df.iterrows()}


def _row_to_dict(row: pd.Series) -> dict:
    return {key: row[key] for key in row.index}


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if abs(high - low) < 1e-9:
        return [0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _normalize_algorithm_key(algorithm: str) -> str:
    value = str(algorithm).strip().lower()
    aliases = {
        "nearest": "nearest_neighbor",
        "nearest_neighbor": "nearest_neighbor",
        "nearest neighbor": "nearest_neighbor",
        "最近邻贪心": "nearest_neighbor",
        "priority": "priority_first",
        "priority_first": "priority_first",
        "priority first": "priority_first",
        "优先级优先": "priority_first",
        "weighted": "weighted",
        "weighted_heuristic": "weighted",
        "weighted heuristic": "weighted",
        "综合评分启发式": "weighted",
    }
    return aliases.get(value, "nearest_neighbor")

