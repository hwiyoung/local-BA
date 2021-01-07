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
        pass
    elif platform.system() == "Linux":
        command = os.path.join(os.path.expanduser("~"), "Metashape/metashape-pro/metashape.sh")
        subprocess.run([command, "-r", "local_ba.py", "--images", images, "--method", "first"])
    else:
        print("Please choose between Windows and Linux")


def solve_local_ba_rest(images):
    if platform.system() == "Windows":
        pass
    elif platform.system() == "Linux":
        command = os.path.join(os.path.expanduser("~"), "Metashape/metashape-pro/metashape.sh")
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
            print("i == 4", images_to_process)
            solve_local_ba_first(' '.join(images_to_process))
            # visualize(eo_file="eo.txt", pc_file="pointclouds.las")
        else:
            images_to_process.append(images[i])
            print("else", images_to_process)
            solve_local_ba_rest(' '.join(images_to_process))
    except Exception as e:
        print(e)
        break

print("==============================================")
print(" *** Elapsed time: %.2f" % (time.time() - start_time))
print("==============================================")
