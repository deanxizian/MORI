"""Real pixel input -> detector -> conservative tracker; no random detection boxes.
Marker fixtures exercise the pipeline. Haar faces are a separate optional CPU candidate,
not an embedded detector or an identity recognizer. No biometrics are persisted.
"""
import math
import cv2
import numpy as np

def bearing(center,head,body_pitch):
 # Synthetic/calibrated normalized coordinates: x right, y down; fx=fy=1.2 widths.
 x,y=center;ray=np.array([1.,-(x-.5)/1.2,-(y-.5)/1.2])
 yaw,pitch=head
 def ry(a):return np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
 rz=np.array([[math.cos(yaw),-math.sin(yaw),0],[math.sin(yaw),math.cos(yaw),0],[0,0,1]])
 ray=ry(body_pitch)@rz@ry(-pitch)@ray
 return math.atan2(ray[1],ray[0]),math.atan2(ray[2],math.hypot(ray[0],ray[1]))

class Vision:
 def __init__(self):
  self.last_center=None;self.cascade=None
 def detect(self,image,method='marker'):
  if image is None or image.size==0:raise ValueError('empty image')
  h,w=image.shape[:2]
  if h>720 or w>1280:raise ValueError('frame resolution limit')
  if method=='face':
   if self.cascade is None:self.cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
   rects=self.cascade.detectMultiScale(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),1.1,4)
   boxes=[tuple(map(int,r)) for r in rects]
  elif method=='marker':
   hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
   mask=cv2.inRange(hsv,np.array([75,90,60]),np.array([105,255,255]))
   contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
   boxes=[cv2.boundingRect(c) for c in contours if cv2.contourArea(c)>80]
  else:raise ValueError('detector')
  certain=len(boxes)==1
  if certain:
   x,y,bw,bh=boxes[0];center=((x+bw/2)/w,(y+bh/2)/h)
   # Crossing/occlusion/large jumps never substitute another person's target.
   if self.last_center and math.dist(center,self.last_center)>.15:certain=False
   self.last_center=center if certain else None
   return {'target_id':'track-1','center':center,'height_fraction':bh/h,'confidence':.95 if certain else 0.,'uncertain':not certain,'boxes':[list(b) for b in boxes],'detector':method,'identity':'NOT_INFERRED'}
  self.last_center=None
  return {'target_id':None,'center':[.5,.5],'height_fraction':0.,'confidence':0.,'uncertain':True,'boxes':[list(b) for b in boxes],'detector':method,'identity':'NOT_INFERRED'}

def fixture(frame,scenario='single',width=320,height=240):
 image=np.zeros((height,width,3),np.uint8);image[:]=(28,31,34)
 x=int(width*.45+math.sin(frame*.04)*width*.12);y=int(height*.43)
 if scenario not in ['lost','dark']:cv2.rectangle(image,(x,y),(x+28,y+36),(210,185,15),-1)
 if scenario=='multiple':cv2.rectangle(image,(int(width*.2),y),(int(width*.2)+26,y+40),(210,185,15),-1)
 cv2.putText(image,'SIMULATED PIXEL FIXTURE',(10,20),cv2.FONT_HERSHEY_SIMPLEX,.4,(180,180,180),1)
 return image

def target_angles(center,capture_head,capture_pitch,capture_yaw,current_pitch,current_yaw):
 """Capture optical ray -> world at capture -> current body. No head subtraction twice."""
 def ry(a):return np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
 def rz(a):return np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
 x,y=center;ray=np.array([1.,-(x-.5)/1.2,-(y-.5)/1.2]);hy,hp=capture_head
 world=rz(capture_yaw)@ry(capture_pitch)@rz(hy)@ry(-hp)@ray
 body=ry(-current_pitch)@rz(-current_yaw)@world
 return math.atan2(body[1],body[0]),math.atan2(body[2],math.hypot(body[0],body[1]))
