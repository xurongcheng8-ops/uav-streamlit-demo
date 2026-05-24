from __future__ import annotations

import math
import time
from copy import deepcopy
from heapq import heappop, heappush
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
    zones: list[dict] | None = None,
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
                evaluation = evaluate_candidate(
                    uav,
                    nest,
                    task,
                    current_pos,
                    current_time,
                    distance_used,
                    zones=zones,
                )
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

        _return_to_nest(route, uav, nest, current_pos, distance_used, zones=zones)
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
    zones: list[dict] | None = None,
) -> dict[str, dict]:
    return {
        key: run_dispatch_algorithm(key, tasks, nests, uavs, weights=weights, zones=zones)
        for key in ["nearest_neighbor", "priority_first", "weighted"]
    }


def evaluate_candidate(
    uav: dict,
    nest: dict,
    task: dict,
    current_pos: tuple[float, float],
    current_time: float,
    distance_used: float,
    zones: list[dict] | None = None,
) -> dict:
    if float(task["payload_required"]) > float(uav["payload_capacity"]):
        return {"feasible": False, "reason": "payload"}

    task_pos = (float(task["x"]), float(task["y"]))
    nest_pos = (float(nest["x"]), float(nest["y"]))
    travel_path, travel_distance = _safe_path_between(current_pos, task_pos, zones)
    return_path, return_distance = _safe_path_between(task_pos, nest_pos, zones)
    if not travel_path or not return_path:
        return {"feasible": False, "reason": "no_fly_zone"}
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
        "travel_path": travel_path,
        "return_path": return_path,
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
    zones: list[dict] | None = None,
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
        evaluation = evaluate_candidate(uav, nest, task, current_pos, current_time, distance_used, zones=zones)
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

    _return_to_nest(route, uav, nest, current_pos, distance_used, zones=zones)
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
    _extend_path(route["path"], evaluation.get("travel_path", [(float(task["x"]), float(task["y"]))]))
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
    zones: list[dict] | None = None,
) -> None:
    nest_pos = (float(nest["x"]), float(nest["y"]))
    return_path, return_distance = _safe_path_between(current_pos, nest_pos, zones)
    if not return_path:
        return_path = [current_pos, nest_pos]
        return_distance = euclidean(current_pos, nest_pos)
    route["total_distance"] = distance_used + return_distance
    route["remaining_battery"] = float(uav["battery_capacity"]) - route["total_distance"]
    _extend_path(route["path"], return_path)


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


def _extend_path(route_path: list[tuple[float, float]], segment_path: list[tuple[float, float]]) -> None:
    if not segment_path:
        return
    for point in segment_path:
        normalized = (float(point[0]), float(point[1]))
        if route_path and euclidean(route_path[-1], normalized) < 1e-9:
            continue
        route_path.append(normalized)


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


def _segment_hits_no_fly_zone(
    start: tuple[float, float],
    end: tuple[float, float],
    zones: list[dict] | None,
) -> bool:
    for zone in zones or []:
        if zone.get("zone_type") not in {"no_fly", "禁飞区"}:
            continue
        if zone.get("shape") == "rect" and _segment_intersects_rect(start, end, zone):
            return True
        if zone.get("shape") == "circle" and _segment_intersects_circle(start, end, zone):
            return True
    return False


def _safe_path_between(
    start: tuple[float, float],
    end: tuple[float, float],
    zones: list[dict] | None,
) -> tuple[list[tuple[float, float]], float]:
    start = (float(start[0]), float(start[1]))
    end = (float(end[0]), float(end[1]))
    no_fly_zones = _no_fly_zones(zones)
    if not no_fly_zones:
        return [start, end], euclidean(start, end)
    if not _segment_hits_no_fly_zone(start, end, no_fly_zones):
        return [start, end], euclidean(start, end)

    nodes = [start, end]
    for vertex in _obstacle_visibility_vertices(no_fly_zones):
        if not _point_hits_no_fly_zone(vertex, no_fly_zones):
            nodes.append(vertex)
    nodes = _dedupe_points(nodes)
    start_index = 0
    end_index = 1

    adjacency: list[list[tuple[int, float]]] = [[] for _ in nodes]
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if _segment_hits_no_fly_zone(nodes[i], nodes[j], no_fly_zones):
                continue
            length = euclidean(nodes[i], nodes[j])
            adjacency[i].append((j, length))
            adjacency[j].append((i, length))

    distances = [math.inf] * len(nodes)
    previous: list[int | None] = [None] * len(nodes)
    distances[start_index] = 0.0
    heap = [(0.0, start_index)]
    while heap:
        current_distance, node_index = heappop(heap)
        if current_distance > distances[node_index] + 1e-9:
            continue
        if node_index == end_index:
            break
        for next_index, edge_length in adjacency[node_index]:
            candidate = current_distance + edge_length
            if candidate + 1e-9 < distances[next_index]:
                distances[next_index] = candidate
                previous[next_index] = node_index
                heappush(heap, (candidate, next_index))

    if math.isinf(distances[end_index]):
        return [], math.inf

    path_indices = []
    cursor: int | None = end_index
    while cursor is not None:
        path_indices.append(cursor)
        cursor = previous[cursor]
    path_indices.reverse()
    return [nodes[index] for index in path_indices], distances[end_index]


def _no_fly_zones(zones: list[dict] | None) -> list[dict]:
    return [zone for zone in zones or [] if zone.get("zone_type") in {"no_fly", "禁飞区"}]


def _point_hits_no_fly_zone(point: tuple[float, float], zones: list[dict] | None) -> bool:
    for zone in zones or []:
        if zone.get("shape") == "rect":
            x0 = float(zone["x0"])
            y0 = float(zone["y0"])
            x1 = float(zone["x1"])
            y1 = float(zone["y1"])
            xmin, xmax = sorted([x0, x1])
            ymin, ymax = sorted([y0, y1])
            if _point_in_rect(point, xmin, xmax, ymin, ymax):
                return True
        elif zone.get("shape") == "circle":
            center = (float(zone["cx"]), float(zone["cy"]))
            if euclidean(point, center) <= float(zone["r"]) + 1e-9:
                return True
    return False


def _obstacle_visibility_vertices(zones: list[dict]) -> list[tuple[float, float]]:
    vertices: list[tuple[float, float]] = []
    for zone in zones:
        if zone.get("shape") == "rect":
            margin = float(zone.get("safety_margin", 3.0))
            x0 = float(zone["x0"])
            y0 = float(zone["y0"])
            x1 = float(zone["x1"])
            y1 = float(zone["y1"])
            xmin, xmax = sorted([x0, x1])
            ymin, ymax = sorted([y0, y1])
            vertices.extend(
                [
                    (xmin - margin, ymin - margin),
                    (xmin - margin, ymax + margin),
                    (xmax + margin, ymin - margin),
                    (xmax + margin, ymax + margin),
                    ((xmin + xmax) / 2, ymin - margin),
                    ((xmin + xmax) / 2, ymax + margin),
                    (xmin - margin, (ymin + ymax) / 2),
                    (xmax + margin, (ymin + ymax) / 2),
                ]
            )
        elif zone.get("shape") == "circle":
            margin = float(zone.get("safety_margin", 3.0))
            cx = float(zone["cx"])
            cy = float(zone["cy"])
            radius = float(zone["r"]) + margin
            for index in range(12):
                angle = 2 * math.pi * index / 12
                vertices.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return vertices


def _dedupe_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    seen = set()
    deduped = []
    for x, y in points:
        key = (round(float(x), 6), round(float(y), 6))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((float(x), float(y)))
    return deduped


def _segment_intersects_rect(start: tuple[float, float], end: tuple[float, float], zone: dict) -> bool:
    x0 = float(zone["x0"])
    y0 = float(zone["y0"])
    x1 = float(zone["x1"])
    y1 = float(zone["y1"])
    xmin, xmax = sorted([x0, x1])
    ymin, ymax = sorted([y0, y1])
    if _point_in_rect(start, xmin, xmax, ymin, ymax) or _point_in_rect(end, xmin, xmax, ymin, ymax):
        return True
    rect_edges = [
        ((xmin, ymin), (xmax, ymin)),
        ((xmax, ymin), (xmax, ymax)),
        ((xmax, ymax), (xmin, ymax)),
        ((xmin, ymax), (xmin, ymin)),
    ]
    return any(_segments_intersect(start, end, edge_start, edge_end) for edge_start, edge_end in rect_edges)


def _segment_intersects_circle(start: tuple[float, float], end: tuple[float, float], zone: dict) -> bool:
    center = (float(zone["cx"]), float(zone["cy"]))
    radius = float(zone["r"])
    return _distance_point_to_segment(center, start, end) <= radius + 1e-9


def _point_in_rect(point: tuple[float, float], xmin: float, xmax: float, ymin: float, ymax: float) -> bool:
    return xmin <= float(point[0]) <= xmax and ymin <= float(point[1]) <= ymax


def _segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    def orient(p, q, r) -> float:
        return (float(q[1]) - float(p[1])) * (float(r[0]) - float(q[0])) - (
            float(q[0]) - float(p[0])
        ) * (float(r[1]) - float(q[1]))

    def on_segment(p, q, r) -> bool:
        return (
            min(float(p[0]), float(r[0])) - 1e-9 <= float(q[0]) <= max(float(p[0]), float(r[0])) + 1e-9
            and min(float(p[1]), float(r[1])) - 1e-9 <= float(q[1]) <= max(float(p[1]), float(r[1])) + 1e-9
        )

    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    if abs(o1) < 1e-9 and on_segment(a, c, b):
        return True
    if abs(o2) < 1e-9 and on_segment(a, d, b):
        return True
    if abs(o3) < 1e-9 and on_segment(c, a, d):
        return True
    if abs(o4) < 1e-9 and on_segment(c, b, d):
        return True
    return False


def _distance_point_to_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = float(point[0]), float(point[1])
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    dx, dy = ex - sx, ey - sy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return euclidean(point, start)
    t = ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    projection = (sx + t * dx, sy + t * dy)
    return euclidean(point, projection)


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
