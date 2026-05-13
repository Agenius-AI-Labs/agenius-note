"""Theme tokens — canonical AgeniusDesk Dark + Light.

Source: M:\\Code\\ageniusdesk\\frontend\\themes\\default-dark.json + base.css.
Token names use Python-friendly underscores; QSS template substitutes via
str.format_map.
"""

from __future__ import annotations

DARK: dict[str, str] = {
    # Backgrounds
    "bg_void":         "#0a0a0f",
    "bg_panel":        "rgba(18, 18, 28, 0.9)",
    "bg_panel_solid":  "#12121c",
    "bg_input":        "rgba(25, 25, 40, 0.8)",
    "bg_input_solid":  "#191928",
    "bg_hover":        "rgba(255, 255, 255, 0.04)",
    "bg_hover_solid":  "#1a1a26",
    "bg_sidebar":      "#0e0e16",
    "bg_card":         "#12121c",
    "bg_card_done":    "#0d0d14",

    # Borders
    "border_dim":      "rgba(255, 255, 255, 0.06)",
    "border_mid":      "rgba(255, 255, 255, 0.12)",
    "border_bright":   "rgba(255, 255, 255, 0.2)",

    # Text
    "text_primary":    "#e2e2ec",
    "text_secondary":  "#a0a0b8",
    "text_dim":        "#6b6b85",

    # Accent
    "accent":          "#ff6d5a",
    "accent_glow":     "rgba(255, 109, 90, 0.2)",
    "accent_hover":    "#ff8a7a",
    "accent_pressed":  "#e85a48",

    # Semantic
    "success":         "#34d399",
    "success_glow":    "rgba(52, 211, 153, 0.18)",
    "warning":         "#fbbf24",
    "warning_glow":    "rgba(251, 191, 36, 0.18)",
    "error":           "#f87171",
    "error_glow":      "rgba(248, 113, 113, 0.18)",
    "info":            "#60a5fa",
    "info_glow":       "rgba(96, 165, 250, 0.18)",

    # Sizing
    "radius":          "8",
    "radius_lg":       "12",
    "radius_pill":     "20",
    "sidebar_width":   "220",
}

LIGHT: dict[str, str] = {
    # Backgrounds
    "bg_void":         "#eef0f5",
    "bg_panel":        "rgba(255, 255, 255, 0.97)",
    "bg_panel_solid":  "#ffffff",
    "bg_input":        "#f1f3f8",
    "bg_input_solid":  "#f1f3f8",
    "bg_hover":        "rgba(0, 0, 0, 0.04)",
    "bg_hover_solid":  "#e5e7ee",
    "bg_sidebar":      "#e8eaf2",
    "bg_card":         "#ffffff",
    "bg_card_done":    "#f7f8fc",

    # Borders
    "border_dim":      "rgba(0, 0, 0, 0.07)",
    "border_mid":      "rgba(0, 0, 0, 0.13)",
    "border_bright":   "rgba(0, 0, 0, 0.24)",

    # Text
    "text_primary":    "#0f1117",
    "text_secondary":  "#374151",
    "text_dim":        "#6b7280",

    # Accent (Linear/Vercel-inspired indigo)
    "accent":          "#5b5ef4",
    "accent_glow":     "rgba(91, 94, 244, 0.18)",
    "accent_hover":    "#4338ca",
    "accent_pressed":  "#3730a3",

    # Semantic
    "success":         "#047857",
    "success_glow":    "rgba(4, 120, 87, 0.15)",
    "warning":         "#b45309",
    "warning_glow":    "rgba(180, 83, 9, 0.15)",
    "error":           "#c81e1e",
    "error_glow":      "rgba(200, 30, 30, 0.15)",
    "info":            "#1d4ed8",
    "info_glow":       "rgba(29, 78, 216, 0.15)",

    # Sizing
    "radius":          "8",
    "radius_lg":       "12",
    "radius_pill":     "20",
    "sidebar_width":   "220",
}


CYBERPUNK: dict[str, str] = {
    # Backgrounds — deeper than Dark, near-black with hint of indigo
    "bg_void":         "#05060a",
    "bg_panel":        "rgba(10, 14, 24, 0.85)",
    "bg_panel_solid":  "#0a0e18",
    "bg_input":        "rgba(15, 22, 40, 0.7)",
    "bg_input_solid":  "#0f1628",
    "bg_hover":        "rgba(56, 189, 248, 0.05)",
    "bg_hover_solid":  "#0d1626",
    "bg_sidebar":      "#070b14",
    "bg_card":         "#0a0e18",
    "bg_card_done":    "#070b14",

    # Borders — cyan-tinted instead of plain white
    "border_dim":      "rgba(56, 189, 248, 0.08)",
    "border_mid":      "rgba(56, 189, 248, 0.15)",
    "border_bright":   "rgba(56, 189, 248, 0.35)",

    # Text — cool blue-white
    "text_primary":    "#d4e3f5",
    "text_secondary":  "#7ea8cc",
    "text_dim":        "#4a6a88",

    # Accent — sky cyan
    "accent":          "#38bdf8",
    "accent_glow":     "rgba(56, 189, 248, 0.25)",
    "accent_hover":    "#7dd3fc",
    "accent_pressed":  "#0ea5e9",

    # Semantic — purple info, brighter glows
    "success":         "#34d399",
    "success_glow":    "rgba(52, 211, 153, 0.20)",
    "warning":         "#f59e0b",
    "warning_glow":    "rgba(245, 158, 11, 0.20)",
    "error":           "#f87171",
    "error_glow":      "rgba(248, 113, 113, 0.18)",
    "info":            "#a78bfa",
    "info_glow":       "rgba(167, 139, 250, 0.18)",

    # Sizing
    "radius":          "8",
    "radius_lg":       "12",
    "radius_pill":     "20",
    "sidebar_width":   "220",
}


def get_theme(name: str) -> dict[str, str]:
    """Return the token dict for `name` ('dark' | 'light' | 'cyberpunk').

    Defaults to cyberpunk so first-launch users see the Agenius signature look.
    """
    key = (name or "").strip().lower()
    if key == "light":
        return LIGHT
    if key == "dark":
        return DARK
    return CYBERPUNK
