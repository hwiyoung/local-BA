import PhotoScan
import time

class Local_BA_Photoscan:

    def __init__(self):
        print("InnoPAM")

    def photoscan_alignphotos(self, image_path):

        start_time = time.time()

        doc = PhotoScan.app.document
        chunk = doc.addChunk()
        chunk.addPhotos(ImgList)

        # Set pixel size to 0.017mm
        doc.chunk.sensors[0].pixel_height = 0.017
        doc.chunk.sensors[0].pixel_width = 0.017

        # Import RPY from EO file
        for img_fname in ImgList:
            doc.chunk.loadReference(
                img_fname.split('.')[0] + '.txt',
                PhotoScan.ReferenceFormatCSV,
                'nxyzabc',
                '\t'
            )

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

        center_photo_index = int(len(chunk.cameras) / 2)
        print("center image number = ", center_photo_index)

        photo1 = chunk.cameras[center_photo_index]  # 5개의 이미지 list 중에서 중간 영상의 값

        # 기본이미지정보 룰력 작업중
        FocalLenth = photo1.photo.meta["Exif/FocalLength"]
        print(FocalLenth)
        image_width = photo1.photo.meta["Exif/Width"]
        image_height = photo1.photo.meta["Exif/Height"]

        IO = [FocalLenth, image_width, image_height]
        print(IO)

        if not photo1.transform:
            print("There is no transformation matrix")

        print("==extract X(E), Y(N), Z(Altitude), Yaw, Pitch, Roll=============================")
        XYZ = chunk.crs.project(chunk.transform.matrix.mulp(photo1.center))
        T = chunk.transform.matrix
        m = chunk.crs.localframe(
            T.mulp(photo1.center))  # transformation matrix to the LSE coordinates in the given point
        R = m * T * photo1.transform * PhotoScan.Matrix().Diag([1, -1, -1, 1])

        row = list()

        for j in range(0, 3):  # creating normalized rotation matrix 3x3
            row.append(R.row(j))
            row[j].size = 3
            row[j].normalize()

        R = PhotoScan.Matrix([row[0], row[1], row[2]])
        omega, phi, kappa = PhotoScan.utils.mat2opk(R)  # estimated orientation angles

        # print("EO(XYZ) = ", XYZ)
        # print("T = ", T)
        # print("m = ", m)
        # print("R = ", R)
        # print("R = ", R)

        fname = ImgList[center_photo_index]
        # print(type(XYZ))
        XYZ_list = list(XYZ)
        EO = [XYZ_list[0], XYZ_list[1], XYZ_list[2], kappa, phi, omega]

        return fname, EO

        # print("File Name: ", fname, "X(Longitude) = ", EO[0], "Y(Latitude) = ", EO[1], "Z(Altitude) = ", EO[2],
        #       "yaw = ", EO[3], "pitch = ", EO[4],  "roll = ", EO[5])

        print("process time = ", time.time() - start_time)

