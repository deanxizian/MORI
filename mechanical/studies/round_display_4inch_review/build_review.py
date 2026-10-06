"""Read-only sizing study. Never writes production geometry or hardware files."""
from pathlib import Path
import hashlib
import json
import math
import platform

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt, patches, font_manager

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
INPUTS = [ROOT / "config/geometry.json", ROOT / "contracts/mechanical_interfaces.json",
          ROOT / "contracts/components.json", ROOT / "mechanical/reports/mass_budget.json"]
def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS}

before = hashes()
g = json.loads(INPUTS[0].read_text())
mass = json.loads(INPUTS[3].read_text())
head = g["head_diameter_mm"]
old = g["display"]["active_diameter_mm"]
new = 101.52
r = head / 2
old_plane = math.sqrt(r*r - (g["display"]["mask_outer_diameter_mm"] / 2)**2)
new_plane = math.sqrt(r*r - (new / 2)**2)
totals = mass["totals"]["whole_robot"]
m = totals["mass_g_rounded"]
z = totals["center_mm_rounded"][2]
sources = {
    "waveshare_hdmi": "https://www.waveshare.com/wiki/4inch_720x720_LCD",
    "waveshare_p4": "https://docs.waveshare.com/ESP32-P4-WIFI6-Touch-LCD-XC",
    "waveshare_p4_cad": "https://files.waveshare.com/wiki/ESP32-P4-WIFI6-Touch-LCD-XC/ESP32-P4-WIFI6-TOUCH-LCD-4C-3D.zip",
    "zhunyi_raw": "https://www.zhunyidisplay.com/products/z40054-4-inch-720720-lcd-display-mipi-interface-500-cd-m2-round-tft-lcm/",
    "espressif_s3_rgb": "https://docs.espressif.com/projects/esp-iot-solution/en/latest/display/lcd/rgb_lcd.html",
}
result = {
    "date": "2026-09-26", "baseline_revision": g["revision"], "units": "mm",
    "scope": "Independent numerical sizing study; no replacement selected; production CAD/PCB unchanged.",
    "sources": sources, "source_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (OUT / "sources").iterdir() if p.suffix.lower() in (".zip", ".pdf", ".stp")},
    "input_hashes": before,
    "baseline": {"head_diameter": head, "active_diameter": old, "mask_diameter": g["display"]["mask_outer_diameter_mm"],
        "whole_mass_g_assumed": m, "com_z_mm_assumed": z, "mass_uncertainty": mass["uncertainty"]},
    "candidates": [
        {"model": "Waveshare 4inch 720x720 LCD HDMI", "evidence": "VENDOR_DOCUMENTED",
         "active_diameter": new, "module_xyz": [126,126,17], "power_W_typical": 1.8,
         "interface": "HDMI display; USB touch/power", "unchanged_head_fit": "FAIL"},
        {"model": "Waveshare ESP32-P4-WIFI6-Touch-LCD-4C SKU31522", "evidence": "VENDOR_DOCUMENTED",
         "active_diameter": new, "drawing_outer_diameter":126, "drawing_thickness":15.1,
         "official_STEP_AABB_xyz": [126,126,15.5000001],
         "dimension_discrepancy": "Drawing thickness15.1 versus full vendor STEP bound15.5; revision/feature must be confirmed.",
         "interface": "Integrated P4/C6; 2-lane MIPI display/camera; different camera/audio integration",
         "unchanged_head_fit": "FAIL"},
        {"model": "Zhunyi Z40054 bare LCD", "evidence": "VENDOR_DOCUMENTED per-field webpage",
         "active_diameter":new, "LCM_xyz_without_FPC": [105.60,109.87,2.22], "interface": "MIPI",
         "fit": "NOT_TESTED", "unknown": "Installed FPC/controller/backlight supply/fastening/tolerances/mass/quote; no vendor 3D received"}
    ],
    "computed": {"active_diameter_ratio":new/old, "active_area_ratio":(new/old)**2,
        "active_fraction_of_head_diameter":new/head, "projected_side_margin_before_bezel_mm":(head-new)/2,
        "ideal_sphere_chord_plane": {"existing_60mm_mask_normal_distance":old_plane,
            "new_active_only_normal_distance":new_plane, "inward_difference":old_plane-new_plane,
            "limitation": "Mother sphere chord calculation only, not actual collision detection; existing mask compared with new active aperture only. Tilt rotates this normal; it is not global Y."},
        "framebuffer_RGB565_bytes_720square":720*720*2,
        "framebuffer_ratio_vs_360square":4,
        "COM_sensitivity_assumed_net_added_mass_at_z230mm": [
            {"net_added_g":dm,"com_rise_mm":dm*(230-z)/(m+dm)} for dm in (25,50,100)]},
    "checks": {"production_input_unchanged":"PASS", "numerical_diameter_screening":"PASS",
        "full_candidate_solid_collision":"NOT_TESTED", "camera_FOV":"NOT_TESTED", "combined_joint_motion":"NOT_TESTED",
        "electrical_compatibility":"BLOCKED", "measured_mass_and_torque":"NOT_TESTED",
        "power_and_thermal":"NOT_TESTED", "procurement_and_1000CNY_budget":"BLOCKED"},
    "tools": {"python":platform.python_version(),"matplotlib":matplotlib.__version__,
        "CAD_method":"OCP STEPControl_Reader.TransferRoots; BRepBndLib.AddOptimal_s(False,False) on official STEP; mm dimensions cross-checked with drawing"}
}

font = font_manager.FontProperties(fname="/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
plt.rcParams.update({"font.family":font.get_name(), "axes.unicode_minus":False})
fig, axs = plt.subplots(1,3,figsize=(12.4,4.9),dpi=170)
fig.patch.set_facecolor("#f8fafb")
titles = ["当前 1.85 寸", "4 寸裸屏方向", "4 寸微雪成品"]
notes = ["显示 Ø45.68 / 面罩 Ø60", "显示 Ø101.52 / 面积约 4.94 倍", "模块外径 Ø126 > 头部 Ø120"]
for i, ax in enumerate(axs):
    ax.set_aspect("equal");ax.set_xlim(-73,73);ax.set_ylim(-82,83);ax.axis("off")
    ax.add_patch(patches.Circle((0,0),r,facecolor="#fffdf8",edgecolor="#b2bdc7",lw=1.8))
    if i == 0:
        ax.add_patch(patches.Circle((0,0),30,facecolor="#323943",edgecolor="#323943"))
        ax.add_patch(patches.Circle((0,0),old/2,facecolor="#101722",edgecolor="#29b6c5",lw=1.3))
        ax.text(0,0,"45.68",ha="center",va="center",color="white",fontsize=12)
    elif i == 1:
        ax.add_patch(patches.Circle((0,0),new/2,facecolor="#101722",edgecolor="#29b6c5",lw=1.3))
        ax.text(0,0,"101.52",ha="center",va="center",color="white",fontsize=14)
    else:
        ax.add_patch(patches.Circle((0,0),63,facecolor="#f3dfbd",edgecolor="#bb6814",lw=2))
        ax.add_patch(patches.Circle((0,0),r,fill=False,edgecolor="#4d5967",ls="--",lw=1.4))
        ax.add_patch(patches.Circle((0,0),new/2,facecolor="#101722",edgecolor="#101722"))
        ax.text(0,0,"101.52",ha="center",va="center",color="white",fontsize=14)
    ax.text(0,76,titles[i],fontsize=14,weight="bold",ha="center",color="#182938")
    ax.text(0,-73,notes[i],ha="center",fontsize=10,color="#33495b")
fig.suptitle("MORI · 120 mm 头部与 4 寸圆屏的同尺度比较",fontsize=18,weight="bold",y=.97,color="#182938")
fig.text(.5,.095,"灰色圆为当前头部外径；第 3 图虚线为同一头部轮廓。单位：mm。",ha="center",fontsize=10,color="#526575")
fig.text(.5,.038,"仅比较直径：未表示 10° 倾角、曲面安装、摄像头、背板和排线，不构成装配验证。",ha="center",fontsize=10,color="#526575")
fig.subplots_adjust(left=.025,right=.975,top=.86,bottom=.17,wspace=.05)
fig.savefig(OUT/"diameter_comparison.png",facecolor=fig.get_facecolor())
fig.savefig(OUT/"diameter_comparison.svg",facecolor=fig.get_facecolor())
plt.close(fig)
assert before == hashes(), "Production inputs changed during study"
(OUT/"evaluation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"revision":g["revision"],"computed":result["computed"],"inputs_unchanged":True},ensure_ascii=False,indent=2))
