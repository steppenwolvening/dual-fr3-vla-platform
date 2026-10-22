# π0.5 与 LingBot VLA 2：实现和验收边界

## 当前选择与证据

π0.5 主线选用官方 LeRobot 原生 PyTorch 实现，commit `5aa74557f84c54d4b458f8b9643c5aa2982acfed`，已安装版本0.6.2。理由是现有隔离环境已经能读取新 LeRobot v3 数据，并可直接使用真实 PI05Config、TrainPipelineConfig 和 dataset factory。OpenPI JAX 源码/环境保留为独立候选；不迁移其旧 SO-ARM101 权重，不声称两实现的优化器状态、归一化、checkpoint 可互换。模型主体 gemma_2b，action expert gemma_300m；本项目输出16维，内部最大32维，50步chunk，拟执行前5步后重新观测。三相机经模型预处理到224x224，状态/动作使用训练集q01/q99。

LingBot主线固定官方 `Robbyant/lingbot-vla-v2` commit `be969b8fd117fb70550c5d4bf4bc328211b5b1b6`。已经运行真实 VLADataset、FeatureTransform、Normalizer、torch DataLoader、pad_and_concat、prepare_state/action。为避免不相关训练初始化，测试以leaf package方式加载上游文件；没有mock数据加载、归一化或tensor实现。该数据测试运行于现有LeRobot数据环境，**不是**官方完整训练环境兼容认证。完整 tokenizer、collator、模型 forward 尚未运行。官方requirements要求torch2.8.0、transformers4.57.3等，不能在现有PI05环境中强行安装覆盖。

源文件SHA和权重文件清单分别固定在environments目录。`fetch_lingbot_audit.py`只取小型源码审计子集，不能用于完整推理。候选基础权重是 `lerobot/pi05_base@22c30e5b34f9e7ab738b1b34fc2fc5ecfe2d28f0` 和 `robbyant/lingbot-vla-v2-6b@11c703bf6a5c1f45b3b69168482da11fdbba53d7`；后者等待用户确认实际选型。未下载任何权重。PI05主权重约14.47GB；LingBot整个官方文件树约28.24GB，其中六个主模型shards合计约25.50GB，包含额外teacher资产时不能只按主模型算磁盘预算。PI05 tokenizer有独立Gemma许可门槛。模型许可不由源码Apache许可证自动推导。

## 数据与动作比较

| 项目 | π0.5 native | LingBot VLA 2 |
|---|---|---|
| 输入外部状态 | 左7/右7关节rad + 左/右opening width m | 相同物理状态，按机器人config拆分 |
| 三RGB相机 | head / left_wrist / right_wrist | camera_top / camera_wrist_left / camera_wrist_right |
| 动作监督 | sent绝对关节目标和绝对opening width | 关节目标减当前观测关节；夹爪保持绝对opening width |
| 动作归一化 | 训练集q01/q99 | 仅train有效chunk拟合的mean/std |
| 时间 | 10Hz，50步；尾部padding mask | 10Hz，50步；相同物理时间与尾部mask |
| 内部布局 | 模型padding到32维 | 类别槽位51维再padding到55维；有效16维，其余mask为无效 |
| 外部输出 | postprocessor反归一化得到16维绝对目标 | FeatureTransform.unapply逆映射/还原关节delta得到16维绝对目标 |
| 本轮验收 | 真实训练factory batch PASS_OFFLINE | 真实dataset/transform batch PASS_OFFLINE，完整processor/collator NOT_RUN |

LingBot arm类别在[0:14]，effector在[28:30]，不能取55维输出的前16维当物理动作。源代码默认relative_type是quaternion_local；机器人配置显式指定joint_delta，避免把关节向量当成姿态四元数。训练统计文件在所有划分读取前冻结，eval不拟合。两套统计不同，不能交叉复用。

## 配置、推理与共同执行边界

`prepare_pi05_training.py`生成实际可反序列化的TrainPipelineConfig；示例保存在configs/vla/pi05_train_config.json。候选使用expert-only、冻结视觉、batch1、累积8、BF16、gradient checkpointing、1000步/100步保存；未训练，不承诺能放入显存。示例占位路径必须替换。独立validation/test根需通过相同factory单独加载并使用冻结统计；当前训练配置内的自动eval关闭，**独立验证loss循环尚未接入**。resume需同一runtime commit、数据清单、统计、模型/optimizer/scheduler/随机状态及完整training-state checkpoint；只有safetensors不等于可恢复训练状态。

LingBot训练候选从同一commit的real_robot.yaml派生，配置路径与机器人映射独立。microbatch1/global8、gradient checkpointing只是资源探测候选。完整训练还需Qwen3-VL、相关depth/video teacher配置及资产；当前不提供单卡成功保证，validation loss/恢复流程亦待实际训练环境验收。配置保留teacher辅助监督，不能把它当作输入了真实D405或FlexiTac。

`vla_runtimes.py`包含真实模型加载和推理API。PI05明确严格加载safetensors，绕开上游from_pretrained吞掉加载异常的行为。两模型都要求本地已训练双FR3 checkpoint及外部profile，profile字段为model、robot=dual_fr3_franka_hand、physical_fields、output_semantics、training_split_manifest_sha256、normalization_sha256、所有checkpoint文件的SHA256。原始通用base权重不自动获得双FR3动作语义。模型加载/processor/rollout状态：**NOT_RUN**，无伪造成功。

`model_worker.py`在模型自己的Python环境运行，JSONL IPC隔离MuJoCo/Mink环境；`evaluate_vla.py`提供共同free_space_hold_v1任务、相同HOME初态/场景/三虚拟相机、20帧10Hz、相同命令验证/碰撞/超时门槛。成功条件是完整执行、无安全违规/碰撞、工具最大位移<2cm；这是专用自由空间保持任务，不是抓取成功率。GPU/rendering/实际模型未运行，当前无两模型成功率或延迟排名。工具输出中分别记录推理延迟、端到端延迟、完成度和墙钟频率；正式跨模型比较还需固定checkpoint、训练数据量、随机种子和重复episode。depth/tactile只保存在canonical中，未来编码器扩展不属于本轮已验证结果。

ChunkScheduler只接收已反归一化的物理动作，通过统一OfflineExecutor限位/速度/夹爪/观测关联/控制权检查；过期chunk撤权并hold，错维/NaN/未声明语义拒绝。不连接真机，也不允许各模型直连Franka驱动。
