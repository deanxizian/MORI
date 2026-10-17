#!/usr/bin/env python3
"""Read-only Welch spectra of recorded balance signals; no hardware access.

Resample the native time series at 200 Hz by linear interpolation. Use
2048-point Hann segments, 50% overlap and per-segment mean removal. Report
one-sided density and integrated band RMS. This is descriptive, not causal
identification of mechanical vibration, sensor noise or a closed-loop plant.
"""
import argparse
import cmath
import hashlib
import json
import math
from pathlib import Path
import statistics


def fft(values):
    a = [complex(v) for v in values]
    n = len(a)
    if n < 2 or n & (n - 1):
        raise ValueError('power-of-two FFT length required')
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    size = 2
    while size <= n:
        step = cmath.exp(-2j * math.pi / size)
        for start in range(0, n, size):
            w = 1 + 0j
            for k in range(start, start + size // 2):
                u, v = a[k], w * a[k + size // 2]
                a[k], a[k + size // 2] = u + v, u - v
                w *= step
        size *= 2
    return a


def periodogram(values, fs):
    n = len(values)
    mean = statistics.mean(values)
    window = [.5 - .5 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)]
    power_window = sum(w * w for w in window)
    transformed = fft([(v - mean) * w for v, w in zip(values, window)])
    psd = [abs(v) ** 2 / (fs * power_window) for v in transformed[:n // 2 + 1]]
    for i in range(1, len(psd) - 1):
        psd[i] *= 2
    weighted_variance = sum(((v - mean) * w) ** 2 for v, w in zip(values, window)) / power_window
    if not math.isclose(sum(psd) * fs / n, weighted_variance, rel_tol=1e-9, abs_tol=1e-12):
        raise AssertionError('Parseval normalization failed')
    return psd


def resample(times, values, start, end, fs):
    out = []
    j = 0
    for i in range(math.floor((end - start) * fs) + 1):
        t = start + i / fs
        while j + 1 < len(times) and times[j + 1] < t:
            j += 1
        if j + 1 == len(times):
            break
        weight = (t - times[j]) / (times[j + 1] - times[j])
        out.append(values[j] + weight * (values[j + 1] - values[j]))
    return out


def bands(values, fs=200., n=2048):
    spectra = [periodogram(values[i:i + n], fs) for i in range(0, len(values) - n + 1, n // 2)]
    if not spectra:
        raise ValueError('at least one complete Welch segment required')
    psd = [statistics.mean(v) for v in zip(*spectra)]
    df = fs / n
    total = sum(psd) * df
    ranges = [(0, .3), (.3, 1), (1, 3), (3, 6), (6, 15), (15, 30), (30, 100.001)]
    rows = []
    for lo, hi in ranges:
        power = sum(p * df for k, p in enumerate(psd) if lo <= k * df < hi)
        rows.append(dict(hz=[lo, min(100, hi)], rms=math.sqrt(power), power_fraction=power / total if total else 0.))
    peaks = sorted((k for k in range(1, len(psd) - 1)
                    if .2 <= k * df <= 30 and psd[k] >= psd[k - 1] and psd[k] >= psd[k + 1]),
                   key=lambda k: psd[k], reverse=True)[:5]
    return dict(segments=len(spectra), samples=len(values), mean=statistics.mean(values),
                rms=math.sqrt(statistics.mean(v * v for v in values)),
                welch_ac_rms=math.sqrt(total), peak_hz=[k * df for k in peaks], bands=rows)


def self_check():
    fs, n, frequency = 200., 2048, 16 * 200 / 2048
    psd = periodogram([math.sin(2 * math.pi * frequency * i / fs) for i in range(n)], fs)
    assert max(range(len(psd)), key=lambda i: psd[i]) == 16
    assert abs(math.sqrt(sum(psd) * fs / n) - 1 / math.sqrt(2)) < 1e-5
    assert max(periodogram([3.] * n, fs)) == 0
    return dict(status='PASS', sine_frequency_hz=frequency, sine_rms=1 / math.sqrt(2),
                checks=['known sine peak and RMS', 'constant signal rejection', 'Parseval on every segment'])


def analyze(path, lo, hi):
    raw = path.read_bytes()
    d = json.loads(raw)
    samples = d['samples']
    times = [s['elapsed_s'] for s in samples]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('non-increasing recording timestamps')
    start, end = max(lo, times[0]), min(hi, times[-1])
    channels = {
        'pitch_deg': [s['attitude']['pitch_deg'] for s in samples],
        'gyro_dps': [s['attitude']['pitch_rate_dps'] for s in samples],
        'd_nm': [s['attitude']['ardupilot_balance']['d_nm'] for s in samples],
        'p_nm': [s['attitude']['ardupilot_balance']['p_nm'] for s in samples],
        'encoder_velocity_m_s': [s['attitude']['velocity_hold']['encoder_velocity_proxy_m_s'] for s in samples],
        'common_encoder_position_m': [statistics.mean(s['rolling_equivalent']['forward_offset_m'].values()) for s in samples],
    }
    return dict(log=str(path), sha256=hashlib.sha256(raw).hexdigest(), requested_window_s=[lo, hi],
                actual_window_s=[start, end], native_max_gap_ms=1000 * max(b - a for a, b in zip(times, times[1:])),
                signals={name: bands(resample(times, values, start, end, 200.)) for name, values in channels.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', nargs='+', type=Path)
    p.add_argument('--window', nargs=2, type=float, default=[7., 60.])
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    if not all(math.isfinite(v) for v in a.window) or not 0 <= a.window[0] < a.window[1]:
        p.error('finite increasing window required')
    result = dict(method=__doc__, analysis_checks=self_check(), records=[analyze(f, *a.window) for f in a.logs])
    with a.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    for record in result['records']:
        print(json.dumps(dict(log=record['log'], actual_window_s=record['actual_window_s'],
                              signals={k: dict(peak_hz=v['peak_hz'][:2], rms=v['rms'],
                                               high_band=v['bands'][4]) for k, v in record['signals'].items()})))


if __name__ == '__main__':
    main()
