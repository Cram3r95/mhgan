import pandas as pd
import numpy as np
import pdb

filename = "/home/robesafe/libraries/SoPhie/evaluate/argoverse/test_trajectories/mp_so_goals_decoder_evaluation.csv"
df = pd.read_csv(filename,sep=" ")

n = 2
df.drop(df.tail(n).index, inplace=True) # Remove last two rows

sota_ade = 1.57
mean_ade = df['ADE'].mean()

# bb = len(df[(df['ADE']<=sota_ade

pdb.set_trace()