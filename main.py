import FreeCAD, Draft, Arch, importOBJ
import json, math

WALL_HEIGHT = 200
WALL_WIDTH = 10

doc = FreeCAD.newDocument()


def endpoints(rect):
    # 四个角点的坐标
    point_1, point_2, point_3, point_4 = rect

    # 计算每条边的长度
    side_1 = math.sqrt((point_2[0] - point_1[0]) ** 2 + (point_2[1] - point_1[1]) ** 2)
    side_2 = math.sqrt((point_3[0] - point_2[0]) ** 2 + (point_3[1] - point_2[1]) ** 2)
    side_3 = math.sqrt((point_4[0] - point_3[0]) ** 2 + (point_4[1] - point_3[1]) ** 2)
    side_4 = math.sqrt((point_1[0] - point_4[0]) ** 2 + (point_1[1] - point_4[1]) ** 2)

    # 找出最短的两条边
    sides = [
        (point_1, point_2, side_1),
        (point_2, point_3, side_2),
        (point_3, point_4, side_3),
        (point_4, point_1, side_4),
    ]
    sides.sort(key=lambda x: x[2])
    s1 = sides[0]
    s2 = sides[1]

    return ((s1[0][0] + s1[1][0]) / 2, (s1[0][1] + s1[1][1]) / 2), (
        (s2[0][0] + s2[1][0]) / 2,
        (s2[0][1] + s2[1][1]) / 2,
    )


def make_line(p1, p2, index):
    pa = FreeCAD.Vector(p1[0], p1[1], 0)
    pb = FreeCAD.Vector(p2[0], p2[1], 0)
    points = [pa, pb]
    line = Draft.makeWire(points, closed=False, face=False, support=None)
    line.Label = f"myline{index}"
    return line


def is_close(a, b, eps=1e-2):
    return abs(a - b) < eps


def angle_with_x_axis(p1, p2):
    if is_close(p2[0], p1[0]):
        return 90
    slope = (p2[1] - p1[1]) / (p2[0] - p1[0])
    angle_rad = math.atan(slope)
    angle_deg = math.degrees(angle_rad)
    return angle_deg


def assign_object_to_wall(object):
    target, min_dist = None, float("inf")
    for obj in doc.Objects:
        if obj.Label.startswith("mywall"):
            dist = obj.Shape.distToShape(object.Shape)[0]
            if dist < min_dist:
                min_dist = dist
                target = obj
    object.Hosts = target


def add_window(p1, p2, index):
    width = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
    height = WALL_HEIGHT * 0.5

    placement = FreeCAD.Placement(
        FreeCAD.Vector(-width / 2, 0, 0),
        FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90),
    )
    window = Arch.makeWindowPreset(
        "Open 1-pane",
        width=width,
        height=height,
        h1=1,
        h2=1,
        h3=1,
        w1=1,
        w2=1,
        o1=1,
        o2=1,
        placement=placement,
    )

    angle = angle_with_x_axis(p1, p2)

    Draft.rotate(window, angle)
    Draft.move(
        window,
        FreeCAD.Vector(
            (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (WALL_HEIGHT - height) / 2
        ),
    )
    assign_object_to_wall(window)
    window.HoleWire = 1
    window.SymbolPlan = True
    window.Label = f"mywindow{index}"
    return window


def add_door(p1, p2, index):
    width = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
    height = WALL_HEIGHT * 0.7

    placement = FreeCAD.Placement(
        FreeCAD.Vector(-width / 2, 0, 0),
        FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90),
    )
    door = Arch.makeWindowPreset(
        "Simple door",
        width=width,
        height=height,
        h1=1,
        h2=1,
        h3=1,
        w1=1,
        w2=1,
        o1=1,
        o2=1,
        placement=placement,
    )

    angle = angle_with_x_axis(p1, p2)

    Draft.rotate(door, angle)
    Draft.move(
        door,
        FreeCAD.Vector((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, 0),
    )
    assign_object_to_wall(door)
    door.HoleWire = 1
    door.SymbolPlan = True
    door.Label = f"mydoor{index}"
    door.Opening = 90
    return door


def main():
    file = r"/mnt/e/workspace/dataset/98_others/wu_json/F_836915.json"

    with open(file, "r") as f:
        data = json.load(f)
    shapes = data["shapes"]

    print("=== add wall ===")
    cnt = 0
    lines = []
    for shape in shapes:
        if shape["label"] != "wall":
            continue
        rect = shape["points"]
        p1, p2 = endpoints(rect)
        line = make_line(p1, p2, cnt)
        lines.append(line)
        cnt += 1
    Draft.join_wires(lines)
    doc.recompute()

    cnt = 0
    for obj in doc.Objects:
        if obj.Label.startswith("myline"):
            obj = Arch.makeWall(obj, length=None, width=WALL_WIDTH, height=WALL_HEIGHT)
            obj.Label = f"mywall{cnt}"
            cnt += 1
    doc.recompute()

    print("=== add window ===")
    cnt = 0
    for shape in shapes:
        if shape["label"] != "windows":
            continue
        rect = shape["points"]
        p1, p2 = endpoints(rect)
        line = add_window(p1, p2, cnt)
        cnt += 1
    doc.recompute()

    print("=== add door ===")
    cnt = 0
    for shape in shapes:
        if shape["label"] != "door":
            continue
        rect = shape["points"]
        p1, p2 = endpoints(rect)
        line = add_door(p1, p2, cnt)
        cnt += 1
    doc.recompute()

    print("=== save ===")
    doc.saveAs(r"out.FCStd")
    objs = []
    for obj in doc.Objects:
        if obj.Label.startswith("mywall"):
            objs.append(obj)
    importOBJ.export(objs, r"out.obj")


main()
