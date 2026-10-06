"""Plot actual upper-route witnesses; projections do not establish clearance."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator,FormatStrFormatter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/upper_departure_review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((OUT/'departure_review.json').read_text())
assert report['status']=='PASS' and sha(OUT/'arcs.npz')==report['curve_sha256']
for path,h in report['inputs'].items():assert sha(ROOT/path)==h,path
arcs=np.load(OUT/'arcs.npz');loops=np.load(HERE/'cam_upper_candidates.npz')
fig=plt.figure(figsize=(12,6));results=[]
for panel,pin,other in [(1,3,2),(2,4,3)]:
    a=arcs[f'pin{pin}_heading270'];b=loops[f'slot{other-1}_pitch-20']
    d2=np.sum((a[:,None,:]-b[None,:,:])**2,axis=2);i,j=np.unravel_index(d2.argmin(),d2.shape)
    dist=float(np.sqrt(d2[i,j]));sa=float(np.linalg.norm(np.diff(a,axis=0),axis=1).max());sb=float(np.linalg.norm(np.diff(b,axis=0),axis=1).max())
    gap=dist-.6604-(sa+sb)/2-report['arc_chord_error_mm']-.0003-.0001
    results.append(dict(pin=pin,other_pin=other,pitch=-20,heading_deg=270,nearest_a=a[i].tolist(),nearest_b=b[j].tolist(),center_distance_mm=dist,gap_lower_bound_mm=gap,required_surface_gap_mm=.3,status='BLOCKED' if gap<.3 else 'PASS'))
    ax=fig.add_subplot(1,2,panel,projection='3d');ax.plot(*a.T,color='#cd582b',lw=3,label=f'CAM {pin} departure')
    ends=np.vstack([a[i],b[j]]);ax.plot(*ends.T,color='#e03345',lw=2,marker='o',markersize=4)
    lo=np.minimum(a.min(0),b[j])-np.array([1,1,1]);hi=np.maximum(a.max(0),b[j])+np.array([1,1,1])
    mask=np.all((b>=lo)&(b<=hi),axis=1);ids=np.flatnonzero(mask)
    spans=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)
    for k,span in enumerate(spans):
        if len(span)>1:ax.plot(*b[span].T,color='#356779',lw=2,label=f'CAM {other} existing pitch loop' if k==0 else None)
    ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),zlim=(lo[2],hi[2]),xlabel='X / mm',ylabel='Y / mm',zlabel='Z / mm')
    for axis in [ax.xaxis,ax.yaxis,ax.zaxis]:axis.set_major_locator(MaxNLocator(4));axis.set_major_formatter(FormatStrFormatter('%.1f'))
    ax.set_box_aspect((max(hi[0]-lo[0],2),hi[1]-lo[1],hi[2]-lo[2]));ax.view_init(elev=24,azim=-53)
    ax.set_title(f'CAM {pin}: old loop blocks the exit\nBounded gap {gap:.3f} mm < 0.300 mm');ax.legend(loc='upper left',fontsize=8)
fig.suptitle('Actual route coordinates at pitch -20 degrees; initial R7 arc only\nCenterlines shown. Hardware / printed geometry / connector pins were not moved.',fontsize=12)
fig.subplots_adjust(top=.78,bottom=.1,wspace=.15);path=OUT/'upper_exit_conflicts.png';fig.savefig(path,dpi=140,facecolor='white');plt.close(fig)
out=dict(status='PASS',scope='Diagnostic plot and global sampled-distance bound; failed routes remain BLOCKED',inputs={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'departure_review.json',OUT/'arcs.npz',HERE/'cam_upper_candidates.npz']},witnesses=results,images=[dict(file=path.name,sha256=sha(path))],script_sha256=sha(Path(__file__)))
(OUT/'plot_manifest.json').write_text(json.dumps(out,indent=2)+'\n');print('UPPER_DEPARTURE_PLOT_PASS',flush=True)
