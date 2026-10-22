"""Explicit synthetic fixtures, NEVER a fallback for failed hardware drivers."""
import copy
import struct
from .contracts import VERSION, JOINTS, SIDES
from .data import Recorder, validate


def timestamp(t, seq):
    return {'source_ns':t, 'received_ns':t+1000, 'sequence':seq, 'clock':'host_monotonic', 'receive_clock':'host_monotonic'}


def state(t=1_000_000_000, seq=0):
    def measure(value, unit): return {'value': value, 'unit':unit, 'status':'measured'}
    arms = {}
    for side in SIDES:
        arms[side] = {'joint_names':JOINTS[side], 'position':measure([0.01*seq]*7,'rad'),
                      'velocity':measure([0.1]*7,'rad/s'), 'gripper':{**measure(0.04,'m'),'quantity':'opening_width'},
                      'eef':None, 'tcp':None, 'valid_fields':['position','velocity','gripper']}
    return {'state_id':f'state-{seq}', 'stamp':timestamp(t,seq), 'source':'synthetic', 'arms':arms, 'controller_status':'synthetic_only', 'safety_status':'no_hardware'}


def command(t=1_001_000_000, seq=0):
    return {'stamp':timestamp(t,seq), 'command_id':f'command-{seq}', 'observation_id':f'state-{seq}',
            'owner':'vr', 'kind':'joint_position', 'side_order':list(SIDES),
            'arms':{s:{'joint_names':JOINTS[s], 'unit':'rad', 'target':[0.01*seq+0.0001]*7,
                       'gripper':{'quantity':'opening_width','unit':'m','target':0.04}} for s in SIDES}}


def event(kind, stream, t, seq, payload):
    return {'schema':VERSION, 'id':f'{stream}-{seq}', 'kind':kind, 'stream':stream,
            'source':'synthetic', 'stamp':timestamp(t,seq), 'payload':payload}


def metadata():
    return {'schema':VERSION, 'episode_id':'synthetic-fixture', 'synthetic':True, 'task':'synthetic offline contract validation',
            'outcome':'synthetic_only', 'split':'train', 'code_version':'0.1.0', 'config_version':'synthetic-v1',
            'calibration_version':'SYNTHETIC_NOT_PHYSICAL',
            'streams':['state','requested','sent','rgb','depth','tactile','vr','authority'],
            'clocks':{'host_monotonic':{'scale':1.0,'offset_ns':0,'uncertainty_ns':0,
                       'common_clock':'episode_monotonic','provenance':'synthetic single clock',
                       'valid_from_ns':0,'valid_to_ns':10_000_000_000}}}


def make_episode(root, frames=8):
    if not 2 <= frames <= 50: raise ValueError('synthetic fixture bounded to 2..50 frames')
    with Recorder(root, metadata(), capacity=frames*8+1) as rec:
        for i in range(frames):
            t = 1_000_000_000+i*100_000_000
            values = [('state','state',t,state(t,i),None),
                      ('vr','vr',t,{'tracking':True,'deadman':True,'tracking_origin':'synthetic_origin'},None),
                      ('authority','authority',t,{'owner':'vr','reason':'synthetic lease'},None)]
            common = {'pair_id':f'camera-pair-{i}', 'valid':True, 'intrinsics':{'source':'synthetic','fx':4,'fy':4,'cx':1.5,'cy':1.5}, 'extrinsics':'UNCONFIGURED'}
            values += [('rgb','rgb',t,{**common,'dtype':'uint8','shape':[4,4,3],'encoding':'rgb8'},bytes([i*10,20,30]*16)),
                       ('depth','depth',t,{**common,'dtype':'uint16_le','shape':[4,4],'depth_scale_m':0.001,'invalid_values':[0]},struct.pack('<16H',*([100+i]*16))),
                       ('tactile','tactile',t,{'quantity':'raw_reading','dtype':'uint16_le','shape':[2], 'calibrated':None,'calibration_version':'UNCONFIGURED'},struct.pack('<2H',i,i+1))]
            cmd = command(t+1_000_000,i)
            values += [('requested','requested',t+1_000_000,{'command':cmd},None),
                       ('sent','sent',t+2_000_000,{'command':copy.deepcopy(cmd),'interface_semantics':'synthetic sink received target; no hardware execution'},None)]
            for kind,stream,ts,payload,blob in values:
                if not rec.submit(event(kind,stream,ts,i,payload),blob): raise RuntimeError('synthetic queue overflow')
    return validate(root)
