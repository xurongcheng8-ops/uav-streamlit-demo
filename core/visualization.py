from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .data_generator import normalize_task_dataframe


ROUTE_COLORS = [
    "#32d7ff",
    "#23d18b",
    "#ffb44c",
    "#ff5b73",
    "#b58cff",
    "#66a3ff",
    "#ffd166",
    "#06d6a0",
    "#ef476f",
    "#118ab2",
]

PLOT_FONT = "#eaf4ff"
PLOT_MUTED_FONT = "#b9d7f2"
PLOT_LEGEND_BG = "rgba(7, 17, 31, 0.86)"


def plot_schedule_map(
    nests: pd.DataFrame,
    tasks: pd.DataFrame,
    result: dict | None = None,
    zones: list[dict] | None = None,
    title: str = "UAV Scheduling Map",
) -> go.Figure:
    result = result or {}
    zones = zones or []
    served_ids = set(result.get("served_tasks", {}).keys())
    unserved_ids = set(result.get("unserved_tasks", []))
    tasks_df = normalize_task_dataframe(tasks)
    tasks_df["task_id"] = tasks_df["task_id"].astype(str)
    tasks_df["_status"] = tasks_df["task_id"].apply(
        lambda task_id: "unserved" if task_id in unserved_ids else ("served" if task_id in served_ids else "pending")
    )

    fig = go.Figure()
    for zone in zones:
        _add_zone_shape(fig, zone)

    fig.add_trace(
        go.Scatter(
            x=nests["x"],
            y=nests["y"],
            mode="markers+text",
            text=nests["nest_id"],
            textposition="top center",
            marker=dict(symbol="square", size=15, color="#f7fbff", line=dict(color="#1c7ed6", width=2)),
            name="机巢",
            hovertemplate="Nest %{text}<br>(%{x:.1f}, %{y:.1f})<extra></extra>",
        )
    )

    _add_task_trace(fig, tasks_df[(tasks_df["_status"] == "served") & (~tasks_df["is_emergency"])], "已服务任务", "#23d18b", "circle")
    _add_task_trace(fig, tasks_df[(tasks_df["_status"] == "pending") & (~tasks_df["is_emergency"])], "待调度任务", "#9fb9d2", "circle-open")
    _add_task_trace(fig, tasks_df[tasks_df["_status"] == "unserved"], "未服务任务", "#ff5b73", "x")
    _add_task_trace(fig, tasks_df[(tasks_df["priority"] >= 4) & (~tasks_df["is_emergency"])], "高优先级任务", "#ffb44c", "diamond")
    _add_task_trace(fig, tasks_df[tasks_df["is_emergency"]], "突发任务", "#ff2f5f", "star")

    for index, route in enumerate(result.get("routes", {}).values()):
        path = route.get("path", [])
        if len(path) < 2:
            continue
        xs = [point[0] for point in path]
        ys = [point[1] for point in path]
        color = ROUTE_COLORS[index % len(ROUTE_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                line=dict(color=color, width=2.5),
                marker=dict(size=5, color=color),
                name=f"{route['uav_id']} 路径",
                hovertemplate=f"{route['uav_id']}<br>(%{{x:.1f}}, %{{y:.1f}})<extra></extra>",
            )
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        font=dict(color=PLOT_FONT),
        title_font=dict(color=PLOT_FONT, size=18),
        height=560,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor=PLOT_LEGEND_BG,
            bordercolor="rgba(98, 175, 255, 0.25)",
            borderwidth=1,
            font=dict(color=PLOT_FONT, size=12),
        ),
        showlegend=False,
        xaxis=dict(
            range=[0, 100],
            title="x",
            gridcolor="rgba(255,255,255,0.09)",
            color=PLOT_MUTED_FONT,
            title_font=dict(color=PLOT_FONT),
        ),
        yaxis=dict(
            range=[0, 100],
            title="y",
            gridcolor="rgba(255,255,255,0.09)",
            color=PLOT_MUTED_FONT,
            title_font=dict(color=PLOT_FONT),
            scaleanchor="x",
            scaleratio=1,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,17,31,0.55)",
    )
    return fig


def _add_zone_shape(fig: go.Figure, zone: dict) -> None:
    if zone.get("shape") == "rect":
        fig.add_shape(
            type="rect",
            x0=zone["x0"],
            y0=zone["y0"],
            x1=zone["x1"],
            y1=zone["y1"],
            fillcolor=zone.get("color", "rgba(255, 91, 115, 0.14)"),
            line=dict(color=zone.get("line", "#ff5b73"), width=2),
            layer="below",
        )
        fig.add_annotation(
            x=(float(zone["x0"]) + float(zone["x1"])) / 2,
            y=float(zone["y1"]) + 2,
            text=zone.get("name", zone.get("zone_id", "zone")),
            showarrow=False,
            font=dict(color=zone.get("line", "#ff5b73"), size=11),
        )
    elif zone.get("shape") == "circle":
        cx = float(zone["cx"])
        cy = float(zone["cy"])
        radius = float(zone["r"])
        fig.add_shape(
            type="circle",
            x0=cx - radius,
            y0=cy - radius,
            x1=cx + radius,
            y1=cy + radius,
            fillcolor=zone.get("color", "rgba(255, 180, 76, 0.14)"),
            line=dict(color=zone.get("line", "#ffb44c"), width=2),
            layer="below",
        )
        fig.add_annotation(
            x=cx,
            y=cy + radius + 2,
            text=zone.get("name", zone.get("zone_id", "zone")),
            showarrow=False,
            font=dict(color=zone.get("line", "#ffb44c"), size=11),
        )


def plot_metric_bars(metrics_df: pd.DataFrame, metric_columns: list[str]) -> go.Figure:
    fig = go.Figure()
    for column in metric_columns:
        if column not in metrics_df.columns:
            continue
        fig.add_trace(
            go.Bar(
                x=metrics_df["algorithm"],
                y=metrics_df[column],
                name=column,
                text=[_format_value(value) for value in metrics_df[column]],
                textposition="auto",
            )
        )
    fig.update_layout(
        template="plotly_dark",
        font=dict(color=PLOT_FONT),
        barmode="group",
        height=420,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor=PLOT_LEGEND_BG,
            font=dict(color=PLOT_FONT, size=12),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,17,31,0.55)",
    )
    return fig


def plot_route_animation(
    nests: pd.DataFrame,
    tasks: pd.DataFrame,
    result: dict,
    zones: list[dict] | None = None,
    title: str = "调度过程动态回放",
    frame_count: int = 60,
    highlight_uav_id: str | None = None,
    only_uav_id: str | None = None,
) -> go.Figure:
    zones = zones or []
    frame_count = max(10, int(frame_count))
    tasks_df = normalize_task_dataframe(tasks)
    tasks_df["task_id"] = tasks_df["task_id"].astype(str)
    served_ids = set(result.get("served_tasks", {}).keys())
    tasks_df["_status"] = tasks_df["task_id"].apply(lambda task_id: "served" if task_id in served_ids else "pending")

    fig = go.Figure()
    for zone in zones:
        _add_zone_shape(fig, zone)

    fig.add_trace(
        go.Scatter(
            x=nests["x"],
            y=nests["y"],
            mode="markers+text",
            text=nests["nest_id"],
            textposition="top center",
            marker=dict(symbol="square", size=15, color="#f7fbff", line=dict(color="#1c7ed6", width=2)),
            name="机巢",
            hovertemplate="Nest %{text}<br>(%{x:.1f}, %{y:.1f})<extra></extra>",
        )
    )
    _add_task_trace(fig, tasks_df[(tasks_df["_status"] == "served") & (~tasks_df["is_emergency"])], "待执行任务", "#23d18b", "circle")
    _add_task_trace(fig, tasks_df[tasks_df["is_emergency"]], "突发任务", "#ff2f5f", "star")

    routes = list(result.get("routes", {}).values())
    if only_uav_id is not None:
        routes = [route for route in routes if str(route.get("uav_id")) == str(only_uav_id)]
    dynamic_trace_indices = []
    for index, route in enumerate(routes):
        path = route.get("path", [])
        if len(path) < 2:
            continue
        is_highlight = highlight_uav_id is not None and str(route["uav_id"]) == str(highlight_uav_id)
        color = "#ff3d5a" if is_highlight else ROUTE_COLORS[index % len(ROUTE_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=[point[0] for point in path],
                y=[point[1] for point in path],
                mode="lines",
                line=dict(color=color, width=2.5 if is_highlight else 1.5, dash="dot"),
                opacity=0.55 if is_highlight else 0.28,
                name=f"{route['uav_id']} 计划路径",
                hoverinfo="skip",
            )
        )

        start_path = [path[0]]
        fig.add_trace(
            go.Scatter(
                x=[point[0] for point in start_path],
                y=[point[1] for point in start_path],
                mode="lines",
                line=dict(color=color, width=6 if is_highlight else 4),
                name=f"{route['uav_id']} 已飞行" + ("（受影响）" if is_highlight else ""),
                hoverinfo="skip",
            )
        )
        dynamic_trace_indices.append(len(fig.data) - 1)

        fig.add_trace(
            go.Scatter(
                x=[path[0][0]],
                y=[path[0][1]],
                mode="markers+text",
                text=[route["uav_id"]],
                textposition="top center",
                marker=dict(
                    size=20 if is_highlight else 16,
                    symbol="triangle-up",
                    color=color,
                    line=dict(color="#ffffff", width=1.6),
                ),
                name=f"{route['uav_id']} 实时位置",
                hovertemplate=f"{route['uav_id']}<br>(%{{x:.1f}}, %{{y:.1f}})<extra></extra>",
            )
        )
        dynamic_trace_indices.append(len(fig.data) - 1)

    frames = []
    for step in range(frame_count + 1):
        progress = step / frame_count
        frame_data = []
        for route in routes:
            path = route.get("path", [])
            if len(path) < 2:
                continue
            travelled = _path_until_fraction(path, progress)
            current = travelled[-1]
            frame_data.append(
                go.Scatter(
                    x=[point[0] for point in travelled],
                    y=[point[1] for point in travelled],
                    mode="lines",
                )
            )
            frame_data.append(
                go.Scatter(
                    x=[current[0]],
                    y=[current[1]],
                    mode="markers+text",
                    text=[route["uav_id"]],
                )
            )
        frames.append(
            go.Frame(
                data=frame_data,
                traces=dynamic_trace_indices,
                name=str(step),
                layout=go.Layout(title_text=f"{title} | 进度 {progress:.0%}"),
            )
        )
    fig.frames = frames

    fig.update_layout(
        title=title,
        template="plotly_dark",
        font=dict(color=PLOT_FONT),
        title_font=dict(color=PLOT_FONT, size=18),
        height=620,
        margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor=PLOT_LEGEND_BG,
            bordercolor="rgba(98, 175, 255, 0.25)",
            borderwidth=1,
            font=dict(color=PLOT_FONT, size=12),
        ),
        showlegend=False,
        xaxis=dict(
            range=[0, 100],
            title="x",
            gridcolor="rgba(255,255,255,0.09)",
            color=PLOT_MUTED_FONT,
            title_font=dict(color=PLOT_FONT),
        ),
        yaxis=dict(
            range=[0, 100],
            title="y",
            gridcolor="rgba(255,255,255,0.09)",
            color=PLOT_MUTED_FONT,
            title_font=dict(color=PLOT_FONT),
            scaleanchor="x",
            scaleratio=1,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,17,31,0.55)",
        updatemenus=[
            {
                "type": "buttons",
                "direction": "left",
                "x": 0.02,
                "y": -0.08,
                "bgcolor": "rgba(17, 55, 91, 0.98)",
                "bordercolor": "rgba(50, 215, 255, 0.55)",
                "borderwidth": 1,
                "font": {"color": "#eef8ff", "size": 13},
                "showactive": False,
                "buttons": [
                    {
                        "label": "播放",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 180, "redraw": True},
                                "fromcurrent": True,
                                "transition": {"duration": 60},
                            },
                        ],
                    },
                    {
                        "label": "暂停",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "x": 0.16,
                "y": -0.08,
                "len": 0.78,
                "bgcolor": "rgba(17, 55, 91, 0.66)",
                "bordercolor": "rgba(50, 215, 255, 0.28)",
                "font": {"color": PLOT_FONT, "size": 11},
                "currentvalue": {"prefix": "回放进度: ", "font": {"color": PLOT_FONT, "size": 12}},
                "steps": [
                    {
                        "label": f"{int(step / frame_count * 100)}%",
                        "method": "animate",
                        "args": [
                            [str(step)],
                            {
                                "frame": {"duration": 0, "redraw": True},
                                "mode": "immediate",
                                "transition": {"duration": 0},
                            },
                        ],
                    }
                    for step in range(frame_count + 1)
                ],
            }
        ],
    )
    return fig


def plot_insertion_change_map(
    nests: pd.DataFrame,
    tasks: pd.DataFrame,
    before_result: dict,
    after_result: dict,
    emergency_task_id: str,
    affected_uav_id: str,
    zones: list[dict] | None = None,
    title: str = "动态插入路径变化高亮",
) -> go.Figure:
    zones = zones or []
    tasks_df = normalize_task_dataframe(tasks)
    tasks_df["task_id"] = tasks_df["task_id"].astype(str)
    fig = go.Figure()
    for zone in zones:
        _add_zone_shape(fig, zone)

    fig.add_trace(
        go.Scatter(
            x=nests["x"],
            y=nests["y"],
            mode="markers+text",
            text=nests["nest_id"],
            textposition="top center",
            marker=dict(symbol="square", size=15, color="#f7fbff", line=dict(color="#1c7ed6", width=2)),
            name="机巢",
            hovertemplate="Nest %{text}<br>(%{x:.1f}, %{y:.1f})<extra></extra>",
        )
    )

    normal_tasks = tasks_df[(tasks_df["task_id"] != str(emergency_task_id)) & (~tasks_df["is_emergency"])]
    _add_task_trace(fig, normal_tasks, "原计划任务", "#8fb4d9", "circle")
    emergency_tasks = tasks_df[tasks_df["task_id"] == str(emergency_task_id)]
    if not emergency_tasks.empty:
        fig.add_trace(
            go.Scatter(
                x=emergency_tasks["x"],
                y=emergency_tasks["y"],
                mode="markers+text",
                text=emergency_tasks["task_id"],
                textposition="top center",
                marker=dict(
                    size=22,
                    color="#ff2f5f",
                    symbol="star",
                    line=dict(color="#ffffff", width=2),
                ),
                name="新增突发任务",
                hovertemplate="新增突发任务 %{text}<br>(%{x:.1f}, %{y:.1f})<extra></extra>",
            )
        )

    for route in before_result.get("routes", {}).values():
        path = route.get("path", [])
        if len(path) < 2:
            continue
        fig.add_trace(
            go.Scatter(
                x=[point[0] for point in path],
                y=[point[1] for point in path],
                mode="lines",
                line=dict(color="rgba(175, 195, 215, 0.42)", width=2, dash="dot"),
                name=f"插入前 {route['uav_id']}",
                hoverinfo="skip",
            )
        )

    for route in after_result.get("routes", {}).values():
        path = route.get("path", [])
        if len(path) < 2:
            continue
        is_affected = str(route["uav_id"]) == str(affected_uav_id)
        fig.add_trace(
            go.Scatter(
                x=[point[0] for point in path],
                y=[point[1] for point in path],
                mode="lines+markers",
                line=dict(
                    color="#ff3d5a" if is_affected else "rgba(50, 215, 255, 0.40)",
                    width=5 if is_affected else 2,
                ),
                marker=dict(size=8 if is_affected else 5, color="#ff3d5a" if is_affected else "#32d7ff"),
                name=f"插入后 {route['uav_id']}" + ("（受影响）" if is_affected else ""),
                hovertemplate=f"{route['uav_id']}<br>(%{{x:.1f}}, %{{y:.1f}})<extra></extra>",
            )
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        font=dict(color=PLOT_FONT),
        title_font=dict(color=PLOT_FONT, size=18),
        height=600,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor=PLOT_LEGEND_BG,
            bordercolor="rgba(98, 175, 255, 0.25)",
            borderwidth=1,
            font=dict(color=PLOT_FONT, size=12),
        ),
        xaxis=dict(
            range=[0, 100],
            title="x",
            gridcolor="rgba(255,255,255,0.09)",
            color=PLOT_MUTED_FONT,
            title_font=dict(color=PLOT_FONT),
        ),
        yaxis=dict(
            range=[0, 100],
            title="y",
            gridcolor="rgba(255,255,255,0.09)",
            color=PLOT_MUTED_FONT,
            title_font=dict(color=PLOT_FONT),
            scaleanchor="x",
            scaleratio=1,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,17,31,0.55)",
    )
    return fig


def plot_uav_task_counts(result: dict) -> go.Figure:
    rows = [
        {"uav_id": route["uav_id"], "task_count": len(route.get("task_sequence", []))}
        for route in result.get("routes", {}).values()
    ]
    df = pd.DataFrame(rows)
    fig = go.Figure()
    if not df.empty:
        fig.add_bar(x=df["uav_id"], y=df["task_count"], marker_color="#32d7ff", text=df["task_count"], textposition="auto")
    fig.update_layout(
        title="每架无人机服务任务数量",
        template="plotly_dark",
        font=dict(color=PLOT_FONT),
        title_font=dict(color=PLOT_FONT, size=16),
        height=320,
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis=dict(color=PLOT_MUTED_FONT),
        yaxis=dict(color=PLOT_MUTED_FONT),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,17,31,0.55)",
    )
    return fig


def plot_dynamic_metric_compare(before: dict, after: dict) -> go.Figure:
    keys = ["task_completion_rate", "average_response_time", "total_flight_distance", "uav_utilization"]
    fig = go.Figure()
    fig.add_bar(x=keys, y=[before.get(key, 0) for key in keys], name="插入前", marker_color="#32d7ff")
    fig.add_bar(x=keys, y=[after.get(key, 0) for key in keys], name="插入后", marker_color="#ffb44c")
    fig.update_layout(
        template="plotly_dark",
        font=dict(color=PLOT_FONT),
        barmode="group",
        height=360,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(bgcolor=PLOT_LEGEND_BG, font=dict(color=PLOT_FONT, size=12)),
        xaxis=dict(color=PLOT_MUTED_FONT),
        yaxis=dict(color=PLOT_MUTED_FONT),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,17,31,0.55)",
    )
    return fig


def _add_task_trace(fig: go.Figure, df: pd.DataFrame, name: str, color: str, symbol: str) -> None:
    if df.empty:
        return
    hover = [
        f"{row.task_id}<br>type: {row.task_type}<br>priority: {row.priority}<br>window: {row.earliest_start:.1f}-{row.latest_finish:.1f}"
        for row in df.itertuples()
    ]
    fig.add_trace(
        go.Scatter(
            x=df["x"],
            y=df["y"],
            mode="markers",
            marker=dict(size=11, color=color, symbol=symbol, line=dict(color="#ffffff", width=0.7)),
            name=name,
            text=hover,
            hovertemplate="%{text}<extra></extra>",
        )
    )


def _format_value(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _path_until_fraction(path: list[tuple[float, float]], fraction: float) -> list[tuple[float, float]]:
    if not path:
        return []
    if len(path) == 1:
        return [path[0]]
    total = _polyline_length(path)
    if total <= 0:
        return [path[0]]
    target = total * max(0.0, min(1.0, fraction))
    travelled = [path[0]]
    distance_so_far = 0.0
    for start, end in zip(path[:-1], path[1:]):
        segment = _distance(start, end)
        if distance_so_far + segment < target:
            travelled.append(end)
            distance_so_far += segment
            continue
        ratio = 0.0 if segment <= 0 else (target - distance_so_far) / segment
        current = (
            float(start[0]) + (float(end[0]) - float(start[0])) * ratio,
            float(start[1]) + (float(end[1]) - float(start[1])) * ratio,
        )
        travelled.append(current)
        return travelled
    return list(path)


def _polyline_length(path: list[tuple[float, float]]) -> float:
    return sum(_distance(start, end) for start, end in zip(path[:-1], path[1:]))


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((float(a[0]) - float(b[0])) ** 2 + (float(a[1]) - float(b[1])) ** 2) ** 0.5
