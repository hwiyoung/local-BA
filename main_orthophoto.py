import json
from collections import deque

from rich.console import Console
from rich.table import Table

from georeferencing import *
from dem import boundary, generate_dem
from module import Rot3D, las2nparray, nparray2las
from rectification import *

from processing import orthophoto_dg, orthophoto_lba

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
types = data["types"]  # fixed, nonfixed-initial, nonfixed-estimated
epsg = data["epsg"]
# https://www.agisoft.com/forum/index.php?topic=11697.msg52465#msg52465
downscale = data["downscale"]  # Image alignment accuracy - 0, 1, 2, 4, 8
gsd = data["gsd"]
ground_height = data["ground_height"]  # m

images = Path(image_path).glob('*.' + extension)
images = [str(x) for x in images if x.is_file()]
images.sort()
images_to_process = deque(maxlen=no_images_process)

poses_stack = np.zeros(shape=(0, 4, 4))
points_stack = np.zeros((0, 3))
colors_stack = np.zeros((0, 3))

flag = False
start_time = time.time()
for i in range(len(images)):
    processing_start = time.time()
    name = images[i].split("/")[-1]
    dst = './' + images[i].split("/")[-1].split(".")[0]
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Image", style="dim")
    table.add_column("Output", style="dim")
    try:
        ### 1. Georeferencing
        images_to_process.append(images[i])
        image = ' '.join(images_to_process)
        table.add_row(image, dst)
        console.print(table)
        if i < no_images_process - 1:
            b, g, r, a, bbox, times = orthophoto_dg(images[i], epsg=epsg, gsd=gsd, ground_height=ground_height)
        else:
            b, g, r, a, bbox, times, flag = orthophoto_lba(image, flag, types, epsg=epsg, gsd=gsd, downscale=downscale)

        ### (4. Write the Orthophoto)
        write_start = time.time()
        create_pnga_optical(b, g, r, a, bbox, gsd, epsg, dst)
        write_time = time.time() - write_start
        console.print(f"Write time: {write_time:.2f} sec", style="blink bold red underline")

    except Exception as e:
        print(f" *** {e}")
        b, g, r, a, bbox, times = orthophoto_dg(images[i], epsg=epsg, gsd=gsd, ground_height=ground_height)

        ### (4. Write the Orthophoto)
        write_start = time.time()
        create_pnga_optical(b, g, r, a, bbox, gsd, epsg, dst)
        write_time = time.time() - write_start
        console.print(f"Write time: {write_time:.2f} sec", style="blink bold red underline")
        flag = False
    except KeyboardInterrupt:
        print(" *** KeyboardInterrupt!!!")
        nparray2las(points_stack, colors_stack)
        break

    georef_time = times[0]
    dem_time = times[1]
    rectify_time = times[2]
    processing_time = time.time() - processing_start
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

print("==============================================")
print(" *** Elapsed time: %.2f" % (time.time() - start_time))
print("==============================================")
