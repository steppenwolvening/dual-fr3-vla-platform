"""Fail-closed offline arbitration. No real robot execution implementation."""
import copy
from .contracts import RobotCommand, RobotState, require, number, vector, SIDES

class OfflineExecutor:
    """Single submission boundary for synthetic/simulation sinks, never a ROS driver."""
    def __init__(self, sink, limits, clock='host_monotonic'):
        require(getattr(sink, 'source', None) in ('synthetic', 'simulation'), 'hardware backend forbidden in this build')
        self.sink, self.limits, self.clock = sink, limits, clock
        self.owner = None
        self.expires_ns = 0
        self.last_seq = -1
        self.last_sent = None
        self.events = []
        self.stopped = False

    def acquire(self, owner, now_ns, lease_ns):
        require(owner in ('vr', 'vla', 'replay') and type(lease_ns) is int and 0 < lease_ns <= 1_000_000_000, 'lease')
        self.watchdog(now_ns)
        require(not self.stopped and self.owner in (None, owner), 'authority unavailable')
        if self.owner is None:
            self.last_seq = -1
            self.last_sent = None
        self.owner, self.expires_ns = owner, now_ns + lease_ns
        self.events.append({'owner': owner, 'reason': 'acquired'})

    def release(self, reason='released'):
        self.owner = None
        self.last_sent = None
        self.events.append({'owner': None, 'reason': reason, 'physical_stop_verified': False})

    def watchdog(self, now_ns, connected=True, tracking=True, deadman=True, estop=False):
        if estop:
            self.stopped = True
        if estop or not connected or not tracking or not deadman or now_ns >= self.expires_ns:
            self.release('estop' if estop else 'lease/deadman/tracking/connection lost')
        # This only revokes software authority; external certified stop path remains required.

    def submit(self, command, state, now_ns):
        RobotCommand(command).validate()
        RobotState(state).validate()
        self.watchdog(now_ns)
        require(not self.stopped and self.owner == command['owner'], 'no exclusive authority')
        require(state['source'] in ('synthetic', 'simulation'), 'offline state required')
        require(command['observation_id'] == state['state_id'], 'command/current-state association mismatch')
        require(command['kind'] == 'joint_position', 'EEF requires verified IK; unsupported execution type')
        s, cs = state['stamp'], command['stamp']
        require(cs['clock'] == s['clock'] == self.clock, 'unmapped command/state clock')
        require(type(self.limits.get('max_age_ns')) is int and self.limits['max_age_ns'] > 0, 'age limit unconfigured')
        require(all(0 <= now_ns - x['source_ns'] <= self.limits['max_age_ns'] for x in (s, cs)), 'stale or future command/state')
        require(cs['sequence'] > self.last_seq, 'out-of-order command')
        text_source = self.limits.get('source')
        require(text_source and text_source != 'UNCONFIGURED', 'limit provenance required')
        dt = (cs['source_ns'] - (self.last_sent['stamp']['source_ns'] if self.last_sent else s['source_ns'])) / 1e9
        require(dt > 0, 'positive command horizon required')
        require(number(self.limits.get('min_period_s')) and dt >= self.limits['min_period_s'] > 0, 'rate limit')
        for side in SIDES:
            lim = self.limits[side]
            for name in ('lower', 'upper', 'velocity'): vector(lim[name], 7, name)
            require(all(lo < hi and v > 0 for lo,hi,v in zip(lim['lower'],lim['upper'],lim['velocity'])), 'invalid limits')
            require(state['arms'][side]['position']['status'] != 'missing', 'current position required')
            base = self.last_sent['arms'][side]['target'] if self.last_sent else state['arms'][side]['position']['value']
            for q, prev, lo, hi, vmax in zip(command['arms'][side]['target'], base, lim['lower'],lim['upper'],lim['velocity']):
                require(lo <= q <= hi and abs(q-prev) <= vmax*dt + 1e-12, 'position/velocity limit')
            if 'gripper' in command['arms'][side]:
                g = lim.get('gripper')
                require(isinstance(g, dict) and all(number(g.get(k)) for k in ('min_m','max_m','speed_m_s')), 'gripper limits unconfigured')
                target = command['arms'][side]['gripper']['target']
                prev = state['arms'][side]['gripper']['value']
                if self.last_sent and 'gripper' in self.last_sent['arms'][side]: prev = self.last_sent['arms'][side]['gripper']['target']
                require(number(prev) and g['min_m'] <= target <= g['max_m'] and g['speed_m_s'] > 0 and abs(target-prev) <= dt*g['speed_m_s']+1e-12, 'gripper limit')
        result = self.sink.send(copy.deepcopy(command))
        self.last_seq, self.last_sent = cs['sequence'], copy.deepcopy(command)
        return {'command': copy.deepcopy(command), 'interface_semantics': 'submitted_to_offline_sink; not hardware execution', 'sink_result': result}
