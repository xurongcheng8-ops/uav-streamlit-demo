from __future__ import annotations

import random
from typing import Iterable

import pandas as pd


TASK_COLUMNS = [
    "task_id",
    "x",
    "y",
    "task_type",
    "service_time",
    "earliest_start",
    "latest_finish",
    "priority",
    "payload_required",
    "quality_required",
    "is_emergency",
]

OPTIONAL_TASK_COLUMNS = ["emergency_release_time"]

NEST_COLUMNS = ["nest_id", "x", "y", "capacity"]

UAV_COLUMNS = [
    "uav_id",
    "nest_id",
    "speed",
    "battery_capacity",
    "max_range",
    "payload_capacity",
    "safety_battery",
]

TASK_TYPES = ["river", "traffic", "parking", "infrastructure", "fire", "emergency"]
NORMAL_TASK_TYPES = ["river", "traffic", "parking", "infrastructure"]
EMERGENCY_TASK_TYPES = ["fire", "emergency"]


def generate_nests(
    nest_count: int = 3,
    map_size: float = 100.0,
    random_seed: int = 42,
) -> pd.DataFrame:
    rng = random.Random(random_seed)
    nest_count = max(1, int(nest_count))
    center = map_size / 2
    radius = map_size * 0.36
    rows = []
    for idx in range(nest_count):
        if nest_count == 1:
            x, y = center, center
        else:
            angle = 2 * 3.141592653589793 * idx / nest_count - 3.141592653589793 / 2
            x = center + radius * _cos(angle) + rng.uniform(-4, 4)
            y = center + radius * _sin(angle) + rng.uniform(-4, 4)
        rows.append(
            {
                "nest_id": f"N{idx + 1:02d}",
                "x": round(_clip(x, 5, map_size - 5), 2),
                "y": round(_clip(y, 5, map_size - 5), 2),
                "capacity": 1,
            }
        )
    return pd.DataFrame(rows, columns=NEST_COLUMNS)


def generate_uavs(
    nests: pd.DataFrame,
    random_seed: int = 42,
) -> pd.DataFrame:
    rng = random.Random(random_seed + 101)
    rows = []
    uav_index = 1
    for _, nest in nests.iterrows():
        capacity = int(nest.get("capacity", 1))
        for _ in range(max(1, capacity)):
            rows.append(
                {
                    "uav_id": f"UAV-{uav_index:02d}",
                    "nest_id": nest["nest_id"],
                    "speed": round(rng.uniform(1.2, 1.8), 2),
                    "battery_capacity": round(rng.uniform(230, 270), 1),
                    "max_range": round(rng.uniform(205, 245), 1),
                    "payload_capacity": round(rng.uniform(1.8, 3.2), 1),
                    "safety_battery": round(rng.uniform(18, 26), 1),
                }
            )
            uav_index += 1
    return pd.DataFrame(rows, columns=UAV_COLUMNS)


def generate_tasks(
    task_count: int = 30,
    map_size: float = 100.0,
    high_priority_ratio: float = 0.2,
    time_window_tightness: str = "medium",
    emergency_count: int = 0,
    random_seed: int = 42,
) -> pd.DataFrame:
    rng = random.Random(random_seed + 202)
    task_count = max(1, int(task_count))
    emergency_count = max(0, min(int(emergency_count), task_count))
    high_priority_ratio = _clip(float(high_priority_ratio), 0, 1)

    rows = []
    emergency_indices = set(rng.sample(range(task_count), emergency_count)) if emergency_count else set()
    for idx in range(task_count):
        is_emergency = idx in emergency_indices
        is_high = is_emergency or rng.random() < high_priority_ratio
        priority = rng.randint(4, 5) if is_high else rng.randint(1, 3)
        task_type = rng.choice(EMERGENCY_TASK_TYPES if is_emergency else NORMAL_TASK_TYPES)

        earliest = rng.uniform(0, 120)
        window = _window_width(rng, time_window_tightness)
        service_time = rng.uniform(5, 14)
        latest = earliest + window
        release_time = earliest if is_emergency else None

        rows.append(
            {
                "task_id": f"T{idx + 1:03d}",
                "x": round(rng.uniform(4, map_size - 4), 2),
                "y": round(rng.uniform(4, map_size - 4), 2),
                "task_type": task_type,
                "service_time": round(service_time, 1),
                "earliest_start": round(earliest, 1),
                "latest_finish": round(latest, 1),
                "priority": int(priority),
                "payload_required": round(rng.uniform(0.4, 2.4), 1),
                "quality_required": round(rng.uniform(0.65, 0.98), 2),
                "is_emergency": bool(is_emergency),
                "emergency_release_time": round(release_time, 1) if release_time is not None else None,
            }
        )
    return pd.DataFrame(rows, columns=TASK_COLUMNS + OPTIONAL_TASK_COLUMNS)


def generate_zones(map_size: float = 100.0, random_seed: int = 42) -> list[dict]:
    rng = random.Random(random_seed + 303)
    scale = float(map_size) / 100.0
    return [
        {
            "zone_id": "NFZ-01",
            "zone_type": "no_fly",
            "name": "政务核心禁飞区",
            "shape": "rect",
            "x0": round(43 * scale, 2),
            "y0": round(43 * scale, 2),
            "x1": round(60 * scale, 2),
            "y1": round(58 * scale, 2),
            "color": "rgba(255, 91, 115, 0.18)",
            "line": "#ff5b73",
        },
        {
            "zone_id": "NFZ-02",
            "zone_type": "no_fly",
            "name": "临时活动禁飞区",
            "shape": "rect",
            "x0": round((20 + rng.uniform(-2, 2)) * scale, 2),
            "y0": round((30 + rng.uniform(-2, 2)) * scale, 2),
            "x1": round((34 + rng.uniform(-2, 2)) * scale, 2),
            "y1": round((48 + rng.uniform(-2, 2)) * scale, 2),
            "color": "rgba(255, 91, 115, 0.14)",
            "line": "#ff7b8e",
        },
        {
            "zone_id": "RISK-01",
            "zone_type": "risk",
            "name": "高楼风切变风险区",
            "shape": "circle",
            "cx": round(74 * scale, 2),
            "cy": round(49 * scale, 2),
            "r": round(8 * scale, 2),
            "color": "rgba(255, 180, 76, 0.16)",
            "line": "#ffb44c",
        },
    ]


def generate_emergency_task(
    existing_tasks: pd.DataFrame,
    map_size: float = 100.0,
    random_seed: int = 42,
    release_time: float = 60.0,
) -> pd.DataFrame:
    rng = random.Random(random_seed + 909)
    next_index = len(existing_tasks) + 1
    existing_ids = set(existing_tasks.get("task_id", pd.Series(dtype=str)).astype(str))
    task_id = f"E{next_index:03d}"
    while task_id in existing_ids:
        next_index += 1
        task_id = f"E{next_index:03d}"
    row = {
        "task_id": task_id,
        "x": round(rng.uniform(8, map_size - 8), 2),
        "y": round(rng.uniform(8, map_size - 8), 2),
        "task_type": rng.choice(EMERGENCY_TASK_TYPES),
        "service_time": 8.0,
        "earliest_start": round(release_time, 1),
        "latest_finish": round(release_time + 120, 1),
        "priority": 5,
        "payload_required": 0.8,
        "quality_required": 0.95,
        "is_emergency": True,
        "emergency_release_time": round(release_time, 1),
    }
    return pd.DataFrame([row], columns=TASK_COLUMNS + OPTIONAL_TASK_COLUMNS)


def validate_columns(df: pd.DataFrame, required_columns: Iterable[str]) -> list[str]:
    columns = set(df.columns)
    return [column for column in required_columns if column not in columns]


def normalize_task_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    missing = validate_columns(normalized, TASK_COLUMNS)
    if missing:
        raise ValueError(f"Task CSV missing required columns: {', '.join(missing)}")
    if "emergency_release_time" not in normalized.columns:
        normalized["emergency_release_time"] = None
    numeric_columns = [
        "x",
        "y",
        "service_time",
        "earliest_start",
        "latest_finish",
        "priority",
        "payload_required",
        "quality_required",
        "emergency_release_time",
    ]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized["priority"] = normalized["priority"].fillna(1).clip(1, 5).astype(int)
    normalized["is_emergency"] = normalized["is_emergency"].map(_to_bool)
    normalized["task_id"] = normalized["task_id"].astype(str)
    normalized["task_type"] = normalized["task_type"].astype(str)
    normalized["emergency_release_time"] = normalized["emergency_release_time"].where(
        normalized["emergency_release_time"].notna(),
        normalized["earliest_start"],
    )
    return normalized[TASK_COLUMNS + OPTIONAL_TASK_COLUMNS]


def normalize_nest_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    missing = validate_columns(normalized, NEST_COLUMNS)
    if missing:
        raise ValueError(f"Nest CSV missing required columns: {', '.join(missing)}")
    for column in ["x", "y", "capacity"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized["capacity"] = normalized["capacity"].fillna(1).astype(int).clip(lower=1)
    normalized["nest_id"] = normalized["nest_id"].astype(str)
    return normalized[NEST_COLUMNS]


def normalize_uav_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    missing = validate_columns(normalized, UAV_COLUMNS)
    if missing:
        raise ValueError(f"UAV CSV missing required columns: {', '.join(missing)}")
    for column in ["speed", "battery_capacity", "max_range", "payload_capacity", "safety_battery"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized["uav_id"] = normalized["uav_id"].astype(str)
    normalized["nest_id"] = normalized["nest_id"].astype(str)
    return normalized[UAV_COLUMNS]


def build_sample_dataset(
    task_count: int = 30,
    nest_count: int = 3,
    map_size: float = 100.0,
    high_priority_ratio: float = 0.2,
    time_window_tightness: str = "medium",
    emergency_count: int = 0,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nests = generate_nests(nest_count=nest_count, map_size=map_size, random_seed=random_seed)
    uavs = generate_uavs(nests, random_seed=random_seed)
    tasks = generate_tasks(
        task_count=task_count,
        map_size=map_size,
        high_priority_ratio=high_priority_ratio,
        time_window_tightness=time_window_tightness,
        emergency_count=emergency_count,
        random_seed=random_seed,
    )
    return tasks, nests, uavs


def _window_width(rng: random.Random, tightness: str) -> float:
    mapping = {
        "loose": (150, 230),
        "medium": (90, 155),
        "tight": (48, 92),
        "宽松": (150, 230),
        "中等": (90, 155),
        "紧张": (48, 92),
    }
    low, high = mapping.get(str(tightness).lower(), mapping["medium"])
    return rng.uniform(low, high)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是", "emergency"}


def _sin(angle: float) -> float:
    # Importing math locally keeps this module easy to read in Streamlit reloads.
    import math

    return math.sin(angle)


def _cos(angle: float) -> float:
    import math

    return math.cos(angle)
