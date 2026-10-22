"""Pure conversion for a FUTURE read-only ROS JointState subscriber; no ROS imports.

Use separate per-arm stamps/records until clock-aligned assembly is explicitly performed.
This function never derives gripper width or TCP from unverified finger/FK assumptions.
"""
from .contracts import require, vector, JOINTS


def map_joint_state(*, side, driver_names, positions, velocities, driver_to_canonical):
    require(side in JOINTS, 'arm side')
    require(len(driver_names)==len(set(driver_names)), 'duplicate ROS names')
    require(set(driver_to_canonical.values())==set(JOINTS[side]) and len(driver_to_canonical)==7, 'explicit bijective arm mapping required')
    require(set(driver_to_canonical).issubset(driver_names), 'ROS message missing mapped joints')
    vector(positions,len(driver_names),'ROS positions')
    require(len(velocities) in (0,len(driver_names)), 'ROS velocity dimension')
    if velocities:vector(velocities,len(driver_names),'ROS velocities')
    indices={driver_to_canonical[name]:i for i,name in enumerate(driver_names) if name in driver_to_canonical}
    return {'joint_names':JOINTS[side],
            'position':{'status':'measured','value':[positions[indices[n]] for n in JOINTS[side]],'unit':'rad'},
            'velocity':{'status':'measured' if velocities else 'missing','value':[velocities[indices[n]] for n in JOINTS[side]] if velocities else None,'unit':'rad/s'},
            'gripper':{'status':'missing','value':None,'unit':'m','quantity':'opening_width'},
            'eef':None,'tcp':None,'valid_fields':['position','velocity'] if velocities else ['position']}
