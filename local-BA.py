import argparse
# from lba_photoscan import Local_BA_Photoscan
# import glob
import platform
import subprocess

def solve_local_AT(image_path, method):
    # lba = Local_BA_Photoscan()
    #
    # images = glob.glob(image_path)
    #
    # for i in range(len(images)-5):
    #     images_to_process = images[i:i+4]
    #     name, EO = lba.photoscan_alignphotos(images_to_process)
    #     print(name, EO)
    #
    # print("Done")

    if platform.system() == "Windows" and method == "photoscan":
        command = "C:/Program Files/Agisoft/PhotoScan Pro/photoscan.exe"
        subprocess.call([command, "-r", "lba_photoscan_run.py", "--image-path", image_path])
    elif platform.system() == "Linux" and method == "photoscan":
        command = "~/PhotoScan/photoscan-pro/photoscan.sh"
        subprocess.call([command, "-r", "lba_photoscan_run.py", "--image-path", image_path])
    else:
        print("None")


if __name__ == '__main__':
    # Set argument parser
    parser = argparse.ArgumentParser(description='LocalBA')
    parser.add_argument('--image-path', required=True)
    parser.add_argument('--method', required=True)

    args = parser.parse_args()
    image_path = args.image_path
    method = args.method

    solve_local_AT(image_path, method)
