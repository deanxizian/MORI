"""Persist completed trial evidence after all motor I/O has been closed.

This function performs blocking filesystem I/O and must never be called
from the active control loop. fsync acknowledgement is not a guarantee
against a faulty SD card or loss of power before this function completes.
"""
import hashlib
import json
import os
from pathlib import Path


def sync_parent(path):
    fd=os.open(str(Path(path).parent),os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def persist_report(report,output):
    """Use the caller's exclusively created file; return a verifiable receipt.

    A receipt is produced only after both file and parent-directory fsync
    succeeded. Keep the existing raw JSON representation, including rejected
    sensor frames; do not silently drop values to make a report writable.
    """
    json.dump(report,output,indent=2)
    output.write('\n')
    output.flush()
    os.fsync(output.fileno())
    sync_parent(output.name)
    digest=hashlib.sha256()
    with open(output.name,'rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):
            digest.update(chunk)
    return dict(kind='REPORT_SAVED',status='PASS',path=str(output.name),
                bytes=os.fstat(output.fileno()).st_size,sha256=digest.hexdigest(),
                file_fsync=True,directory_fsync=True)
