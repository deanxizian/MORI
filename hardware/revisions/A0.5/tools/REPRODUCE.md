# A0.5 重建与复核

从已有MORI项目运行。以下是本机实际工具路径，换电脑需设置对应路径；不要在唯一工作副本上运行CAD生成脚本，它会重新创建本版载板和布线起点。

固件与模拟测试：

```sh
cd /Users/dean/Documents/MORI
source /Users/dean/esp/esp-idf/export.sh
idf.py -C hardware/revisions/A0.5/firmware reconfigure build
sh hardware/revisions/A0.5/tests/run_host_tests.sh
sh hardware/revisions/A0.5/tests/run_adapter_tests.sh
```

机械副本与试片：

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python hardware/revisions/A0.5/tools/mechanical_review.py
```

该脚本读取原Blender、params.json和derived.json，保存到A0.5/mechanical，不保存回原机械文件。原始完整零件包不在增量ZIP内。

原生载板从零重建（会覆盖A0.5当前CAD，先复制工程）：

```sh
MORI_KICAD_PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
MORI_KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
MORI_JAVA=/Users/dean/Documents/MORI/hardware/.tools/jdk-25.0.4.1+1-jre/Contents/Home/bin/java
MORI_ROUTER=/Users/dean/Documents/MORI/hardware/.tools/freerouting-2.4.1.jar
"$MORI_KICAD_PY" hardware/revisions/A0.5/tools/generate_kicad.py
"$MORI_KICAD_PY" hardware/revisions/A0.5/tools/route_carrier.py prepare
"$MORI_JAVA" -Xmx3g -Djava.awt.headless=true -jar "$MORI_ROUTER" \
  -de hardware/revisions/A0.5/kicad/MORI_carrier.dsn \
  -do hardware/revisions/A0.5/kicad/MORI_carrier.ses \
  -mp 80 -mt 1 -da --router.job_timeout=00:03:00 \
  --gui.enabled=false --api_server.enabled=false -ll INFO
"$MORI_KICAD_PY" hardware/revisions/A0.5/tools/route_carrier.py import
"$MORI_KICAD_PY" hardware/revisions/A0.5/tools/route_carrier.py zones
"$MORI_KICAD_PY" hardware/revisions/A0.5/tools/finish_ground.py
"$MORI_KICAD_CLI" sch erc hardware/revisions/A0.5/kicad/MORI_carrier.kicad_sch \
  --format json -o hardware/revisions/A0.5/reports/erc.json --exit-code-violations
"$MORI_KICAD_CLI" pcb drc hardware/revisions/A0.5/kicad/MORI_carrier.kicad_pcb \
  --format json -o hardware/revisions/A0.5/reports/drc_routed.json \
  --schematic-parity --exit-code-violations
"$MORI_KICAD_PY" hardware/revisions/A0.5/tools/audit_revision.py
```

当前文件由Freerouting2.4.1/Temurin25本地运行产生，匿名分析禁用。工具缓存不打包；[Freerouting2.4.1官方发布](https://github.com/freerouting/freerouting/releases/tag/v2.4.1)，JAR SHA256为`251101c3eeac22d7e7dfcf6796603279e5d1000283eb82d8f093780f7afc6aa9`。Java压缩包来源与校验见sources/java25_release.json；解压在hardware/.tools，没有全局安装。

初版2.1路由与若干修复尝试未通过原生DRC，记录保留在reports中。最终路由以autorouter_clean_03.log + finish_ground.py + native DRC为准，不以旧日志计数为准。重新路由不保证得到相同路径，所有新结果都必须重新通过DRC与布局审查，不能只套用此版验证结论。
