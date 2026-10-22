# 双 FR3 + Franka Hand 仿真参考模型

来源 franka_description commit 02afaae282d4a8e10d7d2f781b23b3515c303ce5，robot_type=fr3，Apache-2.0。
只复制9个官方 collision STL（124406 bytes）、FR3 参数 YAML、LICENSE/NOTICE；由xacro2.1.1生成URDF，用MuJoCo3.9.0编译MJCF。没有Panda/L20/Robotiq资产。
实际左右FR3各7转动关节、Franka Hand各2移动手指；opening_width = finger1 + finger2；对称目标每指 width/2。
虚拟base位置 y=±0.55m，官方默认hand TCP=0.1034m，未包含D405/FlexiTac安装补偿；不是实验室实测标定。
模型具有34个碰撞geom，使用官方低面数collision mesh与手指box，未复制外观DAE。MuJoCo对mesh采用凸碰撞表示；碰撞验收仅针对本参考几何，不能替代实体装配安全验证。
位置伺服增益、armature、gravcomp是明确的仿真参数，未声称与实际Franka控制器动力学一致。
Mink1.2.0/DAQP使用ConfigurationLimit、VelocityLimit、跨臂及选定非邻接自碰撞约束；最终目标再经MuJoCo接触检查。未将相邻连接的固有重叠当环境碰撞。
FK测试独立组合官方URDF链；MJCF生成保留刚体变换17位精度，避免默认XML保存精度造成微小角度误差。
实际测试：单左、单右、双臂Cartesian位置+旋转IK；600步动力学无接触轨迹；关节越界拒绝。结果见validation/phase2/mujoco_mink.json。
