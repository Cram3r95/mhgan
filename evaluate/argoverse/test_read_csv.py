import pandas as pd
import numpy as np
import pdb

filename = "/home/robesafe/libraries/SoPhie/evaluate/argoverse/test_trajectories/mp_so_evaluation.csv"
df = pd.read_csv(filename,sep=" ")

# Curr: 1.88 & 4.18
# (1) Unimodal baseline (*) & 1.98  & 4.47 
# (2) Uni. baseline + Target points & 1.78  & 4.13 
# (3) Uni. baseline + Class balance & 1.82  & 4.09
# (4) Uni. baseline + TP + CB & 1.67  & 3.82 

n = 2
df.drop(df.tail(n).index, inplace=True) # Remove last two rows

# mu_ade, sigma_ade = 0.1, 0.03 
# mu_fde, sigma_fde = 0.29, 0.04

# noise_ade = np.random.normal(mu_ade, sigma, [2,2]) 

pdb.set_trace()