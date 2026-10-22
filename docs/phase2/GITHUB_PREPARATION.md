# Public GitHub 发布准备

用户最新指示允许公开仓库，覆盖原prompt默认Private。浏览器已确认登录个人账号steppenwolvening；计划名称 `steppenwolvening/dual-fr3-vla-platform`。gh未安装，不为此安装新工具；可用已登录浏览器创建空仓库，再使用已有Git认证方式（不得打印或复制token）。

本地分支codex/v0.2-integration，保留v0.1.0 tag及完整开发历史。当前无remote、无push、无Release。首次上传计划将审核后的开发HEAD推送为远程main并带v0.1.0基线tag；**不使用--mirror**，不自动上传artifact目录。大权重、真实/合成数据集、缓存、Conda/venv、证书/凭据均不上传。小型官方collision STL、许可证、参数、生成的参考模型随代码上传，源模型不是lab校准。

审查对象包括所有可达历史blob，不能只扫HEAD。`tools/audit_release.py`报告已知token/私钥/认证URL/禁入文件模式；报告在artifacts/release-audit.json。完整v0.1历史包含本机账号aning、主机名、/home/aning路径和来源审计，保留历史意味着这些信息随首次push公开。未发现已知凭据模式不代表没有任何敏感内容。代码/实验室归属及历史路径是否可公开仍需所有者确认。项目暂不擅自添加开源LICENSE，第三方许可已保留。

按用户最新prompt第4、16节：创建远程仓库、首次push、发布Release各需单独批准。审批顺序：

1. 具体空仓库：steppenwolvening/dual-fr3-vla-platform，Public，无自动README/License/gitignore。创建不上传本地源码。
2. 首次push：指定经审核commit与v0.1.0 tag；用户确认有权公开此代码、官方资产及保留的历史元数据。
3. Release：目前平台仍PARTIAL，只适合清楚标注开发基线的Pre-release；必须再次确认tag、commit、Release notes与将上传的源码归档。正式v0.2.0稳定Release尚未满足整体验收，不伪报通过。

`tools/package_v2.py`为干净已提交HEAD生成源码tar.gz、逐文件SHA清单、Git bundle、包外SHA和解包后回归证据。Git bundle保留历史；bundle/数据/模型不自动加入远程仓库。Docker未开始。
