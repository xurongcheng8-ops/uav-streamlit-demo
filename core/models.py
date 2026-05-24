from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Nest:
    nest_id: str
    x: float
    y: float
    capacity: int = 1


@dataclass(frozen=True)
class UAV:
    uav_id: str
    nest_id: str
    speed: float
    battery_capacity: float
    max_range: float
    payload_capacity: float
    safety_battery: float


@dataclass(frozen=True)
class Task:
    task_id: str
    x: float
    y: float
    task_type: str
    service_time: float
    earliest_start: float
    latest_finish: float
    priority: int
    payload_required: float
    quality_required: float
    is_emergency: bool = False
    emergency_release_time: float | None = None


@dataclass
class RouteStop:
    task_id: str
    x: float
    y: float
    arrival_time: float
    start_service_time: float
    finish_time: float
    travel_distance: float


@dataclass
class UAVRoute:
    uav_id: str
    nest_id: str
    task_sequence: List[str]
    path: List[Tuple[float, float]]
    stops: List[RouteStop]
    total_distance: float
    total_service_time: float
    remaining_battery: float


def dataclass_to_dict(item) -> Dict:
    return asdict(item)

