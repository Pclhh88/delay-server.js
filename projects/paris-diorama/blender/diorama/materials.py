"""Materialbibliothek: warme, leicht matte Miniatur-Materialien (Principled BSDF).

Jede Oberfläche bekommt eine feine prozedurale Farbvariation und ein wenig
Bump, damit nichts nach glattem Platzhalter aussieht.
"""
import bpy


def _hex(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    # sRGB -> linear
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def _mat(name, color, rough=0.6, metal=0.0, var=0.08, noise_scale=40.0, bump=0.15,
         color2=None, spec=0.4, emission=None, transmission=0.0, alpha=1.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Specular IOR Level"].default_value = spec
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
    if transmission:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission:
        bsdf.inputs["Emission Color"].default_value = _hex(emission[0])
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    base = _hex(color)
    m.diffuse_color = base
    if var > 0 or color2:
        tex = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = noise_scale
        noise.inputs["Detail"].default_value = 6.0
        noise.inputs["Roughness"].default_value = 0.6
        nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        c2 = _hex(color2) if color2 else tuple(max(0.0, x * (1 - var * 2.5)) for x in base[:3]) + (1.0,)
        ramp.color_ramp.elements[0].color = c2
        ramp.color_ramp.elements[0].position = 0.3
        ramp.color_ramp.elements[1].color = base
        ramp.color_ramp.elements[1].position = 0.7
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        if bump > 0:
            b = nt.nodes.new("ShaderNodeBump")
            b.inputs["Strength"].default_value = bump
            b.inputs["Distance"].default_value = 0.02
            nt.links.new(noise.outputs["Fac"], b.inputs["Height"])
            nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        bsdf.inputs["Base Color"].default_value = base
    return m


def _foliage(name, c_light, c_dark, scale=9.0):
    """Laub: Voronoi-Blätterbüschel + Farbverlauf + kräftiger Bump."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.75
    bsdf.inputs["Subsurface Weight"].default_value = 0.15
    bsdf.inputs["Subsurface Radius"].default_value = (0.2, 0.3, 0.1)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = scale * 3
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = 'MULTIPLY_ADD'
    mix.inputs[1].default_value = 0.5
    nt.links.new(noise.outputs["Fac"], mix.inputs[0])
    nt.links.new(vor.outputs["Distance"], mix.inputs[2])
    # Höhen-Verlauf: oben heller (Sonne), unten dunkler
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Normal"], sep.inputs["Vector"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = 'MULTIPLY_ADD'
    add.inputs[1].default_value = 0.25
    nt.links.new(sep.outputs["Z"], add.inputs[0])
    nt.links.new(mix.outputs[0], add.inputs[2])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = _hex(c_dark)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[1].color = _hex(c_light)
    ramp.color_ramp.elements[1].position = 0.85
    nt.links.new(add.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.9
    b.inputs["Distance"].default_value = 0.08
    nt.links.new(vor.outputs["Distance"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = _hex(c_light)
    return m


def make_materials():
    M = {}
    # Fassaden (Kalkstein / Putz)
    M['stone_beige'] = _mat('stone_beige', '#D2B48A', 0.75, var=0.06, noise_scale=25)
    M['stone_cream'] = _mat('stone_cream', '#DCC5A0', 0.75, var=0.05, noise_scale=25)
    M['stone_sand'] = _mat('stone_sand', '#CFAE80', 0.75, var=0.07, noise_scale=25)
    M['stone_warm'] = _mat('stone_warm', '#D3A57A', 0.75, var=0.07, noise_scale=25)
    M['stone_light'] = _mat('stone_light', '#E9DCC4', 0.7, var=0.04, noise_scale=25)
    M['trim_white'] = _mat('trim_white', '#F4EFE5', 0.6, var=0.03)
    M['shop_dark'] = _mat('shop_dark', '#3A3530', 0.5, var=0.05)
    M['stone_tan'] = _mat('stone_tan', '#B98F62', 0.75, var=0.07, noise_scale=25)
    M['shutter_brown'] = _mat('shutter_brown', '#7A4B2E', 0.6, var=0.08)
    M['wood_dark'] = _mat('wood_dark', '#4A3426', 0.55, var=0.1, noise_scale=60)
    M['door_green'] = _mat('door_green', '#2F6B3A', 0.45, var=0.05)
    # Glas: dunkel, leicht spiegelnd
    M['glass'] = _mat('glass', '#2A3036', 0.12, var=0.0, bump=0, spec=0.7, coat=0.3)
    M['glass_warm'] = _mat('glass_warm', '#5A4A3A', 0.15, var=0.0, bump=0, spec=0.7)
    M['frame_white'] = _mat('frame_white', '#EDE8DE', 0.5, var=0.0, bump=0)
    M['iron_black'] = _mat('iron_black', '#1C1C1E', 0.45, metal=0.6, var=0.0, bump=0)
    # Dächer
    M['zinc_blue'] = _mat('zinc_blue', '#5F6E80', 0.45, metal=0.35, var=0.06, noise_scale=12)
    M['zinc_light'] = _mat('zinc_light', '#B7BABB', 0.6, metal=0.1, var=0.05, noise_scale=15)
    M['roof_flat'] = _mat('roof_flat', '#C9C7C2', 0.8, var=0.06, noise_scale=10)
    M['roof_red'] = _mat('roof_red', '#9C5B4C', 0.6, var=0.08, noise_scale=12)
    M['terracotta'] = _mat('terracotta', '#A65A3C', 0.7, var=0.08)
    M['brick'] = _mat('brick', '#B26A4A', 0.8, var=0.1)
    M['copper_green'] = _mat('copper_green', '#9DBE95', 0.55, metal=0.2, var=0.08)
    # Eiffelturm
    M['tower_bronze'] = _mat('tower_bronze', '#8A5638', 0.5, metal=0.45, var=0.1, noise_scale=30, bump=0.05)
    M['tower_dark'] = _mat('tower_dark', '#5E3626', 0.55, metal=0.4, var=0.08)
    M['gold'] = _mat('gold', '#D9A93A', 0.3, metal=1.0, var=0.0, bump=0)
    # Straße / Plattform
    M['asphalt'] = _mat('asphalt', '#34373D', 0.85, var=0.08, noise_scale=80, bump=0.2)
    M['sidewalk'] = _mat('sidewalk', '#B3AB9E', 0.8, var=0.05, noise_scale=30)
    M['curb'] = _mat('curb', '#CFCBC3', 0.75, var=0.04)
    M['plaza'] = _mat('plaza', '#9C9488', 0.85, var=0.07, noise_scale=20)
    M['slab'] = _mat('slab', '#C4C0B8', 0.8, var=0.03)
    M['marking'] = _mat('marking', '#F2F0EA', 0.6, var=0.0, bump=0)
    M['grass'] = _mat('grass', '#7A8A45', 0.9, var=0.15, noise_scale=40, bump=0.3)
    M['dirt'] = _mat('dirt', '#8C7A62', 0.95, var=0.1, noise_scale=30)
    M['floor'] = _mat('floor', '#FFEFD0', 0.95, var=0.0, bump=0)
    # Vegetation
    M['leaf_green'] = _foliage('leaf_green', '#A3B35C', '#3E5A26')
    M['leaf_dark'] = _foliage('leaf_dark', '#8A9E4C', '#2E4A20')
    M['leaf_orange'] = _foliage('leaf_orange', '#E8904A', '#A2401C')
    M['leaf_ochre'] = _foliage('leaf_ochre', '#C9963F', '#7A4E22')
    M['leaf_white'] = _foliage('leaf_white', '#F2EEE6', '#B9B4AA', scale=14)
    M['hedge'] = _foliage('hedge', '#A9C463', '#4F7A2E', scale=12)
    M['bark'] = _mat('bark', '#5A4334', 0.9, var=0.15, noise_scale=50, bump=0.4)
    # Fahrzeuge
    M['car_white'] = _mat('car_white', '#E8E8E6', 0.25, var=0.0, bump=0, coat=0.6)
    M['car_dark'] = _mat('car_dark', '#3E3F45', 0.25, metal=0.5, var=0.0, bump=0, coat=0.6)
    M['car_red'] = _mat('car_red', '#B8463A', 0.25, metal=0.3, var=0.0, bump=0, coat=0.6)
    M['car_teal'] = _mat('car_teal', '#8FB3C2', 0.3, var=0.0, bump=0, coat=0.5)
    M['car_gray'] = _mat('car_gray', '#7D7F84', 0.3, metal=0.5, var=0.0, bump=0, coat=0.5)
    M['tire'] = _mat('tire', '#1A1A1A', 0.8, var=0.0, bump=0)
    M['chrome'] = _mat('chrome', '#D0D0D0', 0.2, metal=1.0, var=0.0, bump=0)
    M['lamp_glow'] = _mat('lamp_glow', '#FFE6A8', 0.3, var=0.0, bump=0, emission=('#FFD27A', 2.0))
    M['headlight'] = _mat('headlight', '#FFF2C0', 0.2, var=0.0, bump=0, emission=('#FFE89A', 1.5))
    return M
