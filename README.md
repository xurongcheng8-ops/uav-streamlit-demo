# 城市治理多机巢无人机巡检调度可视化仿真平台

本项目是面向城市治理的多机巢无人机巡检任务计划排班与动态响应优化平台，使用 **Python + Streamlit + Plotly** 构建。平台用于展示任务点、机巢、无人机、禁飞/风险区等态势，并进一步支持算法验证、动态突发任务插入和多算法对比实验。

第一阶段目标是形成一个完整的最小可验证闭环：可生成数据、可运行调度算法、可输出路径和指标、可插入突发任务、可导出实验结果。

## 新增功能

- 任务数据随机生成 / CSV 上传 / CSV 下载。
- 机巢、无人机、巡检任务三类标准数据模型。
- 最近邻贪心、优先级优先、综合评分启发式三种可运行调度算法。
- 每架无人机任务访问顺序、路径坐标、开始服务时间、未服务任务输出。
- 任务完成率、高优先级准时率、平均响应时间、总飞行距离、总能耗、无人机利用率、计划扰动度、算法耗时等指标计算。
- 突发任务动态插入演示，支持插入前后路径与指标对比。
- 多算法对比实验，支持固定随机种子复现实验并导出 CSV。
- 预留启发式以外的 MILP / VRPTW 精确模型扩展空间，但当前运行不依赖 Gurobi、CPLEX 等商业求解器。

## 运行方式

建议使用 Python 3.9 及以上版本。

```bash
pip install -r requirements.txt
streamlit run app.py
```

启动后访问：

```text
http://localhost:8501
```

## 数据格式

### 任务 CSV 字段

```text
task_id,x,y,task_type,service_time,earliest_start,latest_finish,priority,payload_required,quality_required,is_emergency,emergency_release_time
```

说明：

- `task_type` 可取 `river`、`traffic`、`parking`、`infrastructure`、`fire`、`emergency`。
- `priority` 为 1-5，数值越大优先级越高。
- `is_emergency` 可填 `true/false`、`1/0`、`是/否`。
- `emergency_release_time` 可为空；为空时平台默认用 `earliest_start` 计算响应时间。

### 机巢 CSV 字段

```text
nest_id,x,y,capacity
```

### 无人机 CSV 字段

```text
uav_id,nest_id,speed,battery_capacity,max_range,payload_capacity,safety_battery
```

示例数据位于：

- `data/sample_tasks.csv`
- `data/sample_nests.csv`
- `data/sample_uavs.csv`

## 页面说明

原有页面继续保留：总览、地图态势、任务管理、无人机资源、算法对比、数字孪生仿真。

新增重点页面：

- **算法验证平台 Algorithm Lab**：生成或上传任务数据，选择算法并运行，查看路径、服务时间、指标卡片和 CSV 导出。
- **动态任务插入 Dynamic Insertion**：生成初始计划，新增高优先级突发任务，尝试插入现有路径，展示插入前后地图和扰动指标。
- **算法对比实验 Experiment**：设置任务数量、机巢数量、时间窗紧迫程度和随机种子，一键运行三种算法并导出对比结果。

## 答辩展示建议

推荐使用“30 个任务点、3 个机巢、3 架无人机、1 个突发任务、3 种算法对比”的最小验证闭环进行展示：

1. 在“算法验证平台”生成 30 个任务、3 个机巢，运行“综合评分启发式”，展示路径地图、未服务任务和核心指标。
2. 切换到“动态任务插入”，生成初始计划，点击“新增突发任务并尝试插入”，讲解额外距离、响应时间和扰动程度。
3. 切换到“算法对比实验”，固定随机种子，一键运行三种算法，展示对比表、柱状图和 CSV 导出。

## 后续可完善方向

- 接入真实 GIS 路网、禁飞区和低空航线网格。
- 增加风速、天气、通信覆盖、空域容量等动态约束。
- 引入 MILP、VRPTW、遗传算法、强化学习或局部搜索做更强对比。
- 支持多架无人机共享同一机巢容量与充换电排队约束。
- 自动生成实验报告或答辩材料。
