import Metashape
import time
import argparse


def photoscan_alignphotos_first(images):
    start_time = time.time()

    images = images.split()
    doc = Metashape.Document()
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
        camera.reference.rotation_enabled = True

    match_time = time.time()
    chunk.matchPhotos(downscale=2)
    print("  *** match time: ", time.time() - match_time)
    align_time = time.time()
    chunk.alignCameras(adaptive_fitting=True)
    print("  *** align time: ", time.time() - align_time)

    print("*************************************************************")
    print("  *** process time of each image = ", time.time() - start_time)
    print("*************************************************************")

    chunk.crs = Metashape.CoordinateSystem("EPSG::5186")
    chunk.euler_angles = Metashape.EulerAnglesOPK

    chunk.exportReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, items=Metashape.ReferenceItemsCameras,
                          columns="nuvwdefo", delimiter=",")
    chunk.exportPoints(path="pointclouds.las", source_data=Metashape.PointCloudData, format=Metashape.PointsFormatLAS,
                       crs=Metashape.CoordinateSystem("EPSG::5186"))

    doc.save(path="first.psz", chunks=[doc.chunk])


def photoscan_alignphotos_rest(images):
    start_time = time.time()

    images = images.split()

    doc = Metashape.Document()
    chunk = doc.addChunk()
    chunk.addPhotos(images)

    chunk.crs = Metashape.CoordinateSystem("EPSG::5186")
    chunk.euler_angles = Metashape.EulerAnglesOPK

    chunk.importReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, columns="nxyzabco",
                          delimiter=",", skip_rows=2)
    # chunk.updateTransform()

    in_crs = Metashape.CoordinateSystem("EPSG::4326")
    out_crs = Metashape.CoordinateSystem("EPSG::5186")
    chunk.cameras[-1].reference.location = \
        Metashape.CoordinateSystem.transform(point=chunk.cameras[-1].reference.location, source=in_crs, target=out_crs)
    z = float(chunk.cameras[-1].photo.meta["DJI/RelativeAltitude"])
    chunk.cameras[-1].reference.location = (
        chunk.cameras[-1].reference.location.x, chunk.cameras[-1].reference.location.y, z)

    # fist 4 images
    chunk.camera_location_accuracy = Metashape.Vector([0.001, 0.001, 0.001])
    chunk.camera_rotation_accuracy = Metashape.Vector([0.01, 0.01, 0.01])
    # last image
    chunk.cameras[-1].reference.accuracy = Metashape.Vector([10, 10, 10])

    # doc.save(path="rest3.psz", chunks=[doc.chunk])

    # # TODO: ypr to opk
    # gimbal_roll = float(chunk.cameras[-1].photo.meta["DJI/GimbalRollDegree"])
    # gimbal_pitch = float(chunk.cameras[-1].photo.meta["DJI/GimbalPitchDegree"])
    # gimbal_yaw = float(chunk.cameras[-1].photo.meta["DJI/GimbalYawDegree"])
    # chunk.cameras[-1].reference.rotation = (gimbal_yaw, 90 + gimbal_pitch, gimbal_roll)  # ypr

    # doc.save(path="rest.psz", chunks=[doc.chunk])

    # TODO: reset_matches, reset_alignment
    chunk.matchPhotos(downscale=2)
    chunk.alignCameras(adaptive_fitting=True)

    camera = chunk.cameras[-1]
    if not camera.transform:
        print("There is no transformation matrix")
        return

    estimated_coord = chunk.crs.project(
        chunk.transform.matrix.mulp(camera.center)) #estimated XYZ in coordinate system units
    T = chunk.transform.matrix
    m = chunk.crs.localframe(
        T.mulp(camera.center))  # transformation matrix to the LSE coordinates in the given point
    R = (m * T * camera.transform * Metashape.Matrix().Diag([1, -1, -1, 1])).rotation()

    estimated_ypr = Metashape.utils.mat2ypr(R)  # estimated orientation angles - yaw, pitch, roll
    estimated_opk = Metashape.utils.mat2opk(R)  # estimated orientation angles - omega, phi, kappa

    pos = list(estimated_coord)
    ori = list(estimated_opk)
    eo = [pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]]
    print("======================================================================================================")
    print(images[-1], eo)
    print("======================================================================================================")

    print("  *** process time of each image = ", time.time() - start_time)

    chunk.exportReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, items=Metashape.ReferenceItemsCameras,
                          columns="nuvwdefo", delimiter=",")
    chunk.exportPoints(path="pointclouds.las", source_data=Metashape.PointCloudData, format=Metashape.PointsFormatLAS,
                       crs=Metashape.CoordinateSystem("EPSG::5186"))

    doc.save(path="rest.psz", chunks=[doc.chunk])


if __name__ == '__main__':
    # Set argument parser
    parser = argparse.ArgumentParser(description='LBA-metashape')
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
