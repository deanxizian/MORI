"""Pure curve construction for an eleven-conductor neck feasibility study.

No Blender state, imported study initializer, or source geometry modification.
The wire sizes are explicit screening allocations, not a selected harness.
"""
import math
import numpy as np
from numpy.polynomial import polynomial as poly

S = np.array([0., 0., 0., 10., -15., 6.])
B = np.array([0., 0., 16., -32., 16., 0.])
Q, W = np.polynomial.legendre.leggauss(128)
Q, W = (Q + 1) / 2, W / 2


def absmax(co):
    roots = poly.polyroots(poly.polyder(co))
    ts = [0., 1.] + [float(v.real) for v in roots if abs(v.imag) < 1e-8 and 0 < v.real < 1]
    return float(np.max(np.abs(poly.polyval(ts, co))))


def length(radius, height, coefficients):
    d = poly.polyval(Q, poly.polyder(coefficients))
    return float(np.sum(W * np.sqrt(height * height + radius * radius * d * d)))


def family(z0=130., z1=175., radius=7.2, sample_count=901):
    height = z1 - z0
    target = length(radius, height, math.pi / 3 * S) + .025
    t = np.linspace(0, 1, sample_count)
    rows = []
    for yaw in range(-60, 61, 10):
        alpha = math.radians(yaw)
        lo, hi = 0., 3.
        assert length(radius, height, alpha*S) <= target <= length(radius, height, alpha*S+hi*B)
        for _ in range(52):
            mid = (lo + hi) / 2
            if length(radius, height, alpha*S+mid*B) < target:
                lo = mid
            else:
                hi = mid
        co = alpha*S + (lo+hi)/2*B
        theta = poly.polyval(t, co)
        d = poly.polyval(t, poly.polyder(co))
        dd = poly.polyval(t, poly.polyder(co, 2))
        cs, sn = np.cos(theta), np.sin(theta)
        points = np.c_[radius*cs, radius*sn, z0+height*t]
        speed = np.c_[-radius*sn*d, radius*cs*d, np.full(len(t), height)]
        accel = np.c_[-radius*cs*d*d-radius*sn*dd, -radius*sn*d*d+radius*cs*dd, np.zeros(len(t))]
        curvature = np.linalg.norm(np.cross(speed, accel), axis=1) / np.linalg.norm(speed, axis=1)**3
        second = radius*(absmax(poly.polyder(co))**2 + absmax(poly.polyder(co, 2)))
        rows.append(dict(yaw_deg=yaw, points=points, coefficients=co.tolist(),
                         model_length_mm=length(radius, height, co),
                         sampled_min_radius_mm=float(1/curvature.max()),
                         chord_error_mm=second/(sample_count-1)**2/8))
    return rows


def upper(radius=7.2, start_z=175., bend_radius=15., radial_delta=8., end_z=206.):
    angle = math.acos(1-radial_delta/(2*bend_radius))
    t = np.linspace(0, angle, 241)
    q = np.linspace(angle, 0, 241)[1:]
    r = np.r_[radius+bend_radius*(1-np.cos(t)), radius+radial_delta-bend_radius*(1-np.cos(q))]
    z = np.r_[start_z+bend_radius*np.sin(t), start_z+2*bend_radius*math.sin(angle)-bend_radius*np.sin(q)]
    tail = np.linspace(z[-1], end_z, max(2, math.ceil((end_z-z[-1])/.04)+1))[1:]
    points = np.c_[np.r_[r, np.full(len(tail), radius+radial_delta)], np.zeros(len(z)+len(tail)), np.r_[z, tail]]
    return points, bend_radius*(1-math.cos(angle/480))


def rotate(points, degrees):
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(points) @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]]).T
