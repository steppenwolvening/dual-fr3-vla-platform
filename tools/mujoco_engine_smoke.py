"""20 headless CPU steps, primitive model. NOT a Dual FR3 / IK / Twin acceptance test."""
import json
import sys
sys.dont_write_bytecode=True
import mujoco
import numpy as np
model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body pos="0 0 1"><freejoint/><geom type="sphere" size="0.02" mass="0.1"/></body></worldbody></mujoco>')
data=mujoco.MjData(model)
for _ in range(20):mujoco.mj_step(model,data)
assert np.isfinite(data.qpos).all() and data.time>0
print(json.dumps({'engine':mujoco.__version__,'steps':20,'headless':True,'input':'primitive sphere, not robot model','engine_smoke':'PASS_SIM','dual_fr3_mink':'BLOCKED','time_s':data.time}))
