"""Bounded evidence, local state and nonblocking status output. No hardware I/O."""
from collections import deque
import json
import os
from pathlib import Path
import threading
import time
import uuid


def serializable(value):
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, deque)):
        return [serializable(v) for v in value]
    return value


def atomic_json(path, value, *, durable=False):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(serializable(value), stream, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        if durable:
            stream.flush()
            os.fsync(stream.fileno())
    os.replace(temporary, path)
    if durable:
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class StatusOutput:
    """All journal/file writes occur off the control thread, with a bounded queue."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.pending = deque(maxlen=16)
        self.stopping = threading.Event()
        self.ready = threading.Event()
        self.error = None
        self.telemetry = {}
        self.thread = threading.Thread(target=self.work, daemon=True, name='balance-status')

    def __enter__(self):
        self.thread.start()
        if not self.ready.wait(2.):
            raise RuntimeError('status_worker_start_timeout')
        self.check()
        return self

    def __call__(self, message):
        self.check()
        self.pending.append((message, self.telemetry.copy()))

    def check(self):
        if self.error:
            raise RuntimeError('status_worker_failed: ' + self.error)

    def work(self):
        try:
            os.sched_setscheduler(0, os.SCHED_OTHER, os.sched_param(0))
            os.sched_setaffinity(0, {0, 1})
            os.setpriority(os.PRIO_PROCESS, 0, 10)
            self.ready.set()
            while not self.stopping.is_set() or self.pending:
                try:
                    message, telemetry = self.pending.popleft()
                except IndexError:
                    self.stopping.wait(.05)
                    continue
                state = 'BALANCING' if message.startswith('{"elapsed_s":') else message.split(':', 1)[0]
                atomic_json(self.directory / 'status.json', dict(
                    state=state, message=message, monotonic=time.monotonic(), **telemetry))
                print(message, flush=True)
        except Exception as exc:
            self.error = type(exc).__name__ + ': ' + str(exc)
            self.ready.set()

    def __exit__(self, *_):
        self.stopping.set()
        self.thread.join(2.)


def current_boot_id():
    """Kernel boot identity, independent of wall-clock/NTP changes."""
    return str(uuid.UUID(Path('/proc/sys/kernel/random/boot_id').read_text().strip()))


def begin_session(directory, *, boot_id=None):
    """Admit a fresh boot after interrupted power; persist all known faults.

    Caller holds the controller lock. This only admits device initialization;
    the disabled checks, neutral input and full upright dwell still follow.
    Same-boot process restarts and legacy/unknown markers never auto-recover.
    """
    boot_id = current_boot_id() if boot_id is None else str(uuid.UUID(boot_id))
    directory = Path(directory)
    marker = directory / 'latch.json'
    startup = dict(boot_id=boot_id, recovered_interrupted_boot=False)
    if marker.exists():
        raw = marker.read_bytes()
        try:
            previous = json.loads(raw)
            previous_boot = str(uuid.UUID(previous.get('boot_id', '')))
            recoverable = (previous.get('schema_version') == 2
                           and previous.get('state') == 'RUNNING_OR_INTERRUPTED'
                           and previous_boot != boot_id)
        except (ValueError, TypeError, AttributeError):
            recoverable = False
        if not recoverable:
            raise RuntimeError('fault_latched: inspect last-result.json and explicitly reset while supporting the car')
        # Preserve exact prior bytes before replacing the marker. If archive
        # persistence fails, admission aborts without touching any hardware.
        archive = directory / ('power-interrupted-' + str(uuid.uuid4()) + '.json')
        with archive.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        startup.update(recovered_interrupted_boot=True, previous_boot_id=previous_boot,
                       previous_session_archive=archive.name)
    atomic_json(marker, dict(schema_version=2, state='RUNNING_OR_INTERRUPTED',
                            boot_id=boot_id, started_unix=time.time()), durable=True)
    return startup


def finish_session(directory, report):
    directory = Path(directory)
    atomic_json(directory / 'last-result.json', report, durable=True)
    # A clean system shutdown/service stop can boot again. A fault, remote
    # disarm or unconfirmed motor stop requires an explicit operator reset.
    clean = (report.get('final_disabled_verified')
             and report.get('reason') in ('signal_15', 'signal_2')
             and not any(report.get(k) for k in (
                 'stop_fault_count', 'stop_faults', 'stop_transition_findings',
                 'stop_errors', 'stop_observer_findings', 'stop_observer_setup_error'))
             and report.get('stop_imu_observation', {}).get('status') != 'FAIL')
    if clean:
        (directory / 'latch.json').unlink(missing_ok=True)
    else:
        atomic_json(directory / 'latch.json', dict(
            state='FAULT_LATCHED', reason=report.get('reason'),
            final_disabled_verified=report.get('final_disabled_verified', False)), durable=True)
    return bool(clean)
