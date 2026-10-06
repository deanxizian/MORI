# -*- coding: utf-8 -*-
"""Publish the sourced stock-wheel screening; no geometry or procurement changes."""
from pathlib import Path
import html
import json
import hashlib

P = Path(__file__).resolve().parent
rows = [
    dict(sku='BaneBots T81P-406BB', size='101.6 × 20.32 mm', detail='60 Shore A；页面重量约90.7g，包含范围待确认。现有外形中最接近，但为成品轮，需T81中心接口与防脱设计。', url='https://banebots.com/banebots-compliant-wheel-4-x-0-8-hub-mount-60a-black/', result='保留候选'),
    dict(sku='BaneBots T81P-396BB', size='98.425 × 20.32 mm', detail='60 Shore A；页面重量约99.2g，包含范围待确认。更小但未带来公布重量优势。', url='https://banebots.com/banebots-wheel-3-7-8-x-0-8-hub-mount-60a-black/', result='暂不优先'),
    dict(sku='Pololu 3410 独立硅胶胎圈', size='适配80/90 mm轮，宽10 mm', detail='自由外径66mm、厚2.5mm。厂家允许范围只到90mm；不能据此扩大到105mm。', url='https://www.pololu.com/product/3410', result='尺寸偏小'),
    dict(sku='Hiwonder 21100072', size='外径100 mm；胎面宽29 mm，总宽41 mm', detail='官方尺寸图给出了胎面与整个轮子的不同宽度。铸铝轮芯；单轮重量、胶料硬度尚缺。', url='https://www.hiwonder.com/products/100mm-high-load-bearing-and-wear-resistant-tire', result='宽度过大'),
]
manifest=json.loads((P/'source_manifest.json').read_text())
assert all(hashlib.sha256((P/'sources'/r['file']).read_bytes()).hexdigest()==r['sha256'] for r in manifest['sources'])
report=dict(status='PASS', scope='Sourced first-pass product screening only', selection_status='BLOCKED', main_geometry_changed=False,
            current_design_mm=[105,18], candidates=rows, retrieved_utc=manifest['retrieved_utc'],
            missing=['Matched center/bead dimensions and tolerances','Loaded radius and traction data','Weight scope','Delivered-to-China price and availability'],
            applied=False, purchased=False)
(P/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
table=''.join(f'<tr><td><a href="{r["url"]}">{html.escape(r["sku"])}</a></td><td>{html.escape(r["size"])}</td><td>{html.escape(r["detail"])}</td><td>{r["result"]}</td></tr>' for r in rows)
(P/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 现成软轮胎筛选</title><style>body{margin:0;background:#edf1f0;color:#243a33;font:16px/1.8 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:30px 24px 70px}h1{font-size:32px}h2{margin-top:30px}a{color:#146c53}.notice{padding:18px;background:#fff1d5;border:1px solid #dec59d;border-radius:10px}table{border-collapse:collapse;width:100%}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #c5d2ca}img{width:100%;max-width:720px}code{word-break:break-all}@media(max-width:700px){table,tbody,tr,td{display:block}th{display:none}td{border:0;padding:8px}tr{border-bottom:1px solid #c5d2ca;margin-bottom:16px}}</style><main><a href="../index.html">返回本轮交付</a><h1>现成软轮胎：首轮筛选</h1><p>2026-10-02 · 当前设计105 × 18 mm · 型号尚未冻结</p><p class="notice">已按“现成软胎优先”查找。最近尺寸候选为BaneBots T81P-406BB；它带有成型中心，需要新的转接和防脱接口。尚无可直接套用现有打印轮毂的完整产品资料，主模型没有替换。</p><table><tr><th>厂家产品</th><th>厂家尺寸</th><th>证据与适配影响</th><th>筛选结果</th></tr>'''+table+'''</table><h2>采用最近尺寸候选会改变什么</h2><p>101.6mm相对105mm，直径减小3.4mm、半径减小1.7mm；宽度增加2.32mm。若宽度中心保持，两侧各多占1.16mm。接地后需重核离地间隙、轮轴高度和轮壳间隙，不能直接沿用原检查结果。</p><p>厂家网页的重量范围还不明确，不能与当前“仅软胎”的44.5g估算直接相减。其4英寸产品页面另注明不适用于高速，数值工作范围仍需资料。</p><h2>还缺的到货前输入</h2><ul><li>配合圆、方口、卡簧槽的完整尺寸、公差与装配图；若可单卖胎圈，需自由截面及推荐轮毂配合。</li><li>重量范围、载荷变形及工作转速；国内可交付渠道与含运价格。</li><li>有资料后形成轮径/轮毂修改候选，再请用户确认。此次没有下单或联系供应商。</li></ul><details><summary>幻尔官方尺寸图：胎面宽29mm，总宽41mm</summary><img src="sources/hiwonder_4.jpg" alt="Hiwonder官方尺寸图，100毫米外径、29毫米胎面宽、41毫米总宽"></details><p><a href="REVIEW.md">详细选型记录</a> · <a href="source_manifest.json">来源快照和哈希</a> · <a href="review.json">结构化筛选结果</a></p><p>数据为厂家公布及单位换算，不是实测或采购放行。</p></main></html>''')
print('TYRE_SCREENING_PUBLISHED')
