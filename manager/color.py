"""Colour arithmetic for the themes page: WCAG 2 contrast ratio."""


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance of a '#rrggbb' colour, 0 (black) to 1 (white)."""
    r, g, b = (int(hex_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2 contrast ratio between two colours, 1.0 to 21.0."""
    lighter, darker = sorted((relative_luminance(hex_a), relative_luminance(hex_b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)
