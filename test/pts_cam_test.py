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

    # TODO: read the color of points

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


def main():
    # Import camera pose - test 100_0156_0113
    # TODO: based on files
    eo = np.array([188142.8267815202700000, 555628.0175237776700000, 153.2081868545070300,
                   -20.4685031451434160, -34.0945958355284020, -31.7078702493588980])
    R = Rot3D(eo * np.pi / 180)


    # Import las to numpy array
    points = las2nparray("test_KAU_150m_5186.las")
    # points = points / 100

    pangolin.CreateWindowAndBind('Main', 640, 480)
    gl.glEnable(gl.GL_DEPTH_TEST)

    # Define Projection and initial ModelView matrix
    scam = pangolin.OpenGlRenderState(
        pangolin.ProjectionMatrix(640, 480, 420, 420, 320, 240, 0.2, 200),
        # pangolin.ModelViewLookAt(-2, 2, -2, 0, 0, 0, pangolin.AxisDirection.AxisY))
        pangolin.ModelViewLookAt(np.average(points[:, 0]),
                                 np.average(points[:, 1]),
                                 np.average(points[:, 2]), 0, 0, 0, pangolin.AxisDirection.AxisY))
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
        pose[:3, :3] = R
        gl.glLineWidth(1)
        gl.glColor3f(0.0, 0.0, 1.0)
        pangolin.DrawCamera(pose, 0.5, 0.75, 0.8)

        pangolin.FinishFrame()


if __name__ == '__main__':
    main()