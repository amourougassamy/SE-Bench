"""Deterministic engineering schematic; not a construction drawing generator."""

from html import escape

from .model import digest


def render(model):
    nodes = model["nodes"]
    xmin, xmax = min(p[0] for p in nodes.values()), max(p[0] for p in nodes.values())
    ymin, ymax = min(p[1] for p in nodes.values()), max(p[1] for p in nodes.values())
    scale = min(650 / max(xmax - xmin, 1), 280 / max(ymax - ymin, 1))

    def xy(node):
        x, y = nodes[node]
        return (90 + (x - xmin) * scale, 380 - (y - ymin) * scale)

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="720" viewBox="0 0 900 720">',
             '<rect width="900" height="720" fill="white"/>',
             '<g font-family="Arial,sans-serif" fill="#12263a">',
             f'<text x="40" y="38" font-size="24">SE-Bench | Revision {escape(model["revision"])}</text>',
             '<text x="40" y="65" font-size="14">2D frame schematic | SI | x right, y up | not for construction</text>']
    for key, element in model["elements"].items():
        a, b = element["nodes"]
        x1, y1 = xy(a)
        x2, y2 = xy(b)
        parts.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="#1670a5" stroke-width="6"/>')
        parts.append(f'<text x="{(x1+x2)/2+12:g}" y="{(y1+y2)/2-12:g}" font-size="13">E{escape(key)} {escape(element["section"])}</text>')
    for key, p in nodes.items():
        x, y = xy(key)
        parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="5" fill="#12263a"/>')
        parts.append(f'<text x="{x+10:g}" y="{y+24:g}" font-size="12">N{escape(key)} ({p[0]:g}, {p[1]:g}) m</text>')
        if key in model["supports"]:
            flags = ",".join(map(str, model["supports"][key]))
            parts.append(f'<text x="{x-20:g}" y="{y+45:g}" font-size="11">Restraints [{flags}]</text>')
    text = [f'Span extent {xmax-xmin:g} m; height extent {ymax-ymin:g} m; load case {model["load_case"]["name"]}',
            'Nodal loads [Fx N, Fy N, Mz N.m]: ' + str(model["load_case"]["nodal"]),
            'Element uniform local-y loads [N/m]: ' + str(model["load_case"]["uniform"])]
    for key, sec in model["sections"].items():
        text.append(f'{key}: A={sec["A_m2"]:g} m²; E={sec["E_Pa"]:g} Pa; I={sec["I_m4"]:g} m⁴')
    text.extend(['First-order elastic analysis; no strength, stability, or connection checks.',
                 'Model SHA256: ' + digest(model)])
    for index, line in enumerate(text):
        parts.append(f'<text x="40" y="{475+index*27}" font-size="12">{escape(line)}</text>')
    parts.append('</g></svg>')
    return "\n".join(parts) + "\n"
