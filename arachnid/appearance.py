"""Finishes for the shared mechanical rig."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Finish:
    label: str
    armor: tuple[str, str]
    trim: str
    optic: str
    links: str = "#7893a2"


DEFAULT_FINISH = "blackout"
FINISHES = {
    "graphite": Finish("Graphite", ("#a2b6c1", "#465e70"), "#c9d9de", "#73ffe3"),
    "foundry": Finish("Foundry", ("#f4bc7b", "#995537"), "#ffe3b6", "#ffe18e"),
    "glacier": Finish("Glacier", ("#f4faff", "#7e9db8"), "#e2f6ff", "#8bdcfd"),
    "blackout": Finish("Blackout Red", ("#45414b", "#16151c"), "#dc4756", "#ff334e", "#4a3d48"),
    "neon": Finish("EdgeRunner", ("#ffdf4a", "#aa700f"), "#e8b824", "#52f9ff", "#303139"),
}
