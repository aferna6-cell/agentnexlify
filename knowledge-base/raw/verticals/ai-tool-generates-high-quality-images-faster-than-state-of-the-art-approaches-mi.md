---
source_url: https://news.mit.edu/2025/ai-tool-generates-high-quality-images-faster-0321
fetched_at: 2026-04-12T22:25:10Z
category: verticals
title: "AI tool generates high-quality images faster than state-of-the-art approaches | MIT News | Massachusetts Institute of Technology"
---

AI tool generates high-quality images faster than state-of-the-art approaches | MIT News | Massachusetts Institute of Technology 

 Skip to content ↓ 

 Massachusetts Institute of Technology 

 See More Results 

 Suggestions or feedback? 

 Browse By

 Topics

 View All → 

 Explore:

 Machine learning 

 Sustainability 

 Startups 

 Black holes 

 Classes and programs 

 Departments

 View All → 

 Explore:

 Aeronautics and Astronautics 

 Brain and Cognitive Sciences 

 Architecture 

 Political Science 

 Mechanical Engineering 

 Centers, Labs, & Programs

 View All → 

 Explore:

 Abdul Latif Jameel Poverty Action Lab (J-PAL) 

 Picower Institute for Learning and Memory 

 Media Lab 

 Lincoln Laboratory 

 Schools

 School of Architecture + Planning 

 School of Engineering 

 School of Humanities, Arts, and Social Sciences 

 Sloan School of Management 

 School of Science 

 MIT Schwarzman College of Computing 

 View all news coverage of MIT in the media → 

 Listen to audio content from MIT News → 

 Subscribe to MIT newsletter → 

 Close 

 Breadcrumb

 MIT News 

 AI tool generates high-quality images faster than state-of-the-art approaches

 AI tool generates high-quality images faster than state-of-the-art approaches 

 Researchers fuse the best of two popular methods to create an image generator that uses less energy and can run locally on a laptop or smartphone. 

 Adam Zewe 
 | 
 MIT News 

 Publication Date : 

 March 21, 2025 

 Press Inquiries 

 Press Contact : 

 Melanie 

 Grados 

 Email:
 mgrados@mit.edu 

 Phone:
 617-253-1682 

 MIT News Office 

 Media Download

 ↓ Download Image 

 Caption : 

 Researchers combined two types of generative AI models, an autoregressive model and a diffusion model, to create a tool that leverages the best of each model to rapidly generate high-quality images. 

 Credits : 

 Credit: Christine Daniloff, MIT; image of astronaut on horseback courtesy of the researchers 

 ↓ Download Image 

 Caption : 

 The new image generator, called HART (short for Hybrid Autoregressive Transformer), can generate images that match or exceed the quality of state-of-the-art diffusion models, but do so about nine times faster. 

 Credits : 

 Credit: Courtesy of the researchers 

 *Terms of Use:

 Images for download on the MIT News office website are made available to non-commercial entities, press and the general public under a 
 Creative Commons Attribution Non-Commercial No Derivatives license .
 You may not alter the images provided, other than to crop them to size. A credit line must be used when reproducing images; if one is not provided 
 below, credit the images to "MIT." 

 Close 

 Caption : 

 Researchers combined two types of generative AI models, an autoregressive model and a diffusion model, to create a tool that leverages the best of each model to rapidly generate high-quality images. 

 Credits : 

 Credit: Christine Daniloff, MIT; image of astronaut on horseback courtesy of the researchers 

 Caption : 

 The new image generator, called HART (short for Hybrid Autoregressive Transformer), can generate images that match or exceed the quality of state-of-the-art diffusion models, but do so about nine times faster. 

 Credits : 

 Credit: Courtesy of the researchers 

 Previous image 
 Next image 

 The ability to generate high-quality images quickly is crucial for producing realistic simulated environments that can be used to train self-driving cars to avoid unpredictable hazards, making them safer on real streets.
 But the generative artificial intelligence techniques increasingly being used to produce such images have drawbacks. One popular type of model, called a diffusion model, can create stunningly realistic images but is too slow and computationally intensive for many applications. On the other hand, the autoregressive models that power LLMs like ChatGPT are much faster, but they produce poorer-quality images that are often riddled with errors.
 Researchers from MIT and NVIDIA developed a new approach that brings together the best of both methods. Their hybrid image-generation tool uses an autoregressive model to quickly capture the big picture and then a small diffusion model to refine the details of the image.
 Their tool, known as HART (short for hybrid autoregressive transformer), can generate images that match or exceed the quality of state-of-the-art diffusion models, but do so about nine times faster.
 The generation process consumes fewer computational resources than typical diffusion models, enabling HART to run locally on a commercial laptop or smartphone. A user only needs to enter one natural language prompt into the HART interface to generate an image.
 HART could have a wide range of applications, such as helping researchers train robots to complete complex real-world tasks and aiding designers in producing striking scenes for video games.
 “If you are painting a landscape, and you just paint the entire canvas once, it might not look very good. But if you paint the big picture and then refine the image with smaller brush strokes, your painting could look a lot better. That is the basic idea with HART,” says Haotian Tang SM ’22, PhD ’25, co-lead author of a new paper on HART .
 He is joined by co-lead author Yecheng Wu, an undergraduate student at Tsinghua University; senior author Song Han, an associate professor in the MIT Department of Electrical Engineering and Computer Science (EECS), a member of the MIT-IBM Watson AI Lab, and a distinguished scientist of NVIDIA; as well as others at MIT, Tsinghua University, and NVIDIA. The research will be presented at the International Conference on Learning Representations.
 The best of both worlds 
 Popular diffusion models, such as Stable Diffusion and DALL-E, are known to produce highly detailed images. These models generate images through an iterative process where they predict some amount of random noise on each pixel, subtract the noise, then repeat the process of predicting and “de-noising” multiple times until they generate a new image that is completely free of noise.
 Because the diffusion model de-noises all pixels in an image at each step, and there may be 30 or more steps, the process is slow and computationally expensive. But because the model has multiple chances to correct details it got wrong, the images are high-quality.
 Autoregressive models, commonly used for predicting text, can generate images by predicting patches of an image sequentially, a few pixels at a time. They can’t go back and correct their mistakes, but the sequential prediction process is much faster than diffusion.
 These models use representations known as tokens to make predictions. An autoregressive model utilizes an autoencoder to compress raw image pixels into discrete tokens as well as reconstruct the image from predicted tokens. While this boosts the model’s speed, the information loss that occurs during compression causes errors when the model generates a new image.
 With HART, the researchers developed a hybrid approach that uses an autoregressive model to predict compressed, discrete image tokens, then a small diffusion model to predict residual tokens. Residual tokens compensate for the model’s information loss by capturing details left out by discrete tokens.
 “We can achieve a huge boost in terms of reconstruction quality. Our residual tokens learn high-frequency details, like edges of an object, or a person’s hair, eyes, or mouth. These are places where discrete tokens can make mistakes,” says Tang.
 Because the diffusion model only predicts the remaining details after the autoregressive model has done its job, it can accomplish the task in eight steps, instead of the usual 30 or more a standard diffusion model requires to generate an entire image. This minimal overhead of the additional diffusion model allows HART to retain the speed advantage of the autoregressive model while significantly enhancing its ability to generate intricate image details.
 “The diffusion model has an easier job to do, which leads to more efficiency,” he adds.
 Outperforming larger models 
 During the development of HART, the researchers encountered challenges in effectively integrating the diffusion model to enhance the autoregressive model. They found that incorporating the diffusion model in the early stages of the autoregressive process resulted in an accumulation of errors. Instead, their final design of applying the diffusion model to predict only residual tokens as the final step significantly improved generation quality.
 Their method, which uses a combination of an autoregressive transformer model with 700 million parameters and a lightweight diffusion model with 37 million parameters, can generate images of the same quality as those created by a diffusion model with 2 billion parameters, but it does so about nine times faster. It uses about 31 percent less computation than state-of-the-art models.
 Moreover, because HART uses an autoregressive model to do the bulk of the work — the same type of model that powers LLMs — it is more compatible for integration with the new class of unified vision-language generative models. In the future, one could interact with a unified vision-language generative model, perhaps by asking it to show the intermediate steps required to assemble a piece of furniture.
 “LLMs are a good interface for all sorts of models, like multimodal models and models that can reason. This is a way to push the intelligence to a new frontier. An efficient image-generation model would unlock a lot of possibilities,” he says.
 In the future, the researchers want to go down this path and build vision-language models on top of the HART architecture. Since HART is scalable and generalizable to multiple modalities, they also want to apply it for video generation and audio prediction tasks.
 This research was funded, in part, by the MIT-IBM Watson AI Lab, the MIT and Amazon Science Hub, the MIT AI Hardware Program, and the U.S. National Science Foundation. The GPU infrastructure for training this model was donated by NVIDIA. 

 Share this news article on: 

 X 

 Facebook 

 LinkedIn 

 Reddit 

 Print 

 Paper: “HART: Efficient Visual Generation with Hybrid Autoregressive Transformer” 

 Related Links

 Project page 
 Song Han 
 Department of Electrical Engineering and Computer Science 
 School of Engineering 
 MIT Schwarzman College of Computing 
 MIT-IBM Watson AI Lab 
 Research Laboratory of Electronics 

 Related Topics

 Research 

 Computer science and technology 

 Artificial intelligence 

 Machine learning 

 Computer vision 

 Visual arts 

 Electrical engineering and computer science (EECS) 

 School of Engineering 

 MIT Schwarzman College of Computing 

 MIT-IBM Watson AI Lab 

 National Science Foundation (NSF) 

 Related Articles

 A new way to let AI chatbots converse all day without crashing 

 Technique enables AI on edge devices to keep learning over time 

 AI model speeds up high-resolution computer vision 

 Learning on the edge 

 Previous item 
 Next item 

 More MIT News

 Jazz in the key of life 

 Saxophonist Miguel Zenón, a Grammy-winning MIT faculty member, creates a distinctive blend of jazz and traditional Puerto Rican music.

 Read full story →

 Professor Emeritus Jack Dennis, pioneering developer of dataflow models of computation, dies at 94 

 The influential first leader of the Computation Structures Group at MIT played a key role in the development of asynchronous computing.

 Read full story →

 Learning with audiobooks 

 A new study finds that audiobooks help students learn new words — especially when paired with one-on-one instruction.

 Read full story →

 A philosophy of work 

 As the NC Ethics of Technology Postdoctoral Fellow, Michal Masny is advancing dialogue, teaching, and research into the social and ethical dimensions of new computing technologies.

 Read full story →

 Slice and dice 

 SNIPE, a newly characterized biological defense system, directly protects bacteria by chopping up invading viral DNA. 

 Read full story →

 Bridging space research and policy 

 PhD student Carissma McGee studies exoplanets and examines intellectual property frameworks for space collaborations.

 Read full story →

 More news on MIT News homepage →

 Massachusetts Institute of Technology 

 Massachusetts Institute of Technology 
77 Massachusetts Avenue, Cambridge, MA, USA

 Recommended Links: 

 Visit 

 Map (opens in new window) 

 Events (opens in new window) 

 People (opens in new window) 

 Careers (opens in new window) 

 Contact 

 Privacy 

 Accessibility 

 Social Media Hub 

 MIT on X 

 MIT on Facebook 

 MIT on YouTube 

 MIT on Instagram
