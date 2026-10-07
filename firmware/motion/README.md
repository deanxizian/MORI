# MORI独立软件工作副本 SW-0.4

初始来源为HW-SW-0.3快照，本次按用户指令选择性合并HW-SW-0.4。已保留软件状态机、协议、模拟HAL、安装矩阵和实时性修复；本目录没有被上游最小固件覆盖。

从MORI根目录执行：

```sh
bash software/scripts/idf_build.sh
bash software/scripts/test_host.sh
python3 -m unittest discover -s software/tests -p 'test_*.py' -v
python3 software/scripts/verify_delivery.py --require-current-handoff
```

仅构建和离线验证，不连接/烧录设备。ESP-IDF v5.5.2及dependencies.lock保持。功率、平衡、头部、轴四安全门默认n，增益全0；任何实物功能NOT_TESTED。

轮比例唯一运行时来源为components/mori_core/include/mori_io.h：#4863，48CPR已含x4，精确20.4086667:1，1:1候选皮带，979.616 counts/rev。头部/显示/电池阈值不变。接线、电平、J12/J14 USB互斥供电、VMAIN/VM_MOTOR边界和全部实测前置条件见../../README.md、../../docs/debug_manual.md、../../docs/hw_sw_0_4.md。
