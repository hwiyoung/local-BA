from pathlib import Path
import time
from collections import deque
from local_ba3 import solve_local_ba_first, solve_local_ba_rest
import json
import numpy as np
from module import read_eo, Rot3D, las2nparray, nparray2las
import Metashape
# from viewer3D import Viewer3D

Metashape.app.gpu_mask = 1

with open("config.json") as f:
    data = json.load(f)

no_images_process = data["no_images_process"]
image_path = data["image_path"]
images = Path(image_path).glob('*.JPG')
images = [str(x) for x in images if x.is_file()]
images.sort()
images_to_process = deque(maxlen=no_images_process)

is_paused = False

poses_stack = np.zeros(shape=(0, 4, 4))
points_stack = np.zeros((0, 3))
colors_stack = np.zeros((0, 3))

start_time = time.time()
for i in range(len(images)):
    if not is_paused:
        print('............................................')
        print(' * image: ', images[i])
        print('............................................')
        try:
            if i < 4:
                images_to_process.append(images[i])
                print("i < 4", images_to_process)
                continue
            elif i == 4:
                images_to_process.append(images[i])
                print("i == 4", images_to_process)
                solve_local_ba_first(' '.join(images_to_process))
                # viewer3D = Viewer3D()
                viewer3D = None

                # Import camera pose
                EOs = read_eo(eo_file="eo.txt")
                EOs[:, 3:] *= np.pi / 180  # deg to rad
                poses = np.zeros(shape=(EOs.shape[0], 4, 4))
                poses[:, -1, -1] = 1
                for i in range(EOs.shape[0]):
                    poses[i, :3, 3] = EOs[i, 0:3].T  # translation
                    R = Rot3D(EOs[i])  # Transform *coordinate system*
                    poses[i, :3, :3] = -R.T  # rotation
                poses_stack = np.vstack((poses_stack, poses))
                print(poses_stack.shape)
            else:
                images_to_process.append(images[i])
                print("else", images_to_process)
                solve_local_ba_rest(' '.join(images_to_process))

                # Import camera pose
                EOs = read_eo(eo_file="eo.txt")
                EOs[:, 3:] *= np.pi / 180  # deg to rad
                poses = np.zeros(shape=(1, 4, 4))
                poses[:, -1, -1] = 1
                poses[0, :3, 3] = EOs[-1, 0:3].T  # translation
                R = Rot3D(EOs[-1])  # Transform *coordinate system*
                poses[0, :3, :3] = -R.T  # rotation
                poses_stack = np.vstack((poses_stack, poses))
                print(poses_stack.shape)
        except Exception as e:
            print(e)
            break
        except KeyboardInterrupt:
            print(" *** KeyboardInterrupt!!!")
            nparray2las(points_stack, colors_stack)
            break

        # Import las to numpy array
        points, colors = las2nparray(file_path="pointclouds.las")
        points_stack = np.vstack((points_stack, points))
        colors_stack = np.vstack((colors_stack, colors))
        
        # 3D display (map display)
        if viewer3D is not None:
            viewer3D.draw_map(poses=poses_stack, points=points_stack, colors=colors_stack)
    else:
        time.sleep(1)

    if viewer3D is not None:
        is_paused = not viewer3D.is_paused()

    # time.sleep(1)
nparray2las(points_stack, colors_stack)
print("==============================================")
print(" *** Elapsed time: %.2f" % (time.time() - start_time))
print("==============================================")
