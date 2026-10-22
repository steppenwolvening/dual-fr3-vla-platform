# 实现与验收状态

本包完成已授权的离线基础构建与迁移打包，不等于整个机器人研究闭环完成。
证据标签：FILE_VERIFIED=本轮文件/源码/保存的测试证据，USER_PROVIDED=用户既有记录，INFERRED=推断，UNKNOWN=未核实。

| 能力 | 实现状态 | 验证状态 | 证据与限制 |
|---|---|---|---|
| M0 有边界审计/配置 | IMPLEMENTED | PASS_OFFLINE | FILE_VERIFIED：Phase1 审计、commit/文件摘要；未知装配明确 UNCONFIGURED |
| 状态/命令/传感帧契约 | IMPLEMENTED | PASS_UNIT | FILE_VERIFIED：维度、单位、时间、有效字段、来源、关联检查 |
| 离线单一执行入口 | IMPLEMENTED | PASS_UNIT | FILE_VERIFIED：租约互斥/失效撤权/限速等；无真机 backend |
| 真机 ROS 控制链 | NOT_IMPLEMENTED | BLOCKED | UNKNOWN：具体硬件/固件与安全参数；官方双臂源码仅静态核查 |
| Canonical 记录/读取/校验/恢复 | IMPLEMENTED | PASS_OFFLINE | FILE_VERIFIED：8 帧、64 事件 synthetic 小闭环及异常测试 |
| 离线事件回放 | IMPLEMENTED | PASS_OFFLINE | FILE_VERIFIED：64 事件，无硬件发送 |
| Canonical→LeRobot | PARTIAL | PASS_OFFLINE | FILE_VERIFIED：真实 0.4.4 reader，8 帧状态/动作/RGB 逐值通过；单相机 train-only 显式 profile |
| LeRobot validation/test 导出 | NOT_IMPLEMENTED | BLOCKED | 固定训练统计复用未实现；非规则重采样、多相机映射未实现 |
| 离线 VR translation/clutch | PARTIAL | PASS_UNIT | FILE_VERIFIED：synthetic 映射/跳变/deadman；非完整 SE(3)/IK |
| Quest 主链路 | NOT_IMPLEMENTED | BLOCKED | UNKNOWN：实际 SDK/transport、tracking origin、按键与标定 |
| MuJoCo 引擎 | IMPLEMENTED | PASS_SIM | FILE_VERIFIED：3.9.0，20 步简单球体；不代表机器人模型 |
| 当前双 FR3 模型/Mink IK | PARTIAL | BLOCKED | 实际 MuJoCo replay consumer 已写；没有适用模型/外参、Mink 缺失，未运行其正向模型加载 |
| 统一 Twin 状态协议/回放发布 | IMPLEMENTED | PASS_OFFLINE | FILE_VERIFIED：JSONL 和同源时刻比较；无实测延迟/丢帧指标 |
| IsaacLab 当前模型加载 | NOT_IMPLEMENTED | BLOCKED | 模型/装配未知；未获本轮启动授权；环境有依赖冲突 |
| 两个实际 Twin 同时运行 | NOT_IMPLEMENTED | BLOCKED | 未执行；JSONL 单元/离线协议不能代替两引擎验收 |
| ROS JointState 映射 | PARTIAL | PASS_UNIT | FILE_VERIFIED：纯函数、显式双射；无 live ROS subscriber |
| D405 | PARTIAL | BLOCKED | 帧契约/配置拒绝可用；实际 SDK/serial/流模式/数量未知，未打开设备 |
| FlexiTac | PARTIAL | BLOCKED | raw 帧记录/回放可用；真实协议/固件/形状/频率未知 |
| LingBot loader/训练配置/推理 | NOT_IMPLEMENTED | BLOCKED | 本地代码及选定 checkpoint 未定位；未臆造 adapter 或模型动作映射 |
| 训练、GPU 推理、sim rollout、真机 | NOT_IMPLEMENTED | NOT_RUN | 不在本轮授权内，分别审批 |
| 源码归档/清单/本地 Git | IMPLEMENTED | PASS_OFFLINE | 包内清单和外部 SHA-256；无远程、无权重上传 |

测试详细命令和解释器见 migration/validation-provenance.json，结果及日志见 validation/。
任何 PASS 只适用于该行输入和范围；不存在 PASS_HARDWARE。

## 需要补齐的事实

1. 两台 FR3 的 revision、序列号、固件/FCI、base 装配和限位来源；夹爪确切型号、数量、左右绑定、接口/宽度语义。
2. D405/FlexiTac 数量、序列号/身份、安装位姿、TCP 变化、有效标定；FlexiTac 真实协议/固件/读出程序。
3. Quest 可用 SDK 主链路与时间戳/坐标/按键定义；Mink 安装 pin、当前模型与约束/残差阈值。
4. 当前装配匹配的 URDF/MJCF/USD、mesh 依赖闭包和授权许可；不复用 Panda/Robotiq/L20。
5. LingBot 本地 commit、选定模型 revision、权重/processor/tokenizer/统计/embodiment/action/camera/chunk/周期映射及真实 dataloader。
6. IsaacLab 依赖冲突解决与审批、真实驱动停止路径和现场安全验收。
