"""Small deterministic geometry primitives."""
import math


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def segment_rect(a, b, rect):
    x1, y1, x2, y2 = rect
    lo, hi = 0.0, 1.0
    for p, q in ((a[0] - b[0], a[0] - x1), (b[0] - a[0], x2 - a[0]),
                 (a[1] - b[1], a[1] - y1), (b[1] - a[1], y2 - a[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                lo = max(lo, t)
            else:
                hi = min(hi, t)
            if lo > hi:
                return False
    return True


def segment_circle(a, b, center, radius):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = max(0, min(1, ((center[0]-a[0])*dx + (center[1]-a[1])*dy) / length2)) if length2 else 0
    return distance((a[0]+t*dx, a[1]+t*dy), center) <= radius


def visible(a, b, geometry, smokes):
    return not any(segment_rect(a, b, r) for r in geometry['cover']) and not any(
        segment_circle(a, b, s['pos'], s['radius']) for s in smokes)


def move(pos, target, amount, geometry):
    d = distance(pos, target)
    if not d:
        return list(pos)
    scale = min(1, amount / d)
    dest = [max(0, min(geometry['width'], pos[0] + (target[0]-pos[0])*scale)),
            max(0, min(geometry['height'], pos[1] + (target[1]-pos[1])*scale))]
    if any(segment_rect(pos, dest, r) for r in geometry['cover']):
        return list(pos)
    return dest
