import torch
from torch import nn
import torch.nn.functional as F
from fractions import gcd
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import pdb

from sophie.modules.layers import MLP, TrajConf, LinearRes

class DecoderLSTM(nn.Module):
 
    def __init__(self, seq_len=30, h_dim=64, embedding_dim=16):
        super().__init__()

        self.seq_len = seq_len
        self.h_dim = h_dim
        self.embedding_dim = embedding_dim

        self.decoder = nn.LSTM(self.embedding_dim, self.h_dim, 1)
        self.spatial_embedding = nn.Linear(2, self.embedding_dim)
        self.ln1 = nn.LayerNorm(2)
        self.hidden2pos = nn.Linear(self.h_dim, 2)
        self.ln2 = nn.LayerNorm(self.h_dim)
        self.output_activation = nn.Sigmoid()

    def forward(self, last_pos, last_pos_rel, state_tuple):
        npeds = last_pos.size(0)
        pred_traj_fake_rel = []
        decoder_input = F.leaky_relu(self.spatial_embedding(self.ln1(last_pos_rel))) # 16
        decoder_input = decoder_input.view(1, npeds, self.embedding_dim) # 1x batchx 16

        for _ in range(self.seq_len):
            output, state_tuple = self.decoder(decoder_input, state_tuple) #
            rel_pos = self.output_activation(self.hidden2pos(self.ln2(output.view(-1, self.h_dim))))# + last_pos_rel # 32 -> 2
            curr_pos = rel_pos + last_pos
            embedding_input = rel_pos

            decoder_input = F.leaky_relu(self.spatial_embedding(self.ln1(embedding_input)))
            decoder_input = decoder_input.view(1, npeds, self.embedding_dim)
            pred_traj_fake_rel.append(rel_pos.view(npeds,-1))
            last_pos = curr_pos

        pred_traj_fake_rel = torch.stack(pred_traj_fake_rel, dim=0)
        return pred_traj_fake_rel

class TemporalDecoderLSTM(nn.Module):

    def __init__(self, seq_len=30, h_dim=64, embedding_dim=16):
        super().__init__()

        self.seq_len = seq_len
        self.h_dim = h_dim
        self.embedding_dim = embedding_dim

        self.decoder = nn.LSTM(self.embedding_dim, self.h_dim, 1)
        self.spatial_embedding = nn.Linear(40, self.embedding_dim) # 20 obs * 2 points
        self.ln1 = nn.LayerNorm(40)
        self.hidden2pos = nn.Linear(self.h_dim, 2)
        self.ln2 = nn.LayerNorm(self.h_dim)

    def forward(self, traj_abs, traj_rel, state_tuple):
        """
            traj_abs (20, b, 2)
            traj_rel (20, b, 2)
            state_tuple: h and c
                h : c : (1, b, self.h_dim)
        """
        npeds = traj_abs.size(1)
        pred_traj_fake_rel = []
        decoder_input = F.leaky_relu(self.spatial_embedding(self.ln1(traj_rel.contiguous().view(npeds, -1)))) # bx16
        decoder_input = decoder_input.contiguous().view(1, npeds, self.embedding_dim) # 1x batchx 16

        for _ in range(self.seq_len):
            output, state_tuple = self.decoder(decoder_input, state_tuple) # output (1, b, 32)
            rel_pos = self.hidden2pos(self.ln2(output.contiguous().view(-1, self.h_dim))) # (b, 2)
            traj_rel = torch.roll(traj_rel, -1, dims=(0))
            traj_rel[-1] = rel_pos

            decoder_input = F.leaky_relu(self.spatial_embedding(self.ln1(traj_rel.contiguous().view(npeds, -1))))
            decoder_input = decoder_input.contiguous().view(1, npeds, self.embedding_dim)
            pred_traj_fake_rel.append(rel_pos.contiguous().view(npeds,-1))

        pred_traj_fake_rel = torch.stack(pred_traj_fake_rel, dim=0)
        return pred_traj_fake_rel

class GoalDecoderLSTM(nn.Module):

    def __init__(self, seq_len=30, h_dim=64, embedding_dim=16):
        super().__init__()

        self.seq_len = seq_len
        self.h_dim = h_dim
        self.embedding_dim = embedding_dim

        self.decoder = nn.LSTM(self.embedding_dim, self.h_dim, 1)
        self.spatial_embedding = nn.Linear(2, self.embedding_dim) # Last obs * 2 points
        self.hidden2pos = nn.Linear(3*self.h_dim, 2)

        self.goal_embedding = nn.Linear(2*32,self.h_dim)
        self.abs_embedding = nn.Linear(2,self.h_dim)

    def forward(self, traj_abs, traj_rel, state_tuple, goals):
        """
            traj_abs (1, b, 2)
            traj_rel (1, b, 2)
            state_tuple: h and c
                h : c : (1, b, self.h_dim)
            goals: b x 32 x 2
        """

        batch_size = traj_abs.size(1)

        goals = goals.view(goals.shape[0],-1) 
        goals_embedding = self.goal_embedding(goals) # b x h_dim

        pred_traj_fake_rel = []
        decoder_input = F.leaky_relu(self.spatial_embedding(traj_rel.contiguous().view(batch_size, -1))) # bx16
        decoder_input = decoder_input.contiguous().view(1, batch_size, self.embedding_dim) # 1 x batch x 16

        for _ in range(self.seq_len):
            output, state_tuple = self.decoder(decoder_input, state_tuple) # output (1, b, 32)
            traj_abs_embedding = self.abs_embedding(traj_abs.view(traj_abs.shape[1],-1)) # b x h_dim

            input_final = torch.cat((state_tuple[0],
                                     traj_abs_embedding.unsqueeze(0),
                                     goals_embedding.unsqueeze(0)),dim=2) # 1 x b x 3*h_dim

            rel_pos = self.hidden2pos(input_final.view(input_final.shape[1],-1)) # (b, 2)
            decoder_input = F.leaky_relu(self.spatial_embedding(rel_pos.contiguous().view(batch_size, -1)))
            decoder_input = decoder_input.contiguous().view(1, batch_size, self.embedding_dim)
            pred_traj_fake_rel.append(rel_pos.contiguous().view(batch_size,-1))

            traj_abs = traj_abs + rel_pos # Update next absolute point

        pred_traj_fake_rel = torch.stack(pred_traj_fake_rel, dim=0)
        return pred_traj_fake_rel

class MMDecoderLSTM(nn.Module):

    def __init__(self, seq_len=30, h_dim=64, embedding_dim=16, n_samples=3):
        super().__init__()

        self.seq_len = seq_len
        self.h_dim = h_dim
        self.embedding_dim = embedding_dim
        self.n_samples = n_samples

        traj_points = self.n_samples*2
        self.decoder = nn.LSTM(self.embedding_dim, self.h_dim, 1)
        self.spatial_embedding = nn.Linear(traj_points, self.embedding_dim) # Last obs * 2 points
        self.hidden2pos = nn.Linear(self.h_dim, traj_points)
        self.confidences = nn.Linear(self.h_dim, self.n_samples)

    def forward(self, traj_abs, traj_rel, state_tuple):
        """
            traj_abs (1, b, 2)
            traj_rel (1, b, 2)
            state_tuple: h and c
                h : c : (1, b, self.h_dim)
            goals: b x 32 x 2
        """

        t, batch_size, f = traj_abs.shape
        traj_rel = traj_rel.view(t,batch_size,1,f)
        traj_rel = traj_rel.repeat_interleave(self.n_samples, dim=2)
        traj_rel = traj_rel.view(t, batch_size, -1)

        pred_traj_fake_rel = []
        decoder_input = F.leaky_relu(self.spatial_embedding(traj_rel.contiguous().view(batch_size, -1))) # bx16
        decoder_input = decoder_input.contiguous().view(1, batch_size, self.embedding_dim) # 1 x batch x 16
        for _ in range(self.seq_len):
            output, state_tuple = self.decoder(decoder_input, state_tuple) # output (1, b, 32)

            rel_pos = self.hidden2pos(state_tuple[0].contiguous().view(-1, self.h_dim)) #(b, 2*m)

            decoder_input = F.leaky_relu(self.spatial_embedding(rel_pos.contiguous().view(batch_size, -1)))
            decoder_input = decoder_input.contiguous().view(1, batch_size, self.embedding_dim)
            pred_traj_fake_rel.append(rel_pos.contiguous().view(batch_size,-1))

        pred_traj_fake_rel = torch.stack(pred_traj_fake_rel, dim=0)
        pred_traj_fake_rel = pred_traj_fake_rel.view(self.seq_len, batch_size, self.n_samples, -1)
        pred_traj_fake_rel = pred_traj_fake_rel.permute(1,2,0,3) #(b, m, 30, 2)
        conf = self.confidences(state_tuple[0].contiguous().view(-1, self.h_dim))
        conf = torch.softmax(conf, dim=1)
        return pred_traj_fake_rel, conf

class GoalMMDecoderLSTM(nn.Module):

    def __init__(self, seq_len=30, h_dim=64, embedding_dim=16, n_samples=3):
        super().__init__()

        self.seq_len = seq_len
        self.h_dim = h_dim
        self.embedding_dim = embedding_dim
        self.n_samples = n_samples
        
        traj_points = self.n_samples*2
        self.decoder = nn.LSTM(self.embedding_dim, self.h_dim, 1)
        self.spatial_embedding = nn.Linear(traj_points, self.embedding_dim) # Last obs * 2 points
        self.hidden2pos = nn.Linear(2*self.h_dim, traj_points)
        self.confidences = nn.Linear(self.h_dim, self.n_samples)

        self.goal_embedding = nn.Linear(2*32,self.h_dim)

    def forward(self, traj_abs, traj_rel, state_tuple, goals):
        """
            traj_abs (1, b, 2)
            traj_rel (1, b, 2)
            state_tuple: h and c
                h : c : (1, b, self.h_dim)
            goals: b x 32 x 2
        """

        t, batch_size, f = traj_abs.shape
        traj_rel = traj_rel.view(t,batch_size,1,f)
        traj_rel = traj_rel.repeat_interleave(self.n_samples, dim=2)
        traj_rel = traj_rel.view(t, batch_size, -1)

        goals = goals.view(goals.shape[0],-1) 
        goals_embedding = self.goal_embedding(goals) # b x h_dim

        pred_traj_fake_rel = []
        decoder_input = F.leaky_relu(self.spatial_embedding(traj_rel.contiguous().view(batch_size, -1))) # bx16
        decoder_input = decoder_input.contiguous().view(1, batch_size, self.embedding_dim) # 1 x batch x 16
        for _ in range(self.seq_len):
            output, state_tuple = self.decoder(decoder_input, state_tuple) # output (1, b, 32)

            input_final = torch.cat((state_tuple[0],
                                     goals_embedding.unsqueeze(0)),dim=2)

            rel_pos = self.hidden2pos(input_final.view(input_final.shape[1],-1)) #(b, 2*m)

            decoder_input = F.leaky_relu(self.spatial_embedding(rel_pos.contiguous().view(batch_size, -1)))
            decoder_input = decoder_input.contiguous().view(1, batch_size, self.embedding_dim)
            pred_traj_fake_rel.append(rel_pos.contiguous().view(batch_size,-1))

        pred_traj_fake_rel = torch.stack(pred_traj_fake_rel, dim=0)
        pdb.set_trace()
        pred_traj_fake_rel = pred_traj_fake_rel.view(self.seq_len, batch_size, self.n_samples, -1)
        pred_traj_fake_rel = pred_traj_fake_rel.permute(1,2,0,3) #(b, m, 30, 2)
        conf = self.confidences(state_tuple[0].contiguous().view(-1, self.h_dim))
        conf = torch.softmax(conf, dim=1)
        return pred_traj_fake_rel, conf

class CGH_MMDecoderLSTM(nn.Module): # Carlos (NOT WORKING A LINEAR PER MODE AT THIS MOMENT)

    def __init__(self, seq_len=30, h_dim=64, embedding_dim=16, n_samples=3):
        super().__init__()

        self.seq_len = seq_len
        self.h_dim = h_dim
        self.embedding_dim = embedding_dim
        self.n_samples = n_samples # K-MultiModality
        self.dim_points = 2 # x|y
        self.num_agents = 1 # Single agent prediction in this case
        
        traj_points = self.n_samples*2
        self.decoder = nn.LSTM(self.embedding_dim, self.h_dim, 1)

        self.spatial_embedding = nn.Linear(self.dim_points, self.embedding_dim)
        self.confidences = nn.Linear(self.n_samples*(self.seq_len*self.dim_points + self.h_dim*self.num_agents), 
                                     self.n_samples)
        # self.confidences = nn.Linear(self.h_dim, self.n_samples)

        # Multi-modality (from LaneGCN)

        norm = "GN"
        ng = 1

        pred = []
        for i in range(self.n_samples):
            pred.append(
                nn.Sequential(
                    # LinearRes(2*self.h_dim, 2*self.h_dim, norm=norm, ng=ng), # Not working now (init_weights in trainer)
                    # nn.Linear(2*self.h_dim, self.dim_points), # If goal_points are available
                    nn.Linear(self.h_dim, self.dim_points)
                )
            )
        self.pred = nn.ModuleList(pred)

    def forward(self, traj_abs, traj_rel, state_tuple, goal_points=None):
        """
        N.B. In Argoverse 1.0 we only predict an important AGENT, so num_agents
        here is equal to 1.

            traj_abs [num_agents, batch_size, dim_points] -> dim_points = 2 (x|y)
            traj_rel [num_agents, batch_size, 2]
            state_tuple: h and c
                h : c : [num_agents, batch_size, h_dim]
            goal_points: [batch_size, 32 x 2] (Absolute coordinates)
        """

        num_agents, batch_size, dim_points = traj_abs.shape
        traj_rel = traj_rel.view(num_agents, batch_size, -1)

        decoder_input = F.leaky_relu(self.spatial_embedding(traj_rel.contiguous().view(batch_size, -1))) # batch x 16
        decoder_input = decoder_input.contiguous().view(1, batch_size, self.embedding_dim) # 1 x batch x 16
        
        # Multimodality 

        ## Repeat the input for the different modes (multimodality)

        decoder_input = self.n_samples * [decoder_input] # n_samples (modes) -> Each index has a Tensor (num_agents x batch x 16)
        state_tuple = self.n_samples * [state_tuple] # n_samples (modes) -> Each index has a tuple (h,c)

        pred_traj_fake_rel_mm = [] # Store the rel-rel predictions here
        final_state_tuple_mm = []

        for mod_index in range(self.n_samples):
            pred_traj_fake_rel = []
            for _ in range(self.seq_len):
                output, aux_state_tuple = self.decoder(decoder_input[mod_index], state_tuple[mod_index])
                state_tuple[mod_index] = aux_state_tuple
                
                input_final = state_tuple[mod_index][0]

                rel_pos = self.pred[mod_index](input_final.view(input_final.shape[1],-1))
                pred_traj_fake_rel.append(rel_pos.contiguous().view(batch_size,-1))

                # Update decoder input for the next iteration

                aux_decoder_input = F.leaky_relu(self.spatial_embedding(rel_pos.contiguous().view(batch_size, -1)))
                aux_decoder_input = aux_decoder_input.contiguous().view(1, batch_size, self.embedding_dim)
                decoder_input[mod_index] = aux_decoder_input

            pred_traj_fake_rel = torch.stack(pred_traj_fake_rel, dim=0)
            pred_traj_fake_rel_mm.append(pred_traj_fake_rel)
            final_state_tuple_mm.append(state_tuple[mod_index][0]) # only append the hidden states (h) [0]
 
        # pdb.set_trace()
        pred_traj_fake_rel_mm = torch.stack(pred_traj_fake_rel_mm, dim=0) # num_samples x seq_len x batch_size x dim_point
        
        pred_traj_fake_rel_mm = pred_traj_fake_rel_mm.permute(2,0,1,3) # (b, m, 30, 2)
        final_state_tuple_mm = torch.stack(final_state_tuple_mm, dim=0)
        final_state_tuple_mm = final_state_tuple_mm.permute(2,0,1,3)

        ## Compute confidences

        conf_input = torch.cat((pred_traj_fake_rel_mm.contiguous().view(batch_size, self.n_samples,-1),
                                final_state_tuple_mm.contiguous().view(batch_size, self.n_samples,-1)), dim=2)
        conf_input = conf_input.view(batch_size,-1)
        # conf_input = state_tuple[0][0].contiguous().view(-1, self.h_dim)
        # pdb.set_trace()
        conf = self.confidences(conf_input)
        conf = torch.softmax(conf, dim=1) # batch_size x num_samples
        # pdb.set_trace()
        return pred_traj_fake_rel_mm, conf

class PredNet(nn.Module):
    """
    Final motion forecasting with Linear Residual block
    """
    def __init__(self, config):
        super(PredNet, self).__init__()
        self.config = config
        norm = "GN"
        ng = 1

        n_actor = config["n_actor"]

        pred = []
        for i in range(config["num_mods"]):
            pred.append(
                nn.Sequential(
                    LinearRes(n_actor, n_actor, norm=norm, ng=ng),
                    nn.Linear(n_actor, 2 * config["num_preds"]),
                )
            )
        self.pred = nn.ModuleList(pred)

        self.att_dest = AttDest(n_actor)
        self.cls = nn.Sequential(
            LinearRes(n_actor, n_actor, norm=norm, ng=ng), nn.Linear(n_actor, 1)
        )

    def forward(self, actors: torch.Tensor, actor_idcs: List[torch.Tensor], actor_ctrs: List[torch.Tensor]) -> Dict[str, List[torch.Tensor]]:
        preds = []
        for i in range(len(self.pred)):
            preds.append(self.pred[i](actors))
        reg = torch.cat([x.unsqueeze(1) for x in preds], 1)
        reg = reg.view(reg.size(0), reg.size(1), -1, 2)

        for i in range(len(actor_idcs)):
            idcs = actor_idcs[i]
            ctrs = actor_ctrs[i].view(-1, 1, 1, 2)
            reg[idcs] = reg[idcs] + ctrs

        dest_ctrs = reg[:, :, -1].detach()
        feats = self.att_dest(actors, torch.cat(actor_ctrs, 0), dest_ctrs)
        cls = self.cls(feats).view(-1, self.config["num_mods"])

        cls, sort_idcs = cls.sort(1, descending=True)
        row_idcs = torch.arange(len(sort_idcs)).long().to(sort_idcs.device)
        row_idcs = row_idcs.view(-1, 1).repeat(1, sort_idcs.size(1)).view(-1)
        sort_idcs = sort_idcs.view(-1)
        reg = reg[row_idcs, sort_idcs].view(cls.size(0), cls.size(1), -1, 2)

        out = dict()
        out["cls"], out["reg"] = [], []
        for i in range(len(actor_idcs)):
            idcs = actor_idcs[i]
            ctrs = actor_ctrs[i].view(-1, 1, 1, 2)
            out["cls"].append(cls[idcs])
            out["reg"].append(reg[idcs])
        return out

class AttDest(nn.Module):
    def __init__(self, n_agt: int):
        super(AttDest, self).__init__()
        norm = "GN"
        ng = 1

        self.dist = nn.Sequential(
            nn.Linear(2, n_agt),
            nn.ReLU(inplace=True),
            Linear(n_agt, n_agt, norm=norm, ng=ng),
        )

        self.agt = Linear(2 * n_agt, n_agt, norm=norm, ng=ng)

    def forward(self, agts: torch.Tensor, agt_ctrs: torch.Tensor, dest_ctrs: torch.Tensor) -> torch.Tensor:
        n_agt = agts.size(1)
        num_mods = dest_ctrs.size(1)

        dist = (agt_ctrs.unsqueeze(1) - dest_ctrs).view(-1, 2)
        dist = self.dist(dist)
        agts = agts.unsqueeze(1).repeat(1, num_mods, 1).view(-1, n_agt)

        agts = torch.cat((dist, agts), 1)
        agts = self.agt(agts)
        return agts

class BaseDecoder(nn.Module):
    """The base decoder interface for the encoder-decoder architecture.
    Defined in :numref:`sec_encoder-decoder`"""
    
    def __init__(self, **kwargs):
        super().__init__()
    
    def init_state(self, enc_outputs, *args):
        raise NotImplementedError
    
    def forward(self, X, state):
        raise NotImplementedError