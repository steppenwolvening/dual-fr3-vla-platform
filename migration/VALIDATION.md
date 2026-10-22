# 验证范围与可复跑命令

真实执行结果见 `validation/results.json` 与日志；精确命令/解释器/输入类型/退出码见 `migration/validation-provenance.json`（来源证据）。
本轮使用现有系统 Python、既有独立 LeRobot Python 和 MuJoCo Python；没有建立环境、安装依赖、启硬件、启 Isaac、训练或加载大型权重。

```bash
/usr/bin/python3 -B tools/test.py
/usr/bin/python3 -B tools/fr3.py synthetic artifacts/NEW_EPISODE
/usr/bin/python3 -B tools/fr3.py validate artifacts/NEW_EPISODE
/usr/bin/python3 -B tools/fr3.py replay artifacts/NEW_EPISODE
/usr/bin/python3 -B tools/run_validation.py --lerobot-python DATA_ENV/bin/python --mujoco-python ROBOT_CORE_ENV/bin/python
/usr/bin/python3 -B tools/verify_bundle.py artifacts/dist/ARCHIVE.tar.gz
```

run_validation 限定 CPU/offline flags，缓存/TMP 全部 staging。LeRobot 转换通过真实 reader 验证 8 帧 state/action 数值和 RGB 像素，state/action shape=[16]、RGB=[3,4,4]。
unit 覆盖非法命令、死手/断连/追踪丢失、互斥控制、时序、字段/单位、缺帧/损坏、clock uncertainty、因果对齐、丢弃/异常恢复、路径穿越及篡改归档。
源码 AST 全量解析（不生成 pycache）。17 个已审计源文件末次摘要不变；只对这些明确文件给出证据，不声称全盘审计。

MuJoCo 3.9.0 只跑 20 步球体 headless physics，PASS_SIM 限于引擎，不满足当前双 FR3 + Franka Gripper/Mink 验收。
传感器和 VR 输入全为明确 synthetic。没有 PASS_HARDWARE；没有 LingBot batch、GPU inference、sim rollout 或两引擎同时运行证据。

包验证检查全部成员相对路径、禁止链接/非普通文件、尺寸、全文件校验覆盖、assets manifest 与归档一致。
最后在 staging 内新的解压目录运行无安装 core 最小闭环，检查源码包可独立恢复；不会访问旧环境/源代码。

## 下一阶段需要分别审批

1. 安装/环境：先审查固定源码与目标兼容矩阵，再创建项目级环境、安装 SDK/框架、下载经选择的必要模型；系统依赖交管理员。
2. 设备只读接入：枚举确认 D405/Quest/FlexiTac，核验协议、时间戳、角色和标定；明确哪些服务会打开设备。
3. 仿真/GPU：审批 Isaac 启动、当前模型转换/加载、MuJoCo/Mink、Quest 连续仿真控制、双 Twin 同时回放与延迟/误差指标。
4. LingBot：固定数据 loader 后先小 batch；另批小训练步 loss/梯度/保存恢复、checkpoint 加载、推理和 sim rollout。评估显存，必要时训练与采集机分离。
5. 真机：专门授权、适用固件/驱动与执行层验证、现场急停/停止路径、限位/碰撞/速度、控制权/断连故障验收齐备后才执行。
6. 发布/传输：许可及私密信息审查、私有仓库创建/push；源码、checkpoint、标定和数据各自审批。
