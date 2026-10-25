"""Material-Bibliothek: benannte, stilisierte Materialien (Miniatur-Look:
matt, leicht samtig, warme Pastelltöne). Farben können pro Stadt über
city.json -> "palette" überschrieben werden."""
import bpy

# name: (RGB 0..1 sRGB-ähnlich, roughness, extra)
BASE = {
    "asphalt": ((0.25, 0.26, 0.28), 0.85, {"noise": 0.16, "noise_scale": 1.5, "grime": 0.35, "bump": 0.3, "objvar": 0.0}),
    "road_line": ((0.93, 0.92, 0.86), 0.6, {}),
    "sidewalk": ((0.76, 0.72, 0.66), 0.85, {"noise": 0.07, "grime": 0.45, "pavers": True, "paver_scale": 9.0, "seam_bump": 0.12, "objvar": 0.0}),
    "ground": ((0.80, 0.74, 0.62), 0.9, {}),
    "plaza": ((0.84, 0.79, 0.69), 0.85, {"noise": 0.08, "grime": 0.4, "pavers": True, "seam_bump": 0.15}),
    "grass": ((0.36, 0.52, 0.22), 0.95, {"sheen": 0.6}),
    "soil": ((0.45, 0.31, 0.20), 0.95, {}),
    "soil_dark": ((0.33, 0.22, 0.14), 0.95, {}),
    "backdrop": ((0.96, 0.93, 0.87), 1.0, {}),
    "glass": ((0.10, 0.13, 0.17), 0.25, {}),
    "leaf_blossom": ((0.90, 0.88, 0.84), 0.85, {"leafy": True, "seam_bump": 0.8, "grime": 0.9, "noise": 0.15, "noise_scale": 9.0, "objvar": 0.1, "bump": 0.4}),
    "leaf_olive": ((0.45, 0.50, 0.26), 0.85, {"leafy": True, "seam_bump": 0.8, "grime": 0.9, "noise": 0.2, "noise_scale": 9.0, "objvar": 0.15, "bump": 0.4}),
    "lamp_green": ((0.10, 0.16, 0.13), 0.45, {"metallic": 0.5}),
    "taillight": ((0.75, 0.08, 0.06), 0.3, {}),
    "trunk": ((0.30, 0.22, 0.16), 0.9, {"grime": 0.5, "noise": 0.15}),
    "leaf": ((0.30, 0.48, 0.17), 0.85, {"leafy": True, "seam_bump": 0.8, "grime": 0.9, "noise": 0.2, "noise_scale": 9.0, "objvar": 0.15, "bump": 0.4}),
    "leaf_light": ((0.50, 0.62, 0.25), 0.85, {"leafy": True, "seam_bump": 0.8, "grime": 0.9, "noise": 0.2, "noise_scale": 9.0, "objvar": 0.15, "bump": 0.4}),
    "leaf_dark": ((0.18, 0.33, 0.14), 0.85, {"leafy": True, "seam_bump": 0.8, "grime": 0.9, "noise": 0.2, "noise_scale": 9.0, "objvar": 0.15, "bump": 0.4}),
    "leaf_autumn": ((0.88, 0.47, 0.16), 0.85, {"leafy": True, "seam_bump": 0.8, "grime": 0.9, "noise": 0.25, "noise_scale": 9.0, "objvar": 0.2, "bump": 0.4}),
    "water": ((0.16, 0.55, 0.62), 0.08, {"water": True}),
    "water_river": ((0.18, 0.42, 0.45), 0.1, {"water": True}),
    "foam": ((0.92, 0.97, 1.0), 0.3, {}),
    "white": ((0.93, 0.92, 0.88), 0.6, {}),
    "dark": ((0.12, 0.11, 0.10), 0.7, {}),
    "metal": ((0.55, 0.56, 0.58), 0.35, {"metallic": 1.0}),
    "gold": ((0.95, 0.72, 0.30), 0.25, {"metallic": 1.0}),
    "red": ((0.80, 0.14, 0.12), 0.45, {}),
    "rubber": ((0.06, 0.06, 0.06), 0.8, {}),
    "headlight": ((1.0, 0.95, 0.8), 0.2, {}),
    "cloud": ((0.98, 0.98, 1.0), 0.9, {}),
    "rain": ((0.55, 0.75, 0.95), 0.1, {}),
    # Stein-Töne für Wahrzeichen
    "travertine": ((0.84, 0.76, 0.62), 0.85, {"grime": 0.7, "noise": 0.1, "objvar": 0.02, "bump": 0.25}),
    "travertine_dark": ((0.55, 0.47, 0.36), 0.9, {"grime": 0.7, "noise": 0.1, "objvar": 0.02, "bump": 0.25}),
    "marble": ((0.94, 0.92, 0.87), 0.5, {}),
    "stone_grey": ((0.66, 0.62, 0.55), 0.85, {"grime": 0.6, "noise": 0.1, "bump": 0.2}),
    "lead_dome": ((0.55, 0.60, 0.62), 0.5, {}),
    "bronze": ((0.45, 0.33, 0.18), 0.4, {"metallic": 0.6}),
    "sand": ((0.82, 0.68, 0.48), 0.95, {"noise": 0.1, "noise_scale": 20.0, "bump": 0.3}),
    # Hausfarben (Stile greifen per Name darauf zu)
    "wall_ochre": ((0.88, 0.64, 0.32), 0.9, {}),
    "wall_sienna": ((0.78, 0.42, 0.26), 0.9, {}),
    "wall_cream": ((0.93, 0.85, 0.68), 0.9, {}),
    "wall_salmon": ((0.92, 0.62, 0.48), 0.9, {}),
    "wall_yellow": ((0.95, 0.78, 0.42), 0.9, {}),
    "wall_rose": ((0.86, 0.55, 0.50), 0.9, {}),
    "wall_stone": ((0.82, 0.77, 0.66), 0.9, {}),
    "roof_terracotta": ((0.72, 0.33, 0.20), 0.85, {}),
    "roof_terracotta2": ((0.62, 0.27, 0.17), 0.85, {}),
    "roof_slate": ((0.36, 0.40, 0.46), 0.6, {}),
    "roof_flat": ((0.70, 0.66, 0.60), 0.9, {}),
    "shutter_green": ((0.22, 0.38, 0.27), 0.7, {}),
    "shutter_brown": ((0.42, 0.26, 0.16), 0.7, {}),
    "awning_red": ((0.74, 0.18, 0.16), 0.8, {}),
    "awning_green": ((0.20, 0.42, 0.30), 0.8, {}),
    "car_red": ((0.78, 0.16, 0.12), 0.3, {"coat": 0.6}),
    "car_blue": ((0.30, 0.50, 0.66), 0.3, {"coat": 0.6}),
    "car_cream": ((0.92, 0.88, 0.76), 0.3, {"coat": 0.6}),
    "car_yellow": ((0.95, 0.74, 0.22), 0.3, {"coat": 0.6}),
    "car_green": ((0.42, 0.58, 0.44), 0.3, {"coat": 0.6}),
    "car_grey": ((0.45, 0.46, 0.48), 0.3, {"coat": 0.6}),
    "bus_orange": ((0.90, 0.48, 0.16), 0.4, {"coat": 0.3}),
    # Detail-Häuser (Referenz-Look): gealterte PBR-Oberflächen
    "stone_cream": ((0.87, 0.80, 0.67), 0.85, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_warm": ((0.80, 0.67, 0.50), 0.85, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_tan": ((0.74, 0.62, 0.47), 0.85, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_light": ((0.91, 0.88, 0.81), 0.75, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_pinkish": ((0.84, 0.70, 0.60), 0.85, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_ochre": ((0.86, 0.63, 0.37), 0.9, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_sienna": ((0.76, 0.46, 0.31), 0.9, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_salmon": ((0.87, 0.60, 0.47), 0.9, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_yellow": ((0.90, 0.75, 0.47), 0.9, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "stone_rose": ((0.84, 0.62, 0.52), 0.9, {'grime': 0.55, 'noise': 0.07, 'objvar': 0.1, 'bump': 0.12}),
    "zinc_blue": ((0.39, 0.44, 0.51), 0.5, {"seams": True, "seam_freq": 9.0, "seam_bump": 0.12, "grime": 0.4, "noise": 0.06, "objvar": 0.08, "metallic": 0.25}),
    "zinc_dark": ((0.30, 0.32, 0.36), 0.5, {"seams": True, "seam_freq": 9.0, "seam_bump": 0.12, "grime": 0.4, "noise": 0.06, "objvar": 0.08, "metallic": 0.25}),
    "zinc_red": ((0.52, 0.30, 0.25), 0.6, {"seams": True, "seam_freq": 9.0, "seam_bump": 0.12, "grime": 0.4, "noise": 0.08, "objvar": 0.08}),
    "tile_terracotta": ((0.68, 0.35, 0.23), 0.8, {"tiles": True, "seam_freq": 8.0, "seam_bump": 0.35, "grime": 0.55, "noise": 0.16, "noise_scale": 6.0, "objvar": 0.14}),
    "window_glass": ((0.07, 0.10, 0.14), 0.06, {"spec": 1.0}),
    "frame_white": ((0.90, 0.88, 0.83), 0.6, {"grime": 0.3, "noise": 0.03}),
    "iron": ((0.06, 0.06, 0.07), 0.45, {"metallic": 0.7}),
    "shop_wood": ((0.19, 0.15, 0.13), 0.55, {"grime": 0.3, "noise": 0.05}),
    "shop_green": ((0.12, 0.24, 0.20), 0.5, {"grime": 0.3, "noise": 0.05}),
    "shop_red": ((0.38, 0.10, 0.09), 0.5, {"grime": 0.3, "noise": 0.05}),
    "chimney_pot": ((0.66, 0.36, 0.25), 0.85, {"grime": 0.5, "noise": 0.1}),
    "brick": ((0.62, 0.38, 0.28), 0.9, {"grime": 0.5, "noise": 0.12}),
    "rooftop_grey": ((0.55, 0.54, 0.52), 0.85, {"grime": 0.6, "noise": 0.12}),
    "hedge": ((0.22, 0.38, 0.14), 0.9, {"leafy": True, "seam_bump": 0.8, "grime": 0.8, "noise": 0.15, "noise_scale": 12.0}),
    "pin_red": ((0.90, 0.13, 0.12), 0.3, {"coat": 0.8}),
}

_overrides = {}


def set_palette(overrides):
    """city.json -> "palette": {"wall_ochre": [r,g,b], ...}"""
    _overrides.update({k: tuple(v) for k, v in (overrides or {}).items()})


def mute(names_prefix=("stone_",), amount=0.15, keep=()):
    """Umgebungsfarben leicht entsättigen, damit das Wahrzeichen hervorsticht."""
    for name, (col, rough, extra) in BASE.items():
        if name.startswith(names_prefix) and name not in keep:
            c = _overrides.get(name, col)
            g = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
            _overrides[name] = tuple(x + (g - x) * amount for x in c)


def _srgb_to_lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def get(name):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    col, rough, extra = BASE.get(name, ((1.0, 0.0, 1.0), 0.5, {}))
    col = _overrides.get(name, col)
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    lin = (*_srgb_to_lin(col), 1.0)
    bsdf.inputs["Base Color"].default_value = lin
    bsdf.inputs["Roughness"].default_value = rough
    mat.diffuse_color = lin
    if extra.get("metallic"):
        bsdf.inputs["Metallic"].default_value = extra["metallic"]
    if extra.get("coat"):
        bsdf.inputs["Coat Weight"].default_value = extra["coat"]
    if extra.get("sheen"):
        bsdf.inputs["Sheen Weight"].default_value = extra["sheen"]
    if any(extra.get(k) for k in ("noise", "seams", "tiles", "grime")):
        _surface(nt, bsdf, lin, extra)
    if extra.get("spec"):
        bsdf.inputs["Specular IOR Level"].default_value = extra["spec"]
    if extra.get("water"):
        _water(nt, bsdf, lin)
    return mat


def _water(nt, bsdf, lin):
    """Wasser mit animierbaren Wellen: Wave-Textur -> Bump; die Mapping-Location
    wird in animate_water() verschoben."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.name = "WaterMapping"
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 3.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    # helle Schaumkronen über den Noise
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.62
    ramp.color_ramp.elements[0].color = lin
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (min(lin[0] * 2.2, 1), min(lin[1] * 1.6, 1), min(lin[2] * 1.5, 1), 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.8


def _n(nt, typ, **inputs):
    node = nt.nodes.new(typ)
    for k, v in inputs.items():
        node.inputs[k].default_value = v
    return node


def _math(nt, op, a, b=None, clamp=False):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = op
    m.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            m.inputs[i].default_value = v
        else:
            nt.links.new(v, m.inputs[i])
    return m.outputs[0]


def _mixrgb(nt, blend, fac, a, b):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = blend
    for sock, v in ((0, fac), (6, a), (7, b)):
        if isinstance(v, (int, float)):
            m.inputs[sock].default_value = v
        elif isinstance(v, tuple):
            m.inputs[sock].default_value = v
        else:
            nt.links.new(v, m.inputs[sock])
    return m.outputs[2]


def _surface(nt, bsdf, lin, extra):
    """Prozedurales PBR-"Altern": Farbvariation pro Objekt + großflächig,
    Schmutz in Ecken/Fugen (Ambient Occlusion), senkrechte Regenschlieren,
    Rauheitsvariation, Mikro-Relief; Dachfalze bzw. Ziegelreihen."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    col = lin
    # 1) Farbvariation je Objekt/Instanz
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    hsv = _n(nt, "ShaderNodeHueSaturation", Color=lin)
    var = extra.get("objvar", 0.06)
    nt.links.new(_math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", oi.outputs["Random"], 0.5), var * 0.25), 0.5),
                 hsv.inputs["Hue"])
    nt.links.new(_math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", oi.outputs["Random"], 0.5), var * 2.5), 1.0),
                 hsv.inputs["Value"])
    col = hsv.outputs["Color"]
    # 2) großflächige Fleckigkeit
    k = extra.get("noise", 0.08)
    nz = _n(nt, "ShaderNodeTexNoise", Scale=extra.get("noise_scale", 4.0), Detail=8.0, Roughness=0.6)
    nt.links.new(obj, nz.inputs["Vector"])
    f = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", nz.outputs["Fac"], 0.5), 2 * k), 1.0)
    col = _mixrgb(nt, "MULTIPLY", 1.0, col, _rgb_from_value(nt, f))
    # 3) Ziegelreihen / Falze
    height = None
    if extra.get("seams") or extra.get("tiles"):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        cross = nt.nodes.new("ShaderNodeVectorMath")
        cross.operation = "CROSS_PRODUCT"
        cross.inputs[1].default_value = (0, 0, 1)
        nt.links.new(geo.outputs["Normal"], cross.inputs[0])
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(cross.outputs["Vector"], dot.inputs[1])
        nt.links.new(obj, dot.inputs[0])
        along = dot.outputs["Value"]
        wv = _n(nt, "ShaderNodeTexWave", Scale=1.0, Distortion=0.0)
        wv.wave_profile = "SAW" if extra.get("tiles") else "SIN"
        nt.links.new(_math(nt, "MULTIPLY", along, extra.get("seam_freq", 3.0)), wv.inputs["Vector"])
        height = wv.outputs["Fac"]
        if extra.get("tiles"):  # zusätzlich waagrechte Reihen
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            nt.links.new(obj, sep.inputs[0])
            rows = _n(nt, "ShaderNodeTexWave", Scale=1.0, Distortion=0.0)
            rows.wave_profile = "SAW"
            nt.links.new(_math(nt, "MULTIPLY", sep.outputs["Z"], 2.2), rows.inputs["Vector"])
            height = _math(nt, "MULTIPLY", height, rows.outputs["Fac"])
            col = _mixrgb(nt, "MULTIPLY", 0.25, col, _rgb_from_value(nt, _math(nt, "ADD", rows.outputs["Fac"], 0.4)))
    # 4) Schmutz in Ecken (AO) + Regenschlieren
    g = extra.get("grime", 0.0)
    if g:
        ao = _n(nt, "ShaderNodeAmbientOcclusion", Distance=0.25)
        ao.only_local = True
        dirt = _math(nt, "POWER", ao.outputs["AO"], 1.5)
        col = _mixrgb(nt, "MULTIPLY", g, col, _rgb_from_value(nt, dirt))
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (14, 14, 1.2)
        nt.links.new(obj, mp.inputs["Vector"])
        st = _n(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=4.0)
        nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
        streak = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", st.outputs["Fac"], 0.5), g * 0.5), 1.0)
        col = _mixrgb(nt, "MULTIPLY", 1.0, col, _rgb_from_value(nt, streak))
    if extra.get("pavers"):  # Pflastersteine
        br = _n(nt, "ShaderNodeTexBrick", Scale=extra.get("paver_scale", 5.0), **{"Mortar Size": 0.03})
        br.inputs["Color1"].default_value = (1, 1, 1, 1)
        br.inputs["Color2"].default_value = (0.86, 0.84, 0.8, 1)
        br.inputs["Mortar"].default_value = (0.6, 0.58, 0.55, 1)
        nt.links.new(obj, br.inputs["Vector"])
        col = _mixrgb(nt, "MULTIPLY", 1.0, col, br.outputs["Color"])
        height = br.outputs["Fac"]
    if extra.get("leafy"):  # Blattbüschel: Voronoi-Zellen als Relief + Farbspiel
        vo = _n(nt, "ShaderNodeTexVoronoi", Scale=extra.get("leaf_scale", 30.0))
        nt.links.new(obj, vo.inputs["Vector"])
        col = _mixrgb(nt, "MULTIPLY", 0.35, col, vo.outputs["Color"])
        height = _math(nt, "MULTIPLY", vo.outputs["Distance"], -1.0)
    nt.links.new(col, bsdf.inputs["Base Color"])
    # 5) Rauheit + Relief
    rough = bsdf.inputs["Roughness"].default_value
    r = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", nz.outputs["Fac"], 0.5), 0.3), rough, clamp=True)
    nt.links.new(r, bsdf.inputs["Roughness"])
    micro = _n(nt, "ShaderNodeTexNoise", Scale=80.0, Detail=4.0)
    nt.links.new(obj, micro.inputs["Vector"])
    h = micro.outputs["Fac"] if height is None else _math(nt, "ADD", _math(nt, "MULTIPLY", height, 1.0), _math(nt, "MULTIPLY", micro.outputs["Fac"], 0.15))
    bump = _n(nt, "ShaderNodeBump", Strength=extra.get("bump", 0.12) if height is None else extra.get("seam_bump", 0.35), Distance=0.01)
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def _rgb_from_value(nt, v):
    c = nt.nodes.new("ShaderNodeCombineColor")
    for i in range(3):
        nt.links.new(v, c.inputs[i])
    return c.outputs[0]


def animate_water(f0, f1, speed=0.03):
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        mp = mat.node_tree.nodes.get("WaterMapping")
        if not mp:
            continue
        sock = mp.inputs["Location"]
        sock.default_value = (0, 0, 0)
        sock.keyframe_insert("default_value", frame=f0)
        sock.default_value = (speed * (f1 - f0) * 0.4, speed * (f1 - f0), speed * (f1 - f0) * 0.5)
        sock.keyframe_insert("default_value", frame=f1)
