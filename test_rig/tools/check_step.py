#!/usr/bin/env python3
"""Optional read-only STEP solid checks, using cadquery-ocp 7.8.1.1.post1."""
import json
from pathlib import Path

import OCP
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    files = sorted((ROOT / 'mechanical/print').glob('*.step'))
    if len(files) != 5:
        raise ValueError('Expected exactly five STEP files')
    for path in files:
        reader = STEPControl_Reader()
        if reader.ReadFile(str(path)) != IFSelect_RetDone or reader.TransferRoots() < 1:
            raise ValueError(f'Cannot read {path.name}')
        shape = reader.OneShape()
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        count = 0
        while explorer.More():
            count += 1
            explorer.Next()
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(shape, props)
        valid = BRepCheck_Analyzer(shape).IsValid()
        if not valid or count != 1 or props.Mass() <= 0:
            raise ValueError(f'Invalid or multi-solid STEP: {path.name}')
        rows.append(dict(file=path.name, valid=valid, solids=count, volume_mm3=props.Mass()))
    print(json.dumps(dict(status='PASS', ocp=OCP.__version__, files=rows,
                         scope='STEP solids only; not strength or manufacturing qualification'), indent=2))


if __name__ == '__main__':
    main()
