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

    # eo_files = ["eo.txt", "eo2.txt"]
    # pc_files = ["pointclouds.las", "pointclouds2.las"]
    #
    # # eo_files = ["eo.txt"]
    # # pc_files = ["pointclouds.las"]

    viewer3D = Viewer3D()
    is_paused = False

    while eo_files:
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

            # Import las to numpy array
            points = las2nparray(pc_file)

            if not is_paused:
                print('..................................')
                # 3D display (map display)
                if viewer3D is not None:
                    viewer3D.draw_map(poses=poses, points=points)

            if viewer3D is not None:
                is_paused = not viewer3D.is_paused()

            time.sleep(3)
