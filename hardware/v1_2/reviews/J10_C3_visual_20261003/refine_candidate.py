"""C4 candidate only. Individual reviewed routing changes, native DRC per edit.
No footprint, pad, via, rule, width, board-outline or schematic edits.
"""
from pathlib import Path
import sys, shutil, json, hashlib, subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SRC=ROOT/'hardware/v1_2/j10_routing_C3_20261002'
sys.path.insert(0,str(SRC))
import candidate as c
k=c.k
OLD='MORI_power_J10_C3_CANDIDATE';NAME='MORI_power_J10_C4_CANDIDATE'
D=HERE/NAME;R=HERE/'reports';R.mkdir(exist_ok=True)
c.NAME=NAME;c.D=D;c.PCB=D/(NAME+'.kicad_pcb');c.R=R

OPS=[
 ('V01_CHG_N_bottom','/CHG_N','F.Cu',['1ff2d89d-54db-4e51-a27d-d869cdc217bf','226c8c08-ecf1-4c7b-bec0-04989e4468a5','33c1e746-48db-474d-8808-2d4a1c46ae81','558610f2-6b13-4412-a3c4-ce26033e5c59'],[(38.3,45.4),(40.15,43.55),(43.5,43.55),(44.0,44.05)]),
 ('V02_BAT_ADC_corner','/BAT_ADC','B.Cu',['36555f47-2b4b-467e-b6b2-04f6b69ddfa2','59443ed3-eb69-4abd-90fa-215b6f36cda4','a35a12f6-f4c2-4cc2-80d1-f0d6435c490a'],[(40.4,20.3),(40.4,18.6),(40.8,18.2),(43.5,18.2)]),
 ('V03_BAT_ADC_jog','/BAT_ADC','B.Cu',['09f915a8-7b3a-4808-9b03-a0783fe5e460','a48a539b-53a2-4ff4-b021-83daa8782db4','d5dbd5aa-eab3-4888-82a7-a86a9e7b576d','dcbccba6-057b-46cb-9359-1cd6187a7b49'],[(43.5,18.2),(45.7,20.4),(46.3,20.4)]),
 ('V04_ARM_Q_R54','/ARM_Q','F.Cu',['11ed4325-915d-430e-b9d5-2a0b2a0dd8de','26c451b0-66d7-440a-a27c-380bcc262819','e7ab125f-230d-428a-af60-7d38ce56e3c6','365cc20c-f9e5-4631-9eb7-da68c47ef6b5','1e6bf852-1cdf-4534-a9cd-a655fbdfabba'],[(43.7896,46.3296),(45.9954,46.3296),(46.825,45.5),(47.3,45.5),(48.0,44.8)]),
 ('V05_M5_EN_corner','/M5_EN','B.Cu',['1a02014c-ceee-484d-b42b-a3575325ed6e','549fd95c-b90f-4e72-8de3-bd4490f60232','d45eb035-425c-488a-a131-96bd2694f91e'],[(31.0,28.1),(31.0,28.7),(30.6,29.1),(28.1,29.1)]),
 ('V06_MOTION_feedback','/+5V_MOTION','F.Cu',['1527a5a0-3f27-4621-933a-4e6888c105fb','20bd755f-950a-4fef-8b09-99b9970fd335','367d027c-36ad-4b3d-aeac-43d9c427d5eb','895d7f63-38d7-492f-9ccc-124c9c447003','a9a8b1eb-7b62-4e32-a92b-678987cef9f7','cdc1e876-d498-4b16-be07-4596ecfb8feb','f0e2c74b-e9de-4747-931a-34fd7fae8246'],[(12.7,24.892),(12.7,27.0),(14.0,28.3),(15.4,28.3),(16.6,29.5),(16.6,31.2)]),
 ('V07_CHG_N_board_edge','/CHG_N','F.Cu',['359a531f-ec41-4aa7-9944-b8b80d89447b','3ed1b3b3-87fb-48e1-9d72-96a1b7d4e6db','b4b1f2e7-948e-477b-9112-03ebc441b065'],[(19.6,50.8),(22.1,53.3),(34.9,53.3)]),
 ('V08_CHG_N_exact_join','/CHG_N','B.Cu',['fb647b1d-9dc5-49b1-84d5-a280aba81ec3','88919853-8ea8-42c6-9e66-fa7d7d785f19'],[(4.7752,32.6136),(3.5,33.8888),(3.5,36.0)]),
]

# Second alternatives after native rule failures; original attempts remain in log.
OPS += [
 ('V09_ARM_Q_R54_clean','/ARM_Q','F.Cu',
  ['11ed4325-915d-430e-b9d5-2a0b2a0dd8de','26c451b0-66d7-440a-a27c-380bcc262819','e7ab125f-230d-428a-af60-7d38ce56e3c6'],
  [(43.7896,46.3296),(46.4954,46.3296),(47.325,45.5)]),
 ('V10_MOTION_feedback_clean','/+5V_MOTION','F.Cu',OPS[5][3],
  [(12.7,24.892),(12.7,27.6),(13.2,28.1),(15.2,28.1),(16.6,29.5),(16.6,31.2)]),
 ('V11_BAT_ADC_corridor','/BAT_ADC','B.Cu',OPS[2][3],
  [(43.5,18.2),(44.1,18.8),(44.1,19.6),(44.9,20.4),(46.3,20.4)]),
]

OPS += [
 ('V12_ARM_Q_R54_pad_join','/ARM_Q','F.Cu',OPS[8][3],
  [(43.7896,46.3296),(46.225,46.3296),(46.825,45.7296),(46.825,45.5)]),
]

def init():
    assert not D.exists(),'Candidate already exists; never reset reviewed changes'
    inputs={}
    for p in (SRC/OLD).rglob('*'):
        if not p.is_file() or p.suffix in ['.kicad_prl','.lck']:continue
        inputs[str(p.relative_to(ROOT))]=c.sha(p)
        q=D/p.relative_to(SRC/OLD).parent/p.name.replace(OLD,NAME);q.parent.mkdir(parents=True,exist_ok=True)
        data=p.read_bytes()
        if p.suffix in ['.kicad_sch','.kicad_pro']:data=data.replace(OLD.encode(),NAME.encode())
        q.write_bytes(data)
    c.dump(R/'C3_input_hashes.json',inputs)
    b=c.load();b.GetTitleBlock().SetRevision('J10-C4 / PROTOTYPE / VISUAL REVIEW');c.save(b)

def apply(index):
    log=json.loads((R/'routing_changes.json').read_text()) if (R/'routing_changes.json').exists() else []
    for label,net,layer,ids,pts in [OPS[index]]:
        if any(r['id']==label for r in log):return
        original=c.PCB.read_bytes();b=c.load()
        for zone in b.Zones():
            if not zone.GetIsRuleArea():zone.UnFill()
        tracks={t.m_Uuid.AsString():t for t in b.GetTracks()}
        assert all(u in tracks for u in ids),(label,'missing original track')
        assert all(tracks[u].GetNetname()==net and k.ToMM(tracks[u].GetWidth())==.2 for u in ids)
        for u in ids:b.Delete(tracks[u])
        before={t.m_Uuid.AsString()for t in b.GetTracks()}
        c.track(b,net,pts,.2,b.GetLayerID(layer))
        added=[t.m_Uuid.AsString()for t in b.GetTracks()if t.m_Uuid.AsString()not in before]
        c.save(b);j=c.check(label)
        passed=not j['violations'] and not j['unconnected_items'] and not j['schematic_parity']
        if not passed:c.PCB.write_bytes(original)
        log.append({'id':label,'net':net,'layer':layer,'removed':ids,'added':added,'path':pts,'result':'PASS'if passed else'FAIL_REVERTED','violations':len(j['violations']),'opens':len(j['unconnected_items']),'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':c.sha(c.PCB)})
        c.dump(R/'routing_changes.json',log)

if __name__=='__main__':
    if sys.argv[1]=='init':init()
    elif sys.argv[1]=='one':apply(int(sys.argv[2]))
    elif sys.argv[1]=='snapshot':c.snapshot('C4')
    elif sys.argv[1]=='apply':
        for index in range(len(OPS)):
            subprocess.run([sys.executable,str(Path(__file__)), 'one',str(index)],check=True)
        subprocess.run([sys.executable,str(Path(__file__)), 'snapshot'],check=True)
