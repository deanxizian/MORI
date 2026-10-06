"""Native verification of the independent C4 candidate; no source PCB writes.
Run each stage in its own KiCad Python process to bound SWIG board lifetimes.
"""
from refine_candidate import *
import runpy

def native():
    c.check('FINAL')
    args=[c.CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations',
          '-o',str(R/'FINAL_erc.json'),str(D/(NAME+'.kicad_sch'))]
    result=subprocess.run(args,capture_output=True,text=True)
    c.dump(R/'FINAL_erc_command.json',dict(argv=args,returncode=result.returncode,
        stdout=result.stdout,stderr=result.stderr,schematic_sha256=c.sha(D/(NAME+'.kicad_sch'))))
    c.snapshot('FINAL')
    print('ERC',result.returncode)

def audits():
    import layout_P5, audit_body_P5, all_trace_review_P5R2 as ar
    layout_P5.paths=lambda kind:(NAME,D,c.PCB,R)
    audit_body_P5.paths=layout_P5.paths
    runpy.run_path(str(ROOT/'hardware/v1_2/tools/audit_load_paths_P5.py'),run_name='__main__')
    audit_body_P5.audit('power')
    board=k.LoadBoard(str(c.PCB));j=json.loads((R/'body_review_final.json').read_text())
    for footprint in board.GetFootprints():
        if footprint.GetReference()in j['components']:
            j['components'][footprint.GetReference()]['footprint']=footprint.GetFPIDAsString()
    c.dump(R/'body_review_final.json',j)
    ar.paths=layout_P5.paths;ar.source=lambda kind:(OLD,SRC/OLD,SRC/OLD/(OLD+'.kicad_pcb'))
    ar.ROOT=ROOT;ar.O=HERE
    ar.extract('power','before');ar.extract('power','after')

def invariants():
    import re
    # Shared established verifier, rebound to candidate-only source/destination.
    code=(SRC/'verify.py').read_text().replace('from candidate import *','')
    code=code.replace("R/'input_hashes.json'","R/'C3_input_hashes.json'")
    code=code.replace('C2_source','C3_source').replace('C2_sha256','C3_sha256')
    code=code.replace("'C3_sha256':sha(PCB)","'C4_sha256':sha(PCB)")
    environment=dict(vars(c));environment.update(dict(SD=SRC/OLD,OLD=OLD,NAME=NAME,D=D,PCB=c.PCB,R=R,ROOT=ROOT))
    exec(compile(code,str(SRC/'verify.py'),'exec'),environment)
    j=json.loads((R/'invariants.json').read_text())
    before=json.loads((R/'before_inventory.json').read_text())
    after=json.loads((R/'after_inventory.json').read_text())
    original={t['uuid']:t for t in before['tracks']}
    changed=[t for t in after['tracks']if t['uuid']not in original or any(t[x]!=original[t['uuid']][x]for x in ['net','layer','a','z','width'])]
    removed=[t for t in before['tracks']if t['uuid']not in {u['uuid']for u in after['tracks']}]
    j['checks']['all_via_geometry_unchanged']=sorted(before['vias'],key=lambda x:x['uuid'])==sorted(after['vias'],key=lambda x:x['uuid'])
    j['checks']['only_0p2mm_signal_or_feedback_segments_modified']=all(t['width']==.2 for t in changed+removed)
    erc=json.loads((R/'FINAL_erc.json').read_text())
    j['checks']['zero_ERC']=all(not sheet.get('violations')for sheet in erc['sheets'])
    j['checks']['no_DRC_ignored_checks']=not json.loads((R/'FINAL_drc.json').read_text())['ignored_checks']
    j['status']='PASS'if all(j['checks'].values())else'FAIL'
    j['changed_segments']=len(changed);j['removed_segments']=len(removed)
    j['changed_nets']=sorted({t['net']for t in changed+removed})
    j['before_stats']=before['stats'];j['after_stats']=after['stats']
    c.dump(R/'invariants.json',j);print(j['status'],j['checks'])

if __name__=='__main__':globals()[sys.argv[1]]()
