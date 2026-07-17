#!/usr/bin/env python3
"""Extract WLED's palette DATA from the checkout into JSON for the simulator.

Never hand-copy palette data: this parses the same source the firmware
compiles (wled00/palettes.cpp + JSON_palette_names in FX_fcn.cpp), so the sim
renders from identical bytes. Re-run on WLED upgrades.

Usage: python3 sim/extract_palettes.py [WLED_DIR] [OUT_JSON]
Defaults: ~/workspace/WLED-charge -> docs/sign-preview/simulator/wled_palettes.json
"""
import json, os, re, sys

wled = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/workspace/WLED-charge")
out = sys.argv[2] if len(sys.argv) > 2 else "docs/sign-preview/simulator/wled_palettes.json"
src = open(os.path.join(wled, "wled00/palettes.cpp")).read()
fxf = open(os.path.join(wled, "wled00/FX_fcn.cpp")).read()

def ints(body):
    return [int(x, 16) if x.lower().startswith("0x") else int(x, 10)
            for x in re.findall(r"0[xX][0-9a-fA-F]+|\d+", body)]

# --- gradient palettes: const uint8_t|byte NAME_gp[] PROGMEM = { pos,r,g,b, ... };
grads = {}
for m in re.finditer(r"const (?:uint8_t|byte) (\w+)\[\] PROGMEM = \{(.*?)\};", src, re.S):
    grads[m.group(1)] = ints(m.group(2))

# --- CRGB::Name constants (HTMLColorCode enum in fastled_slim.h)
fsl = open(os.path.join(wled, "wled00/src/dependencies/fastled_slim/fastled_slim.h")).read()
htmlcolors = dict((n, int(v, 16)) for n, v in
                  re.findall(r"(\w+)\s*=\s*(0[xX][0-9a-fA-F]+)", fsl))

# --- fastled palettes: const TProgmemRGBPalette16 NAME PROGMEM = { 16 entries,
#     each a u32 literal or a CRGB::Name constant };
fast16 = {}
for m in re.finditer(r"const TProgmemRGBPalette16 (\w+) PROGMEM = \{(.*?)\};", src, re.S):
    body = re.sub(r"//[^\n]*", "", m.group(2))
    v = [htmlcolors[mm.group(1)] if mm.group(1) else int(mm.group(0), 0)
         for mm in re.finditer(r"CRGB::(\w+)|0[xX][0-9a-fA-F]+|\d+", body)]
    assert len(v) == 16, (m.group(1), len(v))
    fast16[m.group(1)] = v

# --- ordered lists
def order(list_name):
    m = re.search(list_name + r"\[\] PROGMEM = \{(.*?)\};", src, re.S)
    body = re.sub(r"//[^\n]*", "", m.group(1))
    return re.findall(r"&?(\w+)", body)

fast_order = order(r"const TProgmemRGBPalette16 \*const fastledPalettes")
grad_order = order(r"const uint8_t\* const gGradientPalettes")

# --- palette names (JSON literal in FX_fcn.cpp)
m = re.search(r'JSON_palette_names\[\] PROGMEM = R"=====\((.*?)\)====="', fxf, re.S)
names = json.loads(m.group(1))

data = {
    "source": "extracted from GLEDOPTO/WLED gledopto-16.0.1 wled00/palettes.cpp",
    "names": names,
    "fastled": [fast16[n] for n in fast_order],            # ids 6..12, 16 x u32 each
    "gradients": [grads[n] for n in grad_order],           # ids 13.., (pos,r,g,b)*
}
assert len(data["fastled"]) == 7, len(data["fastled"])
assert len(data["gradients"]) == 59, len(data["gradients"])
assert len(names) >= 6 + 7 + 59, len(names)
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(data, open(out, "w"), separators=(",", ":"))
print("wrote %s: %d names, %d fastled, %d gradients"
      % (out, len(names), len(data["fastled"]), len(data["gradients"])))
