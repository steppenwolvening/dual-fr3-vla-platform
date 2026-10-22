# ROS、VR、环境与目标机准备

## ROS 2

系统ROS2 Jazzy保持不变，当前controller_manager/ros2_control包4.45.2，Python3.12 ABI。只在子进程source `/opt/ros/jazzy/setup.bash`。ros_bridge使用rclpy/std_msgs String传递已验证canonical JSON；它是**仿真桥**，并非Franka ros2_control硬件控制器。独立进程DDS localhost测试已确认合法目标进入MuJoCo、越界目标拒绝。使用测试domain173，实际部署应分配不冲突的域；不能用此测试推断真机controller可以接收相同消息。

Overlay位于ros2_overlay/src/dual_fr3_bridge；构建产物全部在artifacts。运行时需项目src在PYTHONPATH及已批准MuJoCo环境，系统ROS包路径只作进程内fallback，不覆盖系统/旧Conda。权限租约、watchdog失效hold、碰撞故障锁定均在仿真边界。

上游固定：franka_ros2 3.4.1 commit b4164f555500fe50c3f44f24d4cccc452ffac442；其dependency.repos要求franka_description2.8.1及libfranka0.20.5（本地commit 3cc708cafa1cdba49ceaab536a14216dfb7bf48a）。构建需要现有Jazzy的ament_cmake/ament_python、colcon、controller_manager、hardware_interface、controller_interface、joint_state_broadcaster、robot_state_publisher、xacro、Eigen/CMake/C++工具链及libfranka所需依赖。应对目标机运行只读rosdep检查后再审批安装，不能将含Robotiq/其他机器人依赖的整个upstream dependency.repos照搬。

真机准备仍需核对实验室FR3 System版本/FCI许可/固件与libfranka兼容、左右独立hardware_interface、关节命名、实时调度、franka_gripper action语义、状态时钟、TCP和base外参、碰撞/速度/力矩安全参数及实体急停。未构建/启动Franka硬件驱动，也没有硬件write实现。本轮仅overlay和仿真通信，不是硬件ready认证。

## Quest 3 主链路

选择OpenTeleVision使用的Vuer传输体系，采用其官方MotionControllers/CONTROLLER_MOVE接口：Vuer commit 10e30b5c7f4ad219048819371821ce619f952d43；OpenTeleVision审查commit e6e25afdb16c1b326b5bf37bd0ae79919bf79f26。原TeleVision示例是HAND_MOVE/Hands及ZED视频，不能直接当作Quest控制器接口或引入无关ZED资产。本项目依据官方Controller字段编写独立小适配器，无上游代码整包复制。

`run_vuer_sim.py`连接MotionControllers事件→显式column-major转换→DualPoseMapper→Mink→OfflineExecutor→MuJoCo。默认只显示计划，`--execute`还需review_status配置。配置示例保留UNCONFIGURED origin/TLS；按钮方案squeeze deadman、thumbstick clutch、bButton recenter、triggerValue夹爪只作为待实机审查建议，不宣称按钮测试完成。左右矩阵/状态缺失时独立撤销该侧跟踪，不猜测旧pose。当前官方事件示例没有设备时间戳，因此保留host_receive_only和未知网络/设备时延；不能将接收时间当成Quest源时间，更不能据此控制真机。

当前各候选环境未安装Vuer。尚未安装、启动网络服务、建立公网隧道、生成证书或连接Quest；需审批独立Vuer依赖解析/安装，并取得可信本地TLS、Quest网络及实际坐标标定后继续。矩阵、按钮和丢臂输入测试PASS_UNIT，SE(3)/Mink离线回放PASS_SIM，PASS_VR_DEVICE仍NOT_RUN。

## 环境及GPU

精确观察值见environments/phase2-runtime-audit.json。已批准的新sim overlay是唯一安装变更；旧环境只读使用。CPU-only数据检查不能证明GPU kernels可用。

实测GPU为RTX5090 **Laptop**，24463MiB（约24GB），compute capability12.0，driver595.99.02；不是桌面32GB。现有PI05 torch2.10.0+cu128与候选LingBot torch2.8.0/cu128分别验证，不能按型号推断FlashAttention/Triton/所有fused MoE kernels支持sm_120。LingBot FP32主权重约25.5GB，仅主权重就几乎占满该机24463MiB总显存，无法为激活/运行时留下正常空间；官方FP32比较路线需更大设备或经单独验证的分片方案。BF16降低权重空间但改变数值路径，且无法保证activation/optimizer/teacher整体能放入24GB。PI05 expert-only/BF16/累积梯度只作候选，先批准短资源探测再决定训练方案。

IsaacLab已安装6.1.14、IsaacSim6.0.1.0、torch2.10.0+cu128；torchaudio2.11.0与torch家族不匹配，未修复旧环境。isaac_replay脚本不使用音频，实际启动仍待单独批准。REPLAY准备完成，SHADOW与独立动力学评测尚未实现/验收。

Docker未开始封装。先固定能运行的宿主基线；后续core、data、sim、pi05、lingbot、isaaclab分别使用这里的版本证据与独立构建锁，不复制Conda二进制目录。真实ROS2控制初期保留在实验室受控宿主机。权重、数据、标定和凭据须分别传输，不能进入代码镜像/Git。
