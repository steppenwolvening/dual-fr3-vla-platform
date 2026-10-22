"""Read-only environment checks. Never runs an installer or imports device SDKs."""
import importlib.metadata as metadata
import os
import platform
import sys


def check():
    packages={}
    for name in ('mujoco','mink','numpy','lerobot','torch','pyrealsense2','isaaclab','isaacsim','vuer'):
        try:packages[name]=metadata.version(name)
        except metadata.PackageNotFoundError:packages[name]='UNRESOLVED'
    ros=bool(os.environ.get('ROS_DISTRO') or os.environ.get('AMENT_PREFIX_PATH') or '/opt/ros/' in os.environ.get('PYTHONPATH','') or '/opt/ros/' in os.environ.get('LD_LIBRARY_PATH',''))
    isolated=bool(os.environ.get('CONDA_PREFIX') or os.environ.get('VIRTUAL_ENV') or sys.prefix!=sys.base_prefix or 'envs' in sys.executable.split('/'))
    risks=[]
    if ros and isolated:risks.append('ROS environment inherited by Conda/venv process; use clean process environment, no global PYTHONPATH bridge')
    return {'python':platform.python_version(),'interpreter':sys.executable,'packages':packages,'ros_environment_present':ros,
            'isolated_interpreter':isolated,'risks':risks,'hardware_execution':'DISABLED_IN_THIS_BUILD'}
