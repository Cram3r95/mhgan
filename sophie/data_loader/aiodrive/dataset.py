import numpy as np, sys, math, os, logging, torch
import copy, glob, glob2
from torch.utils.data import Dataset
import cv2

np.set_printoptions(precision=3, suppress=True)

def safe_list(input_data, warning=False, debug=False):
	safe_data = copy.copy(input_data)
	return safe_data

def safe_path(input_path, warning=False, debug=False):
    safe_data = copy.copy(input_path)
    safe_data = os.path.normpath(safe_data)
    return safe_data

def isstring(string_test):
	return isinstance(string_test, str)

def find_unique_common_from_lists(input_list1, input_list2, only_com=False, warning=False, debug=False):
	input_list1 = safe_list(input_list1, warning=warning, debug=debug)
	input_list2 = safe_list(input_list2, warning=warning, debug=debug)

	common_list = list(set(input_list1).intersection(input_list2))

	if only_com: return common_list

	# find index
	index_list1 = []
	for index in range(len(input_list1)):
		item = input_list1[index]
		if item in common_list:
			index_list1.append(index)

	index_list2 = []
	for index in range(len(input_list2)):
		item = input_list2[index]
		if item in common_list:
			index_list2.append(index)

	return common_list, index_list1, index_list2

def remove_list_from_list(input_list, list_toremove_src, warning=False, debug=False):
	list_remained = safe_list(input_list, warning=warning, debug=debug)
	list_toremove = safe_list(list_toremove_src, warning=warning, debug=debug)
	list_removed = []
	for item in list_toremove:
		try:
			list_remained.remove(item)
			list_removed.append(item)
		except ValueError:
			if warning: print('Warning!!!!!! Item to remove is not in the list. Remove operation is not done.')

	return list_remained, list_removed

def load_list_from_folder(folder_path, ext_filter=None, depth=1, recursive=False, sort=True, save_path=None, debug=True):
    folder_path = safe_path(folder_path)
    if isstring(ext_filter): ext_filter = [ext_filter]                               # convert to a list
    # zxc

    fulllist = list()
    if depth is None:        # find all files recursively
        recursive = True
        wildcard_prefix = '**'
        if ext_filter is not None:
            for ext_tmp in ext_filter:
                # wildcard = os.path.join(wildcard_prefix, '*' + string2ext_filter(ext_tmp))
                wildcard = os.path.join(wildcard_prefix, '*' + ext_tmp)
                curlist = glob2.glob(os.path.join(folder_path, wildcard))
                if sort: curlist = sorted(curlist)
                fulllist += curlist
        else:
            wildcard = wildcard_prefix
            curlist = glob2.glob(os.path.join(folder_path, wildcard))
            if sort: curlist = sorted(curlist)
            fulllist += curlist
    else:                    # find files based on depth and recursive flag
        wildcard_prefix = '*'
        for index in range(depth-1): wildcard_prefix = os.path.join(wildcard_prefix, '*')
        if ext_filter is not None:
            for ext_tmp in ext_filter:
                # wildcard = wildcard_prefix + string2ext_filter(ext_tmp)
                wildcard = wildcard_prefix + ext_tmp
                curlist = glob.glob(os.path.join(folder_path, wildcard))
                if sort: curlist = sorted(curlist)
                fulllist += curlist
            # zxc
        else:
            wildcard = wildcard_prefix
            curlist = glob.glob(os.path.join(folder_path, wildcard))
            # print(curlist)
            if sort: curlist = sorted(curlist)
            fulllist += curlist
        if recursive and depth > 1:
            newlist, _ = load_list_from_folder(folder_path=folder_path, ext_filter=ext_filter, depth=depth-1, recursive=True)
            fulllist += newlist

    fulllist = [os.path.normpath(path_tmp) for path_tmp in fulllist]
    num_elem = len(fulllist)

    return fulllist, num_elem

def fileparts(input_path, warning=False, debug=False):
	good_path = safe_path(input_path, debug=debug)
	if len(good_path) == 0: return ('', '', '')
	if good_path[-1] == '/':
		if len(good_path) > 1: return (good_path[:-1], '', '')	# ignore the final '/'
		else: return (good_path, '', '')	                          # ignore the final '/'
	
	directory = os.path.dirname(os.path.abspath(good_path))
	filename = os.path.splitext(os.path.basename(good_path))[0]
	ext = os.path.splitext(good_path)[1]
	return (directory, filename, ext)

def seq_collate(data): # id_frame
    (obs_seq_list, pred_seq_list, obs_seq_rel_list, pred_seq_rel_list,
     non_linear_ped_list, loss_mask_list, idframe_list) = zip(*data)

    _len = [len(seq) for seq in obs_seq_list]
    cum_start_idx = [0] + np.cumsum(_len).tolist()
    seq_start_end = [[start, end] for start, end in zip(cum_start_idx, cum_start_idx[1:])]

    # Data format: batch, input_size, seq_len
    # LSTM input format: seq_len, batch, input_size
    obs_traj = torch.cat(obs_seq_list, dim=0).permute(2, 0, 1)
    pred_traj = torch.cat(pred_seq_list, dim=0).permute(2, 0, 1)
    obs_traj_rel = torch.cat(obs_seq_rel_list, dim=0).permute(2, 0, 1)
    pred_traj_rel = torch.cat(pred_seq_rel_list, dim=0).permute(2, 0, 1)
    non_linear_ped = torch.cat(non_linear_ped_list)
    loss_mask = torch.cat(loss_mask_list, dim=0)
    seq_start_end = torch.LongTensor(seq_start_end)
    id_frame = torch.cat(idframe_list, dim=0).permute(2, 0, 1)

    out = [obs_traj, pred_traj, obs_traj_rel, pred_traj_rel, non_linear_ped, loss_mask, seq_start_end, id_frame]

    return tuple(out)

def get_folder_name(video_path, seq_name):
    town = str(int(seq_name/1000))
    seq = str(int(seq_name%1000))
    split = video_path.split('/')[-2].split('_')[-1]
    hd = (split == "test") and town == "10"
    folder = "Town{}{}_seq{}".format(
        town.zfill(2),
        "HD" if hd else "",
        seq.zfill(4)
    )
    full_path = os.path.join(video_path, folder)
    return full_path

def load_images(video_path, frames, extension="png", new_shape=(600,600)):
    frames_list = []
    cont = 0
    for frame in frames:
        folder_name = get_folder_name(video_path[0], frame[0].item())
        cont += 1
        image_id = str(int(frame[1].item()))
        image_url = os.path.join(folder_name, "{}.{}".format(image_id.zfill(6), extension))
        #print("image_url: ", image_url)
        frame = cv2.imread(image_url)
        frame = cv2.resize(frame, new_shape)
        frames_list.append(np.expand_dims(frame, axis=0))
    frames_arr = np.concatenate(frames_list, axis=0)
    return frames_arr

def seq_collate_image_aiodrive(data): # id_frame
    """
    (obs_traj, pred_traj_gt, obs_traj_rel, pred_traj_gt_rel, non_linear_ped,
             loss_mask, seq_start_end, frames, prediction_length, "object_class", "seq_name", 
             "seq_frame", object_id) = batch

        seq:  torch.Size([8, 2]) tensor([[3004.,  720.],
            [4002.,   78.],
            [1014.,  809.],
            [3002.,  139.],
            [4003.,   86.],
            [2007.,  794.],
            [4003.,  340.],
            [4003.,   61.]])

    """
    (obs_seq_list, pred_seq_list, obs_seq_rel_list, pred_seq_rel_list,
     non_linear_ped_list, loss_mask_list, idframe_list, vi_path, extension, frame, object_class, objects_id) = zip(*data)

    _len = [len(seq) for seq in obs_seq_list]
    cum_start_idx = [0] + np.cumsum(_len).tolist()
    seq_start_end = [[start, end] 
                     for start, end in zip(cum_start_idx, cum_start_idx[1:])]

    # Data format: batch, input_size, seq_len
    # LSTM input format: seq_len, batch, input_size
    obs_traj = torch.cat(obs_seq_list, dim=0).permute(2, 0, 1)
    pred_traj = torch.cat(pred_seq_list, dim=0).permute(2, 0, 1)
    obs_traj_rel = torch.cat(obs_seq_rel_list, dim=0).permute(2, 0, 1)
    pred_traj_rel = torch.cat(pred_seq_rel_list, dim=0).permute(2, 0, 1)
    non_linear_ped = torch.cat(non_linear_ped_list)
    loss_mask = torch.cat(loss_mask_list, dim=0)
    seq_start_end = torch.LongTensor(seq_start_end)
    id_frame = torch.cat(idframe_list, dim=0).permute(2, 0, 1) # seq_len - peds_in_curr_seq - 3
    frames = load_images(list(vi_path), list(frame), extension[0])
    frames = torch.from_numpy(frames).type(torch.float32)
    frames = frames.permute(0, 3, 1, 2)
    object_cls = torch.stack(object_class)
    seq = torch.stack(frame)
    obj_id = torch.stack(objects_id)

    # print("object_class ", object_cls.shape, object_cls)
    # print("seq: ",seq.shape, seq)
    # print("obj_id: ", obj_id.shape, obj_id)

    out = [
        obs_traj, pred_traj, obs_traj_rel, pred_traj_rel, non_linear_ped,
        loss_mask, seq_start_end, id_frame, frames, object_cls, seq, obj_id
    ]

    return tuple(out)


def read_file(_path, delim='tab'):
    data = []
    if delim == 'tab':     delim = '\t'
    elif delim == 'space': delim = ' '
    with open(_path, 'r') as f:
        for line in f:
            line = line.strip().split(delim)
            line = [float(i) for i in line]
            data.append(line)
    return np.asarray(data)

def ignore_file(path):
    first_token = path.split("/")[-1][0]
    return True if first_token == "." else False

def poly_fit(traj, traj_len, threshold):
    """
    Input:
    - traj: Numpy array of shape (2, traj_len)
    - traj_len: Len of trajectory
    - threshold: Minimum error to be considered for non linear traj
    Output:
    - int: 1 -> Non Linear 0-> Linear
    """

    t = np.linspace(0, traj_len - 1, traj_len)
    res_x = np.polyfit(t, traj[0, -traj_len:], 2, full=True)[1]
    res_y = np.polyfit(t, traj[1, -traj_len:], 2, full=True)[1]
    if res_x + res_y >= threshold: return 1.0
    else:                          return 0.0

# for AIODrive

###
# seq_id_list: [idx_, ?, seqname2int]
def seqname2int(seqname): # Ex: Town01_seq0001.txt -> 1*1000 + 1 
    city_id, seq_id = seqname.split('_')
    city_id = int(city_id[4:6])
    seq_id = int(seq_id[3:])
    final_id = city_id * 1000 + seq_id

    return final_id

def check_eval_windows(start_pred, obs_len, pred_len, split='test'):
    # start_pred:       the frame index starts to predict in this window, e.g., seq of 0-9 -> 10-19 has start frame at 10
    # pred_len:         the number of frames to predict 
    # split:            train, val, test

    if split == 'test':
        reserve_interval = 50
        pred_len = 50
        obs_len  = 50
    else:
        reserve_interval = 0
    check = (start_pred - obs_len) % (obs_len + pred_len + reserve_interval) == 0

    return check


def getObjecClass(url_dataset):
    url_list = url_dataset.split("/")
    objectClass = ""
    for url_id in url_list:
        if "aiodrive_" in url_id:
            objectClass = url_id
    objectClass = objectClass.split("_")[-1]
    return objectClass

# <3 split test siempre activo
class AioDriveDataset(Dataset):
    """Dataloder for the Trajectory datasets"""
    def __init__(self, data_dir, obs_len=8, pred_len=12, skip=1, threshold=0.002, min_ped=0, windows_frames=None, delim='\t', \
        phase='training', split='test', videos_path="", video_extension="png"):
        """
        Args:
        - data_dir: Directory containing dataset files in the format
        <frame_id> <ped_id> <x> <y>
        - obs_len: Number of time-steps in input trajectories
        - pred_len: Number of time-steps in output trajectories
        - skip: Number of frames to skip while making the dataset
        - threshold: Minimum error to be considered for non linear traj
        when using a linear predictor
        - min_ped: Minimum number of pedestrians that should be in a seqeunce
        - delim: Delimiter in the dataset files
        """
        super(AioDriveDataset, self).__init__()
        self.objects_id_dict = {"Car": 0, "Cyc": 1, "Mot": 2, "Ped": 3}
        self.dataset_name = "aiodrive"
        self.videos_path = videos_path
        self.video_extension = video_extension
        self.data_dir = data_dir
        self.obs_len, self.pred_len = obs_len, pred_len
        self.seq_len = self.obs_len + self.pred_len
        self.delim, self.skip = delim, skip
        all_files, _ = load_list_from_folder(self.data_dir)
        num_peds_in_seq = []
        seq_list = []
        seq_list_rel = []
        loss_mask_list = []
        non_linear_ped = []
        seq_id_list = []
        frames_list = []
        object_class_id_list = []
        object_id_list = []

        print("Split: ", split)

        for path in all_files:
            print_str = 'load %s\r' % path
            sys.stdout.write(print_str)
            sys.stdout.flush()

            _, seq_name, _ = fileparts(path)

            # if seq_name != "Town07_seq0001":
            #     continue

            print(">> ", path, seq_name)
            data = read_file(path, delim)
            
            # as testing files only contains past, so add more windows

            if split == 'test':
                min_frame, max_frame = 0, 999
                num_windows = int(max_frame - min_frame + 1 - skip*(self.seq_len - 1))      
                num_windows += (self.pred_len-1)*skip + 1
            else:
                frames = np.unique(data[:, 0]).tolist()
                min_frame, max_frame = frames[0], frames[-1]
                num_windows = int(max_frame - min_frame + 1 - skip*(self.seq_len - 1))      # include all frames for past and future

            # loop through every windows
            for window_index in range(num_windows):
                start_frame = int(window_index + min_frame)
                end_frame = int(start_frame + self.seq_len*skip)        # right-open, not including this frame  
               
                if split=='test':
                    if windows_frames and start_frame not in windows_frames:
                        # print("Continue")
                        continue

                # print("Start frame: ", start_frame)
                    
                frame = start_frame + self.obs_len
                seq_name_int = seqname2int(seq_name)
                if frame > 999:
                    frame -= 1
                seq_frame = np.array([seq_name_int, frame])

                # reduce window during testing, only evaluate every N windows
                # if phase == 'testing':
                #     check_pass = check_eval_windows(start_frame+self.obs_len*skip, self.obs_len*skip, self.pred_len*skip, split=split)
                #     if not check_pass: 
                #         continue

                # get data in current window
                curr_seq_data = []
                for frame in range(start_frame, end_frame, skip):
                    curr_seq_data.append(data[frame == data[:, 0], :])        
                curr_seq_data = np.concatenate(curr_seq_data, axis=0) # frame - id - x - y

                # initialize data

                peds_in_curr_seq_list = []

                peds_in_curr_seq = np.unique(curr_seq_data[:, 1]) # numero de peds en la ventana
                peds_len = peds_in_curr_seq.shape[0]

                num_agents = 32
                num_mini_batches = math.ceil(float(peds_len/32))

                for mini_batch in range(num_mini_batches):
                    if mini_batch == num_mini_batches-1:
                        peds_in_curr_seq_1 = peds_in_curr_seq[num_agents*mini_batch:]
                        dummy = [-1 for i in range(32 - peds_in_curr_seq_1.shape[0])]
                        peds_in_curr_seq_1 = np.concatenate((peds_in_curr_seq_1, dummy))
                        peds_in_curr_seq_list.append(peds_in_curr_seq_1)
                    else:
                        peds_in_curr_seq_1 = peds_in_curr_seq[num_agents*mini_batch:num_agents*(mini_batch+1)]
                        peds_in_curr_seq_list.append(peds_in_curr_seq_1)

                ### crea las esructuras de datos con peds_in_curr_seq de objetos por batch
                # print(">>>>>>>>>>>>>")
                for current_peds in peds_in_curr_seq_list:
                    # print("Current ped: ", current_peds)
                    curr_seq_rel   = np.zeros((len(current_peds), 2, self.seq_len))     # objects x 2 x seq_len
                    curr_seq       = np.zeros((len(current_peds), 2, self.seq_len))
                    curr_loss_mask = np.zeros((len(current_peds)   , self.seq_len))     # objects x seq_len
                    id_frame_list  = np.zeros((len(current_peds), 3, self.seq_len))     # objects x 3 x seq_len
                    object_class_list = np.zeros(len(current_peds))
                    object_class_list.fill(-1)
                    id_frame_list.fill(0)
                    num_peds_considered = 0
                    _non_linear_ped = []

                    # loop through every object in this window
                    # print("current_peds: ", current_peds)
                    for _, ped_id in enumerate(current_peds):
                        if ped_id == -1:
                            num_peds_considered += 1
                            continue

                        object_class = getObjecClass(path)
                        object_class_id = self.objects_id_dict[object_class]
                        curr_ped_seq = curr_seq_data[curr_seq_data[:, 1] == ped_id, :]      # frame - id - x - y for one of the id of the window, same id
                        pad_front    = int(curr_ped_seq[0, 0] ) - start_frame      # first frame of window       
                        pad_end      = int(curr_ped_seq[-1, 0]) - start_frame + skip # last frame of window
                        assert pad_end % skip == 0, 'error'
                        frame_existing = curr_ped_seq[:, 0].tolist() # frames of windows
                        #print("frame_existing: ", frame_existing, pad_front, pad_end, curr_ped_seq)

                        # pad front and back data to make the trajectory complete
                        if pad_end - pad_front != self.seq_len * skip:
                            
                            # pad end
                            to_be_paded_end = int(self.seq_len - pad_end / skip)
                            pad_end_seq  = np.expand_dims(curr_ped_seq[-1, :], axis=0)
                            pad_end_seq  = np.repeat(pad_end_seq, to_be_paded_end, axis=0)
                            frame_offset = np.zeros((to_be_paded_end, 4), dtype='float32')
                            frame_offset[:, 0] = np.array(range(1, to_be_paded_end+1))
                            pad_end_seq += frame_offset * skip                          # shift first columns for frame
                            curr_ped_seq = np.concatenate((curr_ped_seq, pad_end_seq), axis=0)

                            # pad front
                            to_be_paded_front = int(pad_front / skip)
                            pad_front_seq = np.expand_dims(curr_ped_seq[0, :], axis=0)
                            pad_front_seq = np.repeat(pad_front_seq, to_be_paded_front, axis=0)
                            frame_offset = np.zeros((to_be_paded_front, 4), dtype='float32')
                            frame_offset[:, 0] = np.array(range(-to_be_paded_front, 0))
                            pad_front_seq += frame_offset * skip
                            curr_ped_seq = np.concatenate((pad_front_seq, curr_ped_seq), axis=0)

                            # set pad front and end to correct values
                            pad_front = 0
                            pad_end = self.seq_len * skip

                        # add edge case when the object reappears at a bad frame
                        # in other words, missing intermediate frame
                        if curr_ped_seq.shape[0] != (pad_end - pad_front) / skip:
                            frame_all = list(range(int(curr_ped_seq[0, 0]), int(curr_ped_seq[-1, 0])+skip, skip))     
                            frame_missing, _ = remove_list_from_list(frame_all, curr_ped_seq[:, 0].tolist())

                            # pad all missing frames with zeros
                            pad_seq = np.expand_dims(curr_ped_seq[-1, :], axis=0)
                            pad_seq = np.repeat(pad_seq, len(frame_missing), axis=0)
                            pad_seq.fill(0)
                            pad_seq[:, 0] = np.array(frame_missing)
                            pad_seq[:, 1] = ped_id          # fill ID
                            curr_ped_seq = np.concatenate((curr_ped_seq, pad_seq), axis=0)
                            curr_ped_seq = curr_ped_seq[np.argsort(curr_ped_seq[:, 0])]

                        assert pad_front == 0, 'error'
                        assert pad_end == self.seq_len * skip, 'error'
                        
                        # make sure the seq_len frames are continuous, no jumping frames
                        start_frame_now = int(curr_ped_seq[0, 0])
                        if curr_ped_seq[-1, 0] != start_frame_now + (self.seq_len-1)*skip:
                            num_peds_considered += 1
                            continue

                        # make sure that past data has at least one frame
                        past_frame_list = [*range(start_frame_now, start_frame_now + self.obs_len * skip, skip)]
                        common = find_unique_common_from_lists(past_frame_list, frame_existing, only_com=True)
                        #print("common ", common)
                        if len(common) == 0:
                            num_peds_considered += 1
                            continue

                        # make sure that future GT data has at least one frame
                        if phase != 'testing':
                            gt_frame_list = [*range(start_frame_now + self.obs_len*skip, start_frame_now + self.seq_len*skip, skip)]
                            common = find_unique_common_from_lists(gt_frame_list, frame_existing, only_com=True)
                            if len(common) == 0: 
                                num_peds_considered += 1
                                continue

                        # only keep the state
                        cache_tmp = np.transpose(curr_ped_seq[:, :2])       # 2xseq_len | [0,:] list of frames | [1,:] id
                        curr_ped_seq = np.transpose(curr_ped_seq[:, 2:])    # 2 x seq_len | [0,:] x | [1,:] y

                        # print("cache_tmp: ", cache_tmp, cache_tmp.shape)
                        # print("curr_ped_seq: ", curr_ped_seq, curr_ped_seq.shape)

                        # Make coordinates relative
                        rel_curr_ped_seq = np.zeros(curr_ped_seq.shape)
                        rel_curr_ped_seq[:, 1:] = curr_ped_seq[:, 1:] - curr_ped_seq[:, :-1]
                        _idx = num_peds_considered
                        curr_seq[_idx, :, :] = curr_ped_seq     
                        curr_seq_rel[_idx, :, :] = rel_curr_ped_seq

                        # record seqname, frame and ID information 20 - 3 - x
                        id_frame_list[_idx, :2, :] = cache_tmp
                        id_frame_list[_idx, 2, :] = seq_name_int # img_id - ped_id - seqname2int
                        
                        # Linear vs Non-Linear Trajectory, only fit for the future part not past part

                        if phase != 'testing':
                            _non_linear_ped.append(poly_fit(curr_ped_seq, pred_len, threshold))     

                        # add mask onto padded dummay data
                        frame_exist_index = np.array([frame_tmp - start_frame_now for frame_tmp in frame_existing])
                        frame_exist_index = (frame_exist_index / skip).astype('uint8')
                        curr_loss_mask[_idx, frame_exist_index] = 1

                        # object id
                        object_class_list[num_peds_considered] = object_class_id

                        num_peds_considered += 1
                        #print("b")
                    
                    #print("num_peds_considered ", num_peds_considered)
                    #num_peds_considered = 32
                    if num_peds_considered > min_ped:
                        if len(_non_linear_ped) != num_peds_considered:
                            dummy = [-1 for i in range(num_peds_considered - len(_non_linear_ped))]
                            _non_linear_ped = _non_linear_ped + dummy
                        non_linear_ped += _non_linear_ped
                        num_peds_in_seq.append(num_peds_considered)
                        loss_mask_list.append(curr_loss_mask[:num_peds_considered])
                        seq_list.append(curr_seq[:num_peds_considered])
                        seq_list_rel.append(curr_seq_rel[:num_peds_considered])
                        seq_id_list.append(id_frame_list[:num_peds_considered])
                        frames_list.append(seq_frame)
                        object_class_id_list.append(object_class_list)
                        object_id_list.append(id_frame_list[:num_peds_considered][:,1,0])

        self.num_seq = len(seq_list)
        seq_list = np.concatenate(seq_list, axis=0)             # objects x 2 x seq_len
        seq_list_rel = np.concatenate(seq_list_rel, axis=0)
        loss_mask_list = np.concatenate(loss_mask_list, axis=0)
        non_linear_ped = np.asarray(non_linear_ped)
        seq_id_list = np.concatenate(seq_id_list, axis=0)
        frames_list = np.asarray(frames_list)
        object_class_id_list = np.asarray(object_class_id_list)
        object_id_list = np.asarray(object_id_list)
        #print("seq_list: ", seq_list.shape)
        #print("frames_list: ", frames_list.shape)

        # Convert numpy -> Torch Tensor
        self.obs_traj = torch.from_numpy(seq_list[:, :, :self.obs_len]).type(torch.float)
        self.pred_traj = torch.from_numpy(seq_list[:, :, self.obs_len:]).type(torch.float)
        self.obs_traj_rel = torch.from_numpy(seq_list_rel[:, :, :self.obs_len]).type(torch.float)
        self.pred_traj_rel = torch.from_numpy(seq_list_rel[:, :, self.obs_len:]).type(torch.float)
        self.loss_mask = torch.from_numpy(loss_mask_list).type(torch.float)
        self.non_linear_ped = torch.from_numpy(non_linear_ped).type(torch.float)
        cum_start_idx = [0] + np.cumsum(num_peds_in_seq).tolist()
        self.seq_start_end = [(start, end) for start, end in zip(cum_start_idx, cum_start_idx[1:])]
        self.seq_id_list = torch.from_numpy(seq_id_list).type(torch.float)
        self.frames_list = torch.from_numpy(frames_list).type(torch.float)
        self.object_class_id_list = torch.from_numpy(object_class_id_list).type(torch.float)
        self.object_id_list = torch.from_numpy(object_id_list).type(torch.float)
        # print("ID List: ", self.object_id_list)

    def __len__(self):
        return self.num_seq

    def __getitem__(self, index):
        start, end = self.seq_start_end[index]
        out = [
            self.obs_traj[start:end, :], self.pred_traj[start:end, :],
            self.obs_traj_rel[start:end, :], self.pred_traj_rel[start:end, :],
            self.non_linear_ped[start:end], self.loss_mask[start:end, :],
            self.seq_id_list[start:end, :], self.videos_path, self.video_extension, self.frames_list[index, :],
            self.object_class_id_list[index], self.object_id_list[index]
        ]

        return out

        