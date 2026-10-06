# J10 C2：仅供摆放/接口复核，相关网络未布通

PROTOTYPE / BLOCKED / NO FABRICATION。不是已完成的新版PCB。

J10保持编号孔中心及网络，改JST PH侧出；按JST官方针对玻纤镀通孔的PH建议，候选成品孔0.90mm、铜盘1.50mm（孔成品公差要求+0/−0.05mm，须板厂确认）。D30、F70、R50移背面；JP70旋转/平移，TP71移到(23,35)。正式P5R6和已交接A2未修改。

存在未布通网络及真实DRC问题，详见../reports/FINAL_PLACEMENT_ONLY_drc.json。失败的走线试验未采用，留在../rejected_routing_trials。未导出Gerber、钻孔或制造装配文件。

本候选的摆放、线束出线高度/操作空间、端子成品孔公差和背面热设计尚未全部闭合。请看../README.md，不以原生工程存在或ERC通过作为定板依据。
