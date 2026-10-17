#!/usr/bin/env python3
"""Recompute published trial71 claims from frozen telemetry, with no device I/O."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW_SHA = 'c64fa4451acb139a08da24aebb75465c557cf2bfc3dfcc8c7dc4e6cc94647ab1'
RAW_NAME = 'two-deck-balance-71-pitch325-observe.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    evidence = ROOT / 'evidence/balance'
    with zipfile.ZipFile(evidence / 'trial71-raw.json.zip') as archive:
        require(archive.namelist() == [RAW_NAME], 'Unexpected raw log members')
        require(archive.getinfo(RAW_NAME).file_size == 114483111, 'Raw size mismatch')
        raw = archive.read(RAW_NAME)
    require(hashlib.sha256(raw).hexdigest() == RAW_SHA, 'Raw hash mismatch')
    data = json.loads(raw)
    del raw
    result = json.loads((evidence / 'trial71-result-review.json').read_text())
    require(data['status'] == result['status'] == 'PASS', 'Trial status mismatch')
    require(data['final_disabled_verified'] is True, 'Final disabled state not confirmed')
    require(data['control_cycles'] == result['cycles'] == 11952, 'Cycle mismatch')
    require(math.isclose(data['elapsed_s'], result['elapsed_s'], abs_tol=1e-9), 'Duration mismatch')
    require(data['source_manifest']['sha256'] == json.loads(
        (evidence / 'trial71-v142-source-manifest.json').read_text())['sha256'], 'v142 source mismatch')
    samples = [s for s in data['samples'] if 7 <= s['elapsed_s'] <= 60]
    rms = lambda values: math.sqrt(statistics.mean(v * v for v in values))
    positions = [statistics.mean(s['rolling_equivalent']['forward_offset_m'].values()) for s in samples]
    actual = dict(
        samples=len(samples),
        common_encoder_span_m=max(positions) - min(positions),
        encoder_velocity_rms_m_s=rms(s['attitude']['velocity_hold']['encoder_velocity_proxy_m_s'] for s in samples),
        pitch_rms_deg=rms(s['attitude']['pitch_deg'] for s in samples),
        pitch_rate_rms_dps=rms(s['attitude']['pitch_rate_dps'] for s in samples),
        max_temperature_c=max(w['feedback']['temperature_c'] for s in samples for w in s['wheels'].values()),
    )
    for key, value in actual.items():
        require(math.isclose(value, result['matched_metrics'][key], rel_tol=1e-10, abs_tol=1e-12),
                f'Summary mismatch: {key}')
    print(json.dumps(dict(status='PASS', cycles=data['control_cycles'], elapsed_s=data['elapsed_s'],
                         window_s=[7, 60], recomputed=actual,
                         scope='Telemetry consistency; hands-off statement is operator evidence, not inferred'), indent=2))


if __name__ == '__main__':
    main()
