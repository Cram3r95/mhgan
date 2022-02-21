import time
import os
import numpy as np
import sys
import pdb
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point

from argoverse.map_representation.map_api import ArgoverseMap
from matplotlib.pyplot import show

lib_path = os.path.join("/home", "robesafe", "libraries")
if os.path.exists(lib_path):
    sys.path.append("/home/robesafe/libraries/SoPhie")
import sophie.data_loader.argoverse.map_utils as map_utils
import cv2

city_name = None
avm = ArgoverseMap()

curr_obs_seq_data = np.load('relative_sequences.npy')
city_name = str(np.load("city_id.npy"))
curr_ego_origin = np.load("origin.npy")
obj_id_list = np.load("obj_id_list.npy")
num_agents_per_obs = 10

d = 40
dist_rasterized_map = [-d,d,-d,d]

# print("relative_seq ", relative_seq.shape)
# print("ego_origin ", ego_origin.shape)
# print("city_name: ", city_name, type(city_name))

t0 = time.time()
fg_plt, bg_plt, img_cv = map_utils.map_generator(curr_obs_seq_data, 
# fig = map_utils.optimized_map_generator(curr_obs_seq_data, 
                              curr_ego_origin, 
                              dist_rasterized_map, 
                              avm, 
                              city_name,
                              (obj_id_list, num_agents_per_obs), 
                              lane_centerlines=None,
                              show=False, 
                              smoothen=True)

print("Time consumed: ", time.time() - t0)
# t0 = time.time()
# img_render = map_utils.renderize_image(fig)
# img = img_render * 255.0
# print("Time consumed by image rendering: ", time.time() - t0)

curr_folder = os.getcwd()
filename = curr_folder + "/hdmap_images/test_image_full_image.png"
cv2.imwrite(filename,img_cv)