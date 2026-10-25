"""Read-only S288 capture replay. Never opens a port or transmits commands.

JSONL header: {"source":"SIMULATED"|"RECORDED", "clock":"capture_monotonic_us"}.
Rows: captured_us (same capture host), id, packet_hex. CSV preserves capture
time and source. A recorded label alone is not a BENCH qualification.
"""
import argparse,csv,json,math,re,struct
from pathlib import Path
RATIO=70070/243

def crc32_words(data):
    if len(data)%4:raise ValueError('CRC_LENGTH')
    value=0xffffffff
    for (word,) in struct.iter_unpack('<I',data):
        value^=word
        for _ in range(32):value=((value<<1) ^ (0x04c11db7 if value&0x80000000 else 0))&0xffffffff
    return value

def decode(packet,expected_id):
    if type(expected_id) is not int or not 0<=expected_id<=14:raise ValueError('ID')
    if len(packet)!=26:raise ValueError('LENGTH')
    if packet[:2]!=b'\xfc\xee':raise ValueError('HEADER')
    if packet[2]&15!=expected_id or (packet[2]>>4)&7>1:raise ValueError('MODE_OR_ID')
    if crc32_words(packet[2:22])!=struct.unpack_from('<I',packet,22)[0]:raise ValueError('CRC')
    temp,sensor,voltage,torque,speed,pos,error,absolute,_,_=struct.unpack_from('<bBBhhiIHBB',packet,3)
    return dict(id=expected_id,temperature_c=temp,sensor_raw=sensor,voltage_v=voltage/2,
                torque_estimate_nm=torque/256000*RATIO,speed_rad_s=speed/2.56*math.tau/RATIO,
                position_rad=pos/32768*math.tau/RATIO,absolute_output_rad=(absolute&8191)/8192*math.tau,
                warning=absolute>>13,error=error,timeout_active=bool(packet[2]&128))

def rows(path):
    with Path(path).open() as source:
        header=json.loads(source.readline())
        if header.get('source') not in ('SIMULATED','RECORDED') or header.get('clock')!='capture_monotonic_us':raise ValueError('SOURCE_CLOCK_HEADER')
        previous=-1
        for line in source:
            if len(line)>512:raise ValueError('OVERLONG_RECORD')
            row=json.loads(line)
            if set(row)!={'captured_us','id','packet_hex'}:raise ValueError('FIELDS')
            time=row['captured_us']
            if type(time) is not int or not previous<=time<=2**63-1 or time<0:raise ValueError('CAPTURE_TIME')
            previous=time
            if not isinstance(row['packet_hex'],str) or not re.fullmatch('[0-9a-fA-F]{52}',row['packet_hex']):raise ValueError('HEX_LENGTH')
            yield {'source':header['source'],'captured_us':time,**decode(bytes.fromhex(row['packet_hex']),row['id'])}

def main():
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',required=True);a=p.parse_args()
    # Bounded input size prevents accidentally loading an unbounded capture.
    if Path(a.input).stat().st_size>16*1024*1024:raise SystemExit('capture >16 MiB; split it first')
    data=list(rows(a.input))
    if not data:raise SystemExit('empty capture')
    if any(r['source']=='SIMULATED' for r in data) and 'SIMULATED' not in Path(a.output).name:raise SystemExit('SIMULATED filename required')
    with Path(a.output).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    print(f'{len(data)} frames; source={data[0]["source"]}; no device connected; qualification NOT_TESTED')
if __name__=='__main__':main()
