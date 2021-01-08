import numpy as np
from module import read_eo, Rot3D, las2nparray
from viewer3D import Viewer3D
import time
from pathlib import Path

if __name__ == '__main__':
    dir_path = "../00_data/local-BA"
    p_eo = Path(dir_path).glob('*.txt')
    eo_files = [str(x) for x in p_eo if x.is_file()]
    eo_files.sort()
    p_pc = Path(dir_path).glob('*.las')
    pc_files = [str(x) for x in p_pc if x.is_file()]
    pc_files.sort()

    viewer3D = Viewer3D()
    is_paused = False

    while eo_files:
        poses_stack = np.zeros(shape=(0, 4, 4))
        points_stack = np.zeros((0, 3))
        colors_stack = np.zeros((0, 3))
        for eo_file, pc_file in zip(eo_files, pc_files):
            print(eo_file)
            # Import camera pose
            EOs = read_eo(eo_file)
            EOs[:, 3:] *= np.pi / 180  # deg to rad
            poses = np.zeros(shape=(EOs.shape[0], 4, 4))
            poses[:, -1, -1] = 1
            for i in range(EOs.shape[0]):
                poses[i, :3, 3] = EOs[i, 0:3].T    # translation
                R = Rot3D(EOs[i])  # Transform *coordinate system*
                poses[i, :3, :3] = -R.T  # rotation
            poses_stack = np.vstack((poses_stack, poses))
            print(poses_stack.shape)

            # Import las to numpy array
            points, colors = las2nparray(pc_file)
            points_stack = np.vstack((points_stack, points))
            colors_stack = np.vstack((colors_stack, colors))

            if not is_paused:
                print('..................................')
                # 3D display (map display)
                if viewer3D is not None:
                    viewer3D.draw_map(poses=poses_stack, points=points_stack, colors=colors_stack)

            if viewer3D is not None:
                is_paused = not viewer3D.is_paused()

            time.sleep(1)
