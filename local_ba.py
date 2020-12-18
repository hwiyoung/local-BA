import PhotoScan
import time
import argparse
from module import read_eo


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

    chunk.crs = PhotoScan.CoordinateSystem("EPSG::5186")
    chunk.euler_angles = PhotoScan.EulerAnglesOPK

    # chunk.exportCameras(path="eo.txt", format=PhotoScan.CamerasFormatOPK,
    #                     projection=PhotoScan.CoordinateSystem("EPSG::5186"), use_labels=True)
    chunk.saveReference(path="eo.txt", format=PhotoScan.ReferenceFormatCSV, columns="nuvwdef", delimiter=",")
    chunk.exportPoints(path="pointclouds.las", source=PhotoScan.PointCloudData, format=PhotoScan.PointsFormatLAS,
                       projection=PhotoScan.CoordinateSystem("EPSG::5186"))

    doc.save(path="first.psz", chunks=[doc.chunk])


def photoscan_alignphotos_rest(images):
    start_time = time.time()

    # # Read camera pose
    # EOs = read_eo(eo_file="eo.txt")

    images = images.split()

    doc = PhotoScan.app.document
    chunk = doc.addChunk()
    chunk.addPhotos(images)

    chunk.crs = PhotoScan.CoordinateSystem("EPSG::5186")
    chunk.euler_angles = PhotoScan.EulerAnglesOPK

    # chunk.importCameras(path="eo.txt", format=PhotoScan.CamerasFormatOPK)
    chunk.loadReference(path="eo.txt", format=PhotoScan.ReferenceFormatCSV, columns="nxyzabc",
                        delimiter=",", skip_rows=2)
    chunk.updateTransform()

    in_crs = PhotoScan.CoordinateSystem("EPSG::4326")
    out_crs = PhotoScan.CoordinateSystem("EPSG::5186")
    chunk.cameras[-1].reference.location = \
        PhotoScan.CoordinateSystem.transform(point=chunk.cameras[-1].reference.location, source=in_crs, target=out_crs)
    z = float(chunk.cameras[-1].photo.meta["DJI/RelativeAltitude"])
    chunk.cameras[-1].reference.location = (
        chunk.cameras[-1].reference.location.x, chunk.cameras[-1].reference.location.y, z)

    # fist 4 images
    chunk.camera_location_accuracy = PhotoScan.Vector([0.001, 0.001, 0.001])
    chunk.camera_rotation_accuracy = PhotoScan.Vector([0.01, 0.01, 0.01])
    # last image
    chunk.cameras[-1].reference.accuracy = PhotoScan.Vector([10, 10, 10])

    # # TODO: ypr to opk
    # gimbal_roll = float(chunk.cameras[-1].photo.meta["DJI/GimbalRollDegree"])
    # gimbal_pitch = float(chunk.cameras[-1].photo.meta["DJI/GimbalPitchDegree"])
    # gimbal_yaw = float(chunk.cameras[-1].photo.meta["DJI/GimbalYawDegree"])
    # chunk.cameras[-1].reference.rotation = (gimbal_yaw, 90 + gimbal_pitch, gimbal_roll)  # ypr

    # doc.save(path="rest.psz", chunks=[doc.chunk])

    # TODO: reset_matches, reset_alignment
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

    chunk.saveReference(path="eo.txt", format=PhotoScan.ReferenceFormatCSV, columns="nuvwdef", delimiter=",")
    chunk.exportPoints(path="pointclouds.las", source=PhotoScan.PointCloudData, format=PhotoScan.PointsFormatLAS,
                       projection=PhotoScan.CoordinateSystem("EPSG::5186"))

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
