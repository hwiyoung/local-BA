import OpenGL.GL as gl
import pangolin
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
def nparray2las(points, colors):
    header = laspy.header.Header(file_version=1.2, point_format=2)
    outfile = laspy.file.File("output.las", mode="w", header=header)
    outfile.header.offset = np.min(points, axis=0)
    outfile.header.scale = [0.001, 0.001, 0.001]
    outfile.x = points[:, 0]
    outfile.y = points[:, 1]
    outfile.z = points[:, 2]

    # np.array(red / red.max() * 256, dtype=np.int)
    outfile.Red = np.uint8(colors[:, 0] * 256)
    outfile.Green = np.uint8(colors[:, 1] * 256)
    outfile.Blue = np.uint8(colors[:, 2] * 256)
    # outfile.Intensity = i
    # outfile.classification = labels
    outfile.close()


def main():
    # Import camera pose - test 100_0156_0113
    # TODO: based on files
    eo = np.array([412065.2417444444727153, 460266.2869342155754566, 99.5811297956551869,
                   -0.9593599128210599, -0.1490554140282855, -18.2548477188996578])
    eo[3:] *= np.pi / 180
    R = Rot3D(eo)   # Transformation *coordinate system*


    # Import las to numpy array
    points, colors = las2nparray("../pointclouds.las")
    nparray2las(points, colors)
    points_test, colors_test = las2nparray("output.las")

    pangolin.CreateWindowAndBind('Main', 640, 480)
    gl.glEnable(gl.GL_DEPTH_TEST)

    # Define Projection and initial ModelView matrix
    scam = pangolin.OpenGlRenderState(
        pangolin.ProjectionMatrix(640, 480, 420, 420, 320, 240, 0.2, 200),
        pangolin.ModelViewLookAt(eo[0], eo[1], eo[2], eo[0], eo[1], 0, pangolin.AxisDirection.AxisY))
        # pangolin.ModelViewLookAt(fromX, fromY, fromZ, toX, toY, toZ, up_axis))
    handler = pangolin.Handler3D(scam)

    # Create Interactive View in window
    dcam = pangolin.CreateDisplay()
    dcam.SetBounds(0.0, 1.0, 0.0, 1.0, -640.0 / 480.0)
    dcam.SetHandler(handler)

    while not pangolin.ShouldQuit():
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glClearColor(1.0, 1.0, 1.0, 1.0)
        dcam.Activate(scam)

        # Draw Point Cloud
        gl.glPointSize(1)
        gl.glColor3f(1.0, 0.0, 0.0)
        pangolin.DrawPoints(points)

        # Draw Axes - test
        gl.glLineWidth(2)
        gl.glColor3f(1.0, 0.0, 0.0)
        x_axis = np.array([[eo[0], eo[1], eo[2]], [eo[0] + 10, eo[1], eo[2]]])
        pangolin.DrawLine(x_axis)
        gl.glColor3f(0.0, 1.0, 0.0)
        y_axis = np.array([[eo[0], eo[1], eo[2]], [eo[0], eo[1] + 10, eo[2]]])
        pangolin.DrawLine(y_axis)
        gl.glColor3f(0.0, 0.0, 1.0)
        z_axis = np.array([[eo[0], eo[1], eo[2]], [eo[0], eo[1], eo[2] + 10]])
        pangolin.DrawLine(z_axis)

        # Draw camera - test
        pose = np.identity(4)
        # # pose[:3, 3] = np.array([0, -1, -1])    # translation
        # pose[:3, :3] = np.array([[1, 0, 0],
        #                          [0, 1, 1],
        #                          [0, -1, 1]])  # rotation, 45 deg up
        pose[:3, 3] = eo[0:3].T
        pose[:3, :3] = -R.T
        gl.glLineWidth(3)
        gl.glColor3f(1.0, 0.0, 1.0)
        pangolin.DrawCamera(pose, 0.5, 0.75, 0.8)

        pangolin.FinishFrame()


if __name__ == '__main__':
    main()