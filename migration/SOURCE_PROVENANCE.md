# 来源、准入与排除

## 本轮位置与保护边界

FILE_VERIFIED：主机 `aning-ROG-Strix-SCAR-16-G635LX-G635LX`，用户 `aning`；工作区 `/home/aning/Documents/ChatGPT/imitate`。
新工程 `/home/aning/robotics/migration_staging/dual-fr3-vla-platform` 本轮首次创建，无旧结果覆盖。
系统 Python `/usr/bin/python3` 3.12.3；只使用已有解释器，没有安装或创建环境。
源路径仅用于本节及审计/验证来源证据；新代码无两个账号 Home 硬编码。

完整 FILE_VERIFIED 仓库 commit/URL、17 个审计源文件 SHA-256 和环境元数据在 phase1-audit.json。
具体测试解释器、命令、输入与输出位置在 validation-provenance.json；原始审计文件末次哈希复核结果也在其中。

## 上游的采用方式

- LeRobot：`/home/aning/Desktop/lerobot`，Seeed fork，commit `0f392484458cb5ebca0310c0c4c47390a31c80ed`，Apache-2.0。静态读取 dataset 类 create/add_frame/save_episode/finalize/reader API，运行时调用已有安装，不复制实现。
  既有 record.py 修改未采用；仅吸收“发送返回值语义必须澄清”的设计问题。新 exporter 显式 label，保留 requested/sent/accepted 区分，对应真实 reader 逐帧测试。
- Franka：`/home/aning/robotics/vendor/franka_official/repos/` 的 description、ros2、libfranka，Apache-2.0；只核验 commit、声明依赖和双臂接口源码。
  franka_ros2 静态双臂测试显示两个独立硬件组件，各七关节位置/速度/力矩接口、每臂 Cartesian velocity 索引。未运行这些测试，没有将其视为当前装配兼容证明。
  description 2.8.1 和 libfranka 0.20.5 与所核验 ros2 dependency.repos 声明相符；没有导入其中 Robotiq/其他未固定 main 分支依赖。
- IsaacLab：`/home/aning/robotics/repos/IsaacLab`，commit `ffff603eafc6b74264a5261cc0183d6a65390d78`。只读元数据；仓库 VERSION 3.0.0 与安装包 isaaclab 6.1.14 分列。未导入运行时或启动 Isaac。
- MuJoCo：现有 `/home/aning/miniforge3/envs/mujoco_sim/bin/python`，安装元数据 3.9.0，运行 20 步 primitive smoke。未复制二进制环境或旧场景。
- FlexiTac：`/home/aning/Desktop/flexitac_fr3_twin_dc2e1c6`，commit `dc2e1c6607a1b1a0e4b196bb4e2d4ccdc1afdcb0`，仿真来源。没有真实协议证据；不采用旧 pad/碰撞/安装资产。

所有 src、tools、tests 都是本轮新写集成代码；**旧代码片段复制数量为 0**，第三方资产复制数量为 0。
采用已有 LeRobot SDK/MuJoCo 引擎，不重写训练框架、视频编码器、设备驱动或 IK。
每个实际纳入文件的用途、入口/测试、必要性、来源、许可审查状态和路径假设详见 assets.manifest.json。

## LingBot 范围与公开核验

UNKNOWN：相关项目根和加载元数据未定位本地 LingBot VLA 2；默认 `/home/aning/.cache/huggingface/hub` 不存在，未遍历其他模型。
没有选定 checkpoint、revision、分片索引、processor/tokenizer、统计或 embodiment 映射证据。
这表示“已审计范围内未定位”，不表示整机不存在。

仅公开官方资料只读核验：
- [Robbyant LingBot VLA 2](https://github.com/Robbyant/lingbot-vla-v2)
- [官方训练配置说明](https://github.com/Robbyant/lingbot-vla-v2/blob/main/configs/vla/Training_Config.md)

上述网页用于确认官方项目及配置入口存在；网页分支未固定为已选择代码 revision，repos.lock.json 明确 UNRESOLVED。
公开说明的要求不能替代本地 checkpoint 配套审计。没有下载、clone 或执行该上游代码。没有根据名称臆造 dataloader/action dimension。

## 排除项

SO-ARM101、Robotiq、L20/O30 专属资产/控制器/标定、Phase21/22 实验、π0.5/OpenPI/OpenVLA、PPO/奖励/旧策略、历史数据/失败日志、旧 build/install/log、缓存、二进制环境全部不纳入。
Desktop 的 dual_fr3_robotiq85_stage 仅检查根用途，确定是旧 Robotiq/π0.5 平台后排除。
没有复制原始数据、权重、旧 Git 历史、remote 或旧标定；没有删除或修改这些原始资料。
本轮末复核 17 个已审计源文件摘要；验证范围不等于全盘取证。没有全 Home 扫描或读取密钥。

## 目标机来源

USER_PROVIDED：leowu-203 / shuteng / /home/shuteng，Ubuntu 24.04.5，系统 Python3.12.3，ROS Jazzy，RTX5090 32607 MiB、Driver595.99.02，nvidia-smi CUDA13.2。
USER_PROVIDED：CMake3.28.3、Git2.43.0、Miniconda base Python3.14.8、Node24.22.0/npm11.19.1/Codex0.163.0。
没有远程访问或复测。CUDA 驱动显示值不证明 Toolkit 状态，也不保证训练能装进 32GB。
