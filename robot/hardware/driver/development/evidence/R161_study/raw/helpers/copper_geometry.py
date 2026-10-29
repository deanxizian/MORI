"""Native KiCad copper geometry for bounded offline checks, not qualification.

Run with KiCad's Python plus Shapely 2.0.7. Never writes the source board.
All coordinates are mm. Native shapes are polygonized to <= 0.002 mm error.
"""
from collections import defaultdict
from functools import cached_property
import hashlib
import re
from pathlib import Path
import pcbnew as pcb
from shapely.geometry import Polygon, Point, LineString, GeometryCollection
from shapely.ops import unary_union

LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu']
REFERENCE = {'F.Cu': 'In1.Cu', 'In2.Cu': 'In1.Cu', 'In3.Cu': 'In4.Cu', 'B.Cu': 'In4.Cu'}
ERROR_MM = 0.002


def xy(v):
    return (v.x / 1e6, v.y / 1e6)


def uid(item):
    return item.m_Uuid.AsString()


def via_snapshot(board, via):
    """Exact electrical/physical snapshot for an explicitly repurposed via."""
    if not isinstance(via, pcb.PCB_VIA):
        raise ValueError('Expected a native via')
    return {'net': via.GetNetname(), 'position_mm': list(xy(via.GetPosition())),
            'drill_mm': via.GetDrillValue()/1e6, 'via_type': int(via.GetViaType()),
            'layers': [name for name in LAYERS if via.IsOnLayer(board.GetLayerID(name))],
            'diameters_mm': {name: via.GetWidth(board.GetLayerID(name))/1e6 for name in LAYERS}}


def via_contact_layers(board, via, ignored_tracks=()):
    """Native copper touching a via after explicitly replaced tracks are omitted.

    This only screens an obsolete transfer. It is not permission to remove a
    ground stitch, change a rule, or skip native refill/connectivity regression.
    Filled zones are included, so a connection to a power plane is not hidden.
    """
    omitted = set(ignored_tracks) | {uid(via)}
    items = list(board.GetTracks()) + [p for f in board.GetFootprints() for p in f.Pads()]
    contacts = []
    for name in LAYERS:
        lid = board.GetLayerID(name)
        if not via.IsOnLayer(lid):
            continue
        land = shape(via, lid)
        touching = any(
            uid(o) not in omitted and o.GetNetname() == via.GetNetname()
            and o.IsOnLayer(lid)
            and (not isinstance(o, (pcb.PAD, pcb.PCB_VIA)) or o.FlashLayer(lid))
            and land.intersects(shape(o, lid)) for o in items)
        touching |= any(
            not z.GetIsRuleArea() and z.GetNetname() == via.GetNetname()
            and z.IsOnLayer(lid) and land.intersects(polyset(z.GetFilledPolysList(lid)))
            for z in board.Zones())
        if touching:
            contacts.append(name)
    return contacts


def chain(c):
    return [xy(c.CPoint(i)) for i in range(c.PointCount())]


def polyset(s):
    polygons = []
    for i in range(s.OutlineCount()):
        outer = chain(s.Outline(i))
        if len(outer) < 3:
            continue
        holes = [chain(s.Hole(i, j)) for j in range(s.HoleCount(i))]
        p = Polygon(outer, holes)
        if not p.is_valid:
            p = p.buffer(0)
        polygons.append(p)
    return unary_union(polygons)


def shape(item, layer):
    s = pcb.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(s, layer, 0, pcb.FromMM(ERROR_MM), pcb.ERROR_OUTSIDE)
    return polyset(s)


def inner_zone_clearance(board_path):
    """Recognize the received conditional R17 rule, not an assumed global value."""
    rules = Path(board_path).with_suffix('.kicad_dru').read_text()
    match = re.search(
        r'\(rule "R17 internal copper zone spacing"\s*'
        r'\(condition "A.Type == \'Zone\' && \(A.Layer == \'In1.Cu\' \|\| A.Layer == \'In2.Cu\' \|\| A.Layer == \'In3.Cu\' \|\| A.Layer == \'In4.Cu\'\)"\)\s*'
        r'\(constraint clearance \(min ([0-9.]+)mm\)\)', rules)
    if not match:
        raise ValueError('Unrecognized inner-zone clearance rule; reference-void model needs review')
    return float(match.group(1))


def in2_routing_nets(board_path):
    """Read only the exact received R13 allow-list; never broaden its policy."""
    rules = Path(board_path).with_suffix('.kicad_dru').read_text()
    match = re.search(
        r'\(rule "R13 mapped planes and exact In2 signal corridors"\s*'
        r'\(condition "A.Type == \'Track\' && \(A.Layer == \'In1.Cu\' \|\| A.Layer == \'In4.Cu\' \|\| '
        r'\(A.Layer == \'In2.Cu\' && !\(([^\n"]+)\)\)\)"\)\s*'
        r'\(constraint disallow track\)\s*\)', rules)
    if not match:
        raise ValueError('Unrecognized R13 layer rule; routing policy requires review')
    terms = match.group(1).split(' || ')
    names = []
    for term in terms:
        item = re.fullmatch(r"A\.NetName == '([^']+)'", term)
        if not item:
            raise ValueError('Unrecognized R13 whitelist expression')
        names.append(item.group(1))
    return frozenset(names)


def reference_transfer_shape(c, item, reference):
    """Native reference-layer copper or an unflashed circular plated barrel.

    This is ONLY the mandatory local transfer geometry. The caller must check
    net membership and actual connection to the reviewed surface island. SMD,
    NPTH and unsupported slotted pads receive no exemption. It does not assert
    that a return path is adequate, or exempt unrelated holes/plane splits.
    """
    if isinstance(item, pcb.PCB_VIA):
        return c.shapes.get((uid(item), reference))
    if not isinstance(item, pcb.PAD) or item.GetAttribute() != pcb.PAD_ATTRIB_PTH:
        return None
    dx, dy = xy(item.GetDrillSize())
    if (item.GetDrillShape() != pcb.PAD_DRILL_SHAPE_CIRCLE or dx <= 0
            or abs(dx-dy) > 1e-8 or not item.IsOnLayer(c.ids[reference])):
        return None
    # Unused inner annuli are deliberately removed in the received padstacks.
    # The plated hole remains: do not substitute the larger external pad land.
    barrel = Point(xy(item.GetPosition())).buffer(dx/2, resolution=64)
    return barrel.union(c.shapes.get((uid(item), reference), GeometryCollection()))


def parts(g):
    if g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    return [p for p in getattr(g, 'geoms', []) if p.geom_type == 'Polygon']


class Copper:
    def __init__(self, path):
        self.path = str(path)
        self.sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
        self.board = pcb.LoadBoard(self.path)
        self.ids = {n: self.board.GetLayerID(n) for n in LAYERS}
        self.footprints = list(self.board.GetFootprints())
        self.tracks = list(self.board.GetTracks())
        self.pads = [p for f in self.footprints for p in f.Pads()]
        self.pad_names = {uid(p): f.GetReference() + '.' + p.GetNumber() for f in self.footprints for p in f.Pads()}
        self.pad_faces = {uid(p): self.board.GetLayerName(f.GetLayer()) for f in self.footprints for p in f.Pads()}
        self.vias = [t for t in self.tracks if isinstance(t, pcb.PCB_VIA)]
        self.segments = [t for t in self.tracks if not isinstance(t, pcb.PCB_VIA)]
        self.zones = list(self.board.Zones())
        self.items = self.pads + self.tracks
        self.by_id = {uid(o): o for o in self.items}

    @cached_property
    def shapes(self):
        result = {}
        for o in self.items:
            for name, lid in self.ids.items():
                if not o.IsOnLayer(lid):
                    continue
                if isinstance(o, (pcb.PAD, pcb.PCB_VIA)) and not o.FlashLayer(lid):
                    continue
                s = shape(o, lid)
                if not s.is_empty:
                    result[(uid(o), name)] = s
        return result

    @cached_property
    def fills(self):
        result = []
        for z in self.zones:
            if z.GetIsRuleArea():
                continue
            for name, lid in self.ids.items():
                if z.IsOnLayer(lid):
                    result.append((z.GetNetname(), name, polyset(z.GetFilledPolysList(lid))))
        return result

    @cached_property
    def copper(self):
        items = defaultdict(list)
        for (id_, layer), s in self.shapes.items():
            items[(self.by_id[id_].GetNetname(), layer)].append(s)
        for net, layer, s in self.fills:
            items[(net, layer)].append(s)
        return {k: unary_union(v) for k, v in items.items()}

    @cached_property
    def keepouts(self):
        result = []
        for z in self.zones:
            if z.GetIsRuleArea():
                result.append({'id': uid(z), 'name': z.GetZoneName(),
                               'layers': [n for n, i in self.ids.items() if z.IsOnLayer(i)],
                               'tracks': z.GetDoNotAllowTracks(), 'vias': z.GetDoNotAllowVias(),
                               'shape': polyset(z.Outline())})
        return result

    def anchors(self, net):
        return [o for o in self.pads + self.vias if o.GetNetname() == net]

    def pad_name(self, item):
        return self.pad_names.get(uid(item), uid(item))

    def connected_pairs(self, net, width=0):
        """Erode each layer, connect via/pad terminals, return anchor pairs.

        Terminal contact uses native un-eroded land geometry; this measures corridor
        continuity, not plated-barrel ampacity or a guarantee of any current rating.
        """
        anchors = self.anchors(net)
        parents = {}
        def root(x):
            parents.setdefault(x, x)
            while parents[x] != x:
                parents[x] = parents[parents[x]]
                x = parents[x]
            return x
        def join(a, b):
            parents[root(a)] = root(b)
        for layer in LAYERS:
            g = self.copper.get((net, layer), GeometryCollection())
            if width:
                g = g.buffer(-width / 2, join_style=1)
            for i, region in enumerate(parts(g)):
                node = ('region', layer, i)
                root(node)
                for a in anchors:
                    land = self.shapes.get((uid(a), layer))
                    if land is not None and region.intersects(land):
                        join(uid(a), node)
        ids = [uid(a) for a in anchors]
        return {tuple(sorted((a, b))) for i, a in enumerate(ids) for b in ids[i+1:] if root(a) == root(b)}

    def pad_groups(self):
        result = {}
        for net in sorted({p.GetNetname() for p in self.pads if p.GetNetname()}):
            pairs = self.connected_pairs(net)
            ids = {uid(p): self.pad_name(p) for p in self.pads if p.GetNetname() == net}
            pending = set(ids)
            groups = []
            while pending:
                first = min(pending)
                group = {first} | {b if a == first else a for a, b in pairs if a == first or b == first}
                group &= set(ids)
                groups.append(sorted(ids[k] for k in group))
                pending -= group
            result[net] = groups
        return result
