config = {
    # Params for files
    "image_path": "../00_data/04_210525_Moseulpo_Pilot_100m",
    "extension": "JPG",

    # Params for georeferencing
    "no_images_process": 5,         # Number of images to perform local bundle adjustment. At least 3
    "types": "nonfixed-estimated",  # Types of setting accuracy (fixed, nonfixed-initial, nonfixed-estimated)
    "matching_accuracy": 2,         # Image matching accuracy (Highest = 0, High = 1, Medium = 2, Low = 4, Lowest = 8)
                                    # https://www.agisoft.com/forum/index.php?topic=11697.msg52465#msg52465
    "no_gpus": 1,                   # Number of GPUs to process in Metashape

    # Params for handling error
    "diff_init_esti": 10,           # Difference between location of initial and estimated in m
    # "std_init_esti": -,             # The standard deviation of bundle adjustment
    "diff_before_current": 10,      # Difference between location of just before and current photo in m

    # Params for mapping
    "epsg": 5186,                   # Target coordinate system in EPSG
    "gsd": 0.1,                     # Target ground sampling distance in m. Set to 0 to disable
    "ground_height": 0.0            # Target ground height in m
}
