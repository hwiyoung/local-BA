import glob
import time
from collections import deque
import platform
import subprocess
import os
import json
from visualizer import visualize
from module import read_eo


def solve_local_ba_first(images):
    if platform.system() == "Windows":
        command = "C:/Program Files/Agisoft/PhotoScan Pro/photoscan.exe"
        # subprocess.call([command, "-r", "lba_photoscan_run.py", "--image-path", image_path])
        ret_bytes = subprocess.check_output([command, "-r", "test_lba_photoscan_run.py", "--image-path", image_path])
        ret_str = ret_bytes.decode()
        x = float(ret_str.split("\n")[-7])
        y = float(ret_str.split("\n")[-6])
        z = float(ret_str.split("\n")[-5])
        o = float(ret_str.split("\n")[-4])
        p = float(ret_str.split("\n")[-3])
        k = float(ret_str.split("\n")[-2])
        print(x, y, z, o, p, k)
        print("test")
    elif platform.system() == "Linux":
        command = os.path.join(os.path.expanduser("~"), "PhotoScan/photoscan-pro/photoscan.sh")
        subprocess.run([command, "-r", "local_ba.py", "--images", images, "--method", "first"])
    else:
        print("Please choose between Windows and Linux")


def solve_local_ba_rest(images):
    if platform.system() == "Windows":
        command = "C:/Program Files/Agisoft/PhotoScan Pro/photoscan.exe"
        # subprocess.call([command, "-r", "lba_photoscan_run.py", "--image-path", image_path])
        ret_bytes = subprocess.check_output([command, "-r", "test_lba_photoscan_run.py", "--image-path", image_path])
        ret_str = ret_bytes.decode()
        x = float(ret_str.split("\n")[-7])
        y = float(ret_str.split("\n")[-6])
        z = float(ret_str.split("\n")[-5])
        o = float(ret_str.split("\n")[-4])
        p = float(ret_str.split("\n")[-3])
        k = float(ret_str.split("\n")[-2])
        print(x, y, z, o, p, k)
        print("test")
    elif platform.system() == "Linux":
        command = os.path.join(os.path.expanduser("~"), "PhotoScan/photoscan-pro/photoscan.sh")
        subprocess.run([command, "-r", "local_ba.py", "--images", images, "--method", "rest"])
    else:
        print("Please choose between Windows and Linux")


with open("config.json") as f:
    data = json.load(f)

no_images_process = data["no_images_process"]
image_path = data["image_path"]
images = glob.glob(image_path + "/*.JPG")
images.sort()
images_to_process = deque(maxlen=no_images_process)
start_time = time.time()
for i in range(len(images)):
    try:
        if i < 4:
            images_to_process.append(images[i])
            print("i < 4", images_to_process)
            continue
        elif i == 4:
            images_to_process.append(images[i])
            solve_local_ba_first(' '.join(images_to_process))
            # visualize(eo_file="eo.txt", pc_file="pointclouds.las")
            print("i == 4", images_to_process)
        else:
            images_to_process.append(images[i])
            solve_local_ba_rest(' '.join(images_to_process))
            print("else", images_to_process)
    except Exception as e:
        print(e)
        break

print("==============================================")
print(" *** Elapsed time: %.2f" % (time.time() - start_time))
print("==============================================")
