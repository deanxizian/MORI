# MORI A0.5 原生载板工程

入口`MORI_carrier.kicad_pro`。KiCad10.0.6，本地符号/封装库、connectivity.json、carrier_bom.csv齐备。80个封装包含4个安装孔及11个测试点。模块内部电路仍由厂家模块实现，接口采用真实针号/电气类型，不是全集成主板。

当前原生板包含完整连接和两个GND覆铜区。ERC、DRC与原理图一致性检查见`../reports/verification.md`，不使用自动布线器的“完成”标记代替KiCad检查。

**ROUTING CANDIDATE / UNVALIDATED / NOT FOR FABRICATION**。需要完成局部去耦/回流重排、载板三维装配、瞬态与热验证，详见`../electrical_changes.md`。没有生产Gerber/钻孔文件。

板框96×92，四个3.4mm安装孔与原机械XY一致；PCB(x,y)=(BlenderX+100, BlenderY+100)。高度117只是候选。模型外壳、安装耳和电容/接头真实高度未验证。

当前路由过程：生成原生源→配置网络线宽→导出DSN（额外扩大开孔禁布）→本地Freerouting2.4.1/Java25→导入SES→GND覆铜→补U6短接地过孔→KiCad原生DRC。导入SES后仍要执行`finish_ground.py`，最终原生板是交付依据。源码/重建说明见`../tools/REPRODUCE.md`。
