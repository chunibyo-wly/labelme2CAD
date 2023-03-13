import FreeCAD, Draft, Arch, Mesh
import json, math
import numpy as np

WALL_HEIGHT = 200
WALL_WIDTH = 20

w, h = 0, 0

doc = FreeCAD.newDocument()


def endpoints(rect):
    if len(rect) == 2:
        point_1 = (rect[0][0], rect[0][1])
        point_2 = (rect[0][0], rect[1][1])
        point_3 = (rect[1][0], rect[1][1])
        point_4 = (rect[1][0], rect[0][1])
    else:
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

    return [(s1[0][0] + s1[1][0]) / 2, (s1[0][1] + s1[1][1]) / 2], [
        (s2[0][0] + s2[1][0]) / 2,
        (s2[0][1] + s2[1][1]) / 2,
    ]


def add_wall(p1, p2, index):
    pa = FreeCAD.Vector(p1[0], p1[1], 0)
    pb = FreeCAD.Vector(p2[0], p2[1], 0)
    points = [pa, pb]
    line = Draft.makeWire(points, closed=False, face=False, support=None)
    line.Label = f"myline{index}"
    wall = Arch.makeWall(line, length=None, width=WALL_WIDTH, height=WALL_HEIGHT)
    wall.Label = f"mywall{index}"
    return wall


def is_close(a, b, eps=1e-2):
    return abs(a - b) < eps


def angle_with_x_axis(p1, p2):
    p1, p2 = np.array(p1), np.array(p2)
    n1 = np.array([1, 0])
    n2 = p2 - p1
    angle = np.arccos(np.dot(n2, n1) / (np.linalg.norm(n2))) * 180 / np.pi
    return angle


def clockwise(p1, p2, p3):
    p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3)
    return np.cross(p2 - p1, p3 - p1) < 0


def assign_object_to_wall(object):
    target, min_dist = None, float("inf")
    for obj in doc.Objects:
        if obj.Label.startswith("mywall"):
            dist = obj.Shape.distToShape(object.Shape)[0]
            if dist < min_dist:
                min_dist = dist
                target = obj
    object.Hosts = target


def add_window(p1, p2, index, wall=None):
    width = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) * 0.8
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
    FreeCAD.ActiveDocument.recompute()

    angle = angle_with_x_axis(p1, p2)

    Draft.rotate(window, angle)
    Draft.move(
        window,
        FreeCAD.Vector(
            (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (WALL_HEIGHT - height) / 2
        ),
    )

    window.HoleWire = 1
    # window.SymbolPlan = True
    window.Label = f"mywindow{index}"
    if wall is not None:
        window.Hosts = wall

    return window


def add_door(p1, p2, p3, index, wall=None):
    """
    p1: 圆心
    p2: 靠墙点
    p3: 远墙点
    """
    width = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) * 0.8
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

    door.HoleWire = 1
    door.SymbolPlan = True
    door.Opening = 50
    if wall is not None:
        door.Hosts = wall

    if clockwise(p1, p2, p3):
        door = Draft.mirror(
            door,
            FreeCAD.Vector(p1[0], p1[1], 0),
            FreeCAD.Vector(p2[0], p2[1], 0),
        )

    door.Label = f"mydoor{index}"

    return door


def add_image(w, h):
    rectangle1 = Draft.make_rectangle(w, h, face=True)
    rectangle1.Label = "image"
    doc.recompute()


def transform(p):
    p[1] = h - p[1]


def fine_obj(w, h):
    with open("image.obj", "r") as f:
        lines = f.readlines()

    output = []

    # p = []
    for line in lines:
        if line.startswith("v "):
            v = [float(i) for i in line.strip().split(" ")[1:]]
            output.append(f"vt {v[0]//w} {v[1]//h} 0.0")

        if line.startswith("f "):
            tmp = []
            for i in line.strip().split(" ")[1:]:
                tmp2 = i.split("/")
                tmp2[1] = tmp2[0]
                tmp.append("/".join(tmp2))
            output.append("f " + " ".join(tmp))
        else:
            output.append(line)

    with open("image.obj", "w") as f:
        f.write("mtllib out.mtl\n")
        f.write("usemtl image\n")
        for i in output:
            f.write(i + "\n")


def main():
    global w, h
    file = r"A_879715.json"

    with open(file, "r") as f:
        data = json.load(f)
    shapes = data["shapes"]
    w, h = data["imageWidth"], data["imageHeight"]

    print("=== add wall ===")
    cnt = 0

    for shape in shapes:
        if shape["label"] != "wall":
            continue
        rect = shape["points"]
        p1, p2 = endpoints(rect)
        transform(p1)
        transform(p2)
        add_wall(p1, p2, cnt)
        cnt += 1
    doc.recompute()

    print("=== add window ===")
    for shape in shapes:
        if shape["label"] != "windows":
            continue
        rect = shape["points"]
        p1, p2 = endpoints(rect)
        transform(p1)
        transform(p2)
        wall = add_wall(p1, p2, cnt)
        add_window(p1, p2, cnt, wall)
        cnt += 1
    doc.recompute()

    print("=== add door ===")
    for shape in shapes:
        if shape["label"] != "curve_door":
            continue
        doorPts = shape["points"]
        p1, p2, p3, p4 = doorPts
        transform(p1)
        transform(p3)
        transform(p4)
        wall = add_wall(p3, p4, cnt)
        add_door(p4, p3, p1, cnt, wall)
        cnt += 1
    doc.recompute()

    add_image(w, h)

    print("=== save ===")
    doc.saveAs(r"out.FCStd")
    objs = []
    for obj in doc.Objects:
        if obj.Label.startswith("mywall") or obj.Label.startswith("mydoor"):
            objs.append(obj)

    Mesh.export(objs, r"roomplan.obj")

    objs = []
    for obj in doc.Objects:
        if obj.Label.startswith("image"):
            objs.append(obj)

    Mesh.export(objs, r"image.obj")

    fine_obj(w, h)


main()
