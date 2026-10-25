"""Material-Bibliothek: benannte, stilisierte Materialien (Miniatur-Look:
matt, leicht samtig, warme Pastelltöne). Farben können pro Stadt über
city.json -> "palette" überschrieben werden."""
import bpy

# name: (RGB 0..1 sRGB-ähnlich, roughness, extra)
BASE = {
    "asphalt": ((0.20, 0.21, 0.23), 0.8, {}),
    "road_line": ((0.93, 0.92, 0.86), 0.6, {}),
    "sidewalk": ((0.72, 0.69, 0.64), 0.85, {}),
    "ground": ((0.80, 0.74, 0.62), 0.9, {}),
    "plaza": ((0.86, 0.81, 0.71), 0.85, {}),
    "grass": ((0.36, 0.52, 0.22), 0.95, {"sheen": 0.6}),
    "soil": ((0.45, 0.31, 0.20), 0.95, {}),
    "soil_dark": ((0.33, 0.22, 0.14), 0.95, {}),
    "backdrop": ((0.93, 0.88, 0.80), 1.0, {}),
    "glass": ((0.10, 0.13, 0.17), 0.25, {}),
    "trunk": ((0.36, 0.25, 0.16), 0.9, {}),
    "leaf": ((0.30, 0.50, 0.20), 0.9, {"sheen": 0.5}),
    "leaf_light": ((0.50, 0.64, 0.28), 0.9, {"sheen": 0.5}),
    "leaf_dark": ((0.17, 0.34, 0.16), 0.9, {"sheen": 0.5}),
    "leaf_autumn": ((0.88, 0.48, 0.18), 0.9, {"sheen": 0.5}),
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
    "travertine": ((0.86, 0.78, 0.62), 0.85, {}),
    "travertine_dark": ((0.66, 0.57, 0.43), 0.9, {}),
    "marble": ((0.94, 0.92, 0.87), 0.5, {}),
    "stone_grey": ((0.62, 0.60, 0.56), 0.85, {}),
    "lead_dome": ((0.55, 0.60, 0.62), 0.5, {}),
    "bronze": ((0.45, 0.33, 0.18), 0.4, {"metallic": 0.6}),
    "sand": ((0.86, 0.73, 0.50), 0.95, {}),
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
    # Detail-Häuser (Referenz-Look)
    "stone_cream": ((0.86, 0.78, 0.64), 0.85, {"noise": 0.10, "bump": 0.15}),
    "stone_warm": ((0.80, 0.68, 0.52), 0.85, {"noise": 0.12, "bump": 0.15}),
    "stone_light": ((0.92, 0.88, 0.80), 0.8, {"noise": 0.06, "bump": 0.1}),
    "stone_ochre": ((0.86, 0.66, 0.42), 0.85, {"noise": 0.12, "bump": 0.15}),
    "stone_rose": ((0.84, 0.62, 0.52), 0.85, {"noise": 0.12, "bump": 0.15}),
    "zinc_blue": ((0.40, 0.46, 0.54), 0.45, {"seams": True, "metallic": 0.3}),
    "zinc_red": ((0.55, 0.30, 0.24), 0.55, {"seams": True}),
    "tile_terracotta": ((0.70, 0.34, 0.22), 0.8, {"seams": True, "noise": 0.08}),
    "window_glass": ((0.10, 0.14, 0.20), 0.08, {"spec": 1.0}),
    "frame_white": ((0.92, 0.90, 0.85), 0.6, {}),
    "iron": ((0.08, 0.08, 0.09), 0.5, {"metallic": 0.6}),
    "shop_wood": ((0.20, 0.17, 0.15), 0.6, {}),
    "chimney_pot": ((0.66, 0.36, 0.25), 0.85, {}),
    "brick": ((0.62, 0.38, 0.28), 0.9, {"noise": 0.12}),
    "pin_red": ((0.90, 0.13, 0.12), 0.3, {"coat": 0.8}),
}

_overrides = {}


def set_palette(overrides):
    """city.json -> "palette": {"wall_ochre": [r,g,b], ...}"""
    _overrides.update({k: tuple(v) for k, v in (overrides or {}).items()})


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
    if extra.get("noise") or extra.get("seams"):
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


def _surface(nt, bsdf, lin, extra):
    """Leichte Farbvariation (Stein) bzw. Falz-Streifen (Zink-/Ziegeldach)."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    col_out = None
    if extra.get("noise"):
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 6.0
        nz.inputs["Detail"].default_value = 6.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        k = extra["noise"]
        ramp.color_ramp.elements[0].color = (*(c * (1 - k) for c in lin[:3]), 1)
        ramp.color_ramp.elements[1].color = (*(min(1, c * (1 + k)) for c in lin[:3]), 1)
        nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
        col_out = ramp.outputs["Color"]
        nt.links.new(col_out, bsdf.inputs["Base Color"])
        if extra.get("bump"):
            n2 = nt.nodes.new("ShaderNodeTexNoise")
            n2.inputs["Scale"].default_value = 60.0
            nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
            bump = nt.nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = extra["bump"]
            bump.inputs["Distance"].default_value = 0.01
            nt.links.new(n2.outputs["Fac"], bump.inputs["Height"])
            nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if extra.get("seams"):
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.inputs["Scale"].default_value = 18.0
        wv.inputs["Distortion"].default_value = 0.0
        wv.bands_direction = "X"
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        # Falze laufen in Gefällerichtung: Wellenmuster aus der Tangente um die Normale
        sep = nt.nodes.new("ShaderNodeVectorMath")
        sep.operation = "CROSS_PRODUCT"
        sep.inputs[1].default_value = (0, 0, 1)
        nt.links.new(geo.outputs["Normal"], sep.inputs[0])
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(sep.outputs["Vector"], dot.inputs[1])
        nt.links.new(tc.outputs["Object"], dot.inputs[0])
        nt.links.new(dot.outputs["Value"], wv.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.6
        bump.inputs["Distance"].default_value = 0.01
        nt.links.new(wv.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


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
