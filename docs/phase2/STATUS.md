# v0.2 开发基线验收状态

精确机器可读状态：configs/integration-status.json；版本0.2.0.dev1。基线commit10922064d313b9af45a28d6c94c852ccd0ee1f3b、本地tag v0.1.0保留，旧目录未修改。开发分支codex/v0.2-integration。

- **IMPLEMENTED / PASS_SIM**：官方双FR3/Franka Hand、14关节/夹爪执行映射、Mink双臂IK、轨迹/限位/碰撞检查。FK矩阵最大误差1.11e-16，双臂IK位置残差约3.41e-5m，脚本轨迹最大关节误差约0.00267rad，600物理步无穿透接触。虚拟base布局不是实验室标定。
- **IMPLEMENTED / PASS_SIM**：SE(3)控制器回放、clutch/recenter、单臂跟踪失效、超时、命令互斥。**PARTIAL / NOT_RUN**：Vuer/Quest真实设备、网络/TLS与按键标定。
- **IMPLEMENTED / PASS_OFFLINE**：每流来源分离、多模态canonical、train/validation/test、三RGB相机LeRobot真实reader、冻结train统计。60帧720事件；三个合成episode轨迹类似，仅测试管线，不是泛化评测。非规则重采样明确不支持。
- **IMPLEMENTED / PASS_OFFLINE**：π0.5真实训练factory batch。**PARTIAL / PASS_OFFLINE**：LingBot真实上游dataset、transform、归一化和55维padding；未走完整processor/collator。
- **PARTIAL / NOT_RUN**：模型训练配置、严格本地加载/预后处理、chunk调度、隔离模型进程和统一MuJoCo评测入口。缺模型/processor/完整运行环境及下载、GPU执行授权；没有训练、模型rollout或性能比较结果。旧SO权重未使用。
- **PARTIAL / NOT_RUN**：Isaac官方URDF导入/回放和误差比较代码。20帧、180秒的有限测试等待独立授权。SHADOW和独立动力学尚未完成；JSONL不等于双Twin验收。
- **IMPLEMENTED / PASS_OFFLINE**：ROS2 overlay构建和两进程DDS localhost→MuJoCo；合法命令提交、越界命令拒绝。**NOT_IMPLEMENTED / NOT_RUN**：真实Franka硬件write、实际driver/controller和安全标定。
- **PARTIAL / PASS_OFFLINE**：D405/FlexiTac的synthetic/replay接口与原始数据保存。真实serial、固件、FlexiTac帧协议、标定、掉帧策略必须到设备后验证；没有真实读取成功声明。
- **PARTIAL / NOT_RUN**：GitHub本地发布准备，公开可见按用户最新指示；独立创建/push/Release及归属审核待批准。Docker按要求延期。

当前53项unit/offline回归通过，另有独立MuJoCo/Mink、VR、数据、PI05、LingBot、ROS检查证据。环境具体版本见environments/phase2-runtime-audit.json，GPU实测24GB Laptop，训练峰值/吞吐未知。其他尚未满足条件均保留，不把“配置已写”记为“实机/模型通过”。
