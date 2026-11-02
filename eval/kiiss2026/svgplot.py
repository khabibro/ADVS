"""Minimal dependency-free SVG scatter/line chart (matplotlib is not installed in the project venv)."""

from __future__ import annotations

from html import escape

PALETTE = {
    "conf": "#1f77b4",
    "conf_gated": "#17becf",
    "conf_fmt": "#9467bd",
    "advs": "#d62728",
    "ablation": "#ff7f0e",
    "h14": "#2ca02c",
    "none": "#444444",
    "matched": "#000000",
}


def _ticks(lo: float, hi: float, n: int = 6) -> list[float]:
    if hi <= lo:
        hi = lo + 1
    step = (hi - lo) / n
    mag = 10 ** (len(str(int(step))) - 1) if step >= 1 else 10 ** (-(len(str(int(1 / step))) ))
    for m in (1, 2, 2.5, 5, 10):
        if step <= m * mag:
            step = m * mag
            break
    first = int(lo / step) * step
    out = []
    t = first
    while t <= hi + 1e-9:
        if t >= lo - 1e-9:
            out.append(round(t, 10))
        t += step
    return out


def chart(title: str, xlabel: str, ylabel: str, series: list[dict], points: list[dict], note: str = "",
          width: int = 880, height: int = 560) -> str:
    """series: [{name, color, xy:[(x,y),...], labels:[str,...] (optional)}] drawn as polylines with markers.
    points: [{name, color, x, y, marker}] drawn as labelled single points."""
    ml, mr, mt, mb = 70, 230, 50, 60
    pw, ph = width - ml - mr, height - mt - mb
    xs = [x for s in series for x, _ in s["xy"]] + [p["x"] for p in points]
    ys = [y for s in series for _, y in s["xy"]] + [p["y"] for p in points]
    x0, x1 = 0.0, max(xs + [1.0]) * 1.05
    y0, y1 = 0.0, max(ys + [1.0]) * 1.1
    sx = lambda v: ml + (v - x0) / (x1 - x0) * pw
    sy = lambda v: mt + ph - (v - y0) / (y1 - y0) * ph
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="Helvetica, Arial, sans-serif" font-size="12">',
         f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
         f'<text x="{ml}" y="24" font-size="15" font-weight="bold">{escape(title)}</text>']
    for t in _ticks(x0, x1):
        o.append(f'<line x1="{sx(t):.1f}" y1="{mt}" x2="{sx(t):.1f}" y2="{mt+ph}" stroke="#e6e6e6"/>')
        o.append(f'<text x="{sx(t):.1f}" y="{mt+ph+18}" text-anchor="middle" fill="#333">{t:g}</text>')
    for t in _ticks(y0, y1):
        o.append(f'<line x1="{ml}" y1="{sy(t):.1f}" x2="{ml+pw}" y2="{sy(t):.1f}" stroke="#e6e6e6"/>')
        o.append(f'<text x="{ml-8}" y="{sy(t)+4:.1f}" text-anchor="end" fill="#333">{t:g}</text>')
    o.append(f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="none" stroke="#999"/>')
    o.append(f'<text x="{ml+pw/2}" y="{height-18}" text-anchor="middle" fill="#111">{escape(xlabel)}</text>')
    o.append(f'<text transform="translate(18,{mt+ph/2}) rotate(-90)" text-anchor="middle" fill="#111">{escape(ylabel)}</text>')
    for s in series:
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in s["xy"])
        o.append(f'<polyline points="{pts}" fill="none" stroke="{s["color"]}" stroke-width="1.6" stroke-opacity="0.85"/>')
        for x, y in s["xy"]:
            o.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="2.6" fill="{s["color"]}"/>')
    ly = mt + 6
    for s in series:
        o.append(f'<line x1="{ml+pw+14}" y1="{ly}" x2="{ml+pw+34}" y2="{ly}" stroke="{s["color"]}" stroke-width="2"/>')
        o.append(f'<text x="{ml+pw+40}" y="{ly+4}" fill="#111">{escape(s["name"])}</text>')
        ly += 18
    for p in points:
        c, m = p["color"], p.get("marker", "o")
        x, y = sx(p["x"]), sy(p["y"])
        if m == "s":
            o.append(f'<rect x="{x-5:.1f}" y="{y-5:.1f}" width="10" height="10" fill="{c}" stroke="#fff"/>')
        elif m == "d":
            o.append(f'<polygon points="{x:.1f},{y-6:.1f} {x+6:.1f},{y:.1f} {x:.1f},{y+6:.1f} {x-6:.1f},{y:.1f}" fill="{c}" stroke="#fff"/>')
        elif m == "t":
            o.append(f'<polygon points="{x:.1f},{y-6:.1f} {x+6:.1f},{y+5:.1f} {x-6:.1f},{y+5:.1f}" fill="{c}" stroke="#fff"/>')
        else:
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{c}" stroke="#fff"/>')
        o.append(f'<line x1="{ml+pw+14}" y1="{ly}" x2="{ml+pw+24}" y2="{ly}" stroke="{c}" stroke-width="0"/>')
        o.append(f'<circle cx="{ml+pw+24}" cy="{ly}" r="4.5" fill="{c}"/>')
        o.append(f'<text x="{ml+pw+40}" y="{ly+4}" fill="#111">{escape(p["name"])}</text>')
        ly += 18
    if note:
        for i, line in enumerate(note.split("\n")):
            o.append(f'<text x="{ml}" y="{height-4-12*(note.count(chr(10))-i)}" fill="#555" font-size="10.5">{escape(line)}</text>')
    o.append("</svg>")
    return "\n".join(o)
