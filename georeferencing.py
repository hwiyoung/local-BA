import Metashape
import time
import numpy as np


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

# TODO: downscale in matchPhotos, epsg to export
def solve_local_ba_first(images):
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

    camera = chunk.cameras[-1]
    if not camera.transform:
        print("There is no transformation matrix")
        return

    chunk.crs = Metashape.CoordinateSystem("EPSG::5186")
    chunk.euler_angles = Metashape.EulerAnglesOPK
    save_end = time.time() - save_start

    T = chunk.transform.matrix
    estimated_coord = chunk.crs.project(
        T.mulp(camera.center))  # estimated XYZ in coordinate system units
    m = chunk.crs.localframe(
        T.mulp(camera.center))  # transformation matrix to the LSE coordinates in the given point
    R = (m * T * camera.transform * Metashape.Matrix().Diag([1, -1, -1, 1])).rotation()

    estimated_ypr = Metashape.utils.mat2ypr(R)  # estimated orientation angles - yaw, pitch, roll
    estimated_opk = Metashape.utils.mat2opk(R)  # estimated orientation angles - omega, phi, kappa

    pos = list(estimated_coord)
    ori = list(estimated_opk)
    eo = np.array([pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]])

    focal_length = chunk.sensors[0].focal_length / 1000 # unit: m
    pixel_size = chunk.sensors[0].pixel_width / 1000    # unit: m
    # Set region for the last image
    set_region(chunk)
    # https://www.agisoft.com/forum/index.php?topic=3848.0
    center_z = list(chunk.crs.project(chunk.transform.matrix.mulp(chunk.region.center)))[-1]

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

    return eo, focal_length, pixel_size, center_z



# TODO: An option whether removing images except not included in processing or not
def solve_local_ba_rest(images):
    start_time = time.time()

    images = images.split()

    load_start = time.time()
    doc = Metashape.Document()
    doc.open("./localba.psx")
    load_end = time.time() - load_start

    add_start = time.time()
    chunk = doc.chunk
    chunk.remove(chunk.cameras[:-4])
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
    # chunk.camera_location_accuracy = Metashape.Vector([0.001, 0.001, 0.001])
    chunk.camera_rotation_accuracy = Metashape.Vector([0.01, 0.01, 0.01])
    chunk.cameras[0].reference.accuracy = Metashape.Vector([0.001, 0.001, 0.001])
    chunk.cameras[1].reference.accuracy = Metashape.Vector([0.001, 0.001, 0.001])
    chunk.cameras[2].reference.accuracy = Metashape.Vector([0.001, 0.001, 0.001])
    chunk.cameras[3].reference.accuracy = Metashape.Vector([0.001, 0.001, 0.001])

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
        save_start = time.time()
        chunk.crs = Metashape.CoordinateSystem("EPSG::4326")
        doc.save(path="./localba.psx", chunks=[doc.chunk])  # in EPSG::4326
        save_end = time.time() - save_start
        return

    T = chunk.transform.matrix
    estimated_coord = chunk.crs.project(
        T.mulp(camera.center))  # estimated XYZ in coordinate system units
    m = chunk.crs.localframe(
        T.mulp(camera.center))  # transformation matrix to the LSE coordinates in the given point
    R = (m * T * camera.transform * Metashape.Matrix().Diag([1, -1, -1, 1])).rotation()

    estimated_ypr = Metashape.utils.mat2ypr(R)  # estimated orientation angles - yaw, pitch, roll
    estimated_opk = Metashape.utils.mat2opk(R)  # estimated orientation angles - omega, phi, kappa

    pos = list(estimated_coord)
    ori = list(estimated_opk)
    eo = np.array([pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]])

    focal_length = chunk.sensors[0].focal_length / 1000  # unit: m
    pixel_size = chunk.sensors[0].pixel_width / 1000  # unit: m
    # Set region for the last image
    set_region(chunk)
    # https://www.agisoft.com/forum/index.php?topic=3848.0
    center_z = list(chunk.crs.project(chunk.transform.matrix.mulp(chunk.region.center)))[-1]

    cameras_start = time.time()
    chunk.exportReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, items=Metashape.ReferenceItemsCameras,
                          columns="nuvwdefo", delimiter=",")
    cameras_end = time.time() - cameras_start
    points_start = time.time()
    chunk = set_region(chunk)
    point_cloud = chunk.point_cloud
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

    return eo, focal_length, pixel_size, center_z


def georeferencing(images_to_process, no_images_to_process, ith):
    if ith < no_images_to_process - 1:
        # eo, focal_length, pixel_size, center_z = solve_direct_georeferencing(images_to_process)
        return 0, 0, 0, 0
    elif ith == no_images_to_process - 1:
        eo, focal_length, pixel_size, center_z = solve_local_ba_first(images_to_process)
        return eo, focal_length, pixel_size, center_z
    else:
        eo, focal_length, pixel_size, center_z = solve_local_ba_rest(images_to_process)
        return eo, focal_length, pixel_size, center_z
