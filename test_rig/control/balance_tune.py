#!/usr/bin/env python3
"""Local status/gain/DISARM client. Cannot start or rearm balance."""
import argparse
import json
import socket
import uuid


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--socket',default='/run/mori-balance-tune/control.sock')
    sub=p.add_subparsers(dest='op',required=True)
    sub.add_parser('status')
    change=sub.add_parser('set')
    change.add_argument('--session',required=True)
    change.add_argument('--revision',type=int,required=True)
    change.add_argument('--key',choices=['pitch_p','pitch_i','pitch_d','speed_p'],required=True)
    change.add_argument('--value',type=float,required=True)
    change.add_argument('--ramp',type=float,default=2.)
    change.add_argument('--request-id')
    stop=sub.add_parser('disarm');stop.add_argument('--session',required=True)
    a=p.parse_args(argv);request=dict(op=a.op)
    if a.op=='set':request.update(session=a.session,expected_revision=a.revision,key=a.key,
        value=a.value,ramp_s=a.ramp,request_id=a.request_id or uuid.uuid4().hex)
    if a.op=='disarm':request['session']=a.session
    encoded=(json.dumps(request,allow_nan=False)+'\n').encode()
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(.5);s.connect(a.socket);s.sendall(encoded)
        data=b''
        while b'\n' not in data:
            part=s.recv(8192)
            if not part:raise RuntimeError('incomplete_tuning_response')
            data+=part
            if len(data)>65536:raise RuntimeError('oversized_tuning_response')
    result=json.loads(data.split(b'\n',1)[0]);print(json.dumps(result,ensure_ascii=False,indent=2))
    return 2 if result.get('status')=='REJECTED' else 0


if __name__=='__main__':raise SystemExit(main())
