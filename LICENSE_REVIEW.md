# 许可与发布审查

自定义代码仍为 UNASSIGNED_PENDING_OWNER_POLICY；用户已允许公开仓库，但未指定开源许可证，不擅自授予MIT/Apache等权利。公开可见与开源授权是不同决定。

已引入官方franka_description2.8.1的9个小型collision STL、URDF派生模型、参数、LICENSE及NOTICE，来源和SHA保存在assets/fr3_reference/provenance.json。Apache-2.0原始LICENSE/NOTICE保留；所有生成/修改记录在MODEL_REFERENCE.md。未引入旧SO-ARM101/Robotiq/手模型资产。

LingBot训练候选配置派生自Robbyant/lingbot-vla-v2，Apache-2.0源码许可，commit与原文件SHA见environments/lingbot-source.json；完整许可文本可使用assets/fr3_reference/LICENSE（同一Apache-2.0文本），第三方归属见THIRD_PARTY_NOTICES.md。小型上游测试源码在忽略目录.deps中，不纳入发布。PI05、LingBot权重及teacher/tokenizer许可独立审查，权重未下载和上传。

保留的v0.1.0历史含源机用户/主机/绝对路径与审计记录。发布前需要所有者确认是否可以公开这些历史信息，以及是否有实验室/其他权利人的分发限制。自动历史扫描只能识别已知模式，不能代替人工归属确认。

仓库创建、首次push、Release分别审批；目前无remote和上传。大权重、原始数据、二进制环境、缓存、证书及认证凭据均排除。
