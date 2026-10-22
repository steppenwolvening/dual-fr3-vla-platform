# 环境隔离与版本状态

本轮没有安装、升级、创建环境或改全局变量。源码 pin、安装元数据、完整环境锁、运行通过是四个独立事实。
`repos.lock.json` 固定已核实源码 commit；`environments/observed.json` 保存观察值和未解决项，不能作为完整可复现二进制环境锁。

| 边界 | 候选/观察 | 本轮验证 | 未解决 |
|---|---|---|---|
| stdlib core | Python >=3.10；实际系统 3.12.3 | unit/record/read/replay | 无安装依赖；不是硬实时组件 |
| data | 现有 Python3.10.20，LeRobot0.4.4，torch2.7.1+cu128，numpy2.2.6 | CPU small exporter + real reader | fork commit/loader SHA 固定；完整传递依赖 wheel/hash 锁未生成；未验证目标 GPU |
| robot_core | 现有 Python3.12.14，MuJoCo3.9.0，numpy2.5.2 | 20步 headless primitive | Mink、Quest、D405 SDK UNRESOLVED；当前机器人模型 UNCONFIGURED |
| ROS | 用户目标记录 Jazzy、系统 Python3.12.3 | 本轮不运行 ROS | 必须现场核验固件/FCI/libfranka/双臂控制器；独立系统 ROS + overlay |
| isaaclab | repo VERSION3.0.0；installed isaaclab6.1.14、isaacsim6.0.1.0、torch2.10.0+cu128 | 只读元数据 | torchaudio2.11.0 不满足声明2.10.0；运行时 UNKNOWN；不能搬环境 |
| lingbot | 官方候选仓库已核对；本地代码/选定 checkpoint 未定位 | 未运行 | code commit、依赖、loader、配套模型/统计全部待固定 |

LeRobot 仓库声明 torch <2.8，而已观察 Isaac 环境 torch2.10，因此当前不可合并这两个环境。
Python 版本相同也不能推断包约束/ABI/运行时兼容。不要把 ROS setup 注入 Conda/AI/仿真进程。

## 下一阶段经批准才执行的构建命令模板

以下仅供审查，不是本轮已执行操作。当前可直接使用无安装 core 入口。

```bash
# 经批准，且系统已有适用解释器后；只在项目目录创建，不改系统 Python。
python3 -m venv .venv-core
.venv-core/bin/python -m pip install --no-build-isolation --no-deps -e .
# MuJoCo 已观察版本的候选安装；仍需平台 wheel/依赖锁审核。
.venv-core/bin/python -m pip install 'mujoco==3.9.0'
# data 应单独按审核后的 Python3.10 和锁重建，不复用 Conda base。
# 固定源码来源可用下列形式，但安装/联网均须下一阶段授权：
/path/to/data/python -m pip install 'lerobot @ git+https://github.com/Seeed-Projects/lerobot.git@0f392484458cb5ebca0310c0c4c47390a31c80ed'
```

模板中没有声称传递依赖已锁定；未 resolve 的依赖不以 latest/main 替代。
禁止 sudo pip、--break-system-packages、用户全局 site 混装、改 Conda base、系统 ROS/驱动/CUDA、修改 bashrc。
激活时优先显式完整解释器路径；运行 preflight。conda deactivate 不会撤销先前 ROS setup，新终端也可能继承污染变量。
不设置全局 PYTHONPATH；源码启动器只修改本进程 sys.path。

## 管理员/环境审批清单

核验 ROS 控制包和适配固件所需系统组件、实时内核/权限策略（本工程不修改）；核验目标 GPU 与选定 Isaac/LingBot 的官方组合。
Toolkit 是否存在、编译器/FFmpeg/USB 访问权限等仅在选定实际依赖后核对，不自动安装或升降级。
SDK 安装与硬件枚举分别审批，不能在安装脚本中隐式打开设备。
