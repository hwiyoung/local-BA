from pathlib import Path
import time
from collections import deque
from georeferencing import *
from dem import generate_dem
from rectification import *
import json
import numpy as np
import cv2
from module import Rot3D, las2nparray, nparray2las
import Metashape
from rich.console import Console
from rich.table import Table

console = Console()

import logging
# Construct log
logger = logging.getLogger()
# Set the criteria of log
logger.setLevel(logging.INFO)
# Set log format
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(asctime)s %(message)s')
# StreamHandler log
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
# FileHandler log
file_handler = logging.FileHandler('my.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

Metashape.app.gpu_mask = 1  # Set the number of gpus

with open("config.json") as f:
    data = json.load(f)
no_images_process = data["no_images_process"]
image_path = data["image_path"]
extension = data["extension"]
types = data["types"]     # fixed, nonfixed-initial, nonfixed-estimated
epsg = data["epsg"]
# https://www.agisoft.com/forum/index.php?topic=11697.msg52465#msg52465
downscale = data["downscale"]   #  Image alignment accuracy - 0, 1, 2, 4, 8

images = Path(image_path).glob('*.' + extension)
images = [str(x) for x in images if x.is_file()]
images.sort()
images_to_process = deque(maxlen=no_images_process)

poses_stack = np.zeros(shape=(0, 4, 4))
points_stack = np.zeros((0, 3))
colors_stack = np.zeros((0, 3))

start_time = time.time()
for i in range(len(images)):
    name = images[i].split("/")[-1]
    dst = './' + images[i].split("/")[-1].split(".")[0]
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Image", style="dim")
    table.add_column("Output", style="dim")
    # table.add_row(name, dst)
    # console.print(table)
    try:
        ### 1. Georeferencing
        georef_start = time.time()
        images_to_process.append(images[i])
        image = ' '.join(images_to_process)
        table.add_row(image, dst)
        console.print(table)
        if i < no_images_process - 1:
            # solve_direct_georeferencing
            eo, focal_length, pixel_size, center_z = solve_direct_georeferencing(image, epsg)
            continue    # test ... delete later
        elif i == no_images_process - 1:
            # solve_lba_init_uni
            eo, focal_length, pixel_size, center_z = solve_lba_init_uni(image, epsg, downscale)
        elif i > no_images_process - 1 and types == "fixed":
            # solve_lba_esti_div
            console.print(f"solve_lba_esti_div", style="blink bold red underline")
            eo, focal_length, pixel_size, center_z = solve_lba_esti_div(image, epsg, downscale)
        elif i > no_images_process - 1 and types == "nonfixed-initial":
            # solve_lba_init_uni
            console.print(f"solve_lba_init_uni", style="blink bold red underline")
            eo, focal_length, pixel_size, center_z = solve_lba_init_uni(image, epsg, downscale)
        elif i > no_images_process - 1 and types == "nonfixed-estimated":
            # solve_lba_esti_uni
            console.print(f"solve_lba_esti_uni", style="blink bold red underline")
            eo, focal_length, pixel_size, center_z = solve_lba_esti_uni(image, epsg, downscale)
        else:
            console.print(f"Which type of processing you have?", style="blink bold red underline")
            continue

        R = Rot3D(eo * np.pi / 180)
        gsd = (pixel_size * (eo[2] - center_z)) / focal_length
        gsd = 0.1   # test ... delete later
        console.print(f"EOP: {eo[0]:.2f} | {eo[1]:.2f} | {eo[2]:.2f} | {eo[3]:.2f} | {eo[4]:.2f} | {eo[5]:.2f}\n"
                      f"Focal Length: {focal_length * 1000:.2f} mm, Pixel Size: {pixel_size * 1000000:.2f} um/px,"
                      f" Z of center: {center_z:.2f} m, GSD: {gsd * 100:.2f} cm/px",
                      style="blink bold red underline")

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

    if i > no_images_process - 1:
        # Import las to numpy array
        points, colors = las2nparray(file_path="pointclouds.las")
        points_stack = np.vstack((points_stack, points))
        colors_stack = np.vstack((colors_stack, colors))

nparray2las(points_stack, colors_stack)
print("==============================================")
print(" *** Elapsed time: %.2f" % (time.time() - start_time))
print("==============================================")
