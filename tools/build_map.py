"""Convert the compact India TopoJSON into projected SVG paths."""
import json, math, os

SRC = "/tmp/india_topo.json"
OUT = os.path.join(os.path.dirname(__file__), "..", "static", "data", "india_map.json")

topo = json.load(open(SRC))
tr = topo["transform"]
sx, sy = tr["scale"]
tx, ty = tr["translate"]


def decode_arc(arc):
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx
        y += dy
        pts.append((x * sx + tx, y * sy + ty))
    return pts


arcs = [decode_arc(a) for a in topo["arcs"]]

# India bounding box / Mercator projection
lons = [p[0] for a in arcs for p in a]
lats = [p[1] for a in arcs for p in a]
minlon, maxlon = min(lons), max(lons)
minlat, maxlat = min(lats), max(lats)

W, H = 720, 820
PAD = 14


def merc(lon, lat):
    x = math.radians(lon)
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


x0, y0 = merc(minlon, maxlat)
x1, y1 = merc(maxlon, minlat)
scale = min((W - 2 * PAD) / (x1 - x0), (H - 2 * PAD) / (y1 - y0))
ox = PAD + ((W - 2 * PAD) - (x1 - x0) * scale) / 2
oy = PAD + ((H - 2 * PAD) - (y1 - y0) * scale) / 2


def project(pt):
    mx, my = merc(pt[0], pt[1])
    return ((mx - x0) * scale + ox, (my - y0) * scale + oy)


def ring_path(ring):
    pts = [project(p) for p in ring]
    if not pts:
        return ""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for p in pts[1:]:
        d += f"L{p[0]:.1f},{p[1]:.1f}"
    return d + "Z"


def geom_rings(geom):
    t = geom["type"]
    if t == "Polygon":
        return [geom["arcs"]]
    if t == "MultiPolygon":
        return geom["arcs"]
    return []


def assemble(rings):
    out = []
    for poly in rings:
        for ring in poly:
            coords = []
            for idx in ring:
                if idx < 0:
                    a = list(reversed(arcs[~idx]))
                else:
                    a = arcs[idx]
                if coords:
                    coords.extend(a[1:])
                else:
                    coords.extend(a)
            if coords:
                out.append(ring_path(coords))
    return out


states = []
for g in topo["objects"]["india"]["geometries"]:
    name = g.get("properties", {}).get("name")
    if not name:
        continue
    paths = assemble(geom_rings(g))
    if not paths:
        continue
    # rough centroid from first path bounding box
    nums = []
    for d in paths:
        for tok in d.replace("M", " ").replace("L", " ").replace("Z", " ").replace(",", " ").split():
            try:
                nums.append(float(tok))
            except ValueError:
                pass
    xs, ys = nums[0::2], nums[1::2]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    states.append({
        "name": name,
        "path": " ".join(paths),
        "cx": round(cx, 1),
        "cy": round(cy, 1),
        "w": round(max(xs) - min(xs), 1),
        "h": round(max(ys) - min(ys), 1),
    })

states.sort(key=lambda s: s["name"])
json.dump({"width": W, "height": H, "states": states}, open(OUT, "w"), separators=(",", ":"))
print("wrote", OUT, len(states), "states", os.path.getsize(OUT), "bytes")
for s in states:
    print(s["name"], s["cx"], s["cy"], s["w"], s["h"])
