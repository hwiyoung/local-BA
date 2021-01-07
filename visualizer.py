import OpenGL.GL as gl
import pangolin
import numpy as np
from module import read_eo, Rot3D, las2nparray


def visualize(eo_file, pc_file):
    # Import camera pose
    EOs = read_eo(eo_file)
    EOs[:, 3:] *= np.pi / 180   # deg to rad
    R = np.empty(shape=(EOs.shape[0], 3, 3))
    for i in range(EOs.shape[0]):
        R[i] = Rot3D(EOs[i])   # Transformation *coordinate system*

    # Import las to numpy array
    points = las2nparray(pc_file)
    # points = points / 100

    pangolin.CreateWindowAndBind('Main', 640, 480)
    gl.glEnable(gl.GL_DEPTH_TEST)

    # Define Projection and initial ModelView matrix
    scam = pangolin.OpenGlRenderState(
        pangolin.ProjectionMatrix(640, 480, 420, 420, 320, 240, 0.1, 5000),
        pangolin.ModelViewLookAt(EOs[0, 0], EOs[0, 1], EOs[0, 2], EOs[0, 0], EOs[0, 1], 0, pangolin.AxisDirection.AxisY))
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
        x_axis = np.array([[EOs[0, 0], EOs[0, 1], EOs[0, 2]], [EOs[0, 0] + 10, EOs[0, 1], EOs[0, 2]]])
        pangolin.DrawLine(x_axis)
        gl.glColor3f(0.0, 1.0, 0.0)
        y_axis = np.array([[EOs[0, 0], EOs[0, 1], EOs[0, 2]], [EOs[0, 0], EOs[0, 1] + 10, EOs[0, 2]]])
        pangolin.DrawLine(y_axis)
        gl.glColor3f(0.0, 0.0, 1.0)
        z_axis = np.array([[EOs[0, 0], EOs[0, 1], EOs[0, 2]], [EOs[0, 0], EOs[0, 1], EOs[0, 2] + 10]])
        pangolin.DrawLine(z_axis)

        # Draw cameras
        for i in range(EOs.shape[0]):
            pose = np.identity(4)
            pose[:3, 3] = EOs[i, 0:3].T
            pose[:3, :3] = -R[i].T
            gl.glLineWidth(3)
            gl.glColor3f(1.0, 0.0, 1.0)
            pangolin.DrawCamera(pose, 0.5, 0.75, 0.8)

        pangolin.FinishFrame()


if __name__ == '__main__':
    visualize(eo_file="eo.txt", pc_file="pointclouds.las")