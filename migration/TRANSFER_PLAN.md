# 本地源码包与后续资产传输

本轮只创建本地包、源文件清单与校验值；没有上传、push、跨机复制或新建远程仓库。
长期结构：一个私有自定义主仓库 + 固定 commit 上游 + 独立大资产存储。

未来授权后的步骤：先 dry-run → 独立新接收目录 → 核验大小/SHA-256/清单 → 解包到全新目录 → 离线测试 → 再审批设备。
示意命令只显示操作，不在本轮执行：

```bash
rsync --archive --dry-run --itemize-changes --ignore-existing PACKAGE.tar.gz PACKAGE.tar.gz.sha256 USER@HOST:NEW_RECEIVE_DIRECTORY/
# 审查 dry-run 和接收目录无冲突后，另行执行实际 rsync，仍保留 --ignore-existing。
```

不用 --delete，不删除源数据、不自动覆盖冲突，不把源码传输授权扩大到权重/标定/研究数据。
本工程的包校验可发现未列文件、缺文件、损坏、链接、路径穿越和大文件；不能代替接收方的来源信任/访问权限审查。

## 包外资产：当前只列索引

- 当前装配适用的两臂 FR3 + Franka Gripper 模型、mesh、MJCF/USD 及完整引用闭包；型号/许可/外参尚需核实。
- D405/FlexiTac/TCP/双臂 base 的有效标定及设备角色/序列号配置；真实配置不进默认源码包。
- 选定 LingBot VLA 2 checkpoint：尚未定位，revision/大小/分片/checksum 全部 UNKNOWN；未复制任何权重。
- 恢复推理：匹配的模型配置、权重/adapter+基础模型关系、processor/tokenizer、归一化统计、相机/action/embodiment 映射、推理配置。
- 继续微调：上述推理资产 + 固定训练代码、训练配置、授权训练集/划分与统计来源，是否需要 teacher/其他基础资产按实际代码核验。
- 精确恢复训练：还需 optimizer/scheduler、global step、RNG、sampler/data 顺序、训练环境/分布式拓扑及保存语义。默认不复制这些大型资产。

Hugging Face snapshot 必须沿索引和链接核对被引用 blobs、分片总数/大小/摘要，不能只复制 snapshot symlink。未选定本地 checkpoint 前不能形成闭合资产清单。

## GitHub 发布准备

新独立本地 Git，不引入旧历史、不配置 remote。源码归档扫描秘密模式、路径、大小和文件用途；.gitignore 不代替历史审查。
私有发布前仍需审批：实验室代码归属/许可证、来源文档中的主机/用户名/路径是否应脱敏、真实配置/标定是否允许分享、分支历史复核。
禁止凭“private”推定允许上传研究内容。源码许可仍 UNASSIGNED；这也是当前发布阻塞项。
