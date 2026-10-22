"""Append-only canonical episodes with lossless sidecars and bounded async recording."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import threading
from .contracts import VERSION, SOURCES, validate_event, require, finite_tree, number


def dumps(value):
    finite_tree(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def read_json(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_child(root, relative):
    p = Path(relative)
    require(not p.is_absolute() and '..' not in p.parts and bool(p.parts), 'unsafe relative path')
    root = Path(root).resolve()
    child = root / p
    require(not any(x.is_symlink() for x in [child, *child.parents] if x != root.parent), 'symlink not allowed')
    require(child.resolve().is_relative_to(root), 'path escaped episode')
    return child


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('x') as f:
        f.write(dumps(value) + '\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def validate_meta(meta):
    finite_tree(meta)
    require(meta.get('schema') == VERSION, 'episode schema')
    require(meta.get('split') in ('train', 'validation', 'test'), 'explicit split required')
    for key in ('episode_id', 'task', 'outcome', 'code_version', 'config_version', 'calibration_version'):
        require(isinstance(meta.get(key), str) and meta[key], f'missing {key}')
    require(type(meta.get('synthetic')) is bool, 'synthetic label required')
    require(isinstance(meta.get('streams'), list) and len(set(meta['streams'])) == len(meta['streams']) and bool(meta['streams']), 'declared streams required')
    if 'stream_sources' in meta:
        require(set(meta['stream_sources'])==set(meta['streams']), 'complete stream source map required')
        require(all(v in SOURCES for v in meta['stream_sources'].values()), 'invalid stream source')
        require(meta.get('contains_synthetic') == ('synthetic' in meta['stream_sources'].values()), 'contains_synthetic flag mismatch')
    require(isinstance(meta.get('clocks'), dict), 'clock map declarations required')
    for name, c in meta['clocks'].items():
        require(c.get('common_clock') == 'episode_monotonic', 'common clock')
        require(number(c.get('scale')) and c['scale'] > 0 and type(c.get('offset_ns')) is int, 'clock map')
        require(type(c.get('uncertainty_ns')) is int and c['uncertainty_ns'] >= 0, 'clock error bound')
        require(isinstance(c.get('provenance'), str) and bool(c['provenance']), 'clock map evidence')
        require(type(c.get('valid_from_ns')) is int and type(c.get('valid_to_ns')) is int and 0 <= c['valid_from_ns'] <= c['valid_to_ns'], 'clock validity interval')


def validate_source(event, meta):
    if 'stream_sources' in meta:
        require(event['source']==meta['stream_sources'][event['stream']], 'declared stream source mismatch')
    else:
        require((event['source']=='synthetic')==meta['synthetic'], 'synthetic flag mismatch')


class Recorder:
    """submit never waits for disk. Rejected events counted; producer must react to False.

    Not hard realtime: Python lock, validation and serialization have finite-size CPU costs.
    Pass immutable bytes. Close only outside the control callback. Each committed line is fsynced.
    """
    def __init__(self, root, metadata, capacity=64, max_event_bytes=1_000_000, max_blob_bytes=16_000_000):
        validate_meta(metadata)
        require(type(capacity) is int and capacity > 0, 'queue capacity')
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        (self.root/'blobs').mkdir()
        self.metadata = copy.deepcopy(metadata)
        atomic_json(self.root/'episode.json', {**self.metadata, 'status': 'OPEN'})
        self.queue = queue.Queue(capacity)
        self.lock = threading.Lock()
        self.closed = False
        self.error = None
        self.accepted = self.dropped = self.written = 0
        self.max_event_bytes, self.max_blob_bytes = max_event_bytes, max_blob_bytes
        self.thread = threading.Thread(target=self._run, name='canonical-writer', daemon=True)
        self.thread.start()

    def submit(self, event, blob=None):
        event = copy.deepcopy(event)
        if blob is not None:
            require(isinstance(blob, bytes) and 0 < len(blob) <= self.max_blob_bytes, 'immutable bounded blob required')
            h = digest(blob)
            event['payload']['blob'] = {'path': f'blobs/{h}.bin', 'size': len(blob), 'sha256': h}
        validate_event(event)
        require(event['stream'] in self.metadata['streams'], 'undeclared stream')
        validate_source(event, self.metadata)
        require(blob is not None or event['kind'] not in ('rgb','depth','tactile'), 'sensor bytes required')
        line = (dumps(event)+'\n').encode()
        require(len(line) <= self.max_event_bytes, 'event too large')
        with self.lock:
            require(not self.closed, 'recorder closed')
            if self.error: raise OSError(self.error)
            try: self.queue.put_nowait((line, blob, event))
            except queue.Full:
                self.dropped += 1
                return False
            self.accepted += 1
            return True

    def _run(self):
        try:
            with (self.root/'events.jsonl').open('xb') as f:
                while True:
                    item = self.queue.get()
                    if item is None: break
                    line, blob, event = item
                    if blob is not None:
                        path = safe_child(self.root, event['payload']['blob']['path'])
                        if not path.exists():
                            with path.open('xb') as out:
                                out.write(blob); out.flush(); os.fsync(out.fileno())
                    f.write(line); f.flush(); os.fsync(f.fileno())
                    self.written += 1
        except Exception as e:
            self.error = f'{type(e).__name__}: {e}'

    def close(self):
        with self.lock:
            require(not self.closed, 'already closed')
            self.closed = True
        while self.thread.is_alive():
            try:
                self.queue.put(None, timeout=0.05)
                break
            except queue.Full: pass
        self.thread.join()
        summary = {**self.metadata, 'status': 'FAILED' if self.error else ('DEGRADED' if self.dropped else 'CLOSED'),
                   'accepted': self.accepted, 'written': self.written, 'dropped': self.dropped, 'error': self.error}
        atomic_json(self.root/'episode.json', summary)
        if self.error: raise OSError(self.error)
        return summary

    def __enter__(self): return self
    def __exit__(self, kind, value, traceback):
        if kind is not None: self.error = f'producer exception: {kind.__name__}'
        self.close()


class DatasetReader:
    def __init__(self, root):
        self.root = Path(root)
        self.meta = read_json(self.root/'episode.json')
        validate_meta(self.meta)

    def __iter__(self):
        with (self.root/'events.jsonl').open('rb') as f:
            for index, line in enumerate(f, 1):
                require(line.endswith(b'\n'), f'torn final record at line {index}')
                e = json.loads(line, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
                validate_event(e)
                yield e

    def blob(self, event):
        b = event['payload']['blob']
        data = safe_child(self.root, b['path']).read_bytes()
        require(len(data) == b['size'] and digest(data) == b['sha256'], 'blob checksum/size mismatch')
        return data

    def common_time(self, event):
        s = event['stamp']
        m = self.meta['clocks'].get(s['clock'])
        require(m is not None, f"unmapped clock {s['clock']}")
        require(m['valid_from_ns'] <= s['source_ns'] <= m['valid_to_ns'], 'clock map expired')
        return round(s['source_ns']*m['scale'])+m['offset_ns'], m['uncertainty_ns']


def validate(root):
    errors, gaps, seen, prev, streams, pairs = [], [], set(), {}, set(), {}
    count = 0
    observations, requested, sent = {}, {}, {}
    try:
        r = DatasetReader(root)
        if r.meta.get('status') != 'CLOSED': errors.append(f"episode status {r.meta.get('status')}")
        if r.meta.get('dropped', 0): errors.append('recorder backpressure loss')
        for e in r:
            count += 1
            require(e['id'] not in seen, 'duplicate event id')
            seen.add(e['id']); streams.add(e['stream'])
            require(e['stream'] in r.meta['streams'], 'undeclared stream')
            validate_source(e, r.meta)
            s, key = e['stamp'], e['stream']
            r.common_time(e)
            if key in prev:
                p = prev[key]
                require(s['clock']==p['clock'] and s['receive_clock']==p['receive_clock'], 'clock domain changed within stream')
                require(s['source_ns'] > p['source_ns'] and s['received_ns'] >= p['received_ns'] and s['sequence'] > p['sequence'], 'non-monotonic timestamp/sequence')
                if s['sequence'] != p['sequence']+1: gaps.append({'stream': key, 'after':p['sequence'], 'before':s['sequence']})
            elif s['sequence'] != 0: gaps.append({'stream': key, 'missing_initial':s['sequence']})
            prev[key] = s
            if 'blob' in e['payload']: r.blob(e)
            if e['kind'] in ('rgb','depth'):
                pair = pairs.setdefault(e['payload']['pair_id'], {})
                require(e['kind'] not in pair, 'duplicate RGB/depth pair member')
                pair[e['kind']] = e['id']
                if not e['payload']['valid']: errors.append('invalid sensor frame: '+e['id'])
            if e['kind'] == 'state': observations[e['id']] = e
            if e['kind'] in ('requested','sent','accepted'):
                cmd = e['payload']['command']
                require(cmd['observation_id'] in observations, 'command references missing/future state')
                ot, ou = r.common_time(observations[cmd['observation_id']])
                ct, cu = r.common_time({'stamp': cmd['stamp']})
                et, eu = r.common_time(e)
                require(ot+ou <= ct-cu and ct+cu <= et-eu, 'command/event timing before observation or command')
                cid = cmd['command_id']
                if e['kind'] == 'requested':
                    require(cid not in requested, 'duplicate requested command id')
                    requested[cid] = cmd
                elif e['kind'] == 'sent':
                    require(cid in requested, 'sent without recorded request')
                    require(cid not in sent, 'duplicate sent command id')
                    require(cmd['observation_id'] == requested[cid]['observation_id'], 'adaptation changed observation association')
                    sent[cid] = cmd
                else:
                    require(cid in sent and cmd == sent[cid], 'ack does not match recorded sent command')
        if gaps: errors.append('sequence gaps')
        missing = sorted(set(r.meta['streams'])-streams)
        if missing: errors.append('missing streams: '+','.join(missing))
        if any(set(p) != {'rgb','depth'} for p in pairs.values()): errors.append('unpaired RGB/depth frames')
        if count != r.meta.get('written'): errors.append('written count mismatch')
        if not count: errors.append('empty episode')
    except (ValueError, KeyError, TypeError, OSError) as e:
        errors.append(f'{type(e).__name__}: {e}')
    return {'ok': not errors, 'events': count, 'errors': errors, 'sequence_gaps': gaps}


def replay(root):
    """Yield recorded events only; no actuator callback or hardware connection."""
    report = validate(root)
    require(report['ok'], dumps(report))
    yield from DatasetReader(root)


def recover(source, destination):
    """Copy only complete, valid prefix into NEW directory; never repair original in place."""
    r = DatasetReader(source)
    meta = {k:v for k,v in r.meta.items() if k not in ('status','accepted','written','dropped','error')}
    meta['recovery'] = {'source_episode_id': meta['episode_id'], 'semantics':'valid prefix only; completeness not established'}
    n = 0
    with Recorder(destination, meta, capacity=1024) as out:
        try:
            for event in r:
                blob = r.blob(event) if 'blob' in event['payload'] else None
                require(out.submit(event, blob), 'recovery queue full')
                n += 1
        except (ValueError, KeyError, TypeError, OSError) as e:
            reason = str(e)
        else: reason = 'source ended cleanly; recovery still requires review'
    path = Path(destination)/'episode.json'
    result = read_json(path)
    result['status'] = 'RECOVERED_REVIEW_REQUIRED'
    result['recovery']['reason'] = reason
    atomic_json(path, result)
    return {'events_recovered': n, 'reason':reason, 'status':result['status']}


def causal_latest(reader, events, observation, tolerance_ns):
    """Conservative clock-error-aware alignment: never choose potentially future input."""
    t, error = reader.common_time(observation)
    candidates = []
    for e in events:
        s, uncertainty = reader.common_time(e)
        if s+uncertainty <= t-error and t+error-(s-uncertainty) <= tolerance_ns:
            candidates.append((s,e))
    require(bool(candidates), 'no causal sample inside alignment tolerance')
    return max(candidates, key=lambda x:x[0])[1]
