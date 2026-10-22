# Dual FR3 VLA Platform — 0.1.0 离线基础包

这是按当前 Dual FR3 + Franka Gripper + D405 + FlexiTac 重建的可执行离线基础工程。
**完整机器人/VLA 平台尚未完成**：硬件、Quest、当前双 FR3 模型/Mink、Isaac 双 Twin 和 LingBot 集成仍 BLOCKED。
真实可用部分为 Canonical 记录/校验/恢复/回放、命令契约与离线拒绝保护，以及固定 LeRobot 版本的实际导出回读。

## 无安装最小闭环

在工程根目录执行。只需要已有 Python >=3.10；推荐目标系统已有的 `/usr/bin/python3`。
输出目录必须不存在；重复运行请换新目录名。所有示例均不连接设备。

```bash
/usr/bin/python3 -B tools/fr3.py preflight
/usr/bin/python3 -B tools/test.py
/usr/bin/python3 -B tools/fr3.py synthetic artifacts/my-synthetic-episode
/usr/bin/python3 -B tools/fr3.py validate artifacts/my-synthetic-episode
/usr/bin/python3 -B tools/fr3.py replay artifacts/my-synthetic-episode
/usr/bin/python3 -B tools/fr3.py twin-publish artifacts/my-synthetic-episode
/usr/bin/python3 -B tools/fr3.py deployment-plan
```

`replay` 只读事件，不向执行器发送。`twin-publish` 输出统一 JSONL 录制状态；它不是两个实际仿真器。
损坏或中断 episode 可用 `fr3.py recover SOURCE NEW_DEST` 复制完整前缀，恢复结果明确标记需审查，不冒充完整 episode。

## 实际 LeRobot 转换

需已有且符合 `environments/lerobot-reader-pin.json` 的独立解释器。该 pin 固定 loader 的源码 SHA-256、commit、0.4.4 包版本与 v3.0 格式；不是完整依赖锁。
使用过程内离线配置，缓存放入本工程；不要复用旧机器的绝对环境路径。

```bash
DATA_PYTHON=/path/to/approved/data/environment/bin/python
HF_HOME="$PWD/artifacts/hf-cache" HF_DATASETS_CACHE="$PWD/artifacts/hf-cache/datasets" \
HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
HF_HUB_DISABLE_TELEMETRY=1 XDG_CACHE_HOME="$PWD/artifacts/cache" \
PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 \
"$DATA_PYTHON" -B tools/fr3.py export-lerobot artifacts/my-synthetic-episode \
artifacts/my-lerobot-export --label sent --fps 10 --tolerance-ms 20
```

转换器实际调用 SDK writer/finalize，再调用真实 reader 验证每帧状态、动作与 RGB 像素。
profile 明确定义为左右各七关节位置（rad）加两夹爪 opening width（m），不是推断的 LingBot action。
本版只接受 train 划分、单路 RGB、规则状态采样与显式 joint_position/gripper 目标。
validation/test 导出因固定训练统计复用尚未实现而拒绝。缺帧、非规则采样、缺关节/夹爪状态、未知时间映射都拒绝，不能静默补零。
Depth/tactile 保持 Canonical 无损原始数据，未添加到 VLA 模型输入。

## 模型回放入口和阻塞

`tools/mujoco_engine_smoke.py` 用独立 MuJoCo 环境做 20 步基础引擎检查，输入为球体，不代表 FR3 模型验收。
`fr3.py mujoco-replay EPISODE --model MODEL.xml --manifest REVIEWED.json` 有实际 MuJoCo 加载和命名关节状态读写逻辑，必须先取得当前装配审查通过的模型清单；本包模板为 UNCONFIGURED，当前调用应失败。
没有 Quest SDK 服务、ROS 驱动启动、D405 设备打开、FlexiTac 假驱动、Isaac 自动启动或 LingBot 假适配器。
`fr3.py integration-status` 以非零退出码给出阻塞状态。

## 交付资料与打包

- `docs/STATUS.md`：逐项实现/验证状态及阻塞条件。
- `docs/DATA_CONTRACT.md`、`docs/ARCHITECTURE.md`：实际接口与限制。
- `migration/PHASE1_AUDIT.md`、`SOURCE_PROVENANCE.md`：只读调查、上游及排除依据。
- `migration/VALIDATION.md`、`validation-provenance.json`：实际测试命令、解释器、输入和结果。
- `migration/TARGET_SETUP.md`、`ENVIRONMENT_PLAN.md`、`TRANSFER_PLAN.md`：新机恢复与后续审批范围。

```bash
/usr/bin/python3 -B tools/build_bundle.py --version MY_NEW_VERSION
/usr/bin/python3 -B tools/verify_bundle.py artifacts/dist/dual-fr3-vla-platform-MY_NEW_VERSION.tar.gz
```

源码归档排除 `.git`、权重、原始数据、二进制环境和运行缓存；synthetic 样本用上述命令重新生成。
归档含逐文件准入说明与 SHA-256，包外另有归档 SHA-256。只检查本地归档，不上传或创建远程仓库。
本工程未指定开源许可证，分发须先完成实验室政策与许可审查。
