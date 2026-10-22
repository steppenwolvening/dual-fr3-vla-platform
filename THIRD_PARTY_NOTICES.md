# 第三方说明

本源码包未复制第三方源码、mesh、模型、数据集、权重或二进制依赖。上游仅通过现有安装 API 调用或只读源码/公开文档核对。

- LeRobot（已核实 Seeed fork 固定 commit）：Apache-2.0；运行依赖不随本包分发。
- Franka description / franka_ros2 / libfranka：本轮所读 LICENSE/package 声明 Apache-2.0；未分发。
- IsaacLab：未分发，具体框架/扩展与 NVIDIA Isaac Sim 专有组件须分别审查，不能统一套用一个许可证。
- MuJoCo、numpy、torch 等由既有环境提供；未来安装/分发逐个保留其许可，不纳入本工程自定义代码许可。
- LingBot VLA 2 公开官方页面显示 Apache-2.0，但本轮未固定/复制其代码或选定 checkpoint；权重及配套模型条款必须单独核验。

新写集成代码的许可待实验室政策决定；未擅自指定开源许可证。详细来源与 commit 见 migration/SOURCE_PROVENANCE.md 和 repos.lock.json。
