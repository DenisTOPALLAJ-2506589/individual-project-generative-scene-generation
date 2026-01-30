# Information during recap

- colmap to validate
- real vs AI videos (image to video, difficult because you can't really do it
  objectively)
- world explorer (uses text to image models and continues to build upon the
  images and thus creates different views of that space until the entire pace is
  filled in)
- what kind of prompts to generate the videos? (360°? how consistent is this?)

## Paper

- related work
- implementation (can split up in multiple smaller section)
- results
- conclusion

# Claud.ai

Here are several conceptual approaches to generate video or data for 3D Gaussian splatting reconstruction:

## 1. **Multi-View Diffusion Generation**

Generate multiple consistent views of the same scene from different angles using multi-view diffusion models (like Zero-1-to-3, SyncDreamer, or MVDream). These models take a single image and generate novel viewpoints while maintaining 3D consistency. Feed these multi-view images to your Gaussian splatting pipeline as if they were camera captures from different positions.

## 2. **Video Diffusion with Camera Control**

Use video generation models with camera motion control (like MotionCtrl or CameraCtrl) to generate videos with known camera trajectories. You provide text/image prompts along with desired camera paths (orbit, zoom, pan), and the model generates video following that motion. The known camera poses are crucial for 3D reconstruction.

## 3. **NeRF-to-Video-to-Gaussian Pipeline**

First generate a NeRF representation from text using models like DreamFusion or Magic3D, then render video sequences from the NeRF with arbitrary camera paths, and finally use those rendered frames as input to Gaussian splatting. This gives you clean synthetic data with perfect camera poses.

## 4. **Monocular Video + Depth + Pose Estimation**

Generate a video using standard video diffusion models (Runway, Pika, Sora-style models), then post-process it with:

- Monocular depth estimation (DepthAnything, Marigold, MiDaS)
- Camera pose estimation (COLMAP, DROID-SLAM)
- Optional: depth refinement using geometric consistency

This reconstructs the camera trajectory and depth from the generated video.

## 5. **Outpainting/Inpainting Spirals**

Start with an initial image, then progressively outpaint in a spiral or structured pattern while tracking virtual camera movement. Each outpainted frame represents a new viewpoint. Models like Stable Diffusion with ControlNet (depth/normal maps) help maintain consistency. Build a synthetic camera trajectory as you generate.

## 6. **Layered Depth Image (LDI) Generation**

Generate not just RGBD but layered depth images where each pixel has multiple depth layers with color/alpha values. Models can generate these directly or you can construct them from video with depth. LDIs handle occlusions better and can be rendered from nearby viewpoints to create the multi-view data Gaussian splatting needs.

## 7. **Sparse View Generation + Interpolation**

Generate a few key views (3-8 images) from strategic angles using image generation models, then use view synthesis techniques or video interpolation models to generate intermediate frames. The sparse views anchor the 3D structure while interpolation fills in the motion.

## 8. **4D Generation (Space + Time)**

Use emerging 4D generation models that create dynamic scenes with temporal consistency. These generate sequences where objects move/deform consistently across time with implicit 3D understanding. Extract frames at different time steps as your multi-view input.

## 9. **Stereo Pair Generation**

Generate stereoscopic image pairs (left/right eye views) using models trained for stereo consistency, then use stereo matching algorithms to extract depth. Generate multiple stereo pairs from different positions to build your scene coverage.

## Key Considerations

- **Camera pose knowledge** is critical - you need to know (or estimate) where each frame was "captured" from
- **Multi-view consistency** matters more than per-frame quality
- **Sufficient baseline** between views is needed for good 3D reconstruction
- **Overlap** between views ensures the Gaussian splats can be properly constrained

The WorldGen approach you mentioned (panorama + depth) is elegant because panoramas implicitly encode 360° information. Most other approaches require either generating multiple views with known relationships or estimating that relationship post-generation.

Great question! You're essentially looking for **perceptual and structural similarity metrics** that can account for the fact that AI might "hallucinate" or reimagine elements while still capturing the essence of a space. Here are metrics organized by what they measure:

## Geometric/Structural Fidelity

**1. Depth Map Correlation**

- Extract depth maps from both AI and human videos
- Compare depth distributions and structural layouts
- Measures if walls, furniture, and spatial relationships are geometrically similar even if textures differ
- Useful because layout matters more than exact object identity

**2. Semantic Segmentation Overlap (IoU)**

- Segment both videos into categories (wall, floor, furniture, window, etc.)
- Calculate Intersection over Union for each category
- Tells you if AI placed a "chair" where humans filmed a "chair," even if they look different
- Use models like Mask2Former or Segment Anything

**3. Edge/Contour Similarity**

- Extract edge maps (Canny, HED) from both videos
- Compare structural boundaries and spatial composition
- Captures room layout and major object boundaries regardless of texture/color

**4. Pose Graph Alignment**

- Extract camera trajectories from both videos (COLMAP, ORB-SLAM)
- Compare if the AI video follows similar camera movement through 3D space
- Measures if the "navigability" of the space is preserved

## Perceptual/Appearance Metrics

**5. LPIPS (Learned Perceptual Image Patch Similarity)**

- Measures perceptual similarity using deep features
- More aligned with human perception than pixel-level metrics
- Good for "does this feel similar" even with different objects

**6. CLIP Similarity Score**

- Encode frames from both videos with CLIP
- Compare embedding similarity in semantic space
- Captures high-level scene understanding ("bedroom vibe" vs exact objects)
- Can use text prompts to query specific attributes

**7. FID/FVD (Fréchet Distance)**

- Fréchet Inception Distance (images) or Fréchet Video Distance (videos)
- Measures distribution similarity in feature space
- Tells you if AI-generated frames come from the same "statistical distribution" as real footage

**8. DINO Feature Similarity**

- Use self-supervised vision models (DINOv2) to extract features
- These capture semantic object understanding without explicit labels
- Good for measuring if similar "stuff" exists in similar spatial arrangements

## Object/Content Analysis

**9. Object Detection Concordance**

- Run object detection on both videos (YOLO, Grounding DINO)
- Compare: what objects appear, their counts, spatial positions
- Create a "room inventory" and measure overlap
- Accept that AI might add/remove items but check if categories match

**10. Scene Graph Similarity**

- Build scene graphs (objects + relationships) for both videos
- Compare relational structure: "chair near table," "lamp on desk"
- Measures if spatial relationships are preserved even if objects differ

**11. Style/Texture Distribution**

- Analyze color histograms, texture features, lighting characteristics
- Measures if AI captured the "mood" and aesthetic even if not pixel-accurate

## Temporal/Motion Metrics

**12. Optical Flow Consistency**

- Compare motion patterns between videos
- Measures if camera movement through space is similar
- Useful for dynamic scenes or walkthroughs

**13. Temporal Coherence Score**

- Measure frame-to-frame consistency in both videos
- AI often struggles with temporal stability (flickering, morphing)
- Detect if AI maintains object permanence like human footage

## Novel Metrics for Your Use Case

**14. Hallucination Density**

- Identify objects in AI video not present in human video
- Calculate percentage of "invented" content
- Weight by visual prominence/size

**15. Layout Topology Score**

- Create abstract topological representations of both spaces
- Measure if connectivity, room shape, and major zones align
- Ignores decorative details, focuses on spatial structure

**16. Feature Point Matching**

- Extract keypoints (SIFT, SuperPoint) from both videos
- Attempt to match features between corresponding frames
- Low matches = high hallucination; high matches = good fidelity

**17. Semantic Density Map Comparison**

- Create heatmaps showing "where stuff is" in 3D space
- Compare density patterns: cluttered areas, empty areas, focal points
- Agnostic to what the stuff actually is

## Composite Metrics

**18. Weighted Reality Score**
You could create a composite metric like:

```
Reality_Score = w1*(Depth_Correlation) +
                w2*(Semantic_IoU) +
                w3*(CLIP_Similarity) +
                w4*(1 - Hallucination_Density) +
                w5*(Layout_Topology)
```

Where weights reflect what matters most for your application.

## Recommended Approach for Your Scenario

For comparing AI room generation to real footage:

**Tier 1 (Most Important):**

- Semantic Segmentation IoU - are major elements in the right places?
- Depth Map Correlation - is the 3D structure similar?
- CLIP Similarity - does it "feel" like the same space?

**Tier 2 (Secondary):**

- Object Detection Concordance - similar objects present?
- Edge Similarity - structural boundaries preserved?
- Hallucination Density - how much was invented?

**Tier 3 (Nice to have):**

- LPIPS - perceptual quality
- Camera Pose Alignment - similar viewpoint trajectory
- Scene Graph Similarity - relational structure

This approach acknowledges that AI won't recreate your exact room but measures whether it captures the spatial essence, layout, and character of the space in a way that would be useful for 3D reconstruction or VR/AR applications.

# Perplexity.ai

There are several conceptually distinct ways to generate a video suitable for Gaussian 3D model generation—each creating data that allows depth estimation, spatial reconstruction, and temporally consistent frames for Gaussian splatting. Below are several conceptual strategies beyond the WorldGen-Unik3D panorama method you mentioned.

### Using Dynamic 3D Gaussian Fields

Projects such as GS-DiT propose generating **dynamic 3D Gaussian fields** directly tied to dense 3D point tracking within videos. The process begins from any monocular input (e.g., a short generated or real-world video) and builds a temporally consistent 3D Gaussian representation. The dynamic scene is then rendered from multiple camera angles to produce new views. Conceptually, this allows text-to-video or image-to-video generators to act as “guides” for 4D (spatio-temporal) reconstruction.[1]

### Text-to-3D Video Synthesis

A more generative approach uses **text-driven AI synthesis** where a diffusion or transformer-based model creates both the 3D structure and temporal motion directly from a prompt. The video generator outputs data in 3D-aware latent space, producing 2D frames along camera paths with implicit depth information. These 3D latent maps can be lifted into Gaussian point clouds via estimated depth channels or through an internal neural field representation.[2]

### Image or Video-to-Gaussian Scene Reconstruction

Systems like **Vid2Scene** and **VIVERSE Scene AI** support turning existing videos or sets of images into 3D Gaussian Splat scenes. You can use a generated image sequence, even from a simple generative text-to-video model, as the source input. The conversion step uses structure-from-motion or learned monocular depth estimation pipelines that map RGB and motion into a consistent 3D Gaussian representation.[3][7]

### Image Lifting and Camera Simulation

Another conceptual technique is **synthetic camera motion over still images**. By artificially simulating a camera orbit or pan across a generated image (using depth estimation tools such as MiDaS or Unik3D), you can reconstruct a multi-view sequence that mimics true parallax. This image depth-lifting method transforms a single image into a pseudo-3D video suitable for Gaussian splatting when combined with per-pixel geometry estimates.

### Feed-forward 3D Scene Generation Models

New feed-forward 3D scene generators (e.g., **Lyra** from NVIDIA Labs) produce 3D or 4D environments from one source image or a video clip. They learn structure directly in 3D latent space, meaning the model itself can output voxel-like or Gaussian field points—ideal for feeding directly into Gaussian representation pipelines without classical multi-view optimization.[5]

### Generative Gaussian Splatting

There are also generative methods such as **Generative Gaussian Splatting (GGS)** that blend Gaussian field construction with pre-trained video diffusion models. These use the generative process itself to predict Gaussian parameters (mean, covariance, opacity) for each 3D point directly from text, image, or video inputs—bypassing the explicit RGBD or panorama steps.[9]

Thus, conceptually, you can construct input for a 3D Gaussian model in several ways:

1. Generate a dynamic 3D Gaussian field directly (GS-DiT style).
2. Use text-to-3D-video synthesis to produce temporally coherent 3D-aware frames.
3. Convert video/image sequences to Gaussian splats (Vid2Scene method).
4. Generate pseudo-camera views from images with depth inference.
5. Employ feed-forward 3D-scene creation directly from single-view content.
6. Use generative Gaussian-based models that output 3D representations intrinsically.

[1](https://openaccess.thecvf.com/content/CVPR2025/papers/Bian_GS-DiT_Advancing_Video_Generation_with_Dynamic_3D_Gaussian_Fields_through_CVPR_2025_paper.pdf)
[2](https://reelmind.ai/blog/how-to-make-ai-create-a-3d-video-techniques-for-generating-3d-videos-using-ai)
[3](https://www.viverse.com/ai/scene)
[4](https://www.youtube.com/watch?v=GBSaonVuktk)
[5](https://github.com/nv-tlabs/lyra)
[6](https://superagi.com/ai-3d-model-generation-techniques-comparing-text-image-and-video-methods-for-optimal-product-visualization/)
[7](https://www.reddit.com/r/GaussianSplatting/comments/1i7ixsh/vid2scene_a_free_endtoend_video_to_gaussian_splat/)
[8](https://www.youtube.com/watch?v=vfZsOGQikFc)
[9](https://katjaschwarz.github.io/ggs/)
[10](https://www.leidenlearninginnovation.org/stories/gaussian-splatting-rapid-3d-with-ai-tools/)
