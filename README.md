# Dual FR3 VLA Platform — v0.2 development baseline

从v0.1.0保留完整Git历史的独立软件集成工程。已验证官方Dual FR3 + Franka Hand的MuJoCo/Mink控制、双控制器SE(3)离线回放、多相机LeRobot v3数据管线，以及π0.5/LingBot各自的真实数据加载与动作映射。

**这是部分验收的开发基线，不是完整机器人系统发布。** 真实Quest、模型训练/推理、Isaac双Twin和真机动作尚未验收；数据测试使用明确标记的simulation/synthetic来源。新版本入口及证据见下表，历史migration目录仍保留v0.1审计资料。

| 模块 | 本轮实际结果 |
|---|---|
| 核心契约/数据/安全边界 | 53项unit/offline测试通过，原44项保留 |
| 官方双FR3 + Franka Hand / Mink | PASS_SIM：FK/IK、双臂轨迹、限位/碰撞检查 |
| VR SE(3)→Mink→MuJoCo | PASS_SIM：合成控制器离线回放；真实Quest NOT_RUN |
| 三相机RGB-D + tactile raw | 60帧/720事件，canonical录制/校验/回放；传感器均synthetic |
| LeRobot v3 | train/validation/test各20帧，真实SDK逐值回读；eval不拟合统计 |
| π0.5 | 原生训练dataset factory batch通过；tokenizer/model/training NOT_RUN |
| LingBot VLA2 | 上游dataset/transform/normalization/padding通过；完整collator/model NOT_RUN |
| ROS2 Jazzy | overlay构建、独立进程localhost仿真桥通过，无Franka驱动 |
| Isaac Lab | 实际URDF场景回放脚本已准备，等待批准运行；无双Twin通过声明 |
| GitHub/Docker | 本地提交/发布准备；创建、push、Release另行审批，Docker延后 |

## 最小复现

```bash
python3 -B tools/test.py
python3 -B tools/fr3.py integration-status
```

integration-status在完整平台尚未验收时返回2，这是预期行为。核心只需Python>=3.10；打包工具使用Python3.12。模拟、数据、PI05、LingBot、Isaac分别使用经过审计的解释器，不混装CUDA/JAX/系统ROS。

完整命令：[REPRODUCE](docs/phase2/REPRODUCE.md)。实际仿真入口 `tools/smoke_dual_fr3.py`、`tools/record_vr_sim.py`；数据入口 `tools/export_splits.py`、`tools/check_pi05_batch.py`、`tools/check_lingbot_batch.py`。模型加载和评测入口默认只显示计划，实际运行必须有相应独立授权及模型资产。

## 关键资料

- [当前状态](docs/phase2/STATUS.md)与[测试证据](validation/phase2)。
- [模型来源](docs/phase2/MODEL_REFERENCE.md)、[数据/VR](docs/phase2/DATA_AND_VR.md)。
- [双VLA语义和配置](docs/phase2/VLA_PIPELINES.md)、[ROS/Quest/GPU环境](docs/phase2/ROS_VR_ENVIRONMENTS.md)。
- [发布审查](docs/phase2/GITHUB_PREPARATION.md)、[许可](LICENSE_REVIEW.md)、[第三方归属](THIRD_PARTY_NOTICES.md)。

实测GPU是RTX5090 **Laptop 24GB**，不是桌面32GB；没有全参数训练容量或两模型性能排名的承诺。代码仓库排除权重、数据、缓存、二进制环境、证书和凭据。自定义代码许可证尚待所有者决定；用户允许公开可见，不等于自动赋予开源许可。
