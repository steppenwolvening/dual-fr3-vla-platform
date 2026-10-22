# 目标机恢复：不依赖旧 ROG 路径

目标机既有信息是 USER_PROVIDED，未实测。不假设当前可直接访问 leowu-203。
归档只有相对路径源码、小型配置和证据；没有环境二进制、checkpoint、真实数据或装配资产。

1. 在目标用户自己的新接收目录接收 tar.gz 和同名 `.sha256`。不覆盖旧结果。
2. 先 `sha256sum -c ARCHIVE.tar.gz.sha256`。使用本工程 verify_bundle 工具检查清单、成员类型、路径和校验值，再向全新目录解压。不要执行未知包里的代码后才验证包来源。
3. 进入解压根，使用已有系统解释器运行如下命令；不必安装项目。

```bash
/usr/bin/python3 -B tools/fr3.py preflight
/usr/bin/python3 -B tools/test.py
/usr/bin/python3 -B tools/fr3.py synthetic artifacts/target-smoke-001
/usr/bin/python3 -B tools/fr3.py validate artifacts/target-smoke-001
/usr/bin/python3 -B tools/fr3.py replay artifacts/target-smoke-001
/usr/bin/python3 -B tools/fr3.py deployment-plan
```

新工作站的 Conda base Python3.14 不用来承载 ROS/机器人依赖；系统 Python 不安装任何包。
如 preflight 检测 ROS/Conda 环境混用，改用经过检查的独立进程环境；不要全局拼接 ROS PYTHONPATH。

4. 依据 ENVIRONMENT_PLAN.md 独立审批并重建 data、robot_core、LingBot、IsaacLab。新环境解释器通过参数显式传给工具；不要复制旧环境或路径。
5. 有固定 LeRobot 环境后执行 README 的 exporter，再用 SDK reader 验证。使用新目录，保留原 Canonical 数据。
6. 补齐平台配置和经审查模型、标定；当前 template 的 UNCONFIGURED 不是可执行真机配置。核心 joint names 是规范名，不自动等于驱动名。
7. LingBot/模型/设备分别通过独立验收后才能扩大测试；真机依然需要单独授权和现场安全验收。

核心环境可按步骤 1–3 恢复；**完整仿真/VLA/真机环境当前不可宣称可复现部署成功**，缺失项见 STATUS。
