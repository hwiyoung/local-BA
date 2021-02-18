from pathlib import Path
import time
from collections import deque
from georeferencing import georeferencing
import json
import numpy as np
from module import read_eo, Rot3D, las2nparray, nparray2las
import Metashape

Metashape.app.gpu_mask = 1  # Set the number of gpus

with open("config.json") as f:
    data = json.load(f)
no_images_process = data["no_images_process"]
image_path = data["image_path"]
extension = data["extension"]

images = Path(image_path).glob('*.' + extension)
images = [str(x) for x in images if x.is_file()]
images.sort()
images_to_process = deque(maxlen=no_images_process)

poses_stack = np.zeros(shape=(0, 4, 4))
points_stack = np.zeros((0, 3))
colors_stack = np.zeros((0, 3))

start_time = time.time()
for i in range(len(images)):
    print('=' * 30)
    print(' * image: ', images[i].split("/")[-1])
    print('=' * 30)
    try:
        images_to_process.append(images[i])
        ### 1. Georeferencing
        eo, focal_length, pixel_size, center_z = georeferencing(' '.join(images_to_process), no_images_process, i)
        if not focal_length == 0:
            R = Rot3D(eo * np.pi / 180)
            gsd = (pixel_size * (eo[2] - center_z)) / focal_length
            print(eo, focal_length, pixel_size, center_z, gsd)
        else:
            print(eo, focal_length, pixel_size, center_z, 0)

        ### 2. DEM processing
        # dem = process_dem(point_cloud, gsd)

        ### 3. Geodata generation
        # b, g, r, a = rectify_dem_parallel(dem, boundary_rows, boundary_cols, gsd, eo, R, focal_length, pixel_size, image)

        ### (4. Write the Orthophoto)
        # createGeoTiff(b, g, r, a, bbox, gsd, boundary_rows, boundary_cols, dst)
    except Exception as e:
        print(e)
        break
    except KeyboardInterrupt:
        print(" *** KeyboardInterrupt!!!")
        nparray2las(points_stack, colors_stack)
        break

    # # Import las to numpy array
    # points, colors = las2nparray(file_path="pointclouds.las")
    # points_stack = np.vstack((points_stack, points))
    # colors_stack = np.vstack((colors_stack, colors))


nparray2las(points_stack, colors_stack)
print("==============================================")
print(" *** Elapsed time: %.2f" % (time.time() - start_time))
print("==============================================")
