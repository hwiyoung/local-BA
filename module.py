import numpy as np
import laspy


def Rot3D(eo):
    om = eo[3]
    ph = eo[4]
    kp = eo[5]

    #      | 1       0        0    |
    # Rx = | 0    cos(om)  sin(om) |
    #      | 0   -sin(om)  cos(om) |

    Rx = np.zeros(shape=(3, 3))
    cos, sin = np.cos(om), np.sin(om)

    Rx[0, 0] = 1
    Rx[1, 1] = cos
    Rx[1, 2] = sin
    Rx[2, 1] = -sin
    Rx[2, 2] = cos

    #      | cos(ph)   0  -sin(ph) |
    # Ry = |    0      1      0    |
    #      | sin(ph)   0   cos(ph) |

    Ry = np.zeros(shape=(3, 3))
    cos, sin = np.cos(ph), np.sin(ph)

    Ry[0, 0] = cos
    Ry[0, 2] = -sin
    Ry[1, 1] = 1
    Ry[2, 0] = sin
    Ry[2, 2] = cos

    #      | cos(kp)   sin(kp)   0 |
    # Rz = | -sin(kp)  cos(kp)   0 |
    #      |    0         0      1 |

    Rz = np.zeros(shape=(3, 3))
    cos, sin = np.cos(kp), np.sin(kp)

    Rz[0, 0] = cos
    Rz[0, 1] = sin
    Rz[1, 0] = -sin
    Rz[1, 1] = cos
    Rz[2, 2] = 1

    # R = Rz * Ry * Rx
    Rzy = np.dot(Rz, Ry)
    R = np.dot(Rzy, Rx)

    return R


def las2nparray(file_path):
    # reading las file and copy points
    input_las = laspy.file.File(file_path, mode="r")
    point_records = input_las.points.copy()

    # TODO: read the color of points
    #https://github.com/strawlab/python-pcl/issues/171

    # getting scaling and offset parameters
    las_scaleX = input_las.header.scale[0]
    las_offsetX = input_las.header.offset[0]
    las_scaleY = input_las.header.scale[1]
    las_offsetY = input_las.header.offset[1]
    las_scaleZ = input_las.header.scale[2]
    las_offsetZ = input_las.header.offset[2]

    # calculating coordinates
    p_X = np.array((point_records['point']['X'] * las_scaleX) + las_offsetX)
    p_Y = np.array((point_records['point']['Y'] * las_scaleY) + las_offsetY)
    p_Z = np.array((point_records['point']['Z'] * las_scaleZ) + las_offsetZ)

    points = np.zeros((len(p_X), 3))
    points[:, 0] = p_X
    points[:, 1] = p_Y
    points[:, 2] = p_Z

    return points


def read_eo(eo_file):
    print("=======================")
    print(" * Read EOs from a file")
    print("=======================")

    f = open(eo_file, 'r')
    next(f)
    next(f)
    lines = f.readlines()
    f.close()

    EOs = np.empty(shape=(len(lines), 6), dtype=float)
    for i in range(len(lines)):
        params = lines[i].split(",")
        EOs[i, 0] = float(params[1])  # m
        EOs[i, 1] = float(params[2])  # m
        EOs[i, 2] = float(params[3])  # m
        EOs[i, 3] = float(params[4])  # deg
        EOs[i, 4] = float(params[5])  # deg
        EOs[i, 5] = float(params[6])  # deg

    return EOs


def read_eo_list(eo_file):
    print("=====================================")
    print(" * Read EOs, list type from a file")
    print("=====================================")

    f = open(eo_file, 'r')
    next(f)
    next(f)
    lines = f.readlines()
    f.close()

    EOs = []
    for i in range(len(lines)):
        params = lines[i].split("\t")
        x = float(params[1])  # m
        y = float(params[2])  # m
        z = float(params[3])  # m
        o = float(params[4])  # deg
        p = float(params[5])  # deg
        k = float(params[6])  # deg
        EOs.append([x, y, z, o, p, k])

    return EOs


if __name__ == "__main__":
    EOs_np = read_eo(eo_file="eo.txt")
    EOs_list = read_eo_list(eo_file="eo.txt")
    print(EOs_np[0, 0])
    print(EOs_list[0][0])
    print("Done")
