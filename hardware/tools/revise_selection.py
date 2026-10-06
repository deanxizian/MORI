# Archived migration; retained for history, never part of reproduction.
raise SystemExit("Already applied. Use sync_mechanics.py and create_design.py; do not rerun this migration.")
from pathlib import Path
import json,math
R=Path(__file__).resolve().parents[1]
p=R/'tools/create_design.py';s=p.read_text()
s=s.replace("initial +/-50deg","SER0037 270deg; gear8:14; +/-50deg head commissioning, disabled until calibrated")
s=s.replace("add(ref,'Motor5216_SH6','Connector_JST:JST_SH_BM06B-SRSS-TB_1x06-1MP_P1.00mm_Vertical',[('GND','GND','power_in'),('B',f'ENC_{side}B','open_collector'),('A',f'ENC_{side}A','open_collector'),('VCC','3V3','power_in'),('M2',side+'M2','passive'),('M1',side+'M1','passive')],'connector','Factory pin1 GND/green; 2 B/white; 3 A/yellow; 4 Vcc/blue;5 M2/black;6 M1/red')", "add(ref,'Motor4863_CUSTOM_XH6','Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical',[('GND','GND','power_in'),('B',f'ENC_{side}B_5V','output'),('A',f'ENC_{side}A_5V','output'),('VCC','DEVKIT_5V','power_in'),('M2',side+'M2','passive'),('M1',side+'M1','passive')],'connector','CUSTOM retermination:1 green GND;2 white B;3 yellow A;4 blue Vcc 5V;5 black M2;6 red M1. NOT factory header order. LVC14 level shifts required.')")
s=s.replace('FS90_JR_GND_5V_SIGNAL','SER0037_JR_GND_5V_SIGNAL').replace('FS90 brown/black GND','SER0037 brown GND').replace('FS90 red +5V','SER0037 red +5V').replace('FS90 orange/yellow signal','SER0037 yellow signal')
s=s.replace('motor SH','motor custom XH')
s=s.replace("'factory Pololu4767 AWG30 <=25cm; <=0.622A pulse; verify SH contact <=1A'","'stock motor wire: verify gauge; reterminate JST XH6 with correct terminals; <=0.622A/ch peak'")
s=s.replace('TL431CLP','TL431BCLP')
s=s.replace("('R21','10k','3V3','ENC_LA','ENCODER'),('R22','10k','3V3','ENC_LB','ENCODER'),('R23','10k','3V3','ENC_RA','ENCODER'),('R24','10k','3V3','ENC_RB','ENCODER')", "('R21','100k','ENC_LA_5V','GND','ENCODER'),('R22','100k','ENC_LB_5V','GND','ENCODER'),('R23','100k','ENC_RA_5V','GND','ENCODER'),('R24','100k','ENC_RB_5V','GND','ENCODER')")
marker="# Bus-powered clamp stays operational when the master battery connector opens."
code="""# SN74LVC14A: 5.5V tolerant inputs at 3.3V Vcc. Both A/B inverted together.
lp={1:('1A','ENC_LA_5V','input'),2:('1Y','ENC_LA','output'),3:('2A','ENC_LB_5V','input'),4:('2Y','ENC_LB','output'),5:('3A','ENC_RA_5V','input'),6:('3Y','ENC_RA','output'),7:('GND','GND','power_in'),8:('4Y','ENC_RB','output'),9:('4A','ENC_RB_5V','input'),10:('5Y',None,'output'),11:('5A','GND','input'),12:('6Y',None,'output'),13:('6A','GND','input'),14:('VCC','3V3','power_in')}
add('U5','SN74LVC14AD','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',{str(k):dict(name=v[0],net=v[1],type=v[2]) for k,v in lp.items()},section='ENCODER')
two('C13','100nF','3V3','GND','Capacitor_SMD:C_0805_2012Metric',section='ENCODER')
"""
s=s.replace(marker,code+marker) if "add('U5'" not in s else s
s=s.replace("item('balance','wheel motor',2,'Pololu 5216 HPCB12V 100.37:1 back encoder','12V;330rpm;0.75A stall;12CPR motor x4','13.6x13x32.5 +10 shaft',11,P+'5216',32.45", "item('balance','wheel motor',2,'Pololu 4863 25D MP12V 20.408667:1 48CPR','12V;380rpm;1.8A stall;48CPR x4;2S and0.39ohm limit','diameter25 x65 +12.5 shaft',98,P+'4863',53.95")
s=s.replace("item('balance','motor cables',2,'Pololu 4767 SH6 female-female 25cm','factory exact motor pinout; AWG30','250 long','TBD',P+'4767',2.5,'allowance_not_quote','buy bench cable')", "item('balance','encoder level shifting',1,'SN74LVC14AD + SOIC14 adapter','5V encoder to3.3V PCNT;5.5V tolerant Schmitt inputs','8.7x3.9 IC plus adapter','TBD','https://www.ti.com/product/SN74LVC14A',3,'allowance_not_quote','REQUIRED; no direct5V into ESP32')")
s=s.replace("item('balance','motor clamp brackets pair',1,'Pololu 1089 Extended Bracket Pair'", "item('balance','motor clamp brackets pair',1,'Pololu 2676 25D Bracket Pair'").replace("P+'1089'","P+'2676'")
s=s.replace("item('balance','wheel hub pair',1,'Pololu 1996 3mm shaft M3 hub pair','pure plain hub cover; engagement >=7mm','TBD','TBD',P+'1996',8.95,'allowance_not_quote','HOLD wheel offset/clearance fit')", "item('balance','belt pulleys and belts set',1,'MORI-BELT-1to1 candidate 27T 2mm pitch 150mm belt','motor4mm bore / wheel6mm;6mm belt requires width revision','pitch diameter17.19; centre48.0; flange TBD','TBD','supplier drawing and quote required',18,'allowance_not_quote','HOLD exact manufacturer SKU/pitch/tension/width: current belt4mm reserve insufficient')")
s=s.replace('3mm D hub adapter','independent6mm wheel axle; belt drive').replace("70,'local print", "130,'local print")
s=s.replace("buy bench display; mask64mm is not active display","bench only; FAIL active60mm target; requires revised opaque mask").replace('comparison only: Waveshare34955 1.46inch; not drop-in','comparison only: DM-TFT24-432 2.4inch MIPI; incompatible direct S3 interface')
s=s.replace("item('interaction','head yaw',1,'FEETECH FS90 / Pololu 2818','position servo 4.8-6V;700-800mA stall;initial +/-50','23.2x12.5x22',9,P+'2818',8.40,'observed_list','buy servo; hold linkage until measured',False)", "item('interaction','head yaw',1,'DFRobot SER0037 270deg PWM','4.8-6V;500-2500us;spec580/740mA stall;gear8:14','22.9x12.3x22.6 ears extra',11.2,'https://www.dfrobot.com/product-1106.html',7.90,'observed_list','buy one bench; HOLD ears/spline/calibration; lower spec torque used',False)")
s=s.replace("HOLD balancing/regen/cell cutoff and shipping; vendor says no UN38.3; factory XT30 termination required","REJECT current tray:66x54x20 vs40x70x20. Legacy bench budget only; HOLD balance/regen/shipping")
s=s.replace("'80x60x1.6'","'96x92x1.6 clipped corners; four deck holes'")
s=s.replace("5V' if '5V' in net", "5V' if '5V' in net")
# Encoder raw outputs have a 5V suffix and will be labelled 5V by exporter.
p.write_text(s)
# Define motor data centrally; regenerate geometry using sync_mechanics later.
c=json.loads((R/'calculations/inputs.json').read_text());c['motor'].update(mpn='Pololu4863',ratio=(22**3*23)/(12*10**3),encoder_counts_motor_x4=48,no_load_rpm=380,no_load_A=.1,stall_A=1.8,stall_torque_Nm=3.2*.0980665,continuous_current_screen_A=.45)
c['power_states'][0]['motor_each_A']=.15;c['power_states'][1]['motor_each_A']=.20
(R/'calculations/inputs.json').write_text(json.dumps(c,indent=2)+'\n')
p=R/'tools/sync_mechanics.py';s=p.read_text().replace("('wheel_motors',.022","('wheel_motors',.196").replace("'2x11g manufacturer","'2x98g manufacturer")
marker="parts['head_servo'].update"
pos=s.index(marker)
s=s[:pos]+"""mtr.update(mpn='Pololu4863 25D MP12V 20.408667:1',actual_max_case_box=[25,25,65],catalog_case_box=[25,25,65],shaft={'diameter':4,'shape':'D','usable_length':12.5,'projection_envelope':12.5},mounting={'thread':'2 x M3','hole_pitch_mm':None,'max_engagement_mm':6,'view':'gearbox face; drawing required for hole coordinates'},source='motor25; motor25_drawing',full_keepout_local=[29,29,88],fit_status='NOT_TESTED; diameter25 and total65 incl encoder within length72 reservation, encoder OD25 exceeds23 placeholder; output shaft12.5 shorter than14; bracket and leads require review')
"""+s[pos:];p.write_text(s)
# Correct pulse-to-distance constant without touching control policy.
p=R/'firmware/main/board.h';s=p.read_text().replace('(0.0002477925858415781f)',f'({math.pi*.095/(48*c["motor"]["ratio"]):.15f}f)');p.write_text(s)
(R/'tools/create_inputs.py').write_text('raise SystemExit("Deprecated provisional generator. Use sync_mechanics.py with existing root params.json; never overwrite current selection inputs.")\n')
print('Selected motor',c['motor']['mpn'],'outputCPR',48*c['motor']['ratio'])
