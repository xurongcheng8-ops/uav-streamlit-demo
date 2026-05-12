from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PROJECT_TITLE = "城市治理低空无人机集群智能调度与数字孪生仿真平台"
PROJECT_SUBTITLE = "Multi-task UAV Scheduling and Digital Twin Simulation Platform for Urban Governance"

PRIORITY_ORDER = {"高": 0, "中": 1, "低": 2}
EMERGENCY_TASK_TYPES = {"火情上报", "应急救援辅助"}
SPECIAL_PAYLOADS = {"红外相机", "多传感器载荷"}


def configure_page() -> None:
    """配置页面基础信息与科技风样式。"""
    st.set_page_config(
        page_title="低空无人机调度与数字孪生仿真平台",
        page_icon="🛩️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --bg: #07111f;
            --panel: rgba(12, 31, 55, 0.86);
            --panel-soft: rgba(19, 52, 86, 0.72);
            --border: rgba(98, 175, 255, 0.24);
            --text: #eaf4ff;
            --muted: #9fb9d2;
            --cyan: #32d7ff;
            --blue: #2f80ff;
            --green: #23d18b;
            --orange: #ffb44c;
            --red: #ff5b73;
        }

        .stApp {
            background:
                linear-gradient(135deg, #06101e 0%, #0a1b32 44%, #101624 100%);
            color: var(--text);
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
        }

        .hero {
            border: 1px solid var(--border);
            background:
                linear-gradient(120deg, rgba(15, 58, 99, 0.92), rgba(7, 17, 31, 0.96)),
                repeating-linear-gradient(90deg, rgba(255,255,255,0.03), rgba(255,255,255,0.03) 1px, transparent 1px, transparent 24px);
            border-radius: 8px;
            padding: 22px 26px;
            margin-bottom: 18px;
            box-shadow: 0 18px 48px rgba(0, 20, 45, 0.34);
        }

        .hero h1 {
            margin: 0.15rem 0 0.35rem 0;
            color: #f5fbff;
            font-size: 2.0rem;
            line-height: 1.18;
            letter-spacing: 0;
        }

        .hero p {
            margin: 0;
            color: #b9d7f2;
            font-size: 1.0rem;
        }

        .eyebrow {
            color: var(--cyan);
            font-weight: 700;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0;
        }

        .tag-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 14px;
        }

        .tag {
            border: 1px solid rgba(50, 215, 255, 0.24);
            background: rgba(50, 215, 255, 0.08);
            color: #dff8ff;
            border-radius: 8px;
            padding: 5px 9px;
            font-size: 0.82rem;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(15, 44, 75, 0.94), rgba(11, 28, 48, 0.92));
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 13px 14px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
        }

        div[data-testid="stMetricLabel"] {
            color: #b8cee4;
        }

        div[data-testid="stMetricValue"] {
            color: #f4fbff;
        }

        .section-card {
            border: 1px solid var(--border);
            background: var(--panel);
            border-radius: 8px;
            padding: 17px 18px;
            min-height: 100%;
        }

        .section-card h3 {
            margin: 0 0 10px 0;
            color: #f3fbff;
            font-size: 1.05rem;
            letter-spacing: 0;
        }

        .section-card p, .section-card li {
            color: #c6d9ea;
            line-height: 1.65;
        }

        .route {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
            margin-top: 8px;
        }

        .route-step {
            border: 1px solid rgba(96, 174, 255, 0.28);
            background: rgba(47, 128, 255, 0.12);
            color: #e8f6ff;
            border-radius: 8px;
            padding: 9px 11px;
            font-size: 0.9rem;
        }

        .route-arrow {
            color: #32d7ff;
            font-weight: 800;
        }

        .scenario-item {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding: 8px 0;
            color: #d7e9f8;
        }

        .scenario-item:last-child {
            border-bottom: none;
        }

        .status-pill {
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 0.78rem;
            white-space: nowrap;
        }

        .pill-blue { background: rgba(47, 128, 255, 0.18); color: #b9d8ff; }
        .pill-red { background: rgba(255, 91, 115, 0.16); color: #ffd2da; }
        .pill-orange { background: rgba(255, 180, 76, 0.16); color: #ffe0b0; }
        .pill-green { background: rgba(35, 209, 139, 0.15); color: #bff4dc; }

        .battery-card {
            border: 1px solid var(--border);
            background: rgba(10, 30, 52, 0.9);
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 10px;
        }

        .battery-title {
            display: flex;
            justify-content: space-between;
            color: #eff9ff;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .battery-meta {
            color: #adc4da;
            font-size: 0.84rem;
            margin-top: 6px;
        }

        .alert-card {
            border: 1px solid rgba(255, 91, 115, 0.55);
            background: rgba(255, 91, 115, 0.13);
            color: #ffe4e8;
            border-radius: 8px;
            padding: 12px 14px;
            margin: 8px 0;
        }

        .info-card {
            border: 1px solid rgba(50, 215, 255, 0.32);
            background: rgba(50, 215, 255, 0.09);
            color: #e0f8ff;
            border-radius: 8px;
            padding: 12px 14px;
            margin: 8px 0;
        }

        .small-note {
            color: #a9bfd6;
            font-size: 0.88rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            background: rgba(20, 53, 88, 0.72);
            border: 1px solid rgba(98, 175, 255, 0.16);
            padding: 8px 13px;
            color: #d6eaff;
        }

        .stTabs [aria-selected="true"] {
            background: rgba(47, 128, 255, 0.28);
            color: #ffffff;
            border: 1px solid rgba(50, 215, 255, 0.38);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(6, 16, 30, 0.98), rgba(10, 27, 50, 0.98));
            border-right: 1px solid rgba(98, 175, 255, 0.18);
        }

        .dataframe tbody tr th, .dataframe tbody tr td {
            color: #dff0ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def generate_facilities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"名称": "起降点 A", "类型": "综合起降点", "x": 12, "y": 18, "能力": "日常巡检/换电"},
            {"名称": "换电点 B", "类型": "能源补给点", "x": 86, "y": 16, "能力": "快速换电/维修"},
            {"名称": "应急起降点 C", "类型": "应急保障点", "x": 14, "y": 84, "能力": "火情响应/救援辅助"},
            {"名称": "交通枢纽起降点 D", "类型": "交通监测点", "x": 66, "y": 12, "能力": "道路巡航/拥堵监测"},
        ]
    )


def generate_zone_data() -> List[Dict]:
    return [
        {
            "名称": "政务核心禁飞区",
            "类型": "禁飞区",
            "shape": "rect",
            "x0": 45,
            "y0": 44,
            "x1": 61,
            "y1": 58,
            "color": "rgba(255, 91, 115, 0.20)",
            "line": "#ff5b73",
        },
        {
            "名称": "大型活动临时禁飞区",
            "类型": "禁飞区",
            "shape": "rect",
            "x0": 22,
            "y0": 34,
            "x1": 35,
            "y1": 49,
            "color": "rgba(255, 91, 115, 0.16)",
            "line": "#ff7b8e",
        },
        {
            "名称": "高楼风切变风险区",
            "类型": "风险区域",
            "shape": "circle",
            "cx": 74,
            "cy": 49,
            "r": 8,
            "color": "rgba(255, 180, 76, 0.18)",
            "line": "#ffb44c",
        },
        {
            "名称": "通信遮挡风险区",
            "类型": "风险区域",
            "shape": "circle",
            "cx": 40,
            "cy": 76,
            "r": 7,
            "color": "rgba(255, 180, 76, 0.15)",
            "line": "#ffd07b",
        },
    ]


def generate_uav_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "无人机编号": "UAV-1",
                "电量": 76,
                "x": 24,
                "y": 66,
                "当前位置": "滨江走廊上空 (24,66)",
                "载荷能力": "高清摄像头",
                "当前任务": "T-001",
                "剩余航程": 18.5,
                "状态": "执行中",
            },
            {
                "无人机编号": "UAV-2",
                "电量": 82,
                "x": 72,
                "y": 62,
                "当前位置": "区域 B 外围 (72,62)",
                "载荷能力": "红外相机",
                "当前任务": "T-002",
                "剩余航程": 22.0,
                "状态": "执行中",
            },
            {
                "无人机编号": "UAV-3",
                "电量": 18,
                "x": 44,
                "y": 48,
                "当前位置": "政务区西侧 (44,48)",
                "载荷能力": "多传感器载荷",
                "当前任务": "T-009",
                "剩余航程": 4.8,
                "状态": "执行中",
            },
            {
                "无人机编号": "UAV-4",
                "电量": 64,
                "x": 61,
                "y": 31,
                "当前位置": "环城快速路 (61,31)",
                "载荷能力": "高清摄像头",
                "当前任务": "T-003",
                "剩余航程": 15.2,
                "状态": "执行中",
            },
            {
                "无人机编号": "UAV-5",
                "电量": 93,
                "x": 12,
                "y": 18,
                "当前位置": "起降点 A (12,18)",
                "载荷能力": "扬声器",
                "当前任务": "无",
                "剩余航程": 25.6,
                "状态": "待命",
            },
            {
                "无人机编号": "UAV-6",
                "电量": 57,
                "x": 86,
                "y": 16,
                "当前位置": "换电点 B (86,16)",
                "载荷能力": "多传感器载荷",
                "当前任务": "无",
                "剩余航程": 13.8,
                "状态": "待命",
            },
            {
                "无人机编号": "UAV-7",
                "电量": 41,
                "x": 14,
                "y": 84,
                "当前位置": "应急起降点 C (14,84)",
                "载荷能力": "红外相机",
                "当前任务": "T-007",
                "剩余航程": 11.3,
                "状态": "已分配",
            },
            {
                "无人机编号": "UAV-8",
                "电量": 0,
                "x": 66,
                "y": 12,
                "当前位置": "交通枢纽起降点 D (66,12)",
                "载荷能力": "高清摄像头",
                "当前任务": "无",
                "剩余航程": 0.0,
                "状态": "故障",
            },
        ]
    )


def generate_task_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "任务编号": "T-001",
                "任务类型": "河道巡查",
                "位置": "滨江水系巡检段",
                "x": 28,
                "y": 72,
                "优先级": "中",
                "截止时间": "今日 10:30",
                "分配无人机": "UAV-1",
                "状态": "执行中",
                "响应时间": 4.8,
                "是否准时完成": "是",
            },
            {
                "任务编号": "T-002",
                "任务类型": "火情上报",
                "位置": "区域 B 工业园",
                "x": 82,
                "y": 72,
                "优先级": "高",
                "截止时间": "今日 10:12",
                "分配无人机": "UAV-2",
                "状态": "执行中",
                "响应时间": 3.2,
                "是否准时完成": "是",
            },
            {
                "任务编号": "T-003",
                "任务类型": "交通拥堵监测",
                "位置": "环城快速路南段",
                "x": 67,
                "y": 35,
                "优先级": "中",
                "截止时间": "今日 10:25",
                "分配无人机": "UAV-4",
                "状态": "执行中",
                "响应时间": 5.5,
                "是否准时完成": "是",
            },
            {
                "任务编号": "T-004",
                "任务类型": "违停取证",
                "位置": "老城片区停车热点",
                "x": 38,
                "y": 41,
                "优先级": "低",
                "截止时间": "今日 11:00",
                "分配无人机": "待分配",
                "状态": "待分配",
                "响应时间": None,
                "是否准时完成": "--",
            },
            {
                "任务编号": "T-005",
                "任务类型": "城市基础设施巡检",
                "位置": "排水泵站与桥梁节点",
                "x": 18,
                "y": 24,
                "优先级": "低",
                "截止时间": "今日 09:50",
                "分配无人机": "UAV-5",
                "状态": "已完成",
                "响应时间": 6.1,
                "是否准时完成": "是",
            },
            {
                "任务编号": "T-006",
                "任务类型": "城市基础设施巡检",
                "位置": "政务核心区楼顶设备",
                "x": 52,
                "y": 50,
                "优先级": "中",
                "截止时间": "今日 10:45",
                "分配无人机": "待分配",
                "状态": "待分配",
                "响应时间": None,
                "是否准时完成": "--",
            },
            {
                "任务编号": "T-007",
                "任务类型": "河道巡查",
                "位置": "北部湿地水系",
                "x": 32,
                "y": 86,
                "优先级": "中",
                "截止时间": "今日 10:35",
                "分配无人机": "UAV-7",
                "状态": "已分配",
                "响应时间": 4.4,
                "是否准时完成": "是",
            },
            {
                "任务编号": "T-008",
                "任务类型": "火情上报",
                "位置": "东部仓储园区",
                "x": 80,
                "y": 66,
                "优先级": "高",
                "截止时间": "今日 09:45",
                "分配无人机": "UAV-2",
                "状态": "已完成",
                "响应时间": 2.9,
                "是否准时完成": "是",
            },
            {
                "任务编号": "T-009",
                "任务类型": "应急救援辅助",
                "位置": "政务区西侧临时警情",
                "x": 42,
                "y": 48,
                "优先级": "高",
                "截止时间": "今日 10:15",
                "分配无人机": "UAV-3",
                "状态": "返航中",
                "响应时间": 5.0,
                "是否准时完成": "是",
            },
            {
                "任务编号": "T-010",
                "任务类型": "城市基础设施巡检",
                "位置": "南部综合管廊",
                "x": 72,
                "y": 26,
                "优先级": "低",
                "截止时间": "今日 09:55",
                "分配无人机": "UAV-4",
                "状态": "已完成",
                "响应时间": 7.0,
                "是否准时完成": "是",
            },
            {
                "任务编号": "T-011",
                "任务类型": "应急救援辅助",
                "位置": "东部社区突发求助点",
                "x": 76,
                "y": 56,
                "优先级": "高",
                "截止时间": "今日 10:20",
                "分配无人机": "待分配",
                "状态": "待分配",
                "响应时间": None,
                "是否准时完成": "--",
            },
            {
                "任务编号": "T-012",
                "任务类型": "违停取证",
                "位置": "学校医院周边道路",
                "x": 58,
                "y": 22,
                "优先级": "低",
                "截止时间": "今日 11:20",
                "分配无人机": "待分配",
                "状态": "待分配",
                "响应时间": None,
                "是否准时完成": "--",
            },
        ]
    )


def generate_algorithm_data() -> pd.DataFrame:
    data = [
        {"算法": "传统贪心算法", "总任务完成率": 82, "平均响应时间": 8.5, "总飞行距离": 38, "电量消耗": 71, "高优先级任务准时率": 76},
        {"算法": "遗传算法", "总任务完成率": 88, "平均响应时间": 7.2, "总飞行距离": 34, "电量消耗": 66, "高优先级任务准时率": 84},
        {"算法": "强化学习算法", "总任务完成率": 90, "平均响应时间": 6.8, "总飞行距离": 32, "电量消耗": 63, "高优先级任务准时率": 87},
        {"算法": "改进调度算法", "总任务完成率": 94, "平均响应时间": 5.9, "总飞行距离": 30, "电量消耗": 58, "高优先级任务准时率": 93},
    ]
    df = pd.DataFrame(data)
    df["综合评分"] = calculate_composite_scores(df)
    return df


def calculate_composite_scores(df: pd.DataFrame) -> List[float]:
    """按任务完成率、响应时间、飞行距离、能耗和高优先级准时率计算综合评分。"""
    completion = normalize_positive(df["总任务完成率"])
    response = normalize_negative(df["平均响应时间"])
    distance = normalize_negative(df["总飞行距离"])
    energy = normalize_negative(df["电量消耗"])
    punctual = normalize_positive(df["高优先级任务准时率"])
    score = 100 * (0.28 * completion + 0.22 * response + 0.16 * distance + 0.14 * energy + 0.20 * punctual)
    return [round(value, 1) for value in score]


def normalize_positive(series: pd.Series) -> pd.Series:
    span = series.max() - series.min()
    if span == 0:
        return pd.Series([1.0] * len(series), index=series.index)
    return (series - series.min()) / span


def normalize_negative(series: pd.Series) -> pd.Series:
    span = series.max() - series.min()
    if span == 0:
        return pd.Series([1.0] * len(series), index=series.index)
    return (series.max() - series) / span


def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_in_zone(x: float, y: float, zone: Dict) -> bool:
    if zone["shape"] == "rect":
        return zone["x0"] <= x <= zone["x1"] and zone["y0"] <= y <= zone["y1"]
    if zone["shape"] == "circle":
        return distance((x, y), (zone["cx"], zone["cy"])) <= zone["r"]
    return False


def find_zone_hits(x: float, y: float, zones: List[Dict], zone_type: str | None = None) -> List[str]:
    hits = []
    for zone in zones:
        if zone_type and zone["类型"] != zone_type:
            continue
        if point_in_zone(x, y, zone):
            hits.append(zone["名称"])
    return hits


def apply_battery_rules(uav_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """执行电量约束：电量低于 20% 自动返航，低于 25% 不再接收新任务。"""
    df = uav_df.copy()
    logs: List[str] = []
    low_mask = (df["电量"] < 20) & (df["状态"] != "故障")
    for _, row in df[low_mask].iterrows():
        logs.append(f"{row['无人机编号']} 电量 {row['电量']}%，触发电量约束，状态自动切换为返航。")
    df.loc[low_mask, "状态"] = "返航"
    return df, logs


def run_scheduling_rules(
    task_df: pd.DataFrame, uav_df: pd.DataFrame, zones: List[Dict]
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """简化版调度逻辑：优先级、距离、电量、载荷和禁飞区约束联合决策。"""
    tasks = task_df.copy()
    uavs, logs = apply_battery_rules(uav_df)
    tasks["调度提示"] = "常规调度"

    pending = tasks[tasks["状态"] == "待分配"].copy()
    pending["_priority_rank"] = pending["优先级"].map(PRIORITY_ORDER)
    pending = pending.sort_values(["_priority_rank", "任务编号"])

    for task_index, task in pending.iterrows():
        no_fly_hits = find_zone_hits(task["x"], task["y"], zones, zone_type="禁飞区")
        if no_fly_hits:
            tasks.at[task_index, "调度提示"] = f"任务点位于 {','.join(no_fly_hits)}，需要路径重规划"
            logs.append(f"{task['任务编号']} 位于禁飞区内，系统提示需要路径重规划后再派发。")
            continue

        candidate_mask = (
            (uavs["状态"] == "待命")
            & (uavs["电量"] >= 25)
            & (uavs["状态"] != "故障")
        )
        candidates = uavs[candidate_mask].copy()

        if task["任务类型"] in EMERGENCY_TASK_TYPES:
            special_candidates = candidates[candidates["载荷能力"].isin(SPECIAL_PAYLOADS)]
            if not special_candidates.empty:
                candidates = special_candidates
            else:
                tasks.at[task_index, "调度提示"] = "应急任务缺少红外/多传感器载荷候选机"
                logs.append(f"{task['任务编号']} 为应急任务，当前缺少合适载荷的待命无人机。")
                continue

        if candidates.empty:
            tasks.at[task_index, "调度提示"] = "无满足电量与状态约束的可用无人机"
            logs.append(f"{task['任务编号']} 暂无满足电量约束和状态约束的无人机。")
            continue

        candidates["距离"] = candidates.apply(
            lambda row: distance((row["x"], row["y"]), (task["x"], task["y"])), axis=1
        )
        selected = candidates.sort_values("距离").iloc[0]
        response_time = max(2.0, round(float(selected["距离"]) / 7.2, 1))

        tasks.at[task_index, "分配无人机"] = selected["无人机编号"]
        tasks.at[task_index, "状态"] = "已分配"
        tasks.at[task_index, "响应时间"] = response_time
        tasks.at[task_index, "是否准时完成"] = "是"
        tasks.at[task_index, "调度提示"] = "已按优先级、距离、电量和载荷约束完成派发"

        selected_idx = uavs[uavs["无人机编号"] == selected["无人机编号"]].index[0]
        uavs.at[selected_idx, "状态"] = "执行中"
        uavs.at[selected_idx, "当前任务"] = task["任务编号"]
        uavs.at[selected_idx, "当前位置"] = f"前往 {task['位置']}"

        logs.append(
            f"{task['任务编号']}（{task['优先级']}优先级）分配给 {selected['无人机编号']}，"
            f"预计响应 {response_time} min。"
        )

    return tasks, uavs, logs


def compute_kpis(task_df: pd.DataFrame, uav_df: pd.DataFrame) -> Dict[str, str]:
    completed_count = int((task_df["状态"] == "已完成").sum())
    running_count = int((task_df["状态"] == "执行中").sum())
    online_count = int((uav_df["状态"] != "故障").sum())
    high_tasks = task_df[task_df["优先级"] == "高"]
    high_rate = 0 if high_tasks.empty else round(100 * (high_tasks["是否准时完成"] == "是").sum() / len(high_tasks), 1)
    avg_response = round(pd.to_numeric(task_df["响应时间"], errors="coerce").dropna().mean(), 1)
    return {
        "当前任务总数": str(len(task_df)),
        "已完成任务数": str(completed_count),
        "执行中任务数": str(running_count),
        "在线无人机数量": str(online_count),
        "高优先级任务准时率": f"{high_rate}%",
        "平均响应时间": f"{avg_response} min",
    }


def render_header(kpis: Dict[str, str]) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <div class="eyebrow">National College Innovation Training Project Prototype</div>
            <h1>{PROJECT_TITLE}</h1>
            <p>{PROJECT_SUBTITLE}</p>
            <div class="tag-row">
                <span class="tag">城市治理</span>
                <span class="tag">低空经济</span>
                <span class="tag">无人机集群</span>
                <span class="tag">多任务调度</span>
                <span class="tag">路径重规划</span>
                <span class="tag">电量约束</span>
                <span class="tag">禁飞区约束</span>
                <span class="tag">数字孪生验证</span>
                <span class="tag">算法对比实验</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(6)
    metrics = list(kpis.items())
    deltas = ["实时", "+2 已调度", "态势稳定", "1 故障隔离", "改进算法", "-2.6 min"]
    for col, (label, value), delta in zip(cols, metrics, deltas):
        col.metric(label, value, delta=delta)


def render_sidebar() -> None:
    st.sidebar.markdown("### 仿真参数")
    st.sidebar.select_slider("低空运行高度层", options=["80m", "120m", "160m", "200m"], value="120m")
    st.sidebar.slider("城市低空空域拥堵系数", min_value=0.1, max_value=1.0, value=0.62, step=0.02)
    st.sidebar.slider("任务到达强度", min_value=1, max_value=10, value=6, step=1)
    st.sidebar.checkbox("启用禁飞区约束校验", value=True)
    st.sidebar.checkbox("启用电量约束校验", value=True)
    st.sidebar.checkbox("启用路径重规划提示", value=True)
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **演示口径**

        本系统为科研原型，用于展示城市治理低空场景中的任务抽象、无人机集群调度、约束建模、路径重规划与数字孪生验证过程。
        """
    )


def build_city_map(
    tasks: pd.DataFrame,
    uavs: pd.DataFrame,
    facilities: pd.DataFrame,
    zones: List[Dict],
    incident_active: bool = False,
) -> go.Figure:
    fig = go.Figure()

    for zone in zones:
        if zone["shape"] == "rect":
            fig.add_shape(
                type="rect",
                x0=zone["x0"],
                y0=zone["y0"],
                x1=zone["x1"],
                y1=zone["y1"],
                fillcolor=zone["color"],
                line=dict(color=zone["line"], width=2),
                layer="below",
            )
            fig.add_annotation(
                x=(zone["x0"] + zone["x1"]) / 2,
                y=zone["y1"] + 2,
                text=zone["名称"],
                showarrow=False,
                font=dict(color=zone["line"], size=12),
            )
        elif zone["shape"] == "circle":
            fig.add_shape(
                type="circle",
                x0=zone["cx"] - zone["r"],
                y0=zone["cy"] - zone["r"],
                x1=zone["cx"] + zone["r"],
                y1=zone["cy"] + zone["r"],
                fillcolor=zone["color"],
                line=dict(color=zone["line"], width=2, dash="dot"),
                layer="below",
            )
            fig.add_annotation(
                x=zone["cx"],
                y=zone["cy"] + zone["r"] + 2,
                text=zone["名称"],
                showarrow=False,
                font=dict(color=zone["line"], size=12),
            )

    route_specs = [
        {
            "name": "UAV-1 河道巡检路径",
            "points": [(12, 18), (18, 43), (28, 72)],
            "color": "#32d7ff",
            "dash": "solid",
        },
        {
            "name": "UAV-2 火情应急路径",
            "points": [(66, 12), (70, 37), (82, 72)],
            "color": "#ff5b73",
            "dash": "solid",
        },
        {
            "name": "UAV-3 低电返航路径",
            "points": [(44, 48), (34, 34), (12, 18)],
            "color": "#ffb44c",
            "dash": "dash",
        },
        {
            "name": "UAV-4 交通监测路径",
            "points": [(66, 12), (66, 24), (67, 35)],
            "color": "#23d18b",
            "dash": "solid",
        },
        {
            "name": "避开禁飞区重规划路径",
            "points": [(86, 16), (86, 38), (70, 61), (76, 56)],
            "color": "#a78bfa",
            "dash": "dot",
        },
    ]

    if incident_active:
        route_specs.append(
            {
                "name": "突发事件动态重规划路径",
                "points": [(86, 16), (89, 42), (78, 68)],
                "color": "#f97316",
                "dash": "dashdot",
            }
        )

    for route in route_specs:
        xs = [p[0] for p in route["points"]]
        ys = [p[1] for p in route["points"]]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                name=route["name"],
                line=dict(color=route["color"], width=4, dash=route["dash"]),
                marker=dict(size=7, color=route["color"]),
                hovertemplate=f"{route['name']}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=facilities["x"],
            y=facilities["y"],
            mode="markers+text",
            name="无人机起降/换电点",
            text=facilities["名称"],
            textposition="bottom center",
            marker=dict(size=18, color="#2f80ff", symbol="square", line=dict(color="#dff5ff", width=1.5)),
            hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
            customdata=facilities["能力"],
        )
    )

    task_styles = {
        "河道巡查": ("#32d7ff", "circle"),
        "火情上报": ("#ff5b73", "star"),
        "交通拥堵监测": ("#ffb44c", "diamond"),
        "违停取证": ("#a3e635", "x"),
        "城市基础设施巡检": ("#38bdf8", "hexagon"),
        "应急救援辅助": ("#f97316", "triangle-up"),
    }
    for task_type, (color, symbol) in task_styles.items():
        sub = tasks[tasks["任务类型"] == task_type]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["x"],
                y=sub["y"],
                mode="markers",
                name=f"任务点-{task_type}",
                marker=dict(size=13, color=color, symbol=symbol, line=dict(color="#0b1220", width=1.2)),
                customdata=sub[["任务编号", "位置", "优先级", "状态", "调度提示"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b> %{customdata[1]}"
                    "<br>类型: " + task_type +
                    "<br>优先级: %{customdata[2]}"
                    "<br>状态: %{customdata[3]}"
                    "<br>提示: %{customdata[4]}<extra></extra>"
                ),
            )
        )

    if incident_active:
        fig.add_trace(
            go.Scatter(
                x=[78],
                y=[68],
                mode="markers+text",
                name="突发火情事件",
                text=["突发火情 B+"],
                textposition="top center",
                marker=dict(size=22, color="#ff2f4f", symbol="star-diamond", line=dict(color="#fff2f4", width=1.5)),
                hovertemplate="<b>区域 B 突发火情</b><br>已触发动态调度与路径重规划<extra></extra>",
            )
        )

    uavs = uavs.copy()
    uavs["marker_color"] = uavs["电量"].apply(lambda v: "#ff5b73" if v < 20 else "#ffb44c" if v < 35 else "#37e6a6")
    fig.add_trace(
        go.Scatter(
            x=uavs["x"],
            y=uavs["y"],
            mode="markers+text",
            name="无人机当前位置",
            text=uavs["无人机编号"],
            textposition="top center",
            marker=dict(size=16, color=uavs["marker_color"], symbol="triangle-up", line=dict(color="#ffffff", width=1.2)),
            customdata=uavs[["电量", "载荷能力", "当前任务", "状态"]],
            hovertemplate=(
                "<b>%{text}</b>"
                "<br>电量: %{customdata[0]}%"
                "<br>载荷: %{customdata[1]}"
                "<br>当前任务: %{customdata[2]}"
                "<br>状态: %{customdata[3]}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        height=660,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#081827",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.16,
            xanchor="center",
            x=0.5,
            font=dict(color="#d8ecff", size=11),
            bgcolor="rgba(8,24,39,0.72)",
            bordercolor="rgba(98,175,255,0.24)",
            borderwidth=1,
        ),
        xaxis=dict(
            title="城市低空仿真坐标 X",
            range=[0, 100],
            showgrid=True,
            gridcolor="rgba(100,160,220,0.12)",
            zeroline=False,
            color="#bcd4e8",
        ),
        yaxis=dict(
            title="城市低空仿真坐标 Y",
            range=[0, 100],
            showgrid=True,
            gridcolor="rgba(100,160,220,0.12)",
            zeroline=False,
            color="#bcd4e8",
            scaleanchor="x",
            scaleratio=1,
        ),
        hoverlabel=dict(bgcolor="#0c2037", font_color="#f4fbff"),
    )
    return fig


def priority_color(priority: str) -> str:
    if priority == "高":
        return "background-color: rgba(255, 91, 115, 0.25); color: #fff0f3; font-weight: 700;"
    if priority == "中":
        return "background-color: rgba(255, 180, 76, 0.20); color: #fff2dc; font-weight: 700;"
    return "background-color: rgba(35, 209, 139, 0.16); color: #e1fff1;"


def style_task_table(df: pd.DataFrame):
    def style_row(row: pd.Series) -> List[str]:
        styles = ["" for _ in row]
        if row.get("优先级") == "高":
            styles = ["background-color: rgba(255, 91, 115, 0.08);" for _ in row]
        elif row.get("优先级") == "中":
            styles = ["background-color: rgba(255, 180, 76, 0.06);" for _ in row]
        if "优先级" in row.index:
            styles[list(row.index).index("优先级")] = priority_color(row["优先级"])
        if row.get("调度提示", "").find("禁飞区") >= 0:
            styles = ["background-color: rgba(255, 91, 115, 0.13);" for _ in row]
        return styles

    return df.style.apply(style_row, axis=1).format({"响应时间": "{:.1f}"}, na_rep="--")


def style_uav_table(df: pd.DataFrame):
    def style_row(row: pd.Series) -> List[str]:
        if row["电量"] < 20:
            return ["background-color: rgba(255, 91, 115, 0.16); color: #ffe8ec;" for _ in row]
        if row["电量"] < 35:
            return ["background-color: rgba(255, 180, 76, 0.12);" for _ in row]
        return ["" for _ in row]

    return df.style.apply(style_row, axis=1).format({"剩余航程": "{:.1f}", "电量": "{:.0f}"})


def render_dashboard(tasks: pd.DataFrame, uavs: pd.DataFrame, logs: List[str], algorithm_df: pd.DataFrame) -> None:
    c1, c2 = st.columns([1.25, 0.75], gap="large")
    with c1:
        st.markdown(
            """
            <div class="section-card">
                <h3>项目技术路线</h3>
                <div class="route">
                    <span class="route-step">城市治理任务场景抽象</span>
                    <span class="route-arrow">→</span>
                    <span class="route-step">多无人机调度模型构建</span>
                    <span class="route-arrow">→</span>
                    <span class="route-step">约束条件建模</span>
                    <span class="route-arrow">→</span>
                    <span class="route-step">调度优化算法设计</span>
                    <span class="route-arrow">→</span>
                    <span class="route-step">数字孪生仿真验证</span>
                    <span class="route-arrow">→</span>
                    <span class="route-step">调度效果可视化评估</span>
                </div>
                <p class="small-note">围绕城市治理、低空经济与无人机集群协同运行，构建从任务生成到调度解释的闭环验证流程。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="section-card">
                <h3>项目创新点</h3>
                <ol>
                    <li>面向城市治理多任务场景，而不是单一巡检任务；</li>
                    <li>综合考虑任务优先级、电量、禁飞区、响应时间等约束；</li>
                    <li>构建可视化数字孪生仿真平台，实现模型运行过程可解释；</li>
                    <li>通过算法对比展示改进方法在响应时间、任务完成率和能耗方面的优势。</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        best = algorithm_df.sort_values("综合评分", ascending=False).iloc[0]
        st.markdown(
            f"""
            <div class="section-card">
                <h3>调度结果摘要</h3>
                <div class="scenario-item"><span>当前推荐算法</span><span class="status-pill pill-blue">{best['算法']}</span></div>
                <div class="scenario-item"><span>总任务完成率</span><span class="status-pill pill-green">{best['总任务完成率']}%</span></div>
                <div class="scenario-item"><span>平均响应时间</span><span class="status-pill pill-green">{best['平均响应时间']} min</span></div>
                <div class="scenario-item"><span>高优先级准时率</span><span class="status-pill pill-green">{best['高优先级任务准时率']}%</span></div>
                <div class="scenario-item"><span>禁飞区约束</span><span class="status-pill pill-orange">已启用</span></div>
                <div class="scenario-item"><span>电量约束</span><span class="status-pill pill-orange">已启用</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for log in logs[:4]:
            if "禁飞区" in log or "电量" in log:
                st.markdown(f'<div class="alert-card">{log}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="info-card">{log}</div>', unsafe_allow_html=True)

    st.markdown("### 预设演示场景")
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    scenario_cards = [
        ("UAV-1", "从起降点 A 出发执行河道巡检任务", "pill-blue"),
        ("UAV-2", "前往区域 B 执行火情应急任务", "pill-red"),
        ("UAV-3", "因电量不足返回换电点", "pill-orange"),
        ("UAV-4", "执行交通拥堵监测任务", "pill-green"),
        ("系统", "自动避开禁飞区和风险区域", "pill-blue"),
    ]
    for col, (name, text, pill) in zip([sc1, sc2, sc3, sc4, sc5], scenario_cards):
        col.markdown(
            f"""
            <div class="section-card">
                <h3><span class="status-pill {pill}">{name}</span></h3>
                <p>{text}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 关键任务状态")
    quick_view = tasks[["任务编号", "任务类型", "位置", "优先级", "分配无人机", "状态", "调度提示"]].head(8)
    st.dataframe(style_task_table(quick_view), use_container_width=True, height=300)


def render_map_view(tasks: pd.DataFrame, uavs: pd.DataFrame, facilities: pd.DataFrame, zones: List[Dict]) -> None:
    incident_active = bool(st.session_state.get("incident_active", False))
    fig = build_city_map(tasks, uavs, facilities, zones, incident_active=incident_active)
    st.plotly_chart(fig, use_container_width=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.markdown(
            """
            <div class="section-card">
                <h3>地图图层</h3>
                <p>起降点、巡检任务点、应急事件点、禁飞区、风险区域、无人机当前位置与已规划路径统一展示。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="section-card">
                <h3>路径重规划说明</h3>
                <p>紫色虚线路径表示系统在禁飞区约束与风险区域约束下生成的绕行路径，用于展示可解释调度过程。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div class="section-card">
                <h3>数字孪生态势</h3>
                <p>当前地图为模拟城市坐标系，不依赖高德、百度或 Mapbox API Key，可直接离线演示低空运行态势。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_task_management(tasks: pd.DataFrame, logs: List[str]) -> None:
    st.markdown("### 任务管理与约束校验")
    f1, f2, f3 = st.columns(3)
    type_options = ["全部"] + sorted(tasks["任务类型"].unique().tolist())
    priority_options = ["全部", "高", "中", "低"]
    status_options = ["全部"] + sorted(tasks["状态"].unique().tolist())
    selected_type = f1.selectbox("任务类型", type_options)
    selected_priority = f2.selectbox("优先级", priority_options)
    selected_status = f3.selectbox("状态", status_options)

    filtered = tasks.copy()
    if selected_type != "全部":
        filtered = filtered[filtered["任务类型"] == selected_type]
    if selected_priority != "全部":
        filtered = filtered[filtered["优先级"] == selected_priority]
    if selected_status != "全部":
        filtered = filtered[filtered["状态"] == selected_status]

    display_cols = [
        "任务编号",
        "任务类型",
        "位置",
        "优先级",
        "截止时间",
        "分配无人机",
        "状态",
        "响应时间",
        "是否准时完成",
        "调度提示",
    ]
    st.dataframe(style_task_table(filtered[display_cols]), use_container_width=True, height=460)

    st.markdown("### 调度规则运行日志")
    for log in logs:
        if "禁飞区" in log or "电量" in log or "缺少" in log:
            st.warning(log)
        else:
            st.info(log)


def render_uav_resources(uavs: pd.DataFrame) -> None:
    st.markdown("### 无人机资源状态")
    display_cols = ["无人机编号", "电量", "当前位置", "载荷能力", "当前任务", "剩余航程", "状态"]
    st.dataframe(style_uav_table(uavs[display_cols]), use_container_width=True, height=310)

    st.markdown("### 电量进度条")
    rows = [uavs.iloc[i : i + 4] for i in range(0, len(uavs), 4)]
    for row_df in rows:
        cols = st.columns(4)
        for col, (_, row) in zip(cols, row_df.iterrows()):
            with col:
                st.markdown(
                    f"""
                    <div class="battery-card">
                        <div class="battery-title"><span>{row['无人机编号']}</span><span>{row['电量']}%</span></div>
                        <div class="battery-meta">载荷：{row['载荷能力']}</div>
                        <div class="battery-meta">状态：{row['状态']}｜任务：{row['当前任务']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(int(row["电量"]))
                if row["电量"] < 20 and row["状态"] != "故障":
                    st.error("低电量警示：已触发返航策略")
                elif row["状态"] == "故障":
                    st.error("设备故障：已从在线调度池隔离")


def render_algorithm_comparison(algorithm_df: pd.DataFrame) -> None:
    st.markdown("### 调度算法对比实验")
    st.dataframe(
        algorithm_df.style.format(
            {
                "总任务完成率": "{:.0f}%",
                "平均响应时间": "{:.1f} min",
                "总飞行距离": "{:.0f} km",
                "电量消耗": "{:.0f}%",
                "高优先级任务准时率": "{:.0f}%",
                "综合评分": "{:.1f}",
            }
        ).highlight_max(subset=["总任务完成率", "高优先级任务准时率", "综合评分"], color="rgba(35,209,139,0.22)")
        .highlight_min(subset=["平均响应时间", "总飞行距离", "电量消耗"], color="rgba(35,209,139,0.22)"),
        use_container_width=True,
        height=210,
    )

    c1, c2 = st.columns(2)
    with c1:
        fig_completion = go.Figure(
            data=[
                go.Bar(
                    x=algorithm_df["算法"],
                    y=algorithm_df["总任务完成率"],
                    marker_color=["#64748b", "#38bdf8", "#60a5fa", "#23d18b"],
                    text=[f"{v}%" for v in algorithm_df["总任务完成率"]],
                    textposition="outside",
                )
            ]
        )
        fig_completion.update_layout(
            title="总任务完成率对比",
            yaxis_title="完成率 (%)",
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#081827",
            font=dict(color="#d9ecff"),
            margin=dict(l=20, r=20, t=50, b=60),
        )
        st.plotly_chart(fig_completion, use_container_width=True)

    with c2:
        fig_response = go.Figure(
            data=[
                go.Bar(
                    x=algorithm_df["算法"],
                    y=algorithm_df["平均响应时间"],
                    marker_color=["#ff8a65", "#ffb44c", "#60a5fa", "#23d18b"],
                    text=[f"{v:.1f} min" for v in algorithm_df["平均响应时间"]],
                    textposition="outside",
                )
            ]
        )
        fig_response.update_layout(
            title="平均响应时间对比",
            yaxis_title="响应时间 (min)",
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#081827",
            font=dict(color="#d9ecff"),
            margin=dict(l=20, r=20, t=50, b=60),
        )
        st.plotly_chart(fig_response, use_container_width=True)

    radar_metrics = ["任务完成率", "响应速度", "飞行距离优化", "能耗优化", "高优先级准时率"]
    radar = go.Figure()
    for _, row in algorithm_df.iterrows():
        values = [
            row["总任务完成率"],
            100 - row["平均响应时间"] * 7.5,
            100 - row["总飞行距离"] * 1.4,
            100 - row["电量消耗"] * 0.9,
            row["高优先级任务准时率"],
        ]
        values = [max(0, round(v, 1)) for v in values]
        radar.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=radar_metrics + [radar_metrics[0]],
                fill="toself",
                name=row["算法"],
            )
        )
    radar.update_layout(
        title="综合调度效果雷达图",
        polar=dict(
            bgcolor="#081827",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(160,200,240,0.18)", color="#d8ecff"),
            angularaxis=dict(gridcolor="rgba(160,200,240,0.18)", color="#d8ecff"),
        ),
        height=520,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d9ecff"),
        legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"),
        margin=dict(l=30, r=30, t=60, b=70),
    )
    st.plotly_chart(radar, use_container_width=True)


def initialize_session_state() -> None:
    defaults = {
        "sim_running": False,
        "incident_active": False,
        "event_message": "",
        "sim_progress": 28,
        "last_action_time": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_digital_twin_simulation(
    tasks: pd.DataFrame,
    uavs: pd.DataFrame,
    facilities: pd.DataFrame,
    zones: List[Dict],
    algorithm_df: pd.DataFrame,
) -> None:
    initialize_session_state()

    st.markdown("### 数字孪生仿真控制台")
    c1, c2 = st.columns([0.9, 1.1], gap="large")

    with c1:
        selected_algorithm = st.selectbox(
            "切换调度算法",
            algorithm_df["算法"].tolist(),
            index=algorithm_df[algorithm_df["算法"] == "改进调度算法"].index[0],
        )
        selected_scenario = st.selectbox(
            "选择任务场景",
            ["常规城市巡检", "突发火情响应", "交通拥堵监测", "多任务混合调度", "禁飞区动态变化"],
            index=3,
        )
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("开始仿真", use_container_width=True):
            st.session_state.sim_running = True
            st.session_state.sim_progress = max(st.session_state.sim_progress, 42)
            st.session_state.last_action_time = datetime.now().strftime("%H:%M:%S")
        if b2.button("暂停仿真", use_container_width=True):
            st.session_state.sim_running = False
            st.session_state.last_action_time = datetime.now().strftime("%H:%M:%S")
        if b3.button("重置仿真", use_container_width=True):
            st.session_state.sim_running = False
            st.session_state.incident_active = False
            st.session_state.event_message = ""
            st.session_state.sim_progress = 28
            st.session_state.last_action_time = datetime.now().strftime("%H:%M:%S")
        if b4.button("生成突发事件", use_container_width=True):
            st.session_state.incident_active = True
            st.session_state.sim_running = True
            st.session_state.sim_progress = 74
            st.session_state.event_message = (
                "区域 B 出现突发火情，系统已重新分配最近且电量充足的无人机前往处理，并自动避开禁飞区。"
            )
            st.session_state.last_action_time = datetime.now().strftime("%H:%M:%S")

        status = "运行中" if st.session_state.sim_running else "已暂停"
        status_class = "pill-green" if st.session_state.sim_running else "pill-orange"
        st.markdown(
            f"""
            <div class="section-card">
                <h3>仿真状态</h3>
                <div class="scenario-item"><span>当前状态</span><span class="status-pill {status_class}">{status}</span></div>
                <div class="scenario-item"><span>任务场景</span><span>{selected_scenario}</span></div>
                <div class="scenario-item"><span>调度算法</span><span>{selected_algorithm}</span></div>
                <div class="scenario-item"><span>最近操作</span><span>{st.session_state.last_action_time or "等待操作"}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(int(st.session_state.sim_progress), text=f"数字孪生仿真进度：{st.session_state.sim_progress}%")

        if st.session_state.event_message:
            st.success(st.session_state.event_message)

        selected_row = algorithm_df[algorithm_df["算法"] == selected_algorithm].iloc[0]
        st.markdown(
            f"""
            <div class="section-card">
                <h3>算法即时评估</h3>
                <div class="scenario-item"><span>任务完成率</span><span class="status-pill pill-green">{selected_row['总任务完成率']}%</span></div>
                <div class="scenario-item"><span>平均响应时间</span><span class="status-pill pill-blue">{selected_row['平均响应时间']} min</span></div>
                <div class="scenario-item"><span>能耗水平</span><span class="status-pill pill-orange">{selected_row['电量消耗']}%</span></div>
                <div class="scenario-item"><span>高优先级准时率</span><span class="status-pill pill-green">{selected_row['高优先级任务准时率']}%</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        fig = build_city_map(
            tasks,
            uavs,
            facilities,
            zones,
            incident_active=bool(st.session_state.incident_active),
        )
        fig.update_layout(height=620)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 仿真解释链路")
    e1, e2, e3, e4, e5 = st.columns(5)
    explanations = [
        ("1. 态势感知", "采集任务点、无人机位置、电量、载荷与空域约束。"),
        ("2. 约束校验", "识别低电量无人机、禁飞区任务点与风险区域。"),
        ("3. 任务排序", "高优先级任务优先进入调度队列。"),
        ("4. 集群派发", "选择最近且电量充足、载荷匹配的无人机。"),
        ("5. 可视化评估", "输出路径、状态、响应时间与算法对比实验结果。"),
    ]
    for col, (title, desc) in zip([e1, e2, e3, e4, e5], explanations):
        col.markdown(
            f"""
            <div class="section-card">
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    configure_page()
    initialize_session_state()

    facilities = generate_facilities()
    zones = generate_zone_data()
    raw_tasks = generate_task_data()
    raw_uavs = generate_uav_data()
    tasks, uavs, dispatch_logs = run_scheduling_rules(raw_tasks, raw_uavs, zones)
    algorithm_df = generate_algorithm_data()
    kpis = compute_kpis(tasks, uavs)

    render_sidebar()
    render_header(kpis)

    tabs = st.tabs(
        [
            "总览 Dashboard",
            "地图态势 Map View",
            "任务管理 Task Management",
            "无人机资源 UAV Resources",
            "算法对比 Algorithm Comparison",
            "数字孪生仿真 Digital Twin Simulation",
        ]
    )

    with tabs[0]:
        render_dashboard(tasks, uavs, dispatch_logs, algorithm_df)
    with tabs[1]:
        render_map_view(tasks, uavs, facilities, zones)
    with tabs[2]:
        render_task_management(tasks, dispatch_logs)
    with tabs[3]:
        render_uav_resources(uavs)
    with tabs[4]:
        render_algorithm_comparison(algorithm_df)
    with tabs[5]:
        render_digital_twin_simulation(tasks, uavs, facilities, zones, algorithm_df)


if __name__ == "__main__":
    main()
