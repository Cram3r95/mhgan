## Problems
* dummies
    * bad influence in model
* Normalization of rel and abs
* Imbalanced "class" problem
    * relatives min and max
    * few curves in dataset (?)
* Model output in range (0.4,0.6). Normalized
* Decoder Activation Function
    * Sigmoid
    * ReLU
    * PReLU
* Temporal Decoder
    * It takes into account full trajectory
* Layernorm and LeakyReLU 
* Train
    * Generator -> Normalized
    * Discriminator -> no Normalized
* Deep Prediction model based on sgan
    * abs normalized -> min 0
    * rel normalized -> calculated with abs norm
* Trainer problem
    * discriminator step -> detach()
    * check_accuracy -> mask

* multi head self attention local
    * mask concentrate information in agent
* learning rate scheduler
* weight decay
* l2 weight
    * [1, 0.25, 0.2, 0.15, 0.1 , 0.05]
* addnorm -> no converge

## Experimento 1
* multi to single
* Decoder
* only social attention
* rel trajectory space (-3.5,3.5)
* metrics
    * 6.503
    * 14.565

## Experimento 2
* 1400
    * bce loss
    * ade: 12.6
    * fde: 24.7
* 1400
    * manual bce loss - no sigmoid discriminator
    * ade: 12.7
    * fde: 24.8

# Experimento 11
    * ade: 3.3

# Experimento 12
    * ade ~4
    * local attention
    * l2 0.05

# Experimento 13
    * addnorm
    * malo, no converge

# Experimento 14
    * learning rate scheduler
        * 1e-3
        * 0.95
        * 5.2 ade 1k iterations
        * 0.05 de dataset -> learning rate baja muy rapido

# Experimento G 1
    * 5%
    * oscila
    * lr: 1e-3
    * sube ade a +3 -> 7k -> min 2.7
    * mse

# Experimento G 2
    * mse
    * ade min a 2.5
    * 5 % dataset
    * lr: 1e-4
    * tendencia a bajar en iter 12k
    * loss estable

# Experimento G 3
    * nll
    * baja mas rapido
    * lr: 1e-3
    * ade 2.5 -> 6k

# Experimento G 4
    * nll
    * parecido a g 3
    * lr: 1e-4

# Experimento G 5 / 6
    * mse+nll
    * oscila bastante
    * lr: 1e-3
    * 9k -> ade empieza a subir
    * Exp 6 -> lr: 1e-4 -> mas estable -> 20k iteraciones -> 2.2 ade -> tendencia a bajar lentamente -> bajar lr o regularizacion

# Experimento G 7
    * mse+nll
    * lr: 1e-4
    * 50 % dataset
    * ade 1.96

# Experimento G 8
    * load G 7
    * mse+nll
    * lr: 1e-4
    * 75 % dataset
    * ADE: 1.9047845275628752
    * FDE: 4.2565066906233575

# Experimento G 9
    * load G 8
    * mse+nll*2
    * lr: 5.0e-5
    * 75 % dataset
    * ADE: 1.90
    * FDE: 4.25 

# Experimento G 10
    * load G 8
    * mse_w+nll*2
    * lr: 1.0e-3
    * 75 % dataset
    * ADE: 1.90
    * FDE: 4.25

# Experimento G trans (E) 2 - x -> multi - multi
    * 10% dataset
    * mse_w+nll
    * lr: 1.0e-3
    * ade: 1.56
    * fde: 3.34

# Experimento G trans (E) 3 - x -> multi - single
    * 25% dataset
    * mse_w+nll
    * lr: 1.0e-3
    * load g trans 2
    * ade: 2.59
    * fde: 5.71

# Experimento G trans (E) 4 - x -> multi - single
    * 50% dataset
    * mse_w+nll
    * lr: 1.0e-3
    * load g trans 2
    * ade: 2.82
    * fde: 5.97

# Experimento G trans (E+D) 5 - x -> multi - single
    * 25%

# Experimento G trans (E+D) 6 - x -> multi - single
    * 50%

# mp_so | h_dim = 32 | gen_exp/exp_multiloss_1
    * ADE: 1.89
    * FDE: 4.22
    * 5.0e-4
    * 25% dataset
    * lr scheduler
        * 1.0e-3 | 7000 iters

# mp_so | h_dim = 32 | gen_exp/exp_multiloss_2
    * ADE: 
    * FDE: 
    * 1.0e-4
    * 25% dataset
    * lr scheduler
        * 1.0e-4 | 7000 iters

# mp_so | h_dim = 128 | gen_exp/exp_multiloss_128hdim_1
    * 25% dataset
    * lr scheduler
        * 1.0e-3 | 7000 iters