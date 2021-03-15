from pathlib import Path
import time
from collections import deque
from georeferencing import georeferencing
from dem import generate_dem
from rectification import *
import json
import numpy as np
import cv2
from module import read_eo, Rot3D, las2nparray, nparray2las
import Metashape
from rich.console import Console
from rich.table import Table

console = Console()

import logging
# 로그 생성
logger = logging.getLogger()

# 로그의 출력 기준 설정
logger.setLevel(logging.INFO)

# log 출력 형식
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(asctime)s %(message)s')

# log 출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# log를 파일에 출력
file_handler = logging.FileHandler('my.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


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
    name = images[i].split("/")[-1]
    print(' * image: ', name)
    print('=' * 30)
    dst = './' + images[i].split("/")[-1].split(".")[0]
    try:
        images_to_process.append(images[i])
        ### 1. Georeferencing
        georef_start = time.time()
        eo, focal_length, pixel_size, center_z = georeferencing(' '.join(images_to_process), no_images_process, i)
        if not focal_length == 0:
            R = Rot3D(eo * np.pi / 180)
            gsd = (pixel_size * (eo[2] - center_z)) / focal_length
            console.print(f"EOP: {eo[0]:.2f} | {eo[1]:.2f} | {eo[2]:.2f} | {eo[3]:.2f} | {eo[4]:.2f} | {eo[5]:.2f}\n"
                          f"Focal Length: {focal_length * 1000:.2f} mm, Pixel Size: {pixel_size * 1000000:.2f} um/px,"
                          f" Z of center: {center_z:.2f} m, GSD: {gsd * 100:.2f} cm/px",
                          style="blink bold red underline")
        else:
            print(eo, focal_length, pixel_size, center_z, 0)
            continue
        georef_time = time.time() - georef_start
        console.print(f"Georeferencing time: {georef_time:.2f} sec", style="blink bold red underline")

        ### 2. DEM processing
        dem_start = time.time()
        dem_x, dem_y, dem_z, bbox = generate_dem("pointclouds.las", gsd)
        dem_time = time.time() - dem_start
        console.print(f"DEM time: {dem_time:.2f} sec", style="blink bold red underline")

        ### 3. Geodata generation
        rectify_start = time.time()
        boundary_rows = dem_x.shape[0]
        boundary_cols = dem_x.shape[1]
        image = cv2.imread(images[i], -1)
        b, g, r, a = rectify_dem_parallel(dem_x, dem_y, dem_z, boundary_rows, boundary_cols,
                                          eo, R, focal_length, pixel_size, image)
        rectify_time = time.time() - rectify_start
        console.print(f"Rectify time: {rectify_time:.2f} sec", style="blink bold red underline")

        ### (4. Write the Orthophoto)
        write_start = time.time()
        # createGeoTiff(b, g, r, a, bbox, gsd, boundary_rows, boundary_cols, dst)
        create_pnga_optical(b, g, r, a, bbox, gsd, 5186, dst)
        write_time = time.time() - write_start
        console.print(f"Write time: {write_time:.2f} sec", style="blink bold red underline")

        processing_time = time.time() - georef_start
        console.print(f"Process time: {processing_time:.2f} sec", style="blink bold red underline")

        logger.info(images[i].split("/")[-1] + " " + str(round(georef_time, 5)) + " " + str(round(dem_time, 5))
                    + " " + str(round(rectify_time, 5)) + " " + str(round(write_time, 5))
                    + " " + str(round(processing_time, 5)))
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Image", style="dim", width=12)
        table.add_column("Georeferencing", justify="right")
        table.add_column("DEM", justify="right")
        table.add_column("Rectification", justify="right")
        table.add_column("Write", justify="right")
        table.add_column("Processing", justify="right")
        table.add_row(
            name, str(round(georef_time, 5)), str(round(dem_time, 5)), str(round(rectify_time, 5)),
            str(round(write_time, 5)), str(round(processing_time, 5))
        )
        console.print(table)

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


nparray2las(points_stack, colors_stack)
print("==============================================")
print(" *** Elapsed time: %.2f" % (time.time() - start_time))
print("==============================================")
