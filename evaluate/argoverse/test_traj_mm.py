import yaml
import torch
import numpy as np
from pathlib import Path
from prodict import Prodict
import csv
import pdb
import sys
import os
import time

from sklearn import linear_model
from skimage.measure import LineModelND, ransac

import matplotlib.pyplot as plt
from torch.utils.data import DataLoader

BASE_DIR = "/home/robesafe/libraries/SoPhie"
sys.path.append(BASE_DIR)

from sophie.modules.evaluation_metrics import displacement_error, final_displacement_error
from sophie.utils.utils import relative_to_abs_sgan, relative_to_abs_sgan_multimodal
# from sophie.models.sophie_adaptation import TrajectoryGenerator
from sophie.models.mp_soconf import TrajectoryGenerator
from sophie.data_loader.argoverse.dataset_sgan_version_data_augs import ArgoverseMotionForecastingDataset, \
                                                                       seq_collate, load_list_from_folder, \
                                                                       read_file
import sophie.data_loader.argoverse.map_utils as map_utils
# from sophie.trainers.trainer_sophie_adaptation import cal_ade, cal_fde
from argoverse.map_representation.map_api import ArgoverseMap

avm = ArgoverseMap()

pred_gt_file = "test_trajectories/" "pred_gt.npy"
pred_fake_file = "test_trajectories/" "pred_fake.npy"
linear_obj_file = "test_trajectories/" "linear_obj.npy"
non_linear_obj_file = "test_trajectories/" "non_linear_obj.npy"
mask_file = "test_trajectories/" "mask.npy"

pred_len = 30


def cal_ade(pred_traj_gt, pred_traj_fake, linear_obj, non_linear_obj, consider_ped):
    b,m,t,_ = pred_traj_fake.shape
    ade = []
    for i in range(b):
        _ade = []
        for j in range(m):
            print("curr: ", pred_traj_fake[i,j,:,:].unsqueeze(0).permute(1,0,2))
            print("gt: ", pred_traj_gt[:,i,:].unsqueeze(1))
            __ade = displacement_error(
                pred_traj_fake[i,j,:,:].unsqueeze(0).permute(1,0,2), pred_traj_gt[:,i,:].unsqueeze(1), consider_ped
            )
            pdb.set_trace()
            _ade.append(__ade.item())
        ade.append(_ade)
    ade = np.array(ade)
    min_ade = np.min(ade, 1)
    return ade, min_ade

def cal_fde(
    pred_traj_gt, pred_traj_fake, linear_obj, non_linear_obj, consider_ped
):
    b,m,t,_ = pred_traj_fake.shape
    fde = []
    for i in range(b):
        _fde = []
        for j in range(m):
            __fde = final_displacement_error(
                pred_traj_fake[i,j,-1,:].unsqueeze(0), pred_traj_gt[-1,i].unsqueeze(0), consider_ped
            )
            _fde.append(__fde.item())
        fde.append(_fde)
    fde = np.array(fde)
    min_fde = np.min(fde, 1)
    return fde, min_fde

def get_origin_and_city(seq,obs_window):
    """
    """

    frames = np.unique(data[:, 0]).tolist() 
    frame_data = []
    for frame in frames:
        frame_data.append(data[frame == data[:, 0], :]) # save info for each frame

    obs_frame = frame_data[obs_window-1]
    # pdb.set_trace()
    try:
        origin = obs_frame[obs_frame[:,2] == 1][:,3:5] # Get x|y of the AGENT (object_class = 1) in the obs window
    except:
        pdb.set_trace()
    city_id = round(obs_frame[0,-1])
    if city_id == 0:
        city_name = "PIT"
    else:
        city_name = "MIA"

    return origin, city_name

try:
    assert 1 == 0
    with open(pred_gt_file, 'rb') as my_file:
        agent_traj_gt =  torch.from_numpy(np.load(my_file))

    with open(pred_fake_file, 'rb') as my_file:
        agent_traj_fake =  torch.from_numpy(np.load(my_file))

    with open(linear_obj_file, 'rb') as my_file:
        linear_obj =  torch.from_numpy(np.load(my_file))

    with open(non_linear_obj_file, 'rb') as my_file:
        non_linear_obj =  torch.from_numpy(np.load(my_file))

    with open(mask_file, 'rb') as my_file:
        mask =  torch.from_numpy(np.load(my_file))

    print("agent gt: ", agent_traj_gt.shape)
    print("agent fake: ", agent_traj_fake.shape)
    print("agent linear obj: ", linear_obj.shape)
    print("agent non_linear_obj: ", non_linear_obj.shape)
    print("agent mask: ", mask.shape)

    ade, ade_l, ade_nl = cal_ade(
        agent_traj_gt, agent_traj_fake, linear_obj, non_linear_obj, mask
    )

    print("ade: ", ade.item()/pred_len)

    fde, fde_l, fde_nl = cal_fde(
        agent_traj_gt, agent_traj_fake, linear_obj, non_linear_obj, mask
    )

    print("fde: ", fde.item())

except:
    with open(r'./configs/sophie_argoverse.yml') as config:
            config = yaml.safe_load(config)
            config = Prodict.from_dict(config)
            config.base_dir = BASE_DIR

    # Fill some additional dimensions

    past_observations = config.hyperparameters.obs_len
    num_agents_per_obs = config.hyperparameters.num_agents_per_obs
    config.sophie.generator.social_attention.linear_decoder.out_features = past_observations * num_agents_per_obs

    config.dataset.split = "val"
    config.dataset.split_percentage = 0.001 # To generate the final results, must be 1 (whole split test) 0.0001
    config.dataset.start_from_percentage = 0.0
    config.dataset.batch_size = 1 # Better to build the h5 results file
    config.dataset.num_workers = 0
    config.dataset.class_balance = -1.0 # Do not consider class balance in the split val
    config.dataset.shuffle = False

    config.hyperparameters.pred_len = 30 # In test, we do not have the gt (prediction points)

    data_images_folder = config.dataset.path + config.dataset.split + "/data_images"

    MAP_GENERATION = False
    PLOT_QUALITATIVE_RESULTS = True

    dist_around = 40
    dist_rasterized_map = [-dist_around, dist_around, -dist_around, dist_around]

    if MAP_GENERATION:
        # Only load the city and x|y center to generate the background

        obs_window = 20

        folder = config.dataset.path + config.dataset.split + "/data/"
        files, num_files = load_list_from_folder(folder)

        file_id_list = []
        root_file_name = None
        for file_name in files:
            if not root_file_name:
                root_file_name = os.path.dirname(os.path.abspath(file_name))
            file_id = int(os.path.normpath(file_name).split('/')[-1].split('.')[0])
            file_id_list.append(file_id)
        file_id_list.sort()
        print("Num files: ", num_files)

        start_from = int(config.dataset.start_from_percentage*num_files)
        n_files = int(config.dataset.split_percentage*num_files)

        if (start_from + n_files) >= num_files:
            file_id_list = file_id_list[start_from:]
        else:
            file_id_list = file_id_list[start_from:start_from+n_files]

        for i, file_id in enumerate(file_id_list):
            print(f"File {file_id} -> {i}/{len(file_id_list)}")
            path = os.path.join(root_file_name,str(file_id)+".csv")
            data = read_file(path) 

            origin_pos, city_name = get_origin_and_city(data,20)

            map_utils.map_generator(file_id,
                                    origin_pos,
                                    dist_rasterized_map,
                                    avm,
                                    city_name,
                                    show=True,
                                    root_folder=data_images_folder)

            plt.close("all")

    else:
        data_val = ArgoverseMotionForecastingDataset(dataset_name=config.dataset_name,
                                                    root_folder=config.dataset.path,
                                                    obs_len=config.hyperparameters.obs_len,
                                                    pred_len=config.hyperparameters.pred_len,
                                                    distance_threshold=config.hyperparameters.distance_threshold,
                                                    split=config.dataset.split,
                                                    num_agents_per_obs=config.hyperparameters.num_agents_per_obs,
                                                    split_percentage=config.dataset.split_percentage,
                                                    start_from_percentage=config.dataset.start_from_percentage,
                                                    shuffle=False,
                                                    batch_size=config.dataset.batch_size,
                                                    class_balance=config.dataset.class_balance,
                                                    obs_origin=config.hyperparameters.obs_origin)

        loader = DataLoader(data_val,
                            batch_size=config.dataset.batch_size,
                            shuffle=False,
                            num_workers=config.dataset.num_workers,
                            collate_fn=seq_collate)

        exp_name = "mm_k_6_class_balance_0_3" #"gen_exp/exp7"
        model_path = BASE_DIR + "/save/argoverse/" + exp_name + "/argoverse_motion_forecasting_dataset_0_with_model.pt"
        checkpoint = torch.load(model_path)
        generator = TrajectoryGenerator(n_samples=6)

        print("Loading model ...")
        generator.load_state_dict(checkpoint.config_cp['g_best_state'])
        generator.cuda() # Use GPU
        generator.eval()

        print(generator)

        num_samples = 1
        output_all = []

        ade_list = []
        fde_list = []
        num_seq_list = []
        traj_kind_list = []

        DEBUG_TRAJECTORY_CLASSIFIER = False

        with torch.no_grad():
            for batch_index, batch in enumerate(loader):
                # if batch_index > 99:
                #     break
                batch = [tensor.cuda() for tensor in batch]
                
                (obs_traj, pred_traj_gt, obs_traj_rel, pred_traj_gt_rel, non_linear_obj,
                loss_mask, seq_start_end, frames, object_cls, obj_id, ego_origin, num_seq,_) = batch

                predicted_traj = []
                pred_traj_fake_list = []

                print("Analizing sequence: ", num_seq.item())

                agent_idx = torch.where(object_cls==1)[0].cpu().numpy()
                traj_real = torch.cat([obs_traj, pred_traj_gt], dim=0)
                agent_traj_gt = pred_traj_gt[:,agent_idx,:] # From Multi to Single (30 x bs x 2)

                # Check if the trajectory is a straight line or has a curve
    
                agent_seq = traj_real[:,agent_idx,:].cpu().detach().numpy() # 50 x batch_size x 2
                agent_x = agent_seq[:,0,0].reshape(-1,1) # We assume here 50 x 1 x 2 (1 represents batch_size = 1)
                agent_y = agent_seq[:,0,1].reshape(-1,1)

                ## Sklearn    

                ransac = linear_model.RANSACRegressor(residual_threshold=2)
                ransac.fit(agent_x,agent_y)

                inlier_mask = ransac.inlier_mask_
                outlier_mask = np.logical_not(inlier_mask)
                num_inliers = len(np.where(inlier_mask == True)[0])

                ## Study consecutive inliers

                cnt = 0
                num_min_outliers = 8 # Minimum number of consecutive outliers to consider the trajectory as curve
                is_curve = False
                for is_inlier in inlier_mask:
                    if not is_inlier:
                        cnt += 1
                    else:
                        cnt = 0

                    if cnt >= num_min_outliers:
                        is_curve = True

                if DEBUG_TRAJECTORY_CLASSIFIER:
                    x_max = agent_x.max()
                    x_min = agent_x.min()
                    num_steps = 20
                    step_dist = (x_max - x_min) / num_steps
                    line_x = np.arange(x_min, x_max, step_dist)[:, np.newaxis]
                    line_y_ransac = ransac.predict(line_x)

                    y_min = line_y_ransac.min()
                    y_max = line_y_ransac.max()

                    lw = 2
                    plt.scatter(
                        agent_x[inlier_mask], agent_y[inlier_mask], color="blue", marker=".", label="Inliers"
                    )
                    plt.scatter(
                        agent_x[outlier_mask], agent_y[outlier_mask], color="red", marker=".", label="Outliers"
                    )

                    plt.plot(
                        line_x,
                        line_y_ransac,
                        color="cornflowerblue",
                        linewidth=lw,
                        label="RANSAC regressor",
                    )
                    plt.legend(loc="lower right")
                    plt.xlabel("X (m)")
                    plt.ylabel("Y (m)")
                    plt.title('Sequence {}. Num inliers: {}. Is a curve: {}'.format(batch_index,num_inliers,is_curve))

                    threshold = 15
                    plt.xlim([x_min-threshold, x_max+threshold])
                    plt.ylim([y_min-threshold, y_max+threshold])

                    plt.show()
        
                top_k_ade = 50000
                top_k_fde = 50000

                for _ in range(num_samples):
                    # Get predictions
                    # pred_traj_fake_rel = generator(obs_traj, obs_traj_rel, frames, agent_idx) # seq_start_end)
                    t0 = time.time()
                    pred_traj_fake_rel,conf = generator(obs_traj, obs_traj_rel, seq_start_end, agent_idx)
                    print("time: ", time.time() - t0)

                    # Get predictions in absolute coordinates
                    pred_traj_fake = relative_to_abs_sgan_multimodal(pred_traj_fake_rel, obs_traj[-1, agent_idx,:])
                    pred_traj_fake_list.append(pred_traj_fake)
                    
                    # traj_fake = torch.cat([obs_traj[:, agent_idx, :], pred_traj_fake], dim=0) # 50,1,2
                    # predicted_traj.append(traj_fake)

                    # Get metrics
                    agent_traj_fake = pred_traj_fake # The output of the model is already single (30 x bs x 2)

                    agent_obj_id = obj_id[agent_idx]
                    agent_non_linear_obj = non_linear_obj[agent_idx]

                    agent_mask = np.where(agent_obj_id.cpu() == -1, 0, 1)
                    agent_mask = torch.tensor(agent_mask, device=agent_obj_id.device).reshape(-1)
                    
                    agent_linear_obj = 1 - agent_non_linear_obj
#
                    # with open(pred_gt_file, 'wb') as my_file:
                    #     np.save(my_file, agent_traj_gt.cpu().detach().numpy())
                    
                    # with open(pred_fake_file, 'wb') as my_file:
                    #     np.save(my_file, agent_traj_fake.cpu().detach().numpy())
                    
                    # with open(linear_obj_file, 'wb') as my_file:
                    #     np.save(my_file, agent_linear_obj.cpu().detach().numpy())
                
                    # with open(non_linear_obj_file, 'wb') as my_file:
                    #     np.save(my_file, agent_non_linear_obj.cpu().detach().numpy())

                    # with open(mask_file, 'wb') as my_file:
                    #     np.save(my_file, agent_mask.cpu().detach().numpy())
#
                    ade, ade_min = cal_ade(
                        pred_traj_gt, pred_traj_fake, None, None,
                         None
                    )

                    fde, fde_min = cal_fde(
                        pred_traj_gt, pred_traj_fake, None, None,
                        None
                    )

                    ade = ade.min().item() / pred_len
                    fde = fde.min().item()

                    if ade < top_k_ade:
                        top_k_ade = ade
                        top_k_fde = fde

                # Plot qualitative results

                if PLOT_QUALITATIVE_RESULTS:
                    filename = data_images_folder + "/" + str(num_seq.item()) + ".png"
                    img = map_utils.plot_qualitative_results_mm(filename, pred_traj_fake_list, agent_traj_gt, agent_idx,
                                                             object_cls, obs_traj, ego_origin, dist_rasterized_map)

                if not MAP_GENERATION:
                    ade_list.append(ade)
                    fde_list.append(fde)
                    num_seq_list.append(num_seq)

                    if is_curve:
                        traj_kind_list.append(1)
                    else:
                        traj_kind_list.append(0)

                    # predicted_traj = torch.stack(predicted_traj, axis=0)
                    # predicted_traj = predicted_traj.cpu().numpy()
                    # output_all.append(predicted_traj)

            if not MAP_GENERATION:
                ade = round(sum(ade_list) / (len(ade_list)),3)
                print("ade: ", ade)
                fde = round(sum(fde_list) / (len(fde_list)),3)
                print("fde: ", fde)

                # Write ade and fde values in CSV

                file_dir = str(Path(__file__).resolve().parent)

                with open(file_dir+'/test_trajectories/'+exp_name+'_metrics_val.csv', 'w', newline='') as csvfile:
                    csv_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)

                    header = ['Index','Sequence.csv','Traj_Kind','ADE','FDE']
                    csv_writer.writerow(header)

                    sorted_indeces = np.argsort(ade_list)

                    for _,sorted_index in enumerate(sorted_indeces):
                        traj_kind = traj_kind_list[sorted_index]
                        seq_id = num_seq_list[sorted_index].item() 
                        curr_ade = round(ade_list[sorted_index],3)
                        curr_fde = round(fde_list[sorted_index],3)

                        data = [str(sorted_index),str(seq_id),traj_kind,curr_ade,curr_fde]

                        csv_writer.writerow(data)

                    # Write mean ADE and FDE 

                    csv_writer.writerow(['-','-','-'])
                    csv_writer.writerow(['Mean',ade,fde])

    

