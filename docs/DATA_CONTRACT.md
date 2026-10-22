# Canonical v1 数据契约

本工程以 `fr3.canonical/1` JSON 对象为可执行契约，验证实现位于 contracts.py。JSON NaN/Inf、不匹配单位、错误维数、非单位四元数都拒绝。

## 状态和命令

RobotState 具有 state_id、source、stamp、controller_status、safety_status 和左右 arms。
每臂 canonical joint_names 为 `left_joint1..7` 或 `right_joint1..7`；实际驱动名称必须通过显式双射映射，不默认等于这些名称。
位置(rad)、速度(rad/s)、夹爪 opening_width(m)各自携带 measured/estimated/missing；缺失用 null，估计须 provenance。
EEF/TCP 包含 position_m、quaternion_xyzw、frame、child_frame、provenance；FK 需要记录适用模型和标定版本，不能隐含为实测。
valid_fields 必须与真实非缺失字段一致。source 指明 hardware/simulation/replay/synthetic；synthetic 测量值不是硬件测量。

RobotCommand 按 joint_position、eef_absolute、eef_delta、gripper 区分，固定 side_order=left,right；含 command_id、observation_id、owner、stamp。
EEF 增量以 reference frame 中 translation_m 和 rotation_vector_rad 表示，并声明左乘约定、base_state_id。位置目标和速度不可混用。
夹爪仅以 opening_width(m)表述；未实现 finger joint/百分比到宽度的未经核实转换。

事件 kind 分为 state、requested、sent、accepted、vr、rgb、depth、tactile、authority、quality。
requested→sent 可以有适配/限幅变化，但必须同 command_id/observation_id；accepted 必须有真实 ack_id、接口保证说明并精确关联已记录 sent command。
本版 synthetic 数据只有 requested 和 sent，没有伪造 accepted。send 返回值保存在独立语义字段，不叫硬件已执行。
控制状态当前为非空来源字符串，尚非厂商状态枚举标准化映射。

## 时间、对齐和样本标签

各事件包含 source_ns、received_ns、sequence、clock、receive_clock；每 stream 原采样率保存，不在记录时对齐。
各流从 sequence=0 开始，每流 source time 严格递增，接收时间不倒退；缺序号、缺流、RGB-depth 不成对使严格 validator 失败。
支持按 episode 显式提供设备时钟到公共 episode_monotonic 的仿射映射：scale、offset_ns、uncertainty_ns、有效源时间区间和 provenance。
实际时钟同步/漂移估计尚未实现；未知映射不得宣称同步。synthetic 使用单一已知时钟。

导出固定规则状态 fps，不自动补帧或重采样。图像选取满足图像最晚可能时刻 <= 观测最早可能时刻，且最坏年龄在显式容差内的最新样本。
标签通过 `--label requested|sent|accepted` 显式选择，以 observation_id 关联；command 必须在观测之后、时间容差以内，避免把未来测量状态当动作。
已验证例子选择 sent 仅因 synthetic 接口定义清楚；真实数据标签选择须结合控制器和模型训练代码审查，不能静默沿用。

LeRobot 导出字段顺序：左臂七位置、右臂七位置、左宽度、右宽度；float32，动作是绝对目标，维数 16 仅属于此 profile。
RGB 是原始 rgb8 → SDK PNG image → reader CHW /255，不缩放/裁剪。Depth/tactile 不导出为模型输入，完整留在 canonical source。
旧CLI单相机export-lerobot入口继续只接受train。v0.2的tools/export_splits.py支持多相机train/validation/test，所有episode ID跨三组互斥；统计仅从train拟合，validation/test严格复用冻结统计。合成fixture统计只用于管线测试，不是实际任务统计。
每次写入新目录，canonical_mapping.json 保存时钟映射、标签、loader pin、源数据摘要、字段/单位、相机处理及逐样本关联。

## 多模态原始数据

JSONL 存元数据；blobs 按内容 SHA-256 命名。
RGB shape=H,W,3、uint8/rgb8。Depth shape=H,W、uint16_le，必须 depth_scale_m、invalid_values、intrinsics、pair_id/valid，绝不当普通有损 RGB 视频保存。
设备实际其他 depth 类型目前不支持，应先扩展契约，不能强转后丢掉语义。
FlexiTac raw_reading 允许 uint8/uint16_le/float32_le、显式 shape；这只是通用存储能力，不声明真实硬件采用其中某种协议。
有 calibrated 数据必须给 calibration_version；无标定不得标为力/压力。保留原始数据及配对/标定元数据。
Blob 路径必须在 episode 内、不允许 symlink/绝对路径/`..`，校验字节大小与 SHA-256。

## 记录、背压和恢复

Recorder.submit 验证和复制小元数据、引用不可变 bytes、put_nowait；单事件与 blob 有大小上限。返回 False 表示本次被丢弃，调用方必须停止录制或记录质量事故。
默认队列 64 条，metadata 最大 1 MB、blob 最大 16 MB，因此最坏缓存仍可较大；实际吞吐/内存预算未在硬件上验收。
Python 验证、锁、复制仍有 CPU/调度开销，不能直接放进 libfranka 硬实时回调。
后台线程先写 blob、fsync，再写完整 JSONL 行并 fsync。close 在非控制线程 drain；失败/背压标 FAILED/DEGRADED，不报告完整成功。
状态 OPEN 表示录制中或异常中断，完整关闭为 CLOSED。RECOVERED_REVIEW_REQUIRED 永不自动满足严格验收。
recover 只复制合法完整前缀到新目录，原数据不动；孤立 blob 可留在原目录，不自动删除。
