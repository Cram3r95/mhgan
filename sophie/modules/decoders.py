import torch
from torch import nn

from sophie.modules.layers import MLP

class Decoder(nn.Module):

    def __init__(self, config):
        super(Decoder, self).__init__()

        self.num_layers = config.num_layers
        self.hidden_dim = config.hidden_dim
        self.emb_dim = config.emb_dim
        self.decoder_dropout = config.dropout
        self.seq_len = config.seq_len

        self.decoder = nn.LSTM(
            self.emb_dim,
            self.hidden_dim,
            self.num_layers,
            dropout=self.decoder_dropout
        )

        self.spatial_embedding = nn.Linear(
            config.linear_1.input_dim,
            config.linear_1.output_dim
        )
        self.hidden2pos = nn.Linear(
            config.linear_2.input_dim,
            config.linear_2.output_dim
        )

    def init_hidden(self, batch):
        return (
            torch.zeros(self.num_layers, batch, self.hidden_dim).cuda(),
            torch.zeros(self.num_layers, batch, self.hidden_dim).cuda()
        )

    def forward(self,input_data):
        """
        input_data: (batch, 2)
        """
        predicted_trajectories = []
        batch = input_data.size(0)
        input_embedding = self.spatial_embedding(input_data)
        input_embedding = input_embedding.view(
            1, batch, self.emb_dim
        )
        print("Batch: ", batch)
        state_tuple = self.init_hidden(batch)

        print("State tuple: ", state_tuple, len(state_tuple))

        for _ in range(self.seq_len):
            output, state = self.decoder(input_embedding, state_tuple)
            rel_pos = self.hidden2pos(output.view(-1, self.hidden_dim))
            embedding_input = rel_pos
            decoder_input = self.spatial_embedding(embedding_input)
            decoder_input = decoder_input.view(1, batch, self.emb_dim)
            predicted_trajectories.append(rel_pos.view(batch, -1))
            
        pred_traj_fake_rel = torch.stack(predicted_trajectories, dim=0)
        print("pred_traj_fake_rel: ", pred_traj_fake_rel.shape)
        return pred_traj_fake_rel, state_tuple[0]
