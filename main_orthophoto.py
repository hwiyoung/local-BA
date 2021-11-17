from config import config
from collections import deque
import time
import numpy as np
from pathlib import Path
import Metashape

from rich.console import Console
from rich.table import Table
from rich.progress import track

from processing import orthophoto_dg, orthophoto_lba
from module import nparray2las
from rectification import create_pnga_optical

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

# Parameters
image_path = config["image_path"]
extension = config["extension"]
metadata_in_image = config["metadata_in_image"]
output_path = config["output_path"]
if not Path(output_path).exists():
    Path(output_path).mkdir()

no_images_process = config["no_images_process"]
types = config["types"]
matching_accuracy = config["matching_accuracy"]
Metashape.app.gpu_mask = config["no_gpus"]
sys_cal = config["sys_cal"]

diff_init_esti = config["diff_init_esti"]
# std_init_esti = config["std_init_esti"]
diff_before_current = config["diff_before_current"]

epsg = config["epsg"]
gsd = config["gsd"]
dem = config["dem"]
ground_height = config["ground_height"]

console.log(config)

images = Path(image_path).glob('*.' + extension)
images = [str(x) for x in images if x.is_file()]
images.sort()
images_to_process = deque(maxlen=no_images_process)

poses_stack = np.zeros(shape=(0, 4, 4))
points_stack = np.zeros((0, 3))
colors_stack = np.zeros((0, 3))

flag = False
start_time = time.time()
for i in track(range(len(images))):
    processing_start = time.time()
    name = images[i].split("/")[-1]
    dst = str(Path(output_path) / images[i].split("/")[-1].split(".")[0])
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
            b, g, r, a, bbox, gsd, times = orthophoto_dg(image_path=images[i], metadata_in_image=metadata_in_image,
                                                         sys_cal=sys_cal, epsg=epsg,
                                                         gsd=gsd, ground_height=ground_height)
        else:
            b, g, r, a, bbox, gsd, times, flag = orthophoto_lba(image_path=image, flag=flag, types=types,
                                                                matching_accuracy=matching_accuracy,
                                                                diff_init_esti=diff_init_esti,
                                                                epsg=epsg, gsd=gsd, output_path=output_path)
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
