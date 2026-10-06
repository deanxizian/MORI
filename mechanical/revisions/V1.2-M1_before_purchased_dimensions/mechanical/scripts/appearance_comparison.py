"""Compatibility entry point: V1.2 uses same-camera A/B sculpted-body comparison."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("compare_variants.py")),run_name="__main__")
