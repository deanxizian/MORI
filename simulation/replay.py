"""No serial auto-connect. Replay is a SIMULATED monotonic-clock execution.
Input JSONL header declares source; records contain dt_ms and command or vision scenario.
Video mode decodes actual pixels and retains video PTS as relative capture time.
"""
import argparse,json,pathlib
from .harness import Rig
from .vision import Vision,fixture

def replay(records):
 r=Rig();rows=[];v=Vision()
 for item in records:
  dt=item.get('dt_ms',0)
  if type(dt) is not int or not 0<=dt<=10000:raise ValueError('dt_ms')
  r.clock.step(dt);r.d.tick()
  result=None
  if 'command' in item:
   c=item['command'];result=r.issue(c['type'],c['params'])
  if 'scenario' in item:
   f=r.d.capture();r.d.observe(f,v.detect(fixture(f,item['scenario'])))
  rows.append({'source':'SIMULATED','device_ms':r.clock(),'result':result,'state':r.d.snapshot()})
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('--output',required=True);ap.add_argument('--video',action='store_true');args=ap.parse_args()
 output=pathlib.Path(args.output)
 if 'SIMULATED' not in output.name:raise SystemExit('Replay output filename must contain SIMULATED')
 if args.video:
  import cv2
  cap=cv2.VideoCapture(args.input);vision=Vision();rows=[];i=0
  if not cap.isOpened():raise SystemExit('Cannot decode video')
  while True:
   ok,pixels=cap.read()
   if not ok:break
   i+=1;rows.append({'source':'SIMULATED_REPLAY','frame_id':i,'capture_pts_ms':cap.get(cv2.CAP_PROP_POS_MSEC),'observation':vision.detect(pixels)})
  cap.release()
 else:
  data=[json.loads(x) for x in pathlib.Path(args.input).read_text().splitlines() if x.strip()]
  if not data or data.pop(0).get('source') not in ('SIMULATED','RECORDED'):raise SystemExit('Source header required')
  rows=replay(data)
 output.write_text('\n'.join(json.dumps(row,ensure_ascii=False) for row in rows)+'\n');print(f'{len(rows)} frames -> {output}')
if __name__=='__main__':main()
