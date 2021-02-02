import Metashape
import time
import argparse
import logging

# 로그 생성
logger = logging.getLogger()

# 로그의 출력 기준 설정
logger.setLevel(logging.INFO)

# log 출력 형식
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(asctime)s %(message)s')

# log 출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# log를 파일에 출력
file_handler = logging.FileHandler('my.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# logger.info("image load add eo import accuracy match align cameras points save process")

# https://www.agisoft.com/forum/index.php?topic=4669.0
def set_region(chunk):
    point_cloud = chunk.point_cloud
    points = point_cloud.points
    projections = point_cloud.projections

    npoints = len(points)
    point_index = 0
    for proj in projections[chunk.cameras[-1]]:
        track_id = proj.track_id
        while point_index < npoints and points[point_index].track_id < track_id:
            point_index += 1
        if point_index < npoints and points[point_index].track_id == track_id:
            if not points[point_index].valid:
                continue
            else:
                points[point_index].selected = True

    point_cloud.cropSelectedPoints()
    chunk.resetRegion()

    return chunk


def photoscan_alignphotos_first(images):
    start_time = time.time()

    images = images.split()
    doc = Metashape.Document()

    add_start = time.time()
    chunk = doc.addChunk()
    chunk.addPhotos(images)
    add_end = time.time() - add_start

    eo_start = time.time()
    for camera in chunk.cameras:
        if not camera.reference.location:
            continue
        if ("DJI/RelativeAltitude" in camera.photo.meta.keys()) and camera.reference.location:
            z = float(camera.photo.meta["DJI/RelativeAltitude"])
            camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)
        gimbal_roll = float(camera.photo.meta["DJI/GimbalRollDegree"])
        if 180 - abs(gimbal_roll) <= 0.1:
            gimbal_roll = 0
        gimbal_pitch = float(camera.photo.meta["DJI/GimbalPitchDegree"])
        gimbal_yaw = float(camera.photo.meta["DJI/GimbalYawDegree"])
        camera.reference.rotation = (gimbal_yaw, 90+gimbal_pitch, gimbal_roll)
        camera.reference.rotation_enabled = True
    eo_end = time.time() - eo_start

    match_start = time.time()
    chunk.matchPhotos(downscale=2, keep_keypoints=True)
    match_end = time.time() - match_start
    print("  *** match time: ", match_end)

    align_start = time.time()
    chunk.alignCameras(adaptive_fitting=True)
    align_end = time.time() - align_start
    print("  *** align time: ", align_end)

    save_start = time.time()
    doc.save(path="./localba.psx", chunks=[doc.chunk])  # in EPSG::4326

    chunk.crs = Metashape.CoordinateSystem("EPSG::5186")
    chunk.euler_angles = Metashape.EulerAnglesOPK
    save_end = time.time() - save_start

    cameras_start = time.time()
    chunk.exportReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, items=Metashape.ReferenceItemsCameras,
                          columns="nuvwdefo", delimiter=",")
    cameras_end = time.time() - cameras_start
    points_start = time.time()
    chunk.exportPoints(path="pointclouds.las", source_data=Metashape.PointCloudData, format=Metashape.PointsFormatLAS,
                       crs=Metashape.CoordinateSystem("EPSG::5186"))
    points_end = time.time() - points_start

    process_end = time.time() - start_time
    print("*************************************************************")
    print("  *** process time of each image = ", process_end)
    print("*************************************************************")

    logger.info(images[-1] + " " + str(0) + " " + str(round(add_end, 5)) + " " + str(round(eo_end, 5))
                + " " + str(0) + " " + str(0) + " " + str(round(match_end, 5)) + " " + str(round(align_end, 5))
                + " " + str(round(cameras_end, 5)) + " " + str(round(points_end, 5)) + " " + str(round(save_end, 5))
                + " " + str(round(process_end, 5)))


def photoscan_alignphotos_rest(images):
    start_time = time.time()

    images = images.split()

    load_start = time.time()
    doc = Metashape.Document()
    doc.open("./localba.psx")
    load_end = time.time() - load_start

    add_start = time.time()
    chunk = doc.chunk
    chunk.addPhotos(images[-1])
    add_end = time.time() - add_start

    eo_start = time.time()
    in_crs = Metashape.CoordinateSystem("EPSG::4326")
    out_crs = Metashape.CoordinateSystem("EPSG::5186")
    chunk.cameras[-1].reference.location = \
        Metashape.CoordinateSystem.transform(point=chunk.cameras[-1].reference.location, source=in_crs, target=out_crs)
    z = float(chunk.cameras[-1].photo.meta["DJI/RelativeAltitude"])
    chunk.cameras[-1].reference.location = (
        chunk.cameras[-1].reference.location.x, chunk.cameras[-1].reference.location.y, z)
    eo_end = time.time() - eo_start

    # doc.save(path="./check.psx", chunks=[doc.chunk])

    import_start = time.time()
    chunk.crs = Metashape.CoordinateSystem("EPSG::5186")
    chunk.euler_angles = Metashape.EulerAnglesOPK
    chunk.importReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, columns="nxyzabco",
                          delimiter=",", skip_rows=2)
    import_end = time.time() - import_start

    accuracy_start = time.time()
    # fist 4 images
    chunk.camera_location_accuracy = Metashape.Vector([0.001, 0.001, 0.001])
    chunk.camera_rotation_accuracy = Metashape.Vector([0.01, 0.01, 0.01])
    # last image
    chunk.cameras[-1].reference.accuracy = Metashape.Vector([10, 10, 10])
    accuarcy_end = time.time() - accuracy_start

    # doc.save(path="./check2.psx", chunks=[doc.chunk])

    # # TODO: ypr to opk
    # gimbal_roll = float(chunk.cameras[-1].photo.meta["DJI/GimbalRollDegree"])
    # gimbal_pitch = float(chunk.cameras[-1].photo.meta["DJI/GimbalPitchDegree"])
    # gimbal_yaw = float(chunk.cameras[-1].photo.meta["DJI/GimbalYawDegree"])
    # chunk.cameras[-1].reference.rotation = (gimbal_yaw, 90 + gimbal_pitch, gimbal_roll)  # ypr

    match_start = time.time()
    chunk.matchPhotos(downscale=2, keep_keypoints=True, reset_matches=False)
    match_end = time.time() - match_start
    print("  *** match time: ", match_end)

    align_start = time.time()
    chunk.alignCameras(adaptive_fitting=True, reset_alignment=False)
    align_end = time.time() - align_start
    print("  *** align time: ", align_end)

    camera = chunk.cameras[-1]
    if not camera.transform:
        print("There is no transformation matrix")
        return

    cameras_start = time.time()
    chunk.exportReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, items=Metashape.ReferenceItemsCameras,
                          columns="nuvwdefo", delimiter=",")
    cameras_end = time.time() - cameras_start
    points_start = time.time()
    chunk = set_region(chunk)
    chunk.exportPoints(path="pointclouds.las", source_data=Metashape.PointCloudData, format=Metashape.PointsFormatLAS,
                       crs=Metashape.CoordinateSystem("EPSG::5186"))
    points_end = time.time() - points_start

    save_start = time.time()
    chunk.crs = Metashape.CoordinateSystem("EPSG::4326")
    doc.save(path="./localba.psx", chunks=[doc.chunk])  # in EPSG::4326
    save_end = time.time() - save_start

    process_end = time.time() - start_time
    print("*************************************************************")
    print("  *** process time of each image = ", process_end)
    print("*************************************************************")

    logger.info(images[-1] + " " + str(round(load_end, 5)) + " " + str(round(add_end, 5))
                + " " + str(round(eo_end, 5)) + " " + str(round(import_end, 5)) + " " + str(round(accuarcy_end, 5))
                + " " + str(round(match_end, 5)) + " " + str(round(align_end, 5)) + " " + str(round(cameras_end, 5))
                + " " + str(round(points_end, 5)) + " " + str(round(save_end, 5)) + " " + str(round(process_end, 5)))


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
