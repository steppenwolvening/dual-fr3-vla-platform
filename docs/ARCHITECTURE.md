# 架构与执行边界

## 已实现路径

`synthetic/离线调用者 → RobotState/RobotCommand/帧契约 → Recorder → JSONL + 原始 blob → validator → replay / LeRobot exporter`。
Canonical 核心只依赖 Python 标准库；LeRobot、numpy、MuJoCo 仅在相关入口内导入。不存在 import 时打开设备或启动 GPU 的行为。

`VR/VLA/replay 请求 → 验证/动作适配 → 单一执行入口 → backend` 是整体目标。
本版 OfflineExecutor 只实现 synthetic/simulation sink 的独占租约、时间/序号、关节映射、目标及速度拒绝检查；仅执行 joint_position，并要求明确夹爪限制。
EEF absolute/delta 契约已定义，但需要已验证 IK 后才可执行。未实现或伪装底层实时控制器。硬件 sink 无论配置如何都拒绝。

## 进程边界与统一状态协议

未来 ROS 驱动/采集、robot_core、data、LingBot、IsaacLab 分进程运行。
采用一种简单桥接表示：`fr3.twin/1` JSONL，经本地管道/文件传递；协议保留 source_event_id、公共时间、时钟误差、模式、权威来源和 RobotState。
本版 file publisher 可被多个离线读者独立消费；无 live fanout 守护进程、无 ROS 订阅服务，不能声称已并行运行两个 Twin。
真实传感器采集必须只有一个所有者，再分发已采集帧，不由训练/Twin 重复打开同一设备。

- SHADOW：真机测量状态权威；两个 Twin 只消费状态，不产生真机命令。本版未接入 live SHADOW。
- REPLAY：录制状态权威；本版已实现 JSONL publisher、相同源时刻比较，以及受审模型的 MuJoCo kinematic consumer。
- SIMULATION：仅一个明确选中的 backend 推进动力学；其余 shadow。完整选择/推进编排未实现。

不能将两个动作流当状态同步。比较必须 source_event_id/common_time 一致，本版否则拒绝；未实现插值、跨时刻比较或延迟统计。
MuJoCo consumer 设置 qpos/qvel 后 mj_forward；缺速度时使用零仅供 kinematic viewer，并不回写为测量速度。
对齐关节不证明接触力、惯量、碰撞或动力学相同。

## 设备与模型

FR3 base/法兰/tool/TCP/camera/sensor 全链及左右装配外参目前 UNCONFIGURED。
官方 description 源码有 fr3、fr3v2、fr3v2_1，多版本存在不证明当前实际型号。不得随意选其中之一或复用旧 Robotiq/L20 装配。
本包未携带不适用模型。MuJoCoReplay 入口有实际引擎调用，但匹配当前双 FR3 + Franka Gripper 的模型和 gripper mapping 尚未提供，状态 BLOCKED。
Mink 未在所核验 MuJoCo 环境定位；不重写 IK。IsaacLab 不启动，当前模型加载器也未完成。

## 失效行为

过期租约、断连、tracking 丢失、deadman 释放：撤销软件控制权；急停输入在本版 latch 后不可重新 acquire。
这不是经过验证的物理停止。硬件部署前须明确现场急停、驱动停止接口、控制器 watchdog、制动/保持语义及延迟预算。
Python/网络/VLA 不承担机器人低层硬实时控制环。

无设备失败时的 silent synthetic fallback。仿真/回放/硬件/synthetic 数据源必须保留到训练资产清单。
