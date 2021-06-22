from georeferencing import solve_direct_georeferencing, solve_lba_first, solve_lba_esti_div, solve_lba_init_uni, solve_lba_esti_uni
from dem import boundary, generate_dem
from module import Rot3D, las2nparray, nparray2las
from rectification import *

from rich.console import Console
import time

console = Console()


def orthophoto_dg(image_path, epsg=5186, gsd=0, ground_height=0):
    ######################
    ### Georeferencing ###
    ######################
    ### 1. Georeferencing
    georef_start = time.time()
    eo, focal_length, pixel_size, center_z = solve_direct_georeferencing(image_path, epsg)

    R = Rot3D(eo * np.pi / 180)
    if gsd == 0:
        gsd = (pixel_size * (eo[2] - ground_height)) / focal_length  # unit: m/px
    console.print(f"EOP: {eo[0]:.2f} | {eo[1]:.2f} | {eo[2]:.2f} | {eo[3]:.2f} | {eo[4]:.2f} | {eo[5]:.2f}\n"
                  f"Focal Length: {focal_length * 1000:.2f} mm, Pixel Size: {pixel_size * 1000000:.2f} um/px,"
                  f" Z of center: {center_z:.2f} m, GSD: {gsd * 100:.2f} cm/px",
                  style="blink bold red underline")

    georef_time = time.time() - georef_start
    console.print(f"Georeferencing time: {georef_time:.2f} sec", style="blink bold red underline")

    ###############
    ### Mapping ###
    ###############
    ### 2. Extract boundary
    dem_start = time.time()
    image = cv2.imread(image_path, -1)
    bbox = boundary(image, eo, R, ground_height, pixel_size, focal_length)
    dem_time = time.time() - dem_start
    console.print(f"DEM time: {dem_time:.2f} sec", style="blink bold red underline")

    ### 3. Geodata generation
    rectify_start = time.time()
    boundary_cols = int((bbox[1, 0] - bbox[0, 0]) / gsd)
    boundary_rows = int((bbox[3, 0] - bbox[2, 0]) / gsd)
    b, g, r, a = rectify_plane_parallel(bbox, boundary_rows, boundary_cols, gsd, eo, ground_height,
                                        R, focal_length, pixel_size, image)
    bbox = bbox.ravel()  # for generating orthophoto
    rectify_time = time.time() - rectify_start
    console.print(f"Rectify time: {rectify_time:.2f} sec", style="blink bold red underline")

    times = np.array([georef_time, dem_time, rectify_time])

    return b, g, r, a, bbox, times


def orthophoto_lba(image_path, flag, types, matching_accuracy=2, diff_init_esti=10, epsg=5186, gsd=0):
    ######################
    ### Georeferencing ###
    ######################
    ### 1. Georeferencing
    georef_start = time.time()
    if not flag:        # solve_lba_first
        console.print(f"solve_lba_first", style="blink bold red underline")
        eo, focal_length, pixel_size, center_z = solve_lba_first(image_path,    # multiple images
                                                                 epsg, matching_accuracy, diff_init_esti)
    elif flag and types == "fixed":        # solve_lba_esti_div
        console.print(f"solve_lba_esti_div", style="blink bold red underline")
        eo, focal_length, pixel_size, center_z = solve_lba_esti_div(image_path, epsg, matching_accuracy)
    elif flag and types == "nonfixed-initial":        # solve_lba_init_uni
        console.print(f"solve_lba_init_uni", style="blink bold red underline")
        eo, focal_length, pixel_size, center_z = solve_lba_init_uni(image_path, epsg, matching_accuracy)
    elif flag and types == "nonfixed-estimated":        # solve_lba_esti_uni
        console.print(f"solve_lba_esti_uni", style="blink bold red underline")
        eo, focal_length, pixel_size, center_z = solve_lba_esti_uni(image_path, # one image
                                                                    epsg, matching_accuracy, diff_init_esti)
    else:
        console.print(f"Which type of processing you have?", style="blink bold red underline")
        return

    R = Rot3D(eo * np.pi / 180)
    if gsd == 0:
        gsd = (pixel_size * (eo[2] - center_z)) / focal_length  # unit: m/px
    console.print(f"EOP: {eo[0]:.2f} | {eo[1]:.2f} | {eo[2]:.2f} | {eo[3]:.2f} | {eo[4]:.2f} | {eo[5]:.2f}\n"
                  f"Focal Length: {focal_length * 1000:.2f} mm, Pixel Size: {pixel_size * 1000000:.2f} um/px,"
                  f" Z of center: {center_z:.2f} m, GSD: {gsd * 100:.2f} cm/px",
                  style="blink bold red underline")

    georef_time = time.time() - georef_start
    console.print(f"Georeferencing time: {georef_time:.2f} sec", style="blink bold red underline")

    ###############
    ### Mapping ###
    ###############
    ### 2. DEM processing
    dem_start = time.time()
    dem_x, dem_y, dem_z, bbox = generate_dem("pointclouds.pcd", gsd)
    dem_time = time.time() - dem_start
    console.print(f"DEM time: {dem_time:.2f} sec", style="blink bold red underline")

    ### 3. Geodata generation
    rectify_start = time.time()
    boundary_rows = dem_x.shape[0]
    boundary_cols = dem_x.shape[1]
    image = cv2.imread(image_path.split()[-1], -1)
    b, g, r, a = rectify_dem_parallel(dem_x, dem_y, dem_z, boundary_rows, boundary_cols,
                                      eo, R, focal_length, pixel_size, image)
    rectify_time = time.time() - rectify_start
    console.print(f"Rectify time: {rectify_time:.2f} sec", style="blink bold red underline")

    flag = True
    times = np.array([georef_time, dem_time, rectify_time])

    return b, g, r, a, bbox, times, flag

    # # Import las to numpy array
    # points, colors = las2nparray(file_path="pointclouds.las")
    # points_stack = np.vstack((points_stack, points))
    # colors_stack = np.vstack((colors_stack, colors))
    # nparray2las(points_stack, colors_stack)