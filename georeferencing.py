import Metashape
import time
import numpy as np
from pathlib import Path
import math


# https://github.com/agisoft-llc/metashape-scripts/blob/master/src/save_estimated_reference.py
class CameraStats():
    def __init__(self, camera):
        chunk = camera.chunk

        self.camera = camera
        self.estimated_location = None
        self.estimated_rotation = None
        self.reference_location = None
        self.reference_rotation = None
        self.error_location = None
        self.error_rotation = None
        self.sigma_location = None
        self.sigma_rotation = None

        if not camera.transform:
            return

        transform = chunk.transform.matrix
        crs = chunk.crs

        if chunk.camera_crs:
            transform = self.getDatumTransform(crs, chunk.camera_crs) * transform
            crs = chunk.camera_crs

        ecef_crs = self.getCartesianCrs(crs)

        camera_transform = transform * camera.transform
        antenna_transform = self.getAntennaTransform(camera.sensor)
        location_ecef = camera_transform.translation() + camera_transform.rotation() * antenna_transform.translation()
        rotation_ecef = camera_transform.rotation() * antenna_transform.rotation()

        self.estimated_location = Metashape.CoordinateSystem.transform(location_ecef, ecef_crs, crs)
        if camera.reference.location:
            self.reference_location = camera.reference.location
            self.error_location = Metashape.CoordinateSystem.transform(self.estimated_location, crs, ecef_crs) - Metashape.CoordinateSystem.transform(self.reference_location, crs, ecef_crs)
            self.error_location = crs.localframe(location_ecef).rotation() * self.error_location

        if chunk.euler_angles == Metashape.EulerAnglesOPK or chunk.euler_angles == Metashape.EulerAnglesPOK:
            localframe = crs.localframe(location_ecef)
        else:
            localframe = ecef_crs.localframe(location_ecef)

        self.estimated_rotation = Metashape.utils.mat2euler(localframe.rotation() * rotation_ecef, chunk.euler_angles)
        if camera.reference.rotation:
            self.reference_rotation = camera.reference.rotation
            self.error_rotation = self.estimated_rotation - self.reference_rotation
            self.error_rotation.x = (self.error_rotation.x + 180) % 360 - 180
            self.error_rotation.y = (self.error_rotation.y + 180) % 360 - 180
            self.error_rotation.z = (self.error_rotation.z + 180) % 360 - 180

        if camera.location_covariance:
            T = crs.localframe(location_ecef) * transform
            R = T.rotation() * T.scale()

            cov = R * camera.location_covariance * R.t()
            self.sigma_location = Metashape.Vector([math.sqrt(cov[0, 0]), math.sqrt(cov[1, 1]), math.sqrt(cov[2, 2])])

        if camera.rotation_covariance:
            T = crs.localframe(location_ecef) * camera_transform
            R0 = T.rotation()

            dR = antenna_transform.rotation()

            da = Metashape.utils.dmat2euler(R0 * dR, R0 * self.makeRotationDx(0) * dR, chunk.euler_angles);
            db = Metashape.utils.dmat2euler(R0 * dR, R0 * self.makeRotationDy(0) * dR, chunk.euler_angles);
            dc = Metashape.utils.dmat2euler(R0 * dR, R0 * self.makeRotationDz(0) * dR, chunk.euler_angles);

            R = Metashape.Matrix([da, db, dc]).t()

            cov = R * camera.rotation_covariance * R.t()

            self.sigma_rotation = Metashape.Vector([math.sqrt(cov[0, 0]), math.sqrt(cov[1, 1]), math.sqrt(cov[2, 2])])

    def getCartesianCrs(self, crs):
        ecef_crs = crs.geoccs
        if ecef_crs is None:
            ecef_crs = Metashape.CoordinateSystem('LOCAL')
        return ecef_crs

    def getDatumTransform(self, src, dst):
        return Metashape.CoordinateSystem.transformationMatrix(Metashape.Vector((0, 0, 0)), self.getCartesianCrs(src), self.getCartesianCrs(dst))

    def getAntennaTransform(self, sensor):
        location = sensor.antenna.location
        if location is None:
            location = sensor.antenna.location_ref
        rotation = sensor.antenna.rotation
        if rotation is None:
            rotation = sensor.antenna.rotation_ref
        return Metashape.Matrix.Diag((1, -1, -1, 1)) * Metashape.Matrix.Translation(location) * Metashape.Matrix.Rotation(Metashape.Utils.ypr2mat(rotation))

    def makeRotationDx(self, alpha):
        sina = math.sin(alpha)
        cosa = math.cos(alpha)
        return Metashape.Matrix([[0, 0, 0], [0, -sina, -cosa], [0, cosa, -sina]])

    def makeRotationDy(self, alpha):
        sina = math.sin(alpha)
        cosa = math.cos(alpha)
        return Metashape.Matrix([[-sina, 0, cosa], [0, 0, 0], [-cosa, 0, -sina]])

    def makeRotationDz(self, alpha):
        sina = math.sin(alpha)
        cosa = math.cos(alpha)
        return Metashape.Matrix([[-sina, -cosa, 0], [cosa, -sina, 0], [0, 0, 0]])

    def getEulerAnglesName(self, euler_angles):
        if euler_angles == Metashape.EulerAnglesOPK:
            return "OPK"
        if euler_angles == Metashape.EulerAnglesPOK:
            return "POK"
        if euler_angles == Metashape.EulerAnglesYPR:
            return "YPR"
        if euler_angles == Metashape.EulerAnglesANK:
            return "ANK"

    def printVector(self, f, name, value, precision):
        fmt = "{:." + str(precision) + "f}"
        fmt = "    " + name + ": " + fmt + " " + fmt + " " + fmt + "\n"
        f.write(fmt.format(value.x, value.y, value.z))

    def write(self, f):
        euler_name = self.getEulerAnglesName(self.camera.chunk.euler_angles)

        f.write(self.camera.label + "\n")
        if self.reference_location:
            self.printVector(f, "   XYZ source", self.reference_location, 6)
        if self.error_location:
            self.printVector(f, "   XYZ error", self.error_location, 6)
        if self.estimated_location:
            self.printVector(f, "   XYZ estimated", self.estimated_location, 6)
        if self.sigma_location:
            self.printVector(f, "   XYZ sigma", self.sigma_location, 6)
        if self.reference_rotation:
            self.printVector(f, "   " + euler_name + " source", self.reference_rotation, 3)
        if self.error_rotation:
            self.printVector(f, "   " + euler_name + " error", self.error_rotation, 3)
        if self.estimated_rotation:
            self.printVector(f, "   " + euler_name + " estimated", self.estimated_rotation, 3)
        if self.sigma_rotation:
            self.printVector(f, "   " + euler_name + " sigma", self.sigma_rotation, 3)


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


def solve_direct_georeferencing(image, epsg=5186):
    start_time = time.time()

    # 1. Construct a document
    # image = images.split()[-1]
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


def solve_lba_first(images, epsg=5186, downscale=2, diff_init_esti=10, output_path="."):
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
    source_crs = Metashape.CoordinateSystem("EPSG::4326")
    target_crs = Metashape.CoordinateSystem("EPSG::" + str(epsg))

    chunk.euler_angles = Metashape.EulerAnglesOPK   # transform to destination angles(from YPR to OPK)
    for camera in chunk.cameras:
        if not camera.reference.location:
            continue
        # position
        if ("DJI/RelativeAltitude" in camera.photo.meta.keys()) and camera.reference.location:
            z = float(camera.photo.meta["DJI/RelativeAltitude"])
            camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)

        # orientation
        gimbal_roll = float(camera.photo.meta["DJI/GimbalRollDegree"])
        if 180 - abs(gimbal_roll) <= 0.1:
            gimbal_roll = 0
        gimbal_pitch = float(camera.photo.meta["DJI/GimbalPitchDegree"])
        gimbal_yaw = float(camera.photo.meta["DJI/GimbalYawDegree"])

        ori = rpy_to_opk(np.array([gimbal_roll, gimbal_pitch, gimbal_yaw]))
        camera.reference.rotation = ori
        camera.reference.rotation_enabled = True

    chunk.crs = target_crs  # transform to destination crs(from source(4326) to target(epsg))
    for camera in chunk.cameras:
        if not camera.reference.location:
            continue
        else:
            camera.reference.location = Metashape.CoordinateSystem.transform(point=camera.reference.location,
                                                                             source=source_crs, target=target_crs)
    eo_end = time.time() - eo_start

    # doc.save(path="./check.psx", chunks=[doc.chunk])  # EPSG::(epsg), OPK

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
    doc.save(path="./localba.psx", chunks=[doc.chunk])  # EPSG::(epsg), OPK

    camera = chunk.cameras[-1]
    stats = CameraStats(camera)
    error_location = np.sqrt(np.sum(np.square(stats.error_location), axis=0))  # RMS of location, m
    save_end = time.time() - save_start

    if not camera.transform or error_location > diff_init_esti:
        print(f" *** Not processed: {not camera.transform} or Wrong processed: {error_location:.2f} m")
        return

    estimated_coord = stats.estimated_location
    estimated_opk = stats.estimated_rotation

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
                          columns="nuvwdefoUVWDEFpqrijk", delimiter=",")
    chunk.exportReference(path=str(Path(output_path) / str("eo_" + images[-1].split("/")[-1].split(".")[0] + ".txt")),
                          format=Metashape.ReferenceFormatCSV, items=Metashape.ReferenceItemsCameras,
                          columns="nuvwdefoUVWDEFpqrijk", delimiter=",")
    cameras_end = time.time() - cameras_start
    points_start = time.time()
    chunk.exportPoints(path="./pointclouds.pcd", source_data=Metashape.PointCloudData,
                       format=Metashape.PointsFormatPCD, crs=Metashape.CoordinateSystem("EPSG::" + str(epsg)))
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


def solve_lba_esti_uni(images, epsg=5186, downscale=2, diff_init_esti=10, output_path="."):
    start_time = time.time()

    # 1. Construct a document
    images = images.split()
    load_start = time.time()
    doc = Metashape.Document()
    doc.open("./localba.psx")   # EPSG::(epsg), OPK
    load_end = time.time() - load_start

    # 2. Add photos
    add_start = time.time()
    source_crs = Metashape.CoordinateSystem("EPSG::4326")
    target_crs = Metashape.CoordinateSystem("EPSG::" + str(epsg))

    chunk = doc.chunk
    chunk.crs = source_crs  # import reference in newly added image ... position
    chunk.euler_angles = Metashape.EulerAnglesYPR   # import reference in newly added image  ... orientation
    chunk.remove(chunk.cameras[0])
    chunk.addPhotos(images[-1])
    add_end = time.time() - add_start

    # 3. Set reference
    eo_start = time.time()
    camera = chunk.cameras[-1]
    # position
    camera.reference.location = Metashape.CoordinateSystem.transform(point=camera.reference.location,
                                                                     source=source_crs, target=target_crs)
    chunk.crs = target_crs
    z = float(camera.photo.meta["DJI/RelativeAltitude"])
    camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)

    # orientation
    gimbal_roll = float(camera.photo.meta["DJI/GimbalRollDegree"])
    if 180 - abs(gimbal_roll) <= 0.1:
        gimbal_roll = 0
    gimbal_pitch = float(camera.photo.meta["DJI/GimbalPitchDegree"])
    gimbal_yaw = float(camera.photo.meta["DJI/GimbalYawDegree"])

    ori = rpy_to_opk(np.array([gimbal_roll, gimbal_pitch, gimbal_yaw]))
    camera.reference.rotation = ori
    camera.reference.rotation_enabled = True
    eo_end = time.time() - eo_start

    import_start = time.time()
    chunk.euler_angles = Metashape.EulerAnglesOPK
    chunk.importReference(path="eo.txt", format=Metashape.ReferenceFormatCSV, columns="nxyzabco",
                          delimiter=",", skip_rows=2)   # plane CRS, e.g.) EPSG::5186

    # doc.save(path="./check.psx", chunks=[doc.chunk])    # EPSG::(epsg), OPK

    import_end = time.time() - import_start

    # 4. Match photos
    match_start = time.time()
    chunk.matchPhotos(downscale=downscale, keep_keypoints=True, reset_matches=False)
    match_end = time.time() - match_start
    print("  *** match time: ", match_end)

    # 5. Align cameras
    align_start = time.time()
    chunk.alignCameras(adaptive_fitting=True, reset_alignment=False)
    align_end = time.time() - align_start
    print("  *** align time: ", align_end)
    # doc.save(path="./check.psx", chunks=[doc.chunk])

    # Verifying 1: Is it processed?
    if not camera.transform:
        print(f"  *** Not processed: {not camera.transform}")
        save_start = time.time()
        doc.save(path="./localba.psx", chunks=[doc.chunk])  # EPSG::(epsg), OPK
        save_end = time.time() - save_start
        return

    stats = CameraStats(camera)
    error_location = np.sqrt(np.sum(np.square(stats.error_location), axis=0))  # RMS of location, m
    # Verifying 2: Is it well processed?
    if error_location > diff_init_esti:
        print(f"  *** Wrong processed: {error_location:.2f} m")
        save_start = time.time()
        doc.save(path="./localba.psx", chunks=[doc.chunk])  # EPSG::(epsg), OPK
        save_end = time.time() - save_start
        return

    estimated_coord = stats.estimated_location
    estimated_opk = stats.estimated_rotation

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
    chunk.exportReference(path="eo.txt", format=Metashape.ReferenceFormatCSV,
                          items=Metashape.ReferenceItemsCameras,
                          columns="nuvwdefoUVWDEFpqrijk", delimiter=",")
    chunk.exportReference(path=str(Path(output_path) / str("eo_" + images[-1].split("/")[-1].split(".")[0] + ".txt")),
                          format=Metashape.ReferenceFormatCSV, items=Metashape.ReferenceItemsCameras,
                          columns="nuvwdefoUVWDEFpqrijk", delimiter=",")
    cameras_end = time.time() - cameras_start
    points_start = time.time()
    chunk = set_region(chunk)
    point_cloud = chunk.point_cloud
    chunk.exportPoints(path="./pointclouds.pcd", source_data=Metashape.PointCloudData, format=Metashape.PointsFormatPCD,
                       crs=target_crs)
    points_end = time.time() - points_start

    save_start = time.time()
    doc.save(path="./localba.psx", chunks=[doc.chunk])  # EPSG::(epsg), OPK
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
