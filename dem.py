import laspy
import CSF
import numpy as np
from scipy.interpolate import griddata
import time


def cloth_simulation_filtering(xyz, bSloopSmooth=False, cloth_resolution=0.5):
    csf = CSF.CSF()

    # prameter settings
    csf.params.bSloopSmooth = bSloopSmooth
    csf.params.cloth_resolution = cloth_resolution
    # more details about parameter: http://ramm.bnu.edu.cn/projects/CSF/download/

    csf.setPointCloud(xyz)
    ground = CSF.VecInt()  # a list to indicate the index of ground points after calculation
    non_ground = CSF.VecInt()  # a list to indicate the index of non-ground points after calculation
    csf.do_filtering(ground, non_ground)  # do actual filtering.

    filtered_xyz = xyz[ground]  # extract ground points

    return filtered_xyz, ground


def interpolate_dem(xyz, gsd, method='linear'):
    X_min = np.min(xyz[:, 0])
    X_max = np.max(xyz[:, 0])
    Y_min = np.min(xyz[:, 1])
    Y_max = np.max(xyz[:, 1])

    # grid_x, grid_y = np.mgrid[X_min:X_max:gsd, Y_max:Y_min:-gsd]
    grid_y, grid_x = np.mgrid[Y_max:Y_min:-gsd, X_min:X_max:gsd]
    grid_z = griddata(xyz[:, 0:2], xyz[:, 2], (grid_x, grid_y), method=method)

    bbox = np.array([X_min, X_max, Y_min, Y_max])

    return grid_x, grid_y, grid_z, bbox


def generate_dem(point_clouds, gsd):
    start = time.time()
    # 1. Import point clouds
    inFile = laspy.file.File(point_clouds, mode='r')  # read a las file
    points = inFile.points
    xyz = np.vstack((inFile.x, inFile.y, inFile.z)).transpose()  # extract x, y, z and put into a list
    print("No. raw points:", len(xyz))

    # 2. Denoising

    # 3. Ground filtering
    csf_start = time.time()
    filtered_xyz, ground = cloth_simulation_filtering(xyz)
    print("No. filtered points:", len(filtered_xyz))
    print(f"Ground filetering: {time.time() - csf_start:.2f} sec")

    outFile = laspy.file.File(r"ground.las", mode='w', header=inFile.header)
    outFile.points = points[ground]  # extract ground points, and save it to a las file.
    outFile.close()  # do not forget this

    # 4. Interpolation
    interpolation_start = time.time()
    grid_x, grid_y, grid_z, bbox = interpolate_dem(filtered_xyz, gsd)
    print(f"Interpolation: {time.time() - interpolation_start:.2f} sec")
    print(f"Elpased time: {time.time() - start:.2f} sec")

    # import matplotlib.pyplot as plt
    # plt.imshow(grid_z)
    # plt.show()

    return grid_x, grid_y, grid_z, bbox

if __name__ == "__main__":
    generate_dem("pointclouds.las", 0.03)
