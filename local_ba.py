import PhotoScan
import time
import argparse
# from module import read_eo_list


def read_eo_list(eo_file):
    print("=====================================")
    print(" * Read EOs, list type from a file")
    print("=====================================")

    f = open(eo_file, 'r')
    next(f)
    next(f)
    lines = f.readlines()
    f.close()

    EOs = []
    for i in range(len(lines)):
        params = lines[i].split("\t")
        x = float(params[1])  # m
        y = float(params[2])  # m
        z = float(params[3])  # m
        o = float(params[4])  # deg
        p = float(params[5])  # deg
        k = float(params[6])  # deg
        EOs.append([x, y, z, o, p, k])

    return EOs


def photoscan_alignphotos_first(images):
    start_time = time.time()

    images = images.split()
    doc = PhotoScan.app.document
    chunk = doc.addChunk()
    chunk.addPhotos(images)
    for camera in chunk.cameras:
        if not camera.reference.location:
            continue
        if ("DJI/RelativeAltitude" in camera.photo.meta.keys()) and camera.reference.location:
            z = float(camera.photo.meta["DJI/RelativeAltitude"])
            camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)
        gimbal_roll = float(camera.photo.meta["DJI/GimbalRollDegree"])
        gimbal_pitch = float(camera.photo.meta["DJI/GimbalPitchDegree"])
        gimbal_yaw = float(camera.photo.meta["DJI/GimbalYawDegree"])
        camera.reference.rotation = (gimbal_yaw, 90+gimbal_pitch, gimbal_roll)

        # print(camera.reference.location, camera.reference.rotation)
        # print(doc.chunk.sensors[0])
        # print(doc.chunk.sensors[0].focal_length)
        # print(doc.chunk.sensors[0].width, doc.chunk.sensors[0].height)
        # print(doc.chunk.sensors[0].pixel_width, doc.chunk.sensors[0].pixel_height)
        # print(doc.chunk.sensors[0].pixel_size)

    chunk.matchPhotos(accuracy=PhotoScan.MediumAccuracy)
    chunk.alignCameras()

    camera = chunk.cameras[-1]
    if not camera.transform:
        print("There is no transformation matrix")

    estimated_coord = chunk.crs.project(
        chunk.transform.matrix.mulp(camera.center)) #estimated XYZ in coordinate system units
    T = chunk.transform.matrix
    m = chunk.crs.localframe(
        T.mulp(camera.center))  # transformation matrix to the LSE coordinates in the given point
    R = (m * T * camera.transform * PhotoScan.Matrix().Diag([1, -1, -1, 1])).rotation()

    estimated_ypr = PhotoScan.utils.mat2ypr(R)  # estimated orientation angles - yaw, pitch, roll
    estimated_opk = PhotoScan.utils.mat2opk(R)  # estimated orientation angles - omega, phi, kappa

    pos = list(estimated_coord)
    ori = list(estimated_opk)
    eo = [pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]]
    print("======================================================================================================")
    print(images[-1], eo)
    print("======================================================================================================")

    print("  *** process time of each image = ", time.time() - start_time)

    # chunk.exportCameras(path="eo.txt", format=PhotoScan.CamerasFormatOPK, projection=PhotoScan.CoordinateSystem("EPSG::5186"))
    # chunk.exportPoints(path="pointclouds.las", source=PhotoScan.PointCloudData, format=PhotoScan.PointsFormatLAS, projection=PhotoScan.CoordinateSystem("EPSG::5186"))
    chunk.exportCameras(path="eo.txt", format=PhotoScan.CamerasFormatOPK,
                        projection=PhotoScan.CoordinateSystem("EPSG::4326"))
    chunk.exportPoints(path="pointclouds.las", source=PhotoScan.PointCloudData, format=PhotoScan.PointsFormatLAS,
                       projection=PhotoScan.CoordinateSystem("EPSG::4326"))

    doc.save(path="first.psz", chunks=[doc.chunk])


def photoscan_alignphotos_rest(images):
    start_time = time.time()

    # Import camera pose
    EOs = read_eo_list(eo_file="eo.txt")

    images = images.split()
    doc = PhotoScan.app.document
    chunk = doc.addChunk()
    chunk.addPhotos(images)
    chunk.importCameras(path="eo.txt", format=PhotoScan.CamerasFormatOPK)
    # for i in range(len(chunk.cameras)):
    #     if not chunk.cameras[i].reference.location:
    #         continue
    #     if i < 4:
    #         chunk.cameras[i].reference.location = (EOs[i][0], EOs[i][1], EOs[i][2])
    #         chunk.cameras[i].reference.rotation = (EOs[i][3], EOs[i][4], EOs[i][5])     # opk
    #     else:
    #         z = float(chunk.cameras[i].photo.meta["DJI/RelativeAltitude"])
    #         chunk.cameras[i].reference.location = (chunk.cameras[i].reference.location.x, chunk.cameras[i].reference.location.y, z)
    #         # gimbal_roll = float(chunk.cameras[i].photo.meta["DJI/GimbalRollDegree"])
    #         # gimbal_pitch = float(chunk.cameras[i].photo.meta["DJI/GimbalPitchDegree"])
    #         # gimbal_yaw = float(chunk.cameras[i].photo.meta["DJI/GimbalYawDegree"])
    #         # chunk.cameras[i].reference.rotation = (gimbal_yaw, 90 + gimbal_pitch, gimbal_roll)  # ypr
    #
    # # fist 4 images
    # chunk.camera_location_accuracy = PhotoScan.Vector([0.001, 0.001, 0.001])
    # chunk.camera_rotation_accuracy = PhotoScan.Vector([0.01, 0.01, 0.01])
    # # las 1 image
    # chunk.cameras[-1].reference.accuracy = PhotoScan.Vector([10, 10, 10])

    doc.save(path="rest.psz", chunks=[doc.chunk])

    chunk.matchPhotos(accuracy=PhotoScan.MediumAccuracy)
    chunk.alignCameras()

    camera = chunk.cameras[-1]
    if not camera.transform:
        print("There is no transformation matrix")

    estimated_coord = chunk.crs.project(
        chunk.transform.matrix.mulp(camera.center)) #estimated XYZ in coordinate system units
    T = chunk.transform.matrix
    m = chunk.crs.localframe(
        T.mulp(camera.center))  # transformation matrix to the LSE coordinates in the given point
    R = (m * T * camera.transform * PhotoScan.Matrix().Diag([1, -1, -1, 1])).rotation()

    estimated_ypr = PhotoScan.utils.mat2ypr(R)  # estimated orientation angles - yaw, pitch, roll
    estimated_opk = PhotoScan.utils.mat2opk(R)  # estimated orientation angles - omega, phi, kappa

    pos = list(estimated_coord)
    ori = list(estimated_opk)
    eo = [pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]]
    print("======================================================================================================")
    print(images[-1], eo)
    print("======================================================================================================")

    print("  *** process time of each image = ", time.time() - start_time)

    chunk.exportCameras(path="eo.txt", format=PhotoScan.CamerasFormatOPK, projection=PhotoScan.CoordinateSystem("EPSG::5186"))
    chunk.exportPoints(path="pointclouds.las", source=PhotoScan.PointCloudData, format=PhotoScan.PointsFormatLAS, projection=PhotoScan.CoordinateSystem("EPSG::5186"))

    doc.save(path="rest.psz", chunks=[doc.chunk])


if __name__ == '__main__':
    # Set argument parser
    parser = argparse.ArgumentParser(description='LBA-photoscan')
    parser.add_argument('--images', required=True)
    parser.add_argument('--method', required=True)

    args = parser.parse_args()
    images = args.images
    method = args.method

    if method == "first":
        photoscan_alignphotos_first(images)
    elif method == "rest":
        photoscan_alignphotos_rest(images)
    else:
        print("=========================================")
        print(" *** Please choose between first and rest")
        print("=========================================")
