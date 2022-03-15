from os import path
import torch
import torch.nn as nn
import torch.nn.functional as F
import pdb
import math
import torchvision.transforms.functional as TF
from sophie.modules.attention import TransformerEncoder
from sophie.modules.set_transformer import PMA, SAB

def make_mlp(dim_list):
    layers = []
    for dim_in, dim_out in zip(dim_list[:-1], dim_list[1:]):
        layers.append(nn.Linear(dim_in, dim_out))
        layers.append(nn.LeakyReLU())
    return nn.Sequential(*layers)

class TrajectoryGenerator(nn.Module):
    def __init__(
        self, obs_len=20, pred_len=30, mlp_dim=64, h_dim=32, embedding_dim=16, bottleneck_dim=32,
        noise_dim=8, n_agents=10, dropout=0
    ):
        super(TrajectoryGenerator, self).__init__()

        self.obs_len = obs_len
        self.pred_len = pred_len
        self.mlp_dim = mlp_dim
        self.h_dim = h_dim
        self.embedding_dim = embedding_dim
        self.bottleneck_dim = bottleneck_dim
        self.noise_dim = noise_dim
        self.n_agents = n_agents

        self.num_heads = 4
        self.num_blocks = 2

        ## Transformer encoder
        self.encoder = TransformerEncoder(
            2, h_dim, h_dim, h_dim, h_dim, h_dim,
            h_dim, h_dim*2, self.num_heads, self.num_blocks, .5
        )

        ## Transformer decoder
        ln = False
        num_outputs = 3
        self.decoder = nn.Sequential(
                PMA(self.h_dim, self.num_heads, num_outputs, ln=ln),
                SAB(self.h_dim, self.h_dim, self.num_heads, ln=ln)
        )

        ## regressor
        dim_output = 2*pred_len
        self.regressor = nn.Linear(self.h_dim, dim_output)

        # TE + LSTM DECODER
    def forward(self, obs_traj, obs_traj_rel, start_end_seq, agent_idx=None):
        _, nb, _ = obs_traj_rel.shape
        b, _ =start_end_seq.shape
        x = []
        for start, end in start_end_seq.data:
            y = obs_traj_rel[:,start:end,:].contiguous().permute(1,0,2) # (obs,n,2)
            n, t, p = y.shape
            y = y.contiguous().view(1, -1, p) # (1, obs*n, 2)
            y = self.encoder(
                y,
                None
            ) # (1, obs*n, h_dim) -> h_dim of main agent

            y = self.decoder(y)
            y = y.view(n,t,self.h_dim) # (n, obs, h_dim)
            x.append(y)
        x = torch.cat(x, 0) # (n*b, obs, h_dim)
        ## Decode trajectory
        ##########################################################################################
        ## create decoder context input
        if agent_idx is not None:
            x = x[agent_idx,:,:] # (b, obs, h_dim)
        pred_traj_fake_rel = self.regressor(x).reshape(-1, self.pred_len, 2)
        return pred_traj_fake_rel

        # TE + KAGGLE TD
    # def forward(self, obs_traj, obs_traj_rel, start_end_seq, agent_idx=None):
    #     pass

class TrajectoryDiscriminator(nn.Module):
    def __init__(self, mlp_dim=64, h_dim=64):
        super(TrajectoryDiscriminator, self).__init__()

        self.mlp_dim = mlp_dim
        self.h_dim = h_dim

        self.encoder = None
        real_classifier_dims = [self.h_dim, self.mlp_dim, 1]
        self.real_classifier = make_mlp(real_classifier_dims)

    def forward(self, traj, traj_rel):

        final_h = self.encoder(traj_rel)
        scores = self.real_classifier(final_h)
        return scores