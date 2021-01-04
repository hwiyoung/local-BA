import numpy as np
from module import read_eo, Rot3D, las2nparray
from viewer3D import Viewer3D

eo_file = "eo.txt"
pc_file = "pointclouds.las"


if __name__ == '__main__':
    viewer3D = Viewer3D()
    is_paused = False

    while True:
        # Import camera pose
        EOs = read_eo(eo_file)
        EOs[:, 3:] *= np.pi / 180  # deg to rad
        poses = np.zeros(shape=(EOs.shape[0], 4, 4))
        poses[:, -1, -1] = 1
        for i in range(EOs.shape[0]):
            poses[i, :3, 3] = EOs[i, 0:3].T    # translation
            R = Rot3D(EOs[i])  # Transform *coordinate system*
            poses[i, :3, :3] = -R.T  # rotation

        # Import las to numpy array
        points = las2nparray(pc_file)

        if not is_paused:
            print('..................................')
            # 3D display (map display)
            if viewer3D is not None:
                viewer3D.draw_map(poses=poses, points=points)

            if viewer3D is not None:
                is_paused = not viewer3D.is_paused()

