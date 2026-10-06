"""Package an executed mechanical revision without replacing an earlier release."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
import argparse, datetime, hashlib, json, shutil, zipfile

PROJECT = Path(__file__).resolve().parents[2]

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        self.refs.extend(value for key, value in attrs if key in ('href', 'src'))

def check(project):
    root = project / 'mechanical'
    reports = root / 'reports'
    assert read(reports / 'validation.json')['counts']['FAIL'] == 0
    assert read(reports / 'delivery_consistency.json')['status'] == 'PASS'
    assert read(reports / 'rebuild_check.json')['status'] == 'PASS'
    exports = read(reports / 'export_manifest.json')
    assert exports['candidate_count'] == exports['exported_count']
    for part in exports['parts']:
        assert part['status'] == 'PASS' and sha(root / part['file']) == part['sha256']
    for path, digest in read(reports / 'build_manifest.json')['input_sha256'].items():
        assert sha(project / path) == digest, path
    parser = Links()
    parser.feed((root / 'index.html').read_text())
    missing = [value for value in parser.refs if not urlparse(value).scheme
               and urlparse(value).path and not (root / unquote(urlparse(value).path)).exists()]
    assert not missing, missing
    return len(parser.refs)

def ignore(directory, names):
    return [name for name in names if name in ('__pycache__', '.DS_Store', 'history', 'quarantined_stl')
            or name.endswith(('.pyc', '.blend1', '.blend2'))]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-parent', type=Path, required=True)
    args = parser.parse_args()
    check(PROJECT)
    geom = read(PROJECT / 'config/geometry.json')
    revision = geom['revision']
    dest = args.output_parent / ('MORI_' + revision.replace('-', '_'))
    archive = dest.with_suffix('.zip')
    if dest.exists() or archive.exists():
        raise FileExistsError('Existing releases are preserved: ' + str(dest))
    for name in ('mechanical', 'config', 'contracts'):
        shutil.copytree(PROJECT / name, dest / name, ignore=ignore)
    for name in ('MORI_SPEC_V1.md', 'AGENTS.md'):
        shutil.copy2(PROJECT / name, dest / name)
    # Include the currently referenced hardware handoff as context, without changing it.
    for name in ('hardware/v1/procurement', 'hardware/v1/reviews'):
        if (PROJECT / name).exists():
            shutil.copytree(PROJECT / name, dest / name, ignore=ignore)
    if (PROJECT / 'hardware/mechanical_interfaces.json').exists():
        shutil.copy2(PROJECT / 'hardware/mechanical_interfaces.json', dest / 'hardware/mechanical_interfaces.json')
    reports = dest / 'mechanical/reports'
    checks = read(reports / 'validation.json')
    size = next(c['measurement']['xyz_mm'] for c in checks['checks'] if c['id'] == 'assembled_size')
    count = read(reports / 'export_manifest.json')['exported_count']
    hardware = read(dest / 'contracts/mechanical_interfaces.json').get('hardware_candidate_revision')
    (dest / 'README.md').write_text(f'''# MORI {revision} · 参数化机械项目

实际 Blender 模型，正常宽×深×高：{' × '.join(f'{v:.1f}' for v in size)} mm。
轮径 {geom['wheel_diameter_mm']} mm，腹部离地 {geom['ground_clearance_mm']} mm，轮壳目标间隙 {geom['wheel_body_gap_mm']} mm。

- [实际模型图册](mechanical/index.html)
- [同尺度前后对比](mechanical/renders/wheel_inset_front_comparison.jpg)
- [可编辑 Blender 模型](mechanical/models/MORI_V1_A.blend)
- [检查报告](mechanical/reports/阶段A检查报告.md)
- [重新生成说明](mechanical/README.md)
- 候选打印件：mechanical/exports/stl/，共 {count} 件。

在本目录运行 `python3 mechanical/scripts/run_all.py`。可用 MORI_BLENDER 指定 Blender；跨平台依赖及可选 Pillow 见重新生成说明。

检查计数：{checks['counts']}。这是阶段 A 的几何与器件包络模型；仍需阶段 B 硬件适配、试打、强度和实机平衡验证。
共享尺寸只有 config/geometry.json；接口与硬件候选 {hardware} 在 contracts/mechanical_interfaces.json。附带硬件交接资料作上下文，不表示候选已装入，也不包含完整固件、客户端或 PCB 工程。

旧修订按版本标识保留作历史对比。PACKAGE_MANIFEST.json 保存 SHA-256 文件清单（不含清单自身）。
''')
    links = check(dest)
    manifest = {'revision': revision, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'scope': 'Mechanical candidate release, not manufacturing approval',
                'files': {str(p.relative_to(dest)): sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}}
    (dest / 'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(dest.rglob('*')):
            if path.is_file():
                z.write(path, path.relative_to(args.output_parent))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    assert all(sha(dest / path) == digest for path, digest in manifest['files'].items())
    print(json.dumps({'status': 'PASS', 'delivery': str(dest), 'archive': str(archive),
                      'files': len(manifest['files']) + 1, 'gallery_links': links,
                      'zip_bytes': archive.stat().st_size, 'zip_sha256': sha(archive)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
