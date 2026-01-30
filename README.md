# Individual Project - Generative Scene Generation

## Overview

This project, **Generative Scene Generation**, explores how **AI-generated visual content** (images and videos) can be used to construct **3D scenes** through the process of **3D Gaussian Splatting**. The work combines insights from computer vision, deep learning, and 3D reconstruction to evaluate the potential of generative models for creating realistic 3D environments from synthetic data.

## Project Goals

- Study the **3D Gaussian Splatting** paper and related research to understand the theoretical framework behind the technique.
- Investigate how **3D Gaussians** can represent 3D space derived from **AI-generated imagery**.
- Develop a **practical implementation** that uses open-source **AI image** and **video generation** tools to create visual data, which will then be processed with **COLMAP** (or other software) and **3D Gaussian Splatting** to form a 3D scene.
- Compare the AI-generated 3D reconstruction with a **real-world 3D scan**, identify the limitations, and propose potential improvements or solutions.

## Methodology

1. **Data Generation:** Use open-source AI models to produce images and videos as input.
2. **3D Reconstruction:** Employ **COLMAP** for structure-from-motion (SfM) processing and **3D Gaussian Splatting** for scene representation.
3. **Comparison and Analysis:** Evaluate how the AI-generated reconstruction differs from real-world 3D data and discuss corrective techniques.

## Plan Of Action (WIP)

### Docker

Run the following commands to start the system

```bash
# Start docker
sudo systemctl start docker

# Create the docker container using docker-compose
./docker/run_docker.sh -bu 12.8.0

# In the docker folder where the docker-compose.yml file is located:
docker exec -it lichtfeld-studio bash
```

### Using the system

1. Create a video file and place it in the current folder
2. Run the file: `./install_colmap.sh` (if colmap isn't installed already)
3. Run the file: `./pipeline_colmap.sh <video.mp4> <new_project_dir_name> <fps>`
4. Run the following command: `./build/LichtFeld-Studio -d <colmap_project_dir_name> -o output/<folder_name> --gut`
5. In the GUI of LichtFeld-Studio, train the model on the images
6. Check if the folder `output/<folder_name>` contains a `.ply` file.
7. Done

## Author

- Denis Topallaj
- Individual Project – Generative Scene Generation
- University of Hasselt, 2025-2026k
