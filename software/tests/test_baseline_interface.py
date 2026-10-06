"""Extract the legacy parser exactly, then probe a dangerous accepted suffix."""
import math
import pathlib
import re
import subprocess
import tempfile
import unittest
import zipfile
import sys
BASELINE = "--baseline" in sys.argv
if BASELINE: sys.argv.remove("--baseline")

ROOT = pathlib.Path(__file__).resolve().parents[1]
FW = ROOT / 'firmware_work/firmware'

class BaselineInterface(unittest.TestCase):
    def test_distance_per_count_matches_handoff(self):
        if BASELINE:
            with zipfile.ZipFile(ROOT/'reference_sources/HW-SW-0.3_firmware_baseline.zip') as z:
                text = z.read('firmware/main/board.h').decode()
        else:
            with tempfile.TemporaryDirectory(dir=ROOT/'reports') as d:
                src=pathlib.Path(d)/'scale.c';exe=pathlib.Path(d)/'scale'
                src.write_text('#include "mori_io.h"\n#include <stdio.h>\nint main(void){printf("%.15f",(double)MORI_WHEEL_M_PER_COUNT);}\n')
                subprocess.run(['cc','-I'+str(FW/'components/mori_core/include'),str(src),'-o',str(exe)],check=True)
                value=subprocess.check_output([str(exe)],text=True)
                text=f'#define WHEEL_M_PER_COUNT ({value}f)'
        match = re.search(r'WHEEL_M_PER_COUNT \(([\d.]+)f\)', text)
        self.assertIsNotNone(match)
        # --baseline preserves the original HW-SW-0.2 regression's historical expectation.
        self.assertAlmostEqual(float(match[1]), math.pi*.095/(1204.44 if BASELINE else 979.616), places=10)

    def test_legacy_parser_rejects_extra_fields(self):
        with zipfile.ZipFile(ROOT/'reference_sources/HW-SW-0.3_firmware_baseline.zip') as z:
            text = z.read('firmware/main/main.c').decode()
        parser = text[text.index('static void parse_line'):text.index('static void console_task')]
        code = '''#include "mori_core.h"
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
typedef struct{mori_command_t cmd;bool head;float angle;} app_command_t;
static int accepted; static int commands;
#define pdTRUE 1
static int xQueueSend(int q,void *p,int t){(void)q;(void)p;(void)t;accepted++;return 1;}
'''+parser+'\nint main(void){char s[]="duty 0.10 0.10 unexpected";parse_line(s);return accepted?1:0;}\n'
        extra=[]
        if not BASELINE:
            code='#include "mori_protocol.h"\nint main(void){mori_request_t r;return mori_parse("duty 0.10 0.10 unexpected",&r)==MR_OK?1:0;}\n'
            extra=[str(FW/'components/mori_core/mori_protocol.c')]
        with tempfile.TemporaryDirectory(dir=ROOT/'reports') as d:
            src=pathlib.Path(d)/'parser.c';exe=pathlib.Path(d)/'parser';src.write_text(code)
            subprocess.run(['cc','-std=c11','-I'+str(FW/'components/mori_core/include'),str(src),*extra,'-o',str(exe)],check=True)
            self.assertEqual(subprocess.run([str(exe)],check=False).returncode,0,'trailing command fields were accepted')

if __name__ == '__main__': unittest.main()
