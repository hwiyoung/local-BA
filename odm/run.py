import os
import shutil
from config import config
import time

# Run LiveDroneMap using local bundle adjustment
# Generate an individual orthophoto using lba for every images

total_start = time.time()

project_path = config["proejct_path"]
container_name = config["container_name"]
image_name = config["image_name"]
vm_dataset = config["vm_dataset"]
vm_points = config["vm_points"]
vm_opensfm = config["vm_opensfm"]

if not os.path.isdir(os.path.join(project_path, 'results')):
        os.mkdir(os.path.join(project_path, 'results'))

queue = os.listdir(os.path.join(project_path, 'queue'))
queue.sort()
processing_images = os.listdir(os.path.join(project_path, 'images'))
processing_images.sort()

print(f'Run 1 st lba')
os.system(f'docker run -ti --rm --name {container_name} -v {vm_dataset}:/datasets -v {vm_points}:/code/opendm/ldm/points.py -v '
        f'{vm_opensfm}:/code/stages/run_opensfm.py {image_name} --project-path /datasets yangpyeong --use-hybrid-bundle-adjustment '
        '--skip-report --fast-orthophoto --orthophoto-resolution 10.0 --end-with odm_orthophoto --time --rerun-all')
# Result data
shutil.copy(os.path.join(project_path, 'odm_orthophoto', 'odm_orthophoto.tif'), os.path.join(project_path, 'results', f'{os.path.splitext(processing_images[-1])[0]}.tif'))
shutil.copy(os.path.join(project_path, 'benchmark.txt'), os.path.join(project_path, 'results', f'benchmark_{os.path.splitext(processing_images[-1])[0]}.txt'))

for i, new_image in enumerate(queue):
        print(f'Run {i + 2} th lba')
        os.remove(os.path.join(project_path, 'img_list.txt'))

        # Replace the first images to the new image in images folder
        print(f"Replace the first image: {processing_images[i]} with {new_image}")
        shutil.move(os.path.join(project_path, 'images', processing_images[i]), os.path.join(project_path, 'processed'))
        shutil.move(os.path.join(project_path, 'queue', new_image), os.path.join(project_path, 'images'))

        """ TODO: LBA only on new image
        os.system(f'docker run -ti --rm --name {container_name} -v {vm_dataset}:/datasets -v {vm_points}:/code/opendm/ldm/points.py -v '
        f'{vm_opensfm}:/code/stages/run_opensfm.py {image_name} --project-path /datasets yangpyeong --use-hybrid-bundle-adjustment '
        '--skip-report --fast-orthophoto --orthophoto-resolution 10.0 --end-with odm_orthophoto --time') """

        os.system(f'docker run -ti --rm --name {container_name} -v {vm_dataset}:/datasets -v {vm_points}:/code/opendm/ldm/points.py -v '
        f'{vm_opensfm}:/code/stages/run_opensfm.py {image_name} --project-path /datasets yangpyeong --use-hybrid-bundle-adjustment '
        '--skip-report --fast-orthophoto --orthophoto-resolution 10.0 --end-with odm_orthophoto --time --rerun-all')
        
        # Result data
        shutil.copy(os.path.join(project_path, 'odm_orthophoto', 'odm_orthophoto.tif'), os.path.join(project_path, 'results', f'{os.path.splitext(new_image)[0]}.tif'))
        shutil.copy(os.path.join(project_path, 'benchmark.txt'), os.path.join(project_path, 'results', f'benchmark_{os.path.splitext(new_image)[0]}.txt'))

total_processing = time.time() - total_start
print(f"Elpased time: {total_processing: .2f} sec")
print(f"Average processing time: {total_processing / (len(queue) + 1):.2f} sec")

processing_images = os.listdir(os.path.join(project_path, 'images'))
for image in processing_images:
        shutil.move(os.path.join(project_path, 'images', image), os.path.join(project_path, 'queue'))

processed_images = os.listdir(os.path.join(project_path, 'processed'))
for image in processed_images:
        shutil.move(os.path.join(project_path, 'processed', image), os.path.join(project_path, 'images'))