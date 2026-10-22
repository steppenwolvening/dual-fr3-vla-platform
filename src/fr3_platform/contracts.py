"""Versioned, JSON-native contracts; no hardware or optional framework imports."""
from dataclasses import dataclass
import json
import math

VERSION = 'fr3.canonical/1'
SIDES = ('left', 'right')
SOURCES = ('hardware', 'simulation', 'replay', 'synthetic')
JOINTS = {side: [f'{side}_joint{i}' for i in range(1, 8)] for side in SIDES}

class ContractError(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise ContractError(reason)

def finite_tree(value):
    if isinstance(value, float):
        require(math.isfinite(value), 'NaN/Inf forbidden')
    elif isinstance(value, dict):
        require(all(isinstance(k, str) for k in value), 'JSON keys must be strings')
        for v in value.values(): finite_tree(v)
    elif isinstance(value, (list, tuple)):
        for v in value: finite_tree(v)
    else:
        require(value is None or isinstance(value, (str, int, bool)), 'non-JSON value')

def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

def vector(v, size, name):
    require(isinstance(v, list) and len(v) == size and all(number(x) for x in v), f'invalid {name}: expected {size} finite numbers')

def text(v, name):
    require(isinstance(v, str) and bool(v) and v != 'UNCONFIGURED', f'{name} not configured')

def stamp(s):
    for key in ('source_ns', 'received_ns', 'sequence'):
        require(type(s.get(key)) is int and s[key] >= 0, f'invalid stamp.{key}')
    text(s.get('clock'), 'clock domain')
    text(s.get('receive_clock'), 'receive clock domain')

def pose(p):
    vector(p.get('position_m'), 3, 'position_m')
    vector(p.get('quaternion_xyzw'), 4, 'quaternion_xyzw')
    require(abs(sum(v*v for v in p['quaternion_xyzw']) - 1) < 1e-5, 'non-unit quaternion')
    text(p.get('frame'), 'pose frame')
    text(p.get('child_frame'), 'child frame')
    text(p.get('provenance'), 'pose measured/FK provenance')

def measurement(m, size, unit):
    require(m.get('status') in ('measured', 'estimated', 'missing'), 'measurement status')
    require(m.get('unit') == unit, f'expected unit {unit}')
    if m['status'] == 'missing': require(m.get('value') is None, 'missing measurement must be null')
    elif size == 1: require(number(m.get('value')), 'measurement scalar')
    else: vector(m.get('value'), size, 'measurement vector')
    if m['status'] == 'estimated': text(m.get('provenance'), 'estimate provenance')

@dataclass(frozen=True)
class RobotState:
    payload: dict

    def validate(self):
        p = self.payload
        finite_tree(p)
        require(p.get('source') in SOURCES, 'state source')
        text(p.get('state_id'), 'state id')
        stamp(p['stamp'])
        require(set(p['arms']) == set(SIDES), 'both arms required')
        for side in SIDES:
            a = p['arms'][side]
            require(a['joint_names'] == JOINTS[side], 'canonical joint order mismatch')
            measurement(a['position'], 7, 'rad')
            measurement(a['velocity'], 7, 'rad/s')
            measurement(a['gripper'], 1, 'm')
            require(a['gripper'].get('quantity') == 'opening_width', 'width is not finger position or percent')
            if a['gripper']['value'] is not None: require(a['gripper']['value'] >= 0, 'negative width')
            for field in ('eef', 'tcp'):
                if a.get(field) is not None: pose(a[field])
            expected = [k for k in ('position', 'velocity', 'gripper') if a[k]['status'] != 'missing']
            expected += [k for k in ('eef', 'tcp') if a.get(k) is not None]
            require(sorted(a.get('valid_fields', [])) == sorted(expected), 'valid_fields disagrees with measurements')
        text(p.get('controller_status'), 'controller status')
        text(p.get('safety_status'), 'safety status')
        return self

    def to_json(self):
        self.validate()
        return json.dumps(self.payload, allow_nan=False, sort_keys=True)

@dataclass(frozen=True)
class RobotCommand:
    payload: dict

    def validate(self):
        p = self.payload
        finite_tree(p)
        stamp(p['stamp'])
        text(p.get('command_id'), 'command id')
        require(p.get('owner') in ('vr', 'vla', 'replay'), 'command owner')
        require(p.get('kind') in ('joint_position', 'eef_absolute', 'eef_delta', 'gripper'), 'command kind')
        require(p.get('side_order') == list(SIDES), 'side order must be left, right')
        require(set(p.get('arms', {})) == set(SIDES), 'two explicit arm commands required')
        text(p.get('observation_id'), 'causal observation id')
        for side in SIDES:
            a = p['arms'][side]
            if p['kind'] == 'joint_position':
                require(a.get('joint_names') == JOINTS[side], 'command joint mapping')
                require(a.get('unit') == 'rad', 'joint target unit')
                vector(a.get('target'), 7, 'joint target')
            elif p['kind'] == 'eef_absolute': pose(a['pose'])
            elif p['kind'] == 'eef_delta':
                vector(a.get('translation_m'), 3, 'delta translation')
                vector(a.get('rotation_vector_rad'), 3, 'delta rotation')
                text(a.get('frame'), 'delta frame')
                text(a.get('base_state_id'), 'delta application state')
                require(a.get('composition') == 'left_multiply_in_reference_frame', 'rotation convention')
            if p['kind'] == 'gripper' or 'gripper' in a:
                g = a['gripper']
                require(g.get('quantity') == 'opening_width' and g.get('unit') == 'm', 'gripper quantity/unit')
                require(number(g.get('target')) and g['target'] >= 0, 'gripper width')
        return self

    def to_json(self):
        self.validate()
        return json.dumps(self.payload, allow_nan=False, sort_keys=True)


def validate_event(e):
    finite_tree(e)
    require(e.get('schema') == VERSION, 'schema version')
    text(e.get('id'), 'event id')
    text(e.get('stream'), 'stream name')
    require(e.get('source') in SOURCES, 'event source')
    stamp(e['stamp'])
    kind, p = e['kind'], e['payload']
    if kind == 'state':
        RobotState(p).validate()
        require(p['source'] == e['source'] and p['stamp'] == e['stamp'] and p['state_id'] == e['id'], 'state/envelope mismatch')
    elif kind in ('requested', 'sent', 'accepted'):
        RobotCommand(p['command']).validate()
        if kind != 'requested': text(p.get('interface_semantics'), 'send/accept guarantee')
        if kind == 'accepted': text(p.get('controller_ack_id'), 'actual controller acknowledgement')
    elif kind in ('rgb', 'depth', 'tactile'):
        b = p['blob']
        text(b.get('path'), 'blob path')
        require(type(b.get('size')) is int and b['size'] > 0, 'blob size')
        require(isinstance(b.get('sha256'), str) and len(b['sha256']) == 64 and all(c in '0123456789abcdef' for c in b['sha256']), 'blob digest')
        require(isinstance(p.get('shape'), list) and all(type(n) is int and n > 0 for n in p['shape']), 'shape')
        if kind in ('rgb', 'depth'):
            text(p.get('pair_id'), 'RGB/depth association')
            require(type(p.get('valid')) is bool, 'sensor validity')
            require(p.get('intrinsics') is not None, 'intrinsics required (UNCONFIGURED allowed for uncalibrated raw)')
        if kind == 'rgb': require(p.get('dtype') == 'uint8' and len(p['shape']) == 3 and p['shape'][-1] == 3 and p.get('encoding') == 'rgb8', 'RGB format')
        if kind == 'depth':
            require(p.get('dtype') == 'uint16_le' and len(p['shape']) == 2, 'lossless depth format')
            require(number(p.get('depth_scale_m')) and p['depth_scale_m'] > 0, 'depth scale')
            require(isinstance(p.get('invalid_values'), list) and bool(p['invalid_values']), 'depth invalid rule')
        if kind == 'tactile':
            require(p.get('quantity') == 'raw_reading', 'raw tactile is not force')
            require(p.get('dtype') in ('uint8', 'uint16_le', 'float32_le'), 'tactile dtype')
            if p.get('calibrated') is not None: text(p.get('calibration_version'), 'tactile calibration')
        size = math.prod(p['shape']) * {'uint8':1, 'uint16_le':2, 'float32_le':4}[p['dtype']]
        require(size == b['size'], 'blob bytes/shape mismatch')
    elif kind == 'vr':
        require(type(p.get('tracking')) is bool and type(p.get('deadman')) is bool, 'VR tracking/deadman')
        text(p.get('tracking_origin'), 'tracking origin')
    elif kind in ('authority', 'quality'):
        text(p.get('reason'), 'event reason')
    else: raise ContractError(f'unknown event kind: {kind}')
    return e
