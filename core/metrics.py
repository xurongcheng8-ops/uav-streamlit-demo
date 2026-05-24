from __future__ import annotations

from typing import Dict

import pandas as pd

from .data_generator import normalize_task_dataframe, normalize_uav_dataframe


METRIC_COLUMNS = [
    "algorithm",
    "task_completion_rate",
    "high_priority_on_time_rate",
    "average_response_time",
    "total_flight_distance",
    "total_energy_consumption",
    "uav_utilization",
    "plan_disruption_degree",
    "algorithm_runtime",
]


def compute_schedule_metrics(
    tasks: pd.DataFrame,
    uavs: pd.DataFrame,
    result: dict,
    energy_per_distance: float = 1.0,
    planning_horizon: float | None = None,
    plan_disruption_degree: float = 0.0,
) -> Dict[str, float | str]:
    tasks_df = normalize_task_dataframe(tasks)
    uavs_df = normalize_uav_dataframe(uavs)
    served = result.get("served_tasks", {})
    served_count = len(served)
    total_tasks = len(tasks_df)

    high_tasks = tasks_df[tasks_df["priority"] >= 4]
    high_total = len(high_tasks)
    high_on_time = 0
    for task_id in high_tasks["task_id"].astype(str):
        if task_id in served and bool(served[task_id].get("on_time", False)):
            high_on_time += 1

    responses = []
    task_lookup = {str(row["task_id"]): row for _, row in tasks_df.iterrows()}
    for task_id, service in served.items():
        task = task_lookup.get(str(task_id))
        if task is None:
            continue
        release = (
            float(task["emergency_release_time"])
            if bool(task["is_emergency"]) and pd.notna(task["emergency_release_time"])
            else float(task["earliest_start"])
        )
        responses.append(max(0.0, float(service["start_service_time"]) - release))

    total_distance = sum(float(route.get("total_distance", 0.0)) for route in result.get("routes", {}).values())
    total_service_time = sum(
        float(route.get("total_service_time", 0.0)) for route in result.get("routes", {}).values()
    )
    if planning_horizon is None:
        planning_horizon = max(float(tasks_df["latest_finish"].max()), 1.0)
    utilization_denominator = max(1.0, float(len(uavs_df)) * float(planning_horizon))

    return {
        "algorithm": result.get("algorithm", "Algorithm"),
        "task_completion_rate": _safe_rate(served_count, total_tasks),
        "high_priority_on_time_rate": _safe_rate(high_on_time, high_total),
        "average_response_time": round(sum(responses) / len(responses), 2) if responses else 0.0,
        "total_flight_distance": round(total_distance, 2),
        "total_energy_consumption": round(total_distance * float(energy_per_distance), 2),
        "uav_utilization": round(total_service_time / utilization_denominator, 4),
        "plan_disruption_degree": round(float(plan_disruption_degree), 4),
        "algorithm_runtime": round(float(result.get("runtime", 0.0)), 4),
    }


def compare_plan_sequences(before_result: dict, after_result: dict) -> float:
    before_positions = _task_positions(before_result)
    after_positions = _task_positions(after_result)
    if not before_positions:
        return 0.0
    changed = 0
    for task_id, position in before_positions.items():
        if after_positions.get(task_id) != position:
            changed += 1
    return changed / len(before_positions)


def metrics_dataframe(metrics_by_algorithm: dict[str, Dict]) -> pd.DataFrame:
    rows = []
    for key, metrics in metrics_by_algorithm.items():
        row = dict(metrics)
        row["algorithm_key"] = key
        rows.append(row)
    df = pd.DataFrame(rows)
    for column in METRIC_COLUMNS:
        if column not in df.columns:
            df[column] = 0
    return df[["algorithm_key"] + METRIC_COLUMNS]


def _task_positions(result: dict) -> dict[str, tuple[str, int]]:
    positions = {}
    for uav_id, route in result.get("routes", {}).items():
        for index, task_id in enumerate(route.get("task_sequence", [])):
            positions[str(task_id)] = (str(uav_id), index)
    return positions


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)

