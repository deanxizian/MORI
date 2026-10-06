"""Free-span capacity with a smaller rear return; no selected cable claim."""
import math
import numpy as np
from full_static_flex_geometry import rotation, log_rotation

RADII = [5., 5., 7.5, 7.5, 7.5, 7.5]
ANGLES = np.radians([-90, -90, 90, 90, -90, -90])

def trace(start, lengths, twists, step=None):
    pos = np.array(start, float)
    T = np.array([-1., 0, 0]); W = np.array([0., 0, 1])
    points = []; tangents = []; widths = []; pieces = []; station = 0.
    def sample(p, t, w):
        points.append(p.copy()); tangents.append(t.copy()); widths.append(w.copy())
    for i, length in enumerate(lengths):
        twist = twists[i]
        if step:
            for u in np.linspace(0, 1, max(1, math.ceil(length/step))+1)[:-1]:
                sample(pos+T*length*u, T, rotation(T, twist*u)@W)
        pieces.append(dict(kind='straight', length_mm=float(length),
            twist_deg=math.degrees(twist), start_station_mm=station,
            end_station_mm=station+length))
        pos += T*length; W = rotation(T, twist)@W; station += length
        if i == 6: break
        angle = ANGLES[i]; radius = RADII[i]; sign = np.sign(angle)
        A = pos.copy(); t0 = T.copy(); side = np.cross(W, t0)
        if step:
            for q in np.linspace(0, abs(angle), max(2, math.ceil(radius*abs(angle)/step))+1)[:-1]:
                sample(A+radius*(math.sin(q)*t0+sign*(1-math.cos(q))*side),
                    rotation(W, sign*q)@t0, W)
        pos = A+radius*(math.sin(abs(angle))*t0+sign*(1-math.cos(abs(angle)))*side)
        T = rotation(W, angle)@T
        pieces.append(dict(kind='arc', radius_mm=radius, angle_deg=math.degrees(angle),
            length_mm=radius*abs(angle), start_station_mm=station,
            end_station_mm=station+radius*abs(angle)))
        station += radius*abs(angle)
    if step: sample(pos, T, W)
    return dict(end=pos, T=T, W=W, length=station, pieces=pieces,
        points=np.array(points), tangents=np.array(tangents), widths=np.array(widths))

def solve(start, end, first_vertical=1.5, total_length=194., lead=8.8, tail=5.5):
    targetW = rotation([1, 0, 0], math.radians(10))@np.array([0., 0, 1.])
    targetT = np.array([1., 0, 0])
    targetR = np.column_stack([targetT, targetW, np.cross(targetT, targetW)])
    def unpack(v):
        return [lead, first_vertical, *v[:4], tail], [0, 0, v[4], 0, v[5], v[6], 0]
    def residual(v):
        lengths, twists = unpack(v); r = trace(start, lengths, twists)
        R = np.column_stack([r['T'], r['W'], np.cross(r['T'], r['W'])])
        return np.r_[r['end']-end, log_rotation(targetR.T@R)*30., r['length']-total_length]
    q = np.array([45., 20., 45., 5., math.radians(-15), math.radians(-25), 0.])
    lo = np.array([.25]*4+[-math.pi/2]*3); hi = np.array([85.]*4+[math.pi/2]*3)
    history = []
    for iteration in range(100):
        r = residual(q); cost = float(r@r); history.append(cost)
        if np.linalg.norm(r) < 2e-7: break
        J = np.column_stack([(residual(q+np.eye(7)[i]*1e-5)-residual(q-np.eye(7)[i]*1e-5))/2e-5 for i in range(7)])
        update = np.linalg.lstsq(J, -r, rcond=1e-10)[0]
        found = False
        for scale in [1., .5, .25, .125, .0625, .03125, .015625]:
            new = np.clip(q+scale*update, lo, hi); newr = residual(new)
            if newr@newr < cost:
                q = new; found = True; break
        if not found: break
    lengths, twists = unpack(q); r = trace(start, lengths, twists)
    return dict(status='PASS' if np.linalg.norm(residual(q)) < 1e-5 else 'FAIL',
        lengths=lengths, twists=twists, first_vertical=first_vertical,
        start=np.asarray(start), end=np.asarray(end), residual=residual(q),
        iterations=len(history), fit_history=history,
        endpoint_error_mm=float(np.linalg.norm(r['end']-end)), length_mm=r['length'])

def ribbon(fit, width=10.5, thickness=.2, step=.2):
    assert fit['status'] == 'PASS'
    r = trace(fit['start'], fit['lengths'], fit['twists'], step)
    p, t, w = r['points'], r['tangents'], r['widths']; normal = np.cross(t, w)
    assert np.max(np.abs(np.sum(t*w, axis=1))) < 1e-9
    v = np.stack([p-w*width/2-normal*thickness/2, p+w*width/2-normal*thickness/2,
        p+w*width/2+normal*thickness/2, p-w*width/2+normal*thickness/2], axis=1).reshape(-1, 3)
    f = []
    for i in range(len(p)-1):
        for j in range(4):
            a=4*i+j; b=4*i+(j+1)%4; c=b+4; d=a+4
            f.extend([[a,b,c], [a,c,d]])
    f.extend([[0,2,1], [0,3,2]]); a=4*(len(p)-1)
    f.extend([[a,a+1,a+2], [a,a+2,a+3]])
    f = np.array(f, dtype=np.uint64)
    volume = np.einsum('ij,ij->i', v[f[:,0]], np.cross(v[f[:,1]], v[f[:,2]])).sum()/6
    if volume < 0: f = f[:,::-1].copy()
    rates = [abs(angle/length) for length, angle in zip(fit['lengths'], fit['twists'])]
    arc_error = max((radius+thickness/2)*(1-math.cos(step/radius/2)) for radius in RADII)
    twist_error = math.hypot(width, thickness)/2*(1-math.cos(max(rates)*step/2))
    return dict(points_mm=p, tangents=t, width_vectors=w, vertices_mm=v, triangles=f,
        metadata=dict(free_span_analytic_length_mm=r['length'],
            free_span_endpoint_error_mm=fit['endpoint_error_mm'],
            start_mm=fit['start'].tolist(), end_mm=fit['end'].tolist(),
            start_tangent=t[0].tolist(), end_tangent=t[-1].tolist(),
            start_width_vector=w[0].tolist(), end_width_vector=w[-1].tolist(),
            first_vertical_mm=fit['first_vertical'], width_mm=width, thickness_mm=thickness,
            radii_mm=RADII, polygonal_chord_error_bound_mm=max(arc_error, twist_error),
            pieces=r['pieces'], maximum_twist_deg_per_mm=math.degrees(max(rates)),
            orthogonal_sweep_edge_extension_estimate=math.sqrt(1+(width/2*max(rates))**2)-1,
            limits='ASSUMED capacity radii, width, thickness and slot centers; not a selected or fixed cable; no material acceptance.',
            classification='PLACEHOLDER', data_status='ASSUMED', source_stock_length_mm=200,
            unmodeled_connector_zone_budget_mm=200-r['length']))
