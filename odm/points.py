import shutil
import numpy as np
import pandas as pd
import argparse


def query_points(reconstruction, tracks, image_list, reconstruction_original):
    """
    Query point cloud by track_id of a target image
    recontruction: path of reconstruction.json
    tracks: path of tracks.csv
    image_list: path of img_list.txt
    """
    df_reconstruction = pd.read_json(reconstruction)    
    points = df_reconstruction["points"][0]
    print(f" * [Before] no. of points: {len(points)}")

    df_tracks = pd.read_csv(tracks, skiprows=1, sep='\t+', header=None)
    df_tracks.columns = ["image", "track_id", "feature_id", "feature_x", "feature_y", "feature_z", "r", "g", "b", "segmentation", "instance"]
    # extract track_id
    img_list_df = pd.read_csv(image_list, sep='\n+', header=None)
    target_image = img_list_df.sort_values(by=[0]).iloc[-1][0]    # select the last image
    print(f" * {target_image} is selected")
    tracks_id = df_tracks.loc[df_tracks['image'] == target_image]["track_id"]
    # query points
    tmp = []
    for key in tracks_id:
        row = points.get(str(key))
        if row is None:
            continue
        color, coordinates = row["color"], row["coordinates"]
        # id, r, g, b, x, y, z
        tmp.append([key, coordinates[0], coordinates[1], coordinates[2], color[0], color[1], color[2]])
    new_points = np.array(tmp)

    unwanted = set(points) - set(new_points[:, 0].astype(int).astype(str))
    for unwanted_key in unwanted:
        del points[unwanted_key]
    print(f" * [After] no. of points: {len(points)}")

    shutil.move(reconstruction, reconstruction_original)
    df_reconstruction.to_json(reconstruction, orient='records')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='path of files')

    parser.add_argument('--reconstruction', type=str, help='path of reconstruction.json')
    parser.add_argument('--tracks', type=str, help='path of tracks.csv')
    parser.add_argument('--image-list', type=str, help='path of img_list.txt')    

    args = parser.parse_args()
    reconstruction = args.reconstruction
    tracks = args.tracks
    image_list = args.image_list

    query_points(reconstruction=reconstruction, tracks=tracks, image_list=image_list)