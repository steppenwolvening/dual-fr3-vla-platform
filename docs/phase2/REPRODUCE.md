# v0.2 本地复现

这是开发基线，完整硬件/模型/双Twin尚未验收。所有命令从工程根执行，输出目录必须不存在。旧v0.1原目录不修改。

1. 核心无依赖回归：`python3 -B tools/test.py`（当前53项）。
2. 在获准的MuJoCo3.9/Mink1.2环境执行 `python -B tools/smoke_dual_fr3.py`、`python -B tools/check_vr_mapping.py`。
3. 同一sim环境执行 `python -B tools/record_vr_sim.py artifacts/my-vr`，生成明确synthetic/simulation的train/validation/test。
4. 已审计LeRobot0.4.4环境执行 `python -B tools/export_splits.py artifacts/my-vr/splits.json artifacts/my-lerobot`。
5. 独立native PI05环境执行 `python -B tools/check_pi05_batch.py artifacts/my-lerobot`。无权重下载、无GPU执行。
6. 运行 `python3 -B tools/fetch_lingbot_audit.py`（仅固定的小型公开源码子集），然后数据环境执行 `python -B tools/check_lingbot_batch.py artifacts/my-lerobot --output artifacts/my-lingbot-data`。这不是完整LingBot模型环境安装。
7. ROS2 Jazzy只在当前shell source其setup.bash，设置 `ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=173 ROS_LOG_DIR="$PWD/artifacts/ros-log"` 后，用批准的sim环境执行 `tools/check_ros_bridge.py`。运行前确认该domain无其他实验。overlay用系统colcon构建，build/install/log全部指定到artifacts。
8. `isaac_replay.py`、`run_vuer_sim.py`、`evaluate_vla.py`默认仅输出计划。实际Isaac/Quest网络/模型GPU操作遵从独立审批，不以这些脚本的存在当作验收通过。

数据相关进程设置HF_HOME、XDG_CACHE_HOME到本工程artifacts，并设置HF_HUB_OFFLINE/HF_DATASETS_OFFLINE/HF_HUB_DISABLE_IMPLICIT_TOKEN/HF_HUB_DISABLE_TELEMETRY=1。检查进程设置CUDA_VISIBLE_DEVICES=''；不要对正式已批准训练照搬此GPU禁用变量。所有解释器路径从environments/phase2-runtime-audit.json中的版本需求在目标机重新解析，不复制旧Conda环境。

模型、官方参数、来源SHA都随源码；合成样本按脚本生成，真实数据/大权重/缓存不包含在归档。精确安装版本、source commit和测试证据已记录；完整跨机器pip/conda可解析安装锁尚未生成，不能声称已在全新目标机器从零安装成功。历史migration/FILES.sha256和旧build_bundle.py仅描述v0.1交付，v0.2使用tools/package_v2.py产生的新清单。
