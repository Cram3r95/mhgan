# SoPhie
SoPhie: An Attentive GAN for Predicting Paths Compliant to Social and Physical Constraints

<img src="media/system_pipeline.svg"/>

## Overview
The design of a safe and reliable Autonomous Driving stack (ADS) is one of the most challenging tasks of our era. These ADS are expected to be driven in highly dynamic environments with full autonomy and a reliability greater than human beings. In that sense, to efficiently and safely navigate through arbitrarily complex traffic scenario, ADS must have the ability to forecast the future trajectories of surrounding actors. Current state-of-the-art models are typically based on recurrent, graph and convolutionals networks, achieving noticeable results in the context of vehicle prediction. In this paper we explore the influence of attention in generative models for motion prediction, considering both physical and social context to compute the most plausible trajectories. We first encode the past trajectories using a Long Short-Term Memory (LSTM) network, which serves as input to a Multi-Head Self-Attention module that computes the social context. On the other hand, we formulate a weighted interpolation to calculate the velocity and orientation in the last observation frame in order to calculate aceptable target points, extracted from the driveable of the HDMap information, which represents our physical context. Finally, the input of our generator is a white noise vector sampled from a multivariate normal distribution while the social and physical context are its conditions, in order to predict the most plausible trajectories. We validate our method using the Argoverse Motion Forecasting Benchmark 1.1, achieving competitive results. To encourage the use of generative models with attention for motion prediction, our code is publicly available at ([Code](https://github.com/Cram3r95/mhgan)).

<!-- Second, the system is validated ([Qualitative Results](https://cutt.ly/uk9ziaq)) in the CARLA simulator fulfilling the requirements of the Euro-NCAP evaluation for Unexpected Vulnerable Road Users (VRU), where a pedestrian suddenly jumps into the road and the vehicle has to avoid collision or reduce the impact velocity as much as possible. Finally, a comparison between our HD map based perception strategy and our previous work with rectangular based approach is carried out, demonstrating how incorporating enriched topological map information increases the reliability of the Autonomous Driving (AD) stack. Code is publicly available ([Code](https://github.com/Cram3r95/map-filtered-mot)) as a ROS package. -->

## Requirements

<!-- Note that due to ROS1 limitations (till Noetic version), specially in terms of TF ROS package, we limited the Python version to 2.7. Future works will integrate the code using ROS1 Noetic or ROS2, improving the version to Python3. -->

<!-- - Python3.8 
- Numpy
- ROS melodic
- HD map information (Monitorized lanes)
- scikit-image==0.17.2
- lap==0.4.0 -->
- OpenCV==4.1.1
- YAML
- ProDict
- torch (1.8.0+cu111)
- torchfile (0.1.0)
- torchsummary (1.5.1)
- torchtext (0.5.0)
- torchvision (0.9.0+cu111)

## Get Started and Usage
Coming soon ...
## Quantitative results
Coming soon ...
## Qualitative results
Coming soon ...

  - TO DOs:

	- [ ] Study Adaptive Average Pool 2D to apply in the LSTM based encoder (at this moment we are taking final_h =    states[0], so the last one, instead of average, max pool, etc.) and the linear feature of the physical_attention in order to receive different width x height images and get a fixed-size output 
    - [ ] Study the attention module, different approaches, specially the Social Attention module

