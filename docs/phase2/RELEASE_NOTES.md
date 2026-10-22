# v0.2.0.dev1 — 本地开发基线（未发布）

基于v0.1.0 `10922064d313b9af45a28d6c94c852ccd0ee1f3b` 的连续历史，保留旧版本和原目录。

新增官方双FR3/Franka Hand模型、实际MuJoCo/Mink控制和SE(3)遥操作回放；多来源canonical、三相机LeRobot v3 train/validation/test及冻结训练统计；π0.5原生训练factory与LingBot真实dataset/normalization/padding；严格模型加载、独立模型进程、统一物理动作调度/评测入口；ROS2 overlay与localhost仿真桥；Vuer控制器适配器与Isaac实际场景回放代码。

验证：55项unit/offline回归；双FR3 FK/IK与600步轨迹仿真；三组20帧canonical/多相机LeRobot真实回读；两个模型各自数据batch；ROS2 overlay构建和独立进程通信。模型场景三相机编译通过，但渲染/模型rollout未运行。源码归档逐文件SHA和解包回归随artifact提供，完整历史用Git bundle独立保存。

限制：未进行真实Quest/相机/触觉/Franka硬件测试；模型权重未下载、训练/推理/性能比较未运行；Isaac运行待批准，SHADOW和独立动力学未完成；完整训练验证loss循环和全新机器环境安装锁未完成。GPU实测RTX5090 Laptop约24GB。模型、数据、环境、缓存、凭据不在源码包。

本版本不能标为完整v0.2稳定验收。经后续单独批准发布时，应使用明确的Pre-release标签并保留上述限制。远程仓库、首次push和Release均未执行。
