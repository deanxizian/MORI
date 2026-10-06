#!/usr/bin/env python3
"""Offline comparison of pinned vendor packet functions. Never opens a port.

Only the inspected arithmetic functions are loaded from the Python AST. The C
oracle uses the archived vendor protocol functions with a header-only gpio.h
stub, no HAL, no MCU, and no transport. This is not MORI runtime firmware.
"""
import ast
import ctypes
import hashlib
import json
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'hardware/v1_2'
SRC = BASE / 'sources/unitree_v1.0.1_excerpt'


def pure_python_functions():
    tree = ast.parse((SRC / 'python/servo_demo.py').read_text())
    assignments = {'RATIO', 'M_PI', 'CRC32_TABLE'}
    functions = {'crc32_lookup', 'build_control_packet', 'parse_feedback_packet'}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) and t.id in assignments for t in node.targets):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            selected.append(node)
    assert len(selected) == 6
    namespace = {'struct': struct}
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<vendor-pure-functions>', 'exec'), namespace)
    return namespace


def bitwise_reference(data):
    assert len(data) % 4 == 0
    crc = 0xFFFFFFFF
    for offset in range(0, len(data), 4):
        for byte in data[offset:offset + 4][::-1]:
            crc ^= byte << 24
            for _ in range(8):
                crc = ((crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)) & 0xFFFFFFFF
    return crc


def clean_c(path):
    # Vendor comments mix UTF-8/GBK. Strip comments in a TEMPORARY copy only;
    # remaining C declarations and executable statements are unchanged.
    text = path.read_bytes().decode('latin1')
    return re.sub(r'/\*.*?\*/|//[^\r\n]*', '', text, flags=re.S)


def main():
    cc = shutil.which('clang')
    if not cc:
        raise SystemExit('clang required for independent C oracle')
    py = pure_python_functions()
    report = {'revision': 'V1.2-H0.2-P1', 'evidence_layer': 'HOST_TEST',
              'source_tag': 'Unitree digital_servo v1.0.1',
              'transport_used': False, 'BENCH': 'NOT_TESTED', 'ROBOT': 'NOT_TESTED',
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in [SRC/'python/servo_demo.py', SRC/'stm32/firmware/App/protocol.h',
                           SRC/'stm32/firmware/App/protocol.c', SRC/'stm32/firmware/App/crc_ccitt.h']}}
    with tempfile.TemporaryDirectory(prefix='mori-s288-host-audit-') as temp:
        directory = Path(temp)
        for name in ['protocol.h', 'protocol.c', 'crc_ccitt.h']:
            (directory/name).write_text(clean_c(SRC/'stm32/firmware/App'/name))
        (directory/'gpio.h').write_text('#include <stdint.h>\n#include <stddef.h>\n')
        (directory/'oracle.c').write_text('''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "protocol.h"
#include "crc_ccitt.h"
uint32_t oracle_crc(const uint8_t *p, size_t n) { return crc32_lookup_byte_by_byte(p,n); }
size_t oracle_size(int n) {
  if(n==0) return sizeof(ControlData_t);
  if(n==1) return sizeof(RIS_Fbk_t);
  return sizeof(RecvData_t)-2;
}
void oracle_build(float tor, float spd, float pos, float kp, float kd, uint8_t *out) {
  MotorCmd_t m={0}; m.id=1; m.mode=1; m.timeout=1;
  m.outputTor=tor; m.outputSpd=spd; m.outputPos=pos; m.Kp=kp; m.Kd=kd;
  modify_data(&m); memcpy(out,&m.motor_send_data,20);
}
int oracle_parse(const uint8_t *wire, size_t n, float *out) {
  if(n!=26) return 0;
  MotorData_t m={0}; m.rxlen=(uint16_t)n;
  memcpy(&m.motor_recv_data.head[0],wire,26); extract_data(&m);
  out[0]=m.Temp; out[1]=m.sensor; out[2]=m.vol;
  out[3]=m.outputTor; out[4]=m.outputSpd; out[5]=m.outputPos; out[6]=m.ExPos;
  return m.correct;
}
''')
        libpath = directory/'oracle.dylib'
        command = [cc, '-std=c11', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                   '-fPIC', '-I', str(directory), str(directory/'oracle.c'),
                   str(directory/'protocol.c'), '-o', str(libpath)]
        build = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
        report['compiler'] = subprocess.run([cc,'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
        report['build_stderr'] = build.stderr
        lib = ctypes.CDLL(str(libpath))
        byteptr = ctypes.POINTER(ctypes.c_uint8)
        lib.oracle_crc.argtypes = [byteptr, ctypes.c_size_t]
        lib.oracle_crc.restype = ctypes.c_uint32
        lib.oracle_size.argtypes = [ctypes.c_int]
        lib.oracle_size.restype = ctypes.c_size_t
        lib.oracle_build.argtypes = [ctypes.c_float]*5 + [byteptr]
        lib.oracle_parse.argtypes = [byteptr, ctypes.c_size_t, ctypes.POINTER(ctypes.c_float)]
        def buf(data): return (ctypes.c_uint8*len(data)).from_buffer_copy(data)
        sizes = [lib.oracle_size(i) for i in range(3)]
        assert sizes == [20,19,26]
        report['C_sizes'] = dict(zip(['control','feedback_payload','feedback_wire'],sizes))
        rng = random.Random(288)
        vectors = [bytes(n) for n in [16,20]] + [bytes(rng.randrange(256) for _ in range(n)) for n in [16,20] for _ in range(128)]
        for data in vectors:
            assert lib.oracle_crc(buf(data),len(data)) == py['crc32_lookup'](data) == bitwise_reference(data)
        example = bytes(range(16))
        report['CRC'] = {'status':'PASS', 'vectors':len(vectors), 'scope':'16-byte command prefix / 20-byte feedback mode+payload',
            'polynomial':'0x04C11DB7', 'init':'0xFFFFFFFF', 'xorout':'0x00000000',
            'processing':'Each 4-byte little-endian word enters MSB byte first; bits shift left, no bit reflection.',
            'example_input_hex':example.hex(), 'unitree_crc_hex':f"{bitwise_reference(example):08x}",
            'zlib_crc_hex':f"{zlib.crc32(example):08x}",
            'restriction':'Both vendor functions discard a non-multiple-of-four tail; MORI wrapper must require exact packet lengths.'}
        assert py['crc32_lookup'](example + b'\xAA') == py['crc32_lookup'](example)
        comparison = []
        for label,values in [('zero',(0,0,0,0,0)),('positive',(0.01,0.1,0.01,1,0.01)),('negative',(-0.01,-0.1,-0.01,1,0.01))]:
            out=(ctypes.c_uint8*20)(); lib.oracle_build(*values,out)
            cbytes=bytes(out)
            try:
                pbytes=py['build_control_packet'](1,1,1,*values)
                comparison.append({'case':label,'C_hex':cbytes.hex(),'Python_hex':pbytes.hex(),'byte_equal':cbytes==pbytes,
                                   'C_raw':struct.unpack('<hhihh',cbytes[4:16]),'Python_raw':struct.unpack('<hhihh',pbytes[4:16])})
            except struct.error as exc:
                comparison.append({'case':label,'C_hex':cbytes.hex(),'Python_error':str(exc),'finding':'Python uses unsigned I for signed pos_des; negative target rejected.'})
        assert comparison[0]['byte_equal']
        assert 'Python_error' in comparison[2]
        report['command_comparison'] = comparison
        feedback=[]
        for label,sensor,vol in [('nominal',50,24),('unsigned_boundary',200,200)]:
            payload=struct.pack('<bBBhhiIHBB',25,sensor,vol,9,12,10000,0,4096,0,0)
            wire=b'\xFC\xEE\x91'+payload
            wire+=struct.pack('<I',bitwise_reference(wire[2:22]))
            parsed=py['parse_feedback_packet'](wire)
            values=(ctypes.c_float*7)()
            assert lib.oracle_parse(buf(wire),len(wire),values)==1 and parsed is not None
            feedback.append({'case':label,'wire_hex':wire.hex(),'C_sensor':values[1],'Python_sensor':parsed['sensor'],
                             'C_voltage_V':values[2],'Python_voltage_V':parsed['vol']})
            for changed in [wire[:5]+bytes([wire[5]^1])+wire[6:],b'\x00'+wire[1:],wire[:-1]]:
                assert py['parse_feedback_packet'](changed) is None
                assert lib.oracle_parse(buf(changed),len(changed),values)==0
        assert feedback[0]['C_sensor']==feedback[0]['Python_sensor']
        assert feedback[1]['C_sensor']==200 and feedback[1]['Python_sensor']==-56
        report['feedback_comparison'] = feedback
        report['boundary_note'] = 'Synthetic uint8 boundaries are outside normal S288 voltage operation; they expose signedness, not a measured operating fault.'
        report['invalid_feedback_rejection_cases'] = 6
        report['findings'] = [
            'protocol.md uint16 vol is inconsistent with C/Python one-byte layout; C/Python payload size agrees at19 and wire26.',
            'Python command negative pos_des raises struct.error due to unsigned I; C declares int32.',
            'Python sensor/vol uses signed b but C uses uint8; incorrect above127.',
            'C truncates float-to-int; Python rounds. Nonzero command raw values need an explicit conversion policy.',
            'CRC code agrees between C, Python and independent bitwise reference for valid protected lengths; documentation bit-reversed wording is misleading.'
        ]
        report['execution_status']='PASS'
        report['vendor_implementation_consistency']='FAIL'
        report['device_protocol_qualification']='BLOCKED_PENDING_REAL_FIRMWARE_CAPTURE'
    target=BASE/'reports/s288_reference_audit.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(f"HOST audit PASS: {report['CRC']['vectors']} CRC vectors, C sizes20/19/26, 6 invalid frames rejected.")
    print('Vendor consistency FAIL: negative-position packing, uint8 signedness and rounding differ; no device qualified.')


if __name__=='__main__':
    main()
