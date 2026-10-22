# Phase 1 审计完成；第二版要求生效

2026-10-22，在源机 aning-ROG-Strix-SCAR-16-G635LX-G635LX、用户 aning 执行。
当前工作目录 /home/aning/Documents/ChatGPT/imitate。未连接目标机。
第二次粘贴的正文经核对与首版具有相同的实质范围、执行授权和 M0–M5 顺序；后续以第二版为准。

## 已核实边界与结论

- FILE_VERIFIED：限定读取 robotics、Desktop 下相关目录根、依赖文件、官方接口源码；具体文件摘要及 commit 在 phase1-audit.json。
- FILE_VERIFIED：MuJoCo 环境存在、安装元数据 3.9.0；Mink 元数据未找到。尚不能等同当前双 FR3 模型通过。
- FILE_VERIFIED：LeRobot 0.4.4、dataset codebase v3.0；来源为 Seeed fork，固定 commit 0f392484458cb5ebca0310c0c4c47390a31c80ed。record.py 有既有修改；不采用其代码。
- FILE_VERIFIED：franka_ros2 b4164f5 的双臂测试源码要求两个独立 FrankaHardwareInterface、每臂七关节、position/velocity/effort、每臂独立 Cartesian velocity 索引。仅静态核实，未运行 ROS 测试或驱动。对应 dependency.repos 指向 description 2.8.1、libfranka 0.20.5；文件含其他不适用依赖，禁止整份导入。
- FILE_VERIFIED：IsaacLab 仓库 VERSION=3.0.0，安装包 isaaclab=6.1.14、isaacsim=6.0.1.0；内部运行时 UNKNOWN。torchaudio=2.11.0 与声明 2.10.0 冲突。未启动 Isaac。
- FILE_VERIFIED：Desktop 的 dual_fr3_robotiq85_stage 是 Robotiq/π0.5 项目；仅审查根级用途后排除。
- FILE_VERIFIED：FlexiTac 参考仓库是仿真实现；未获得真实协议、固件或采集程序证据。未采纳旧 pad 几何或标定。
- UNKNOWN：本次允许范围内未定位 LingBot VLA 2 本地代码、选定 checkpoint、VR 主链路或适用于当前装配的模型/标定。默认 HF hub 不存在；不推断整机不存在。
- USER_PROVIDED：当前硬件清单及目标机既有环境信息来自需求，未现场枚举设备。
- UNKNOWN：FR3 型号 revision、序列号、夹爪数量/型号、相机/触觉数量与左右分配、安装几何及 TCP。

## 准入决定

新写标准库 Canonical 层；调用已有 LeRobot SDK 而不复制旧 exporter；MuJoCo 仅做有限 headless 引擎冒烟。
模型与硬件专属依赖不猜测。保留真实模型加载入口，但当前双 FR3/Mink/Twin 验收 BLOCKED。
不复制任何旧项目代码片段、旧数据、模型权重、资产或二进制环境。

本轮不会安装、训练、下载、启硬件、启 Isaac、远程发布或传输。后续继续已授权离线构建和打包。
