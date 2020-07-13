import PhotoScan
import time
import argparse
import glob


def photoscan_alignphotos(image_path):
    start_time = time.time()

    images = glob.glob(image_path+"/*.JPG")
    print(images)
    for i in range(len(images)-5):
        images_to_process = images[i:i+5]
        print(images_to_process)

        doc = PhotoScan.app.document
        chunk = doc.addChunk()
        # chunk.addPhotos([images_to_process], load_xmp_orientation=True)
        chunk.addPhotos([images_to_process])
        for camera in chunk.cameras:
            print(camera)
            if not camera.reference.location:
                continue
            if ("DJI/RelativeAltitude" in camera.photo.meta.keys()) and camera.reference.location:
                z = float(camera.photo.meta["DJI/RelativeAltitude"])
                camera.reference.location = (camera.reference.location.x, camera.reference.location.y, z)
            gimbal_roll = float(camera.photo.meta["DJI/GimbalRollDegree"])
            gimbal_pitch = float(camera.photo.meta["DJI/GimbalPitchDegree"])
            gimbal_yaw = float(camera.photo.meta["DJI/GimbalYawDegree"])
            camera.reference.rotation = (gimbal_yaw, 90+gimbal_pitch, gimbal_roll)

            print(camera.reference.location, camera.reference.rotation)

        print(doc.chunk.sensors[0])
        print(doc.chunk.sensors[0].focal_length)
        print(doc.chunk.sensors[0].width, doc.chunk.sensors[0].height)
        print(doc.chunk.sensors[0].pixel_width, doc.chunk.sensors[0].pixel_height)
        print(doc.chunk.sensors[0].pixel_size)

        print("==match Photos=================================================")
        print("===============================================================")
        chunk.matchPhotos(accuracy=PhotoScan.MediumAccuracy)

        print("==align photo==================================================")
        print("===============================================================")
        chunk.alignCameras()

        # print("==save project=================================================")
        # #저장 파일 이름을 center_image_name + 시간 으로 변경
        # path = "./test.psz"
        # doc.save(path)
        # print("===============================================================")

        camera = chunk.cameras[-1]

        if not camera.transform:
            print("There is no transformation matrix")

        print("==extract X(E), Y(N), Z(Altitude), Yaw, Pitch, Roll=============================")
        estimated_coord = chunk.crs.project(chunk.transform.matrix.mulp(camera.center))
        T = chunk.transform.matrix
        m = chunk.crs.localframe(
            T.mulp(camera.center))  # transformation matrix to the LSE coordinates in the given point
        R = m * T * camera.transform * PhotoScan.Matrix().Diag([1, -1, -1, 1])

        row = list()
        for j in range(0, 3):  # creating normalized rotation matrix 3x3
            row.append(R.row(j))
            row[j].size = 3
            row[j].normalize()

        R = PhotoScan.Matrix([row[0], row[1], row[2]])
        estimated_ypr = PhotoScan.utils.mat2ypr(R)  # estimated orientation angles - yaw, pitch, roll
        estimated_opk = PhotoScan.utils.mat2opk(R)  # estimated orientation angles - omega, phi, kappa
        print(estimated_ypr)
        print(estimated_opk)

        omega, phi, kappa = PhotoScan.utils.mat2opk(R)  # estimated orientation angles

        # print("EO(XYZ) = ", XYZ)
        # print("T = ", T)
        # print("m = ", m)
        # print("R = ", R)
        # print("R = ", R)

        pos = list(estimated_coord)
        ori = list(estimated_opk)
        EO = [pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]]
        print(EO)

        print("process time = ", time.time() - start_time)

        return EO


if __name__ == '__main__':
    # Set argument parser
    parser = argparse.ArgumentParser(description='LBA-photoscan')
    parser.add_argument('--image-path', required=True)

    args = parser.parse_args()
    image_path = args.image_path

    EO = photoscan_alignphotos(image_path)

