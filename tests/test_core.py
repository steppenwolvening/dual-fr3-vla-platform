import copy
import json
import os
from pathlib import Path
import queue
import tempfile
import unittest
from unittest.mock import patch

from fr3_platform.contracts import RobotState, RobotCommand, ContractError
from fr3_platform.control import OfflineExecutor
from fr3_platform.data import Recorder, DatasetReader, validate, replay, recover, causal_latest, atomic_json, safe_child
from fr3_platform.synthetic import make_episode, state, command, event, metadata
from fr3_platform.exporter import training_rows
from fr3_platform.teleop import OfflineVRMapper
from fr3_platform.twin import state_packets, compare_packets, MuJoCoReplay
from fr3_platform.sensors import validate_d405_config, validate_flexitac_config
from fr3_platform.preflight import check

class CoreTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[1]/'artifacts/test-tmp'
        base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base)
        self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def episode(self):
        p=self.root/'episode';self.assertTrue(make_episode(p,3)['ok']);return p
    def mutate(self,p,fn):
        events=[json.loads(x) for x in (p/'events.jsonl').read_text().splitlines()]
        fn(events)
        (p/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    def test_complete_episode_and_lossless_depth(self):
        p=self.episode();r=DatasetReader(p)
        self.assertEqual(len(list(replay(p))),24)
        depth=next(e for e in r if e['kind']=='depth')
        self.assertEqual(len(r.blob(depth)),32)
        self.assertEqual(depth['payload']['depth_scale_m'],0.001)
    def test_schema_serialization(self):
        self.assertEqual(json.loads(RobotState(state()).to_json()),state())
        self.assertEqual(json.loads(RobotCommand(command()).to_json()),command())
    def test_nan_and_infinity(self):
        for value in (float('nan'),float('inf'),float('-inf')):
            c=command();c['arms']['left']['target'][0]=value
            with self.assertRaises(ContractError):RobotCommand(c).validate()
    def test_wrong_dimension_and_joint_order(self):
        for key,value in [('target',[0.]*6),('joint_names',['wrong']*7),('unit','deg')]:
            c=command();c['arms']['right'][key]=value
            with self.assertRaises(ContractError):RobotCommand(c).validate()
    def test_bad_gripper_quantity(self):
        c=command();c['arms']['left']['gripper']['quantity']='percent'
        with self.assertRaises(ContractError):RobotCommand(c).validate()
    def test_missing_measurement_not_zero(self):
        s=state();s['arms']['left']['position'].update(status='missing',value=None)
        s['arms']['left']['valid_fields'].remove('position')
        RobotState(s).validate()
        s['arms']['left']['position']['value']=[0.]*7
        with self.assertRaises(ContractError):RobotState(s).validate()
    def test_wrong_valid_fields(self):
        s=state();s['arms']['left']['valid_fields']=[]
        with self.assertRaises(ContractError):RobotState(s).validate()
    def test_bad_pose_quaternion(self):
        s=state();s['arms']['left']['tcp']={'position_m':[0.,0.,0.],'quaternion_xyzw':[0.,0.,0.,0.], 'frame':'world','child_frame':'tcp','provenance':'synthetic'}
        with self.assertRaises(ContractError):RobotState(s).validate()
    def test_timestamp_regression(self):
        p=self.episode()
        def bad(es):
            e=next(e for e in es if e['id']=='rgb-1');e['stamp']['source_ns']=0
        self.mutate(p,bad);self.assertFalse(validate(p)['ok'])
    def test_sequence_gap(self):
        p=self.episode()
        def bad(es):next(e for e in es if e['id']=='rgb-2')['stamp']['sequence']=3
        self.mutate(p,bad);r=validate(p);self.assertFalse(r['ok']);self.assertTrue(r['sequence_gaps'])
    def test_missing_frame(self):
        p=self.episode();self.mutate(p,lambda es:es.pop(next(i for i,e in enumerate(es) if e['id']=='depth-1')))
        self.assertFalse(validate(p)['ok'])
    def test_checksum_corruption(self):
        p=self.episode();b=next((p/'blobs').iterdir());b.write_bytes(b'bad')
        self.assertFalse(validate(p)['ok'])
    def test_path_traversal_and_symlinks(self):
        for name in ('../escape','/tmp/escape'):
            with self.assertRaises(ContractError):safe_child(self.root,name)
        (self.root/'link').symlink_to(self.root)
        with self.assertRaises(ContractError):safe_child(self.root,'link/file')
    def test_torn_tail_and_non_destructive_recovery(self):
        p=self.episode()
        with (p/'events.jsonl').open('ab') as f:f.write(b'{"torn":')
        before=(p/'events.jsonl').read_bytes()
        self.assertFalse(validate(p)['ok'])
        r=recover(p,self.root/'recovered');self.assertEqual(r['events_recovered'],24)
        self.assertEqual((p/'events.jsonl').read_bytes(),before)
        self.assertFalse(validate(self.root/'recovered')['ok'])
    def test_no_overwrite(self):
        p=self.episode()
        with self.assertRaises(FileExistsError):Recorder(p,metadata())
    def test_backpressure_count(self):
        r=Recorder(self.root/'q',metadata())
        with patch.object(r.queue,'put_nowait',side_effect=queue.Full):
            self.assertFalse(r.submit(event('state','state',1_000_000_000,0,state())))
        result=r.close();self.assertEqual(result['dropped'],1);self.assertEqual(result['status'],'DEGRADED')
    def test_writer_failure_reported(self):
        r=Recorder(self.root/'bad',metadata())
        r.error='test disk failure'
        with self.assertRaises(OSError):r.submit(event('state','state',1_000_000_000,0,state()))
        with self.assertRaises(OSError):r.close()
    def test_sensor_requires_blob(self):
        r=Recorder(self.root/'sensor',metadata())
        with self.assertRaises((ContractError,KeyError)):
            r.submit(event('rgb','rgb',1,0,{'shape':[1,1,3]}))
        r.close()
    def test_causal_alignment_excludes_future(self):
        p=self.episode();r=DatasetReader(p);es=list(r)
        obs=next(e for e in es if e['id']=='state-1')
        images=[e for e in es if e['kind']=='rgb']
        self.assertEqual(causal_latest(r,images,obs,200_000_000)['id'],'rgb-1')
        images=[e for e in images if e['id']=='rgb-2']
        with self.assertRaises(ContractError):causal_latest(r,images,obs,200_000_000)
    def test_clock_uncertainty_is_conservative(self):
        p=self.episode();r=DatasetReader(p);r.meta['clocks']['host_monotonic']['uncertainty_ns']=1
        es=list(r);obs=next(e for e in es if e['id']=='state-0');im=next(e for e in es if e['id']=='rgb-0')
        with self.assertRaises(ContractError):causal_latest(r,[im],obs,1000)
    def test_missing_clock_mapping(self):
        p=self.episode();meta=json.loads((p/'episode.json').read_text());meta['clocks']={};atomic_json(p/'episode.json',meta)
        self.assertFalse(validate(p)['ok'])
    def test_export_profile_semantics(self):
        p=self.episode();r,rows=training_rows(p,'sent',10,20_000_000)
        self.assertEqual(len(rows),3);self.assertEqual(len(rows[0]['action']),16)
        self.assertNotEqual(rows[0]['state'],rows[0]['action'])
        with self.assertRaises(ContractError):training_rows(p,'accepted',10,20_000_000)
    def test_export_rejects_validation_fit(self):
        p=self.episode();meta=json.loads((p/'episode.json').read_text());meta['split']='validation';atomic_json(p/'episode.json',meta)
        with self.assertRaises(ContractError):training_rows(p,'sent',10,20_000_000)
    def test_export_rejects_irregular_rate(self):
        p=self.episode()
        with self.assertRaises(ContractError):training_rows(p,'sent',20,20_000_000)
    def test_twin_source_timestamp_comparison(self):
        p=self.episode();packets=list(state_packets(p));self.assertEqual(len(packets),3)
        self.assertEqual(compare_packets(packets[0],packets[0])['max_joint_error_rad'],0)
        with self.assertRaises(ContractError):compare_packets(packets[0],packets[1])
    def test_unverified_model_fails_before_import(self):
        with self.assertRaises(ContractError):MuJoCoReplay('missing',{'hardware':'Dual FR3 + Franka Gripper','review_status':'UNCONFIGURED'})
    def test_unconfigured_sensors_fail(self):
        with self.assertRaises(ContractError):validate_d405_config({'owner':'single_capture_process'})
        with self.assertRaises(ContractError):validate_flexitac_config({})
    def test_vr_clutch_jump_deadman(self):
        m=OfflineVRMapper([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],1.,.2,'synthetic')
        def run(pos,seq,**kw):return m.sample(pos,sequence=seq,source_ns=seq+1,now_ns=seq+1,origin='synthetic',tracking=True,deadman=kw.get('deadman',True),clutch=kw.get('clutch',False))
        self.assertEqual(run([0.,0.,0.],0)['status'],'REANCHORED')
        self.assertAlmostEqual(run([.1,0.,0.],1)['translation_m'][0],.1)
        self.assertEqual(run([1.,0.,0.],2)['status'],'REVOKE_AUTHORITY')
        self.assertEqual(run([1.,0.,0.],3,deadman=False)['status'],'REVOKE_AUTHORITY')
        self.assertEqual(run([1.,0.,0.],4,clutch=True)['status'],'REANCHORED')
    def test_ros_conda_contamination_detected(self):
        with patch.dict(os.environ,{'ROS_DISTRO':'jazzy','CONDA_PREFIX':'/example/env'}):self.assertTrue(check()['risks'])

    def test_command_requires_real_state_reference(self):
        p=self.episode()
        def bad(es):
            next(e for e in es if e['id']=='sent-0')['payload']['command']['observation_id']='rgb-0'
        self.mutate(p,bad);self.assertFalse(validate(p)['ok'])
    def test_sent_requires_request(self):
        p=self.episode();self.mutate(p,lambda es:es.pop(next(i for i,e in enumerate(es) if e['id']=='requested-0')))
        self.assertFalse(validate(p)['ok'])
    def test_command_before_observation(self):
        p=self.episode()
        def bad(es):
            next(e for e in es if e['id']=='requested-0')['payload']['command']['stamp']['source_ns']=0
        self.mutate(p,bad);self.assertFalse(validate(p)['ok'])
    def test_ros_mapping_is_explicit(self):
        from fr3_platform.ros_state import map_joint_state
        names=[f'driver{i}' for i in range(7)]
        mapping={n:f'left_joint{i+1}' for i,n in enumerate(names)}
        a=map_joint_state(side='left',driver_names=list(reversed(names)),positions=list(reversed(range(7))),velocities=[],driver_to_canonical=mapping)
        self.assertEqual(a['position']['value'],list(range(7)))
        self.assertEqual(a['velocity']['status'],'missing')
        with self.assertRaises(ContractError):map_joint_state(side='left',driver_names=names,positions=[0]*7,velocities=[],driver_to_canonical={})

class ControlTests(unittest.TestCase):
    def setUp(self):
        class Sink:
            source='synthetic'
            def __init__(self):self.sent=[]
            def send(self,c):self.sent.append(c);return 'received'
        self.sink=Sink()
        one={'lower':[-1.]*7,'upper':[1.]*7,'velocity':[2.]*7,'gripper':{'min_m':0.,'max_m':.1,'speed_m_s':1.}}
        self.limits={'source':'SYNTHETIC_TEST_LIMITS_NOT_HARDWARE','max_age_ns':100_000_000,'min_period_s':.001,'left':one,'right':copy.deepcopy(one)}
        self.exec=OfflineExecutor(self.sink,self.limits)
        self.exec.acquire('vr',1_000_000_000,100_000_000)
    def test_valid_offline_submission(self):
        r=self.exec.submit(command(),state(),1_001_000_000)
        self.assertEqual(len(self.sink.sent),1);self.assertIn('not hardware',r['interface_semantics'])
    def test_authority_exclusion(self):
        with self.assertRaises(ContractError):self.exec.acquire('vla',1_000_000_000,100_000_000)
    def test_expired_lease(self):
        with self.assertRaises(ContractError):self.exec.submit(command(),state(),2_000_000_000)
    def test_stale_future_and_wrong_clock(self):
        for transform in (lambda c:c['stamp'].update(source_ns=0),lambda c:c['stamp'].update(source_ns=2_000_000_000),lambda c:c['stamp'].update(clock='device')):
            c=command();transform(c)
            with self.assertRaises(ContractError):self.exec.submit(c,state(),1_001_000_000)
    def test_duplicate_sequence(self):
        self.exec.submit(command(),state(),1_001_000_000)
        with self.assertRaises(ContractError):self.exec.submit(command(),state(),1_001_000_000)
    def test_velocity_position_and_gripper_limits(self):
        for val in (.1,2.):
            c=command();c['arms']['left']['target'][0]=val
            with self.assertRaises(ContractError):self.exec.submit(c,state(),1_001_000_000)
        c=command();c['arms']['left']['gripper']['target']=.09
        with self.assertRaises(ContractError):self.exec.submit(c,state(),1_001_000_000)
    def test_deadman_tracking_disconnect_and_estop(self):
        for option in ('connected','tracking','deadman'):
            self.exec.watchdog(1_001_000_000,**{option:False});self.assertIsNone(self.exec.owner)
            self.exec.acquire('vr',1_001_000_000,100_000_000)
        self.exec.watchdog(1_001_000_000,estop=True)
        with self.assertRaises(ContractError):self.exec.acquire('vr',1_001_000_000,100_000_000)
    def test_hardware_sink_forbidden(self):
        self.sink.source='hardware'
        with self.assertRaises(ContractError):OfflineExecutor(self.sink,self.limits)
    def test_missing_limits_and_state(self):
        self.exec.limits['source']='UNCONFIGURED'
        with self.assertRaises(ContractError):self.exec.submit(command(),state(),1_001_000_000)

if __name__=='__main__':unittest.main()
