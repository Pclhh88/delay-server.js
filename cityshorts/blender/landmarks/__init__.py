"""Wahrzeichen-Registry. Ein Builder erzeugt ein Wahrzeichen im lokalen
Ursprung (Vorderseite zeigt nach -y) und gibt ein Info-Dict zurück:

    {"objects": [...], "height": h, "radius": r, "extras": {...}}

Neue Stadt = neues Modul (z. B. paris.py) mit @register("paris.eiffel").
Unbekannte Builder fallen auf einen beschrifteten Platzhalter zurück, damit
jede city.json sofort renderbar ist.
"""
from ..kit.mesh import MeshBuilder

REGISTRY = {}


def register(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


def build(name, col, params):
    from . import rome  # noqa: F401  (registriert sich selbst)
    fn = REGISTRY.get(name, placeholder)
    return fn(col, params)


def placeholder(col, params):
    w, d = params.get("footprint", (3, 3))
    h = params.get("height", 5)
    mb = MeshBuilder()
    mb.box_on(0, 0, 0, w * 1.6, d * 1.6, 0.3, "plaza")
    mb.box_on(0, 0, 0.3, w, d, h, "white")
    mb.hip(0, 0, 0.3 + h, w, d, h * 0.25, "red")
    ob = mb.build("placeholder_" + params.get("id", "x"), col, bevel=0.05)
    return {"objects": [ob], "height": h * 1.25, "radius": max(w, d) * 1.4, "extras": {}}
