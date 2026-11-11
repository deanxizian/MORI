#!/usr/bin/env python3
"""Explicit operator reset while the service is stopped and the car supported."""
import argparse
import fcntl
from pathlib import Path
import time


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--car-supported', action='store_true')
    args = parser.parse_args(argv)
    if not args.car_supported:
        parser.error('support the car, stop the service, then pass --car-supported')
    folder = Path('/run/mori-balance')
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        latch = Path('/var/lib/mori-balance/latch.json')
        if latch.exists():
            latch.rename(latch.with_name('reset-' + str(time.time_ns()) + '.json'))
        print('Fault latch acknowledged. No hardware opened. Start the service only with the car supported.')


if __name__ == '__main__':
    main()
