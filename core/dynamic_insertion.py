from __future__ import annotations

from copy import deepcopy

import pandas as pd

from .algorithms import evaluate_fixed_route_sequence
from .data_generator import (
    generate_emergency_task,
    normalize_nest_dataframe,
    normalize_task_dataframe,
    normalize_uav_dataframe,
)
from .metrics import compare_plan_sequences


def insert_emergency_task(
    base_result: dict,
    tasks: pd.DataFrame,
    nests: pd.DataFrame,
    uavs: pd.DataFrame,
    emergency_task: pd.Series | dict,
    zones: list[dict] | None = None,
    lambda_delay: float = 0.5,
    lambda_disruption: float = 3.0,
    lambda_priority: float = 2.0,
) -> dict:
    tasks_df = normalize_task_dataframe(tasks)
    emergency = _series_to_dict(emergency_task)
    combined_tasks = pd.concat([tasks_df, pd.DataFrame([emergency])], ignore_index=True)
    combined_tasks = normalize_task_dataframe(combined_tasks)
    nests_df = normalize_nest_dataframe(nests)
    uavs_df = normalize_uav_dataframe(uavs)

    tasks_by_id = {str(row["task_id"]): _series_to_dict(row) for _, row in combined_tasks.iterrows()}
    nests_by_id = {str(row["nest_id"]): _series_to_dict(row) for _, row in nests_df.iterrows()}
    uavs_by_id = {str(row["uav_id"]): _series_to_dict(row) for _, row in uavs_df.iterrows()}

    best = None
    emergency_id = str(emergency["task_id"])

    for uav_id, route in base_result.get("routes", {}).items():
        uav = uavs_by_id.get(str(uav_id))
        if uav is None:
            continue
        nest = nests_by_id.get(str(uav["nest_id"]))
        if nest is None:
            continue
        original_sequence = list(route.get("task_sequence", []))
        for position in range(len(original_sequence) + 1):
            new_sequence = original_sequence[:position] + [emergency_id] + original_sequence[position:]
            evaluation = evaluate_fixed_route_sequence(uav, nest, tasks_by_id, new_sequence, zones=zones)
            if not evaluation.get("feasible"):
                continue

            new_route = evaluation["route"]
            extra_distance = float(new_route["total_distance"]) - float(route.get("total_distance", 0.0))
            additional_delay = _additional_delay(route, new_route)
            disrupted_tasks = max(0, len(original_sequence) - position)
            cost = (
                extra_distance
                + lambda_delay * additional_delay
                + lambda_disruption * disrupted_tasks
                - lambda_priority * float(emergency.get("priority", 5))
            )
            candidate = {
                "uav_id": str(uav_id),
                "insert_position": position + 1,
                "new_route": new_route,
                "served_updates": evaluation["served_updates"],
                "extra_distance": extra_distance,
                "additional_delay": additional_delay,
                "affected_tasks": disrupted_tasks,
                "cost": cost,
            }
            if best is None or candidate["cost"] < best["cost"]:
                best = candidate

    if best is None:
        return {
            "feasible": False,
            "message": "当前计划下无法可行插入，建议触发局部重优化。",
            "emergency_task": emergency,
        }

    updated = deepcopy(base_result)
    updated["routes"][best["uav_id"]] = best["new_route"]
    updated["served_tasks"].update(best["served_updates"])
    updated["unserved_tasks"] = [
        task_id for task_id in updated.get("unserved_tasks", []) if str(task_id) != emergency_id
    ]
    updated["algorithm"] = f"{base_result.get('algorithm', 'Algorithm')} + Dynamic Insertion"
    disruption = compare_plan_sequences(base_result, updated)
    response_time = (
        float(best["served_updates"][emergency_id]["start_service_time"])
        - float(emergency.get("emergency_release_time", emergency.get("earliest_start", 0.0)))
    )

    return {
        "feasible": True,
        "message": "突发任务已插入现有路径。",
        "updated_result": updated,
        "emergency_task": emergency,
        "uav_id": best["uav_id"],
        "insert_position": best["insert_position"],
        "extra_distance": round(best["extra_distance"], 2),
        "additional_delay": round(best["additional_delay"], 2),
        "affected_tasks": int(best["affected_tasks"]),
        "response_time": round(max(0.0, response_time), 2),
        "plan_disruption_degree": round(disruption, 4),
        "cost": round(best["cost"], 2),
    }


def generate_feasible_emergency_insertion(
    base_result: dict,
    tasks: pd.DataFrame,
    nests: pd.DataFrame,
    uavs: pd.DataFrame,
    map_size: float = 100.0,
    release_time: float = 60.0,
    random_seed: int = 42,
    zones: list[dict] | None = None,
    max_random_attempts: int = 30,
) -> tuple[pd.DataFrame, dict]:
    """Generate an emergency task that is useful for the insertion demo.

    The real insertion algorithm remains strict. This helper only improves the
    demo data source: it first tries random emergency points, then falls back to
    route-near candidates so the map visibly changes during a presentation.
    """
    best_random_pair = None
    for offset in range(max_random_attempts):
        emergency_df = generate_emergency_task(
            tasks,
            map_size=map_size,
            random_seed=random_seed + offset,
            release_time=release_time,
        )
        insertion = insert_emergency_task(base_result, tasks, nests, uavs, emergency_df.iloc[0], zones=zones)
        if insertion.get("feasible"):
            insertion["generated_by"] = "random_feasible"
            if best_random_pair is None or _demo_visibility_score(insertion) > _demo_visibility_score(best_random_pair[1]):
                best_random_pair = (emergency_df, insertion)

    if best_random_pair is not None and _demo_visibility_score(best_random_pair[1]) >= 20:
        return best_random_pair

    tasks_df = normalize_task_dataframe(tasks)
    next_id = _next_emergency_id(tasks_df)
    candidates = _route_near_emergency_candidates(
        base_result=base_result,
        tasks=tasks_df,
        next_id=next_id,
        release_time=release_time,
        map_size=map_size,
    )
    best_pair = None
    for candidate in candidates:
        emergency_df = pd.DataFrame([candidate])
        insertion = insert_emergency_task(base_result, tasks, nests, uavs, emergency_df.iloc[0], zones=zones)
        if not insertion.get("feasible"):
            continue
        if best_pair is None or _demo_visibility_score(insertion) > _demo_visibility_score(best_pair[1]):
            best_pair = (emergency_df, insertion)

    if best_pair is not None:
        best_pair[1]["generated_by"] = "route_near_feasible"
        return best_pair

    if best_random_pair is not None:
        return best_random_pair

    emergency_df = generate_emergency_task(
        tasks,
        map_size=map_size,
        random_seed=random_seed,
        release_time=release_time,
    )
    insertion = insert_emergency_task(base_result, tasks, nests, uavs, emergency_df.iloc[0], zones=zones)
    insertion["generated_by"] = "strict_random_infeasible"
    return emergency_df, insertion


def _additional_delay(old_route: dict, new_route: dict) -> float:
    old_starts = {stop["task_id"]: float(stop["start_service_time"]) for stop in old_route.get("stops", [])}
    delay = 0.0
    for stop in new_route.get("stops", []):
        task_id = stop["task_id"]
        if task_id in old_starts:
            delay += max(0.0, float(stop["start_service_time"]) - old_starts[task_id])
    return delay


def _series_to_dict(item) -> dict:
    if isinstance(item, dict):
        return dict(item)
    return {key: item[key] for key in item.index}


def _next_emergency_id(tasks_df: pd.DataFrame) -> str:
    existing = set(tasks_df["task_id"].astype(str))
    index = len(tasks_df) + 1
    task_id = f"E{index:03d}"
    while task_id in existing:
        index += 1
        task_id = f"E{index:03d}"
    return task_id


def _route_near_emergency_candidates(
    base_result: dict,
    tasks: pd.DataFrame,
    next_id: str,
    release_time: float,
    map_size: float,
) -> list[dict]:
    candidates = []
    task_lookup = {str(row["task_id"]): _series_to_dict(row) for _, row in tasks.iterrows()}
    for route in base_result.get("routes", {}).values():
        sequence = route.get("task_sequence", [])
        if not sequence:
            continue
        path = route.get("path", [])
        for index in range(1, max(1, len(path) - 1)):
            left = path[index]
            right = path[min(index + 1, len(path) - 1)]
            x = (float(left[0]) + float(right[0])) / 2
            y = (float(left[1]) + float(right[1])) / 2
            if index - 1 < len(sequence):
                near_task = task_lookup.get(str(sequence[index - 1]), {})
                x = (x + float(near_task.get("x", x))) / 2
                y = (y + float(near_task.get("y", y))) / 2
            for dx, dy in [(4, 3), (-4, 3), (3, -4), (-3, -4), (7, 0), (0, 7)]:
                candidates.append(
                    {
                        "task_id": next_id,
                        "x": round(_clip(x + dx, 4, map_size - 4), 2),
                        "y": round(_clip(y + dy, 4, map_size - 4), 2),
                        "task_type": "emergency",
                        "service_time": 5.0,
                        "earliest_start": round(float(release_time), 1),
                        "latest_finish": round(float(release_time) + 180.0, 1),
                        "priority": 5,
                        "payload_required": 0.5,
                        "quality_required": 0.95,
                        "is_emergency": True,
                        "emergency_release_time": round(float(release_time), 1),
                    }
                )
    return candidates


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _demo_visibility_score(insertion: dict) -> float:
    return float(insertion.get("extra_distance", 0.0)) + 45.0 * float(insertion.get("affected_tasks", 0))
