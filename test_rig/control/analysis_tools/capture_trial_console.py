#!/usr/bin/env python3
"""Passive local stdin recorder. Contains no SSH, serial, or motor commands.

Pipe one explicitly started SSH trial into this script with pipefail set.
Each received line is fsynced locally before echoing it to the operator.
EOF records only stream closure, never successful motor stop or file save.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys


def capture_stream(source,path,echo):
    count=0
    with Path(path).open('x',encoding='utf-8') as output:
        def append(kind,**fields):
            entry=dict(kind=kind,received_utc=datetime.now(timezone.utc).isoformat(),**fields)
            output.write(json.dumps(entry,ensure_ascii=False)+'\n')
            output.flush()
            os.fsync(output.fileno())
        append('CAPTURE_STARTED',scope='SSH stdout/stderr text only, not full-rate telemetry')
        fd=os.open(str(Path(path).parent),os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
        try:os.fsync(fd)
        finally:os.close(fd)
        for line in source:
            count+=1
            append('CONSOLE_LINE',sequence=count,text=line.rstrip('\n'))
            echo.write(line)
            echo.flush()
        append('STREAM_EOF',lines=count,remote_motion_status='NOT_INFERRED')
    return count


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    capture_stream(sys.stdin,args.output,sys.stdout)
    return 0


if __name__=='__main__':raise SystemExit(main())
