import Metashape
import time
import numpy as np
from pathlib import Path


def rot_2d(theta):
    # Convert the coordinate system not coordinates
    return np.array([[np.cos(theta), np.sin(theta)],
                     [-np.sin(theta), np.cos(theta)]])


def rpy_to_opk(rpy, maker=""):
    if maker == "samsung":
        roll_pitch = np.empty_like(rpy[0:2])

        roll_pitch[0] = -rpy[1]
        roll_pitch[1] = -rpy[0]

        omega_phi = np.dot(rot_2d(rpy[2] * np.pi / 180), roll_pitch.reshape(2, 1))
        kappa = -rpy[2] - 90
        return np.array([float(omega_phi[0, 0]), float(omega_phi[1, 0]), kappa])
    else:
        roll_pitch = np.empty_like(rpy[0:2])
        roll_pitch[0] = 90 + rpy[1]
        if 180 - abs(rpy[0]) <= 0.1:
            roll_pitch[1] = 0
        else:
            roll_pitch[1] = rpy[0]

        omega_phi = np.dot(rot_2d(rpy[2] * np.pi / 180), roll_pitch.reshape(2, 1))
        kappa = -rpy[2]
        return np.array([float(omega_phi[0, 0]), float(omega_phi[1, 0]), kappa])


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


def solve_direct_georeferencing(images, epsg=5186):
    start_time = time.time()

    # 1. Construct a document
    image = images.split()[-1]
    doc = Metashape.Document()
    chunk = doc.addChunk()

    # 2. Add photos
    chunk.addPhotos(image)

    # 3. Set reference
    camera = chunk.cameras[0]
    if not camera.reference.location:
        return
    if ("DJI/RelativeAltitude" in camera.photo.meta.keys()) and camera.reference.location:
        z = float(camera.photo.meta["DJI/RelativeAltitude"])
        camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)
    gimbal_roll = float(camera.photo.meta["DJI/GimbalRollDegree"])
    if 180 - abs(gimbal_roll) <= 0.1:
        gimbal_roll = 0
    gimbal_pitch = float(camera.photo.meta["DJI/GimbalPitchDegree"])
    gimbal_yaw = float(camera.photo.meta["DJI/GimbalYawDegree"])
    # 3.1. Convert coordinates
    source_crs = chunk.crs
    target_crs = Metashape.CoordinateSystem("EPSG::" + str(epsg))
    pos = Metashape.CoordinateSystem.transform(point=camera.reference.location, source=source_crs, target=target_crs)
    ori = rpy_to_opk(np.array([gimbal_roll, gimbal_pitch, gimbal_yaw]))

    eo = np.array([pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]])

    focal_length = chunk.sensors[0].focal_length / 1000  # unit: m
    pixel_size = chunk.sensors[0].pixel_width / 1000  # unit: m

    process_end = time.time() - start_time
    print("*************************************************************")
    print("  *** process time of each image = ", process_end)
    print("*************************************************************")

    return eo, focal_length, pixel_size, 0


def solve_lba_first(images, epsg=5186, downscale=2):
    start_time = time.time()

    # 1. Construct a document
    images = images.split()
    doc = Metashape.Document()
    chunk = doc.addChunk()

    # 2. Add photos
    add_start = time.time()
    chunk.addPhotos(images)
    add_end = time.time() - add_start

    # 3. Set reference
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
        camera.reference.rotation = (gimbal_yaw, 90 + gimbal_pitch, gimbal_roll)
        camera.reference.rotation_enabled = True
    eo_end = time.time() - eo_start

    # 4. Match photos
    match_start = time.time()
    chunk.matchPhotos(downscale=downscale, keep_keypoints=True)
    match_end = time.time() - match_start
    print("  *** match time: ", match_end)

    # 5. Align cameras
    align_start = time.time()
    chunk.alignCameras(adaptive_fitting=True)
    align_end = time.time() - align_start
    print("  *** align time: ", align_end)

    # 6. Save cameras
    save_start = time.time()
    doc.save(path="./localba.psx", chunks=[doc.chunk])  # EPSG::4326

    camera = chunk.cameras[-1]
    if not camera.transform:
        print("There is no transformation matrix")
        return

    chunk.crs = Metashape.CoordinateSystem("EPSG::" + str(epsg))
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
    chunk.exportPoints(path="pointclouds.las", source_data=Metashape.PointCloudData, format=Metashape.PointsFormatLAS,
                       crs=Metashape.CoordinateSystem("EPSG::" + str(epsg)))
    points_end = time.time() - points_start

    process_end = time.time() - start_time
    print("*************************************************************")
    print("  *** process time of each image = ", process_end)
    print("*************************************************************")

    return eo, focal_length, pixel_size, center_z


def solve_lba_init_uni(images, epsg=5186, downscale=2):
    start_time = time.time()

    # 1. Construct a document
    images = images.split()
    load_start = time.time()
    doc = Metashape.Document()
    doc.open("./localba.psx")   # EPSG::4326
    load_end = time.time() - load_start

    # 2. Add photos
    add_start = time.time()
    chunk = doc.chunk
    chunk.remove(chunk.cameras[0])
    chunk.addPhotos(images[-1])
    add_end = time.time() - add_start

    # 3. Set reference
    eo_start = time.time()
    source_crs = Metashape.CoordinateSystem("EPSG::4326")
    target_crs = Metashape.CoordinateSystem("EPSG::" + str(epsg))
    camera = chunk.cameras[-1]
    # if not camera.reference.location:
    #     continue
    if ("DJI/RelativeAltitude" in camera.photo.meta.keys()) and camera.reference.location:
        z = float(camera.photo.meta["DJI/RelativeAltitude"])
        camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)
        camera.reference.rotation_enabled = True
    # doc.save(path="./check.psx", chunks=[doc.chunk])
    eo_end = time.time() - eo_start

    match_start = time.time()
    chunk.matchPhotos(downscale=downscale, keep_keypoints=True, reset_matches=False)
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
        chunk.crs = source_crs
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
    pos = Metashape.CoordinateSystem.transform(point=pos, source=source_crs, target=target_crs)
    ori = list(estimated_opk)
    eo = np.array([pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]])

    focal_length = chunk.sensors[0].focal_length / 1000  # unit: m
    pixel_size = chunk.sensors[0].pixel_width / 1000  # unit: m
    # Set region for the last image
    set_region(chunk)
    # https://www.agisoft.com/forum/index.php?topic=3848.0
    center_z = list(chunk.crs.project(chunk.transform.matrix.mulp(chunk.region.center)))[-1]

    points_start = time.time()
    chunk = set_region(chunk)
    point_cloud = chunk.point_cloud
    chunk.exportPoints(path="pointclouds.las", source_data=Metashape.PointCloudData, format=Metashape.PointsFormatLAS,
                       crs=target_crs)
    points_end = time.time() - points_start

    save_start = time.time()
    chunk.crs = source_crs
    doc.save(path="./localba.psx", chunks=[doc.chunk])  # in original crs (e.g.: EPSG::4326)
    save_end = time.time() - save_start

    process_end = time.time() - start_time
    print("*************************************************************")
    print("  *** process time of each image = ", process_end)
    print("*************************************************************")

    return eo, focal_length, pixel_size, center_z


def solve_lba_esti_div(images, epsg=5186, downscale=2):
    start_time = time.time()

    # 1. Construct a document
    images = images.split()
    load_start = time.time()
    doc = Metashape.Document()
    doc.open("./localba.psx")
    load_end = time.time() - load_start

    # 2. Add photos
    add_start = time.time()
    chunk = doc.chunk
    chunk.remove(chunk.cameras[0])
    chunk.addPhotos(images[-1])
    add_end = time.time() - add_start

    # 3. Set reference
    eo_start = time.time()
    source_crs = Metashape.CoordinateSystem("EPSG::4326")
    target_crs = Metashape.CoordinateSystem("EPSG::" + str(epsg))
    camera = chunk.cameras[-1]
    camera.reference.location = Metashape.CoordinateSystem.transform(point=camera.reference.location,
                                                                     source=source_crs, target=target_crs)
    z = float(camera.photo.meta["DJI/RelativeAltitude"])
    camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)
    eo_end = time.time() - eo_start

    # doc.save(path="./check.psx", chunks=[doc.chunk])

    import_start = time.time()
    chunk.crs = target_crs
    chunk.euler_angles = Metashape.EulerAnglesOPK
    chunk.importReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, columns="nxyzabco",
                          delimiter=",", skip_rows=2)
    import_end = time.time() - import_start

    accuracy_start = time.time()
    # most recent (n-1) images
    for camera in chunk.cameras[0:-1]:
        camera.reference.location_accuracy = Metashape.Vector([0.001, 0.001, 0.001])
        camera.reference.rotation_accuracy = Metashape.Vector([0.01, 0.01, 0.01])

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
    chunk.matchPhotos(downscale=downscale, keep_keypoints=True, reset_matches=False)
    match_end = time.time() - match_start
    print("  *** match time: ", match_end)

    align_start = time.time()
    chunk.alignCameras(adaptive_fitting=True, reset_alignment=False)
    align_end = time.time() - align_start
    print("  *** align time: ", align_end)

    if not camera.transform:
        print("There is no transformation matrix")
        save_start = time.time()
        chunk.crs = source_crs
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
                       crs=target_crs)
    points_end = time.time() - points_start

    save_start = time.time()
    chunk.crs = source_crs
    doc.save(path="./localba.psx", chunks=[doc.chunk])  # in original crs (e.g.: EPSG::4326)
    save_end = time.time() - save_start

    process_end = time.time() - start_time
    print("*************************************************************")
    print("  *** process time of each image = ", process_end)
    print("*************************************************************")

    return eo, focal_length, pixel_size, center_z


def solve_lba_esti_uni(images, epsg=5186, downscale=2):
    start_time = time.time()

    images = images.split()

    load_start = time.time()
    doc = Metashape.Document()
    doc.open("./localba.psx")   # EPSG::4326
    load_end = time.time() - load_start

    add_start = time.time()
    chunk = doc.chunk
    chunk.remove(chunk.cameras[0])
    chunk.addPhotos(images[-1])
    add_end = time.time() - add_start

    # doc.save(path="./check.psx", chunks=[doc.chunk])

    eo_start = time.time()
    source_crs = Metashape.CoordinateSystem("EPSG::4326")
    target_crs = Metashape.CoordinateSystem("EPSG::" + str(epsg))
    camera = chunk.cameras[-1]
    camera.reference.location = Metashape.CoordinateSystem.transform(point=camera.reference.location,
                                                                     source=source_crs, target=target_crs)
    z = float(camera.photo.meta["DJI/RelativeAltitude"])
    camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)
    eo_end = time.time() - eo_start

    import_start = time.time()
    chunk.crs = target_crs
    chunk.euler_angles = Metashape.EulerAnglesOPK
    chunk.importReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, columns="nxyzabco",
                          delimiter=",", skip_rows=2)   # plane CRS, e.g.) EPSG::5186
    import_end = time.time() - import_start

    # doc.save(path="./check2.psx", chunks=[doc.chunk])

    # # TODO: ypr to opk
    # gimbal_roll = float(chunk.cameras[-1].photo.meta["DJI/GimbalRollDegree"])
    # gimbal_pitch = float(chunk.cameras[-1].photo.meta["DJI/GimbalPitchDegree"])
    # gimbal_yaw = float(chunk.cameras[-1].photo.meta["DJI/GimbalYawDegree"])
    # chunk.cameras[-1].reference.rotation = (gimbal_yaw, 90 + gimbal_pitch, gimbal_roll)  # ypr

    match_start = time.time()
    chunk.matchPhotos(downscale=downscale, keep_keypoints=True, reset_matches=False)
    match_end = time.time() - match_start
    print("  *** match time: ", match_end)

    align_start = time.time()
    chunk.alignCameras(adaptive_fitting=True, reset_alignment=False)
    align_end = time.time() - align_start
    print("  *** align time: ", align_end)

    if not camera.transform:
        print("There is no transformation matrix")
        save_start = time.time()
        chunk.crs = source_crs
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
                       crs=target_crs)
    points_end = time.time() - points_start

    save_start = time.time()
    chunk.crs = source_crs
    doc.save(path="./localba.psx", chunks=[doc.chunk])  # in original crs (e.g.: EPSG::4326)
    save_end = time.time() - save_start

    process_end = time.time() - start_time
    print("*************************************************************")
    print("  *** process time of each image = ", process_end)
    print("*************************************************************")

    return eo, focal_length, pixel_size, center_z


if __name__ == '__main__':
    dir_path = "../00_data/local-BA"
    p_eo = Path(dir_path).glob('*.txt')
    eo_files = [str(x) for x in p_eo if x.is_file()]
    eo_files.sort()
    p_pc = Path(dir_path).glob('*.las')
    pc_files = [str(x) for x in p_pc if x.is_file()]
    pc_files.sort()
