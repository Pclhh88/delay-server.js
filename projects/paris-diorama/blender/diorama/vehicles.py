"""Kleine Miniatur-Fahrzeuge (Karosserie, Kabine mit Scheiben, Räder, Lichter)."""
from .meshkit import MeshBuilder

# Länge, Breite, Höhe Karosserie, Kabinenhöhe, Kabinen-Start/Ende (Anteil), Bodenfreiheit
CAR_TYPES = {
    'van':     (1.45, 0.62, 0.42, 0.32, (0.0, 0.78), 0.10),
    'boxvan':  (1.35, 0.62, 0.40, 0.36, (0.0, 0.70), 0.10),
    'sedan':   (1.15, 0.55, 0.25, 0.20, (0.25, 0.75), 0.08),
    'compact': (0.95, 0.52, 0.27, 0.22, (0.2, 0.75), 0.08),
}


def build_car(name, kind, color, location, heading, materials, collection):
    L, W, H, CH, (c0, c1), g = CAR_TYPES[kind]
    mb = MeshBuilder()
    x0 = -L / 2
    # Karosserie (Unterteil)
    mb.box((0, 0, g + H / 2), (L, W, H), color)
    # Kabine (Glas) + Dach
    cl = (c1 - c0) * L
    cx = x0 + (c0 + c1) / 2 * L
    mb.box((cx, 0, g + H + CH / 2), (cl * 0.98, W * 0.92, CH), 'glass')
    mb.box((cx, 0, g + H + CH - 0.02), (cl, W * 0.95, 0.05), color)
    # Holme
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((cx + sx * (cl / 2 - 0.03), sy * W * 0.45, g + H + CH / 2), (0.05, 0.04, CH), color)
    # Räder
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder_x((sx * L * 0.33, sy * (W / 2 - 0.02), g + 0.02), 0.12, 0.1, 'tire', seg=14, axis='Y')
            mb.cylinder_x((sx * L * 0.33, sy * (W / 2 + 0.01), g + 0.02), 0.06, 0.04, 'chrome', seg=10, axis='Y')
    # Lichter, Stoßfänger
    for sy in (-1, 1):
        mb.box((L / 2 + 0.005, sy * W * 0.33, g + H * 0.65), (0.02, 0.1, 0.05), 'headlight')
        mb.box((-L / 2 - 0.005, sy * W * 0.33, g + H * 0.65), (0.02, 0.1, 0.05), 'car_red')
    mb.box((L / 2 + 0.01, 0, g + 0.06), (0.04, W * 1.0, 0.07), 'car_gray')
    mb.box((-L / 2 - 0.01, 0, g + 0.06), (0.04, W * 1.0, 0.07), 'car_gray')
    if kind in ('van', 'boxvan'):
        mb.box((L / 2 - 0.12, 0, g + H + 0.1), (0.24, W * 0.9, 0.22), 'glass')  # Frontscheibe
    ob = mb.build(name, materials, collection, location=location, rotation=heading)
    bev = ob.modifiers.new('Bevel', 'BEVEL')
    bev.width = 0.025
    bev.segments = 2
    bev.limit_method = 'ANGLE'
    return ob
