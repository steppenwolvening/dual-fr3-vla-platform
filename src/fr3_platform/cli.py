import argparse
import json
from pathlib import Path
import sys
from .data import validate, replay, recover
from .contracts import ContractError
from .preflight import check


def main():
    p=argparse.ArgumentParser(description='Offline Dual FR3 canonical tools; no hardware entrypoints')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('preflight')
    sub.add_parser('deployment-plan')
    sub.add_parser('integration-status')
    s=sub.add_parser('synthetic');s.add_argument('output');s.add_argument('--frames',type=int,default=8)
    for name in ('validate','replay','twin-publish'):
        s=sub.add_parser(name);s.add_argument('episode')
    s=sub.add_parser('recover');s.add_argument('source');s.add_argument('destination')
    s=sub.add_parser('export-lerobot');s.add_argument('source');s.add_argument('destination')
    s.add_argument('--label',required=True,choices=('requested','sent','accepted'))
    s.add_argument('--fps',type=int,required=True);s.add_argument('--tolerance-ms',type=float,required=True)
    s.add_argument('--pin',default=str(Path(__file__).resolve().parents[2]/'environments/lerobot-reader-pin.json'))
    s=sub.add_parser('mujoco-replay');s.add_argument('episode');s.add_argument('--model',required=True);s.add_argument('--manifest',required=True)
    a=p.parse_args()
    try:
        if a.cmd=='preflight':
            r=check();print(json.dumps(r,indent=2));return 2 if r['risks'] else 0
        if a.cmd=='deployment-plan':
            print('PLAN ONLY: core runs with stdlib Python >=3.10.\nOptional installations require separately approved pinned environment resolution.\nROS, robot_core, data, LingBot and IsaacLab run in separate processes.\nSee migration/TARGET_SETUP.md and ENVIRONMENT_PLAN.md. No commands executed.');return 0
        if a.cmd=='integration-status':
            print(json.dumps({'LingBot':'BLOCKED: selected checkpoint, local code pin, loader and embodiment mapping unresolved',
                              'Quest':'BLOCKED: live transport/SDK not verified; translation-only offline mapper available',
                              'IsaacLab':'BLOCKED: current assembly model and approved runtime test missing',
                              'D405_FlexiTac':'BLOCKED: hardware protocol/profile/calibration verification missing',
                              'hardware':'NOT_IMPLEMENTED: no actuator transport in this build'},indent=2));return 2
        report=check()
        if report['risks']:raise ContractError('; '.join(report['risks']))
        if a.cmd=='synthetic':
            from .synthetic import make_episode
            r=make_episode(a.output,a.frames)
        elif a.cmd=='validate':r=validate(a.episode)
        elif a.cmd=='replay':
            events=list(replay(a.episode));r={'events':len(events),'source':'recorded','hardware_sent':0}
        elif a.cmd=='recover':r=recover(a.source,a.destination)
        elif a.cmd=='twin-publish':
            from .twin import state_packets
            for packet in state_packets(a.episode):print(json.dumps(packet,allow_nan=False))
            return 0
        elif a.cmd=='mujoco-replay':
            from .twin import state_packets,MuJoCoReplay
            backend=MuJoCoReplay(a.model,json.loads(Path(a.manifest).read_text()))
            count=0
            for packet in state_packets(a.episode):backend.apply(packet);count+=1
            r={'states_replayed':count,'validation':'runtime replay only; no dynamics equivalence assertion'}
        else:
            from .exporter import export_lerobot
            r=export_lerobot(a.source,a.destination,label=a.label,fps=a.fps,tolerance_ns=round(a.tolerance_ms*1e6),pin_file=a.pin)
        print(json.dumps(r,indent=2,allow_nan=False))
        return 0 if r.get('ok',True) else 1
    except (ContractError,ImportError,FileNotFoundError,ValueError,KeyError) as e:
        print(json.dumps({'status':'BLOCKED_OR_INVALID_INPUT','reason':str(e)}),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
