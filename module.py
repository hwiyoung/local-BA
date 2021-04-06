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

    # read the color of points
    # https://github.com/strawlab/python-pcl/issues/171
    colors = np.zeros((len(p_X), 3))
    red = input_las.red
    green = input_las.green
    blue = input_las.blue
    red = red / red.max()
    green = green / green.max()
    blue = blue / blue.max()

    colors[:, 0] = red
    colors[:, 1] = green
    colors[:, 2] = blue

    return points, colors


# https://github.com/laspy/laspy/commit/4dba4c846eacf119b5e99ccf8ccae73735ef1944
# https://pointly.ai/how-to-convert-your-point-cloud-data-into-las-laz/
def nparray2las(points, colors):
    header = laspy.header.Header(file_version=1.2, point_format=2)
    outfile = laspy.file.File("output.las", mode="w", header=header)

    outfile.header.offset = np.min(points, axis=0)
    outfile.header.scale = [0.001, 0.001, 0.001]

    outfile.x = points[:, 0]
    outfile.y = points[:, 1]
    outfile.z = points[:, 2]

    outfile.Red = np.uint8(colors[:, 0] * 256)
    outfile.Green = np.uint8(colors[:, 1] * 256)
    outfile.Blue = np.uint8(colors[:, 2] * 256)
    # outfile.Intensity = i
    # outfile.classification = labels
    outfile.close()
    print(" *** Write LAS!!!")


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


if __name__ == "__main__":
    EOs_np = read_eo(eo_file="eo01.txt")
    points, colors = las2nparray(file_path="pointclouds01.las")
    print(EOs_np[0, 0])
    print("Done")
