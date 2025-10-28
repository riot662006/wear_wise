# 👗 WearWise — AI-Powered Mirror for Outfit Analysis

**Author:** Onyekachi Ibekwe  
**Advisor:** Dr. Yu Zhang  
**Institution:** Fisk University  
**Course:** Junior Seminar Project  
**Repo:** [WearWise (opencv-to-flask)](https://github.com/riot662006/wear_wise/tree/opencv-to-flask)

---

## 🩵 Overview

**WearWise** is an intelligent clothing analysis system that segments clothing items from live camera input, identifies their patterns and colors, and will soon generate **style coherence scores** and outfit recommendations.

The project integrates **computer vision (YOLO + MediaPipe)** for real-time segmentation and **language models (ChatGPT API)** for pattern reasoning.  
WearWise aims to act as a *smart mirror assistant* that helps users understand and refine their outfits based on visual features.

---

## ⚙️ Tech Stack

### 🖥️ Frontend
- **React + TypeScript**
- Real-time video streaming with `Socket.IO`
- Dynamic overlay using SVG
- Modal-based garment detail viewer (pattern + confidence)

### 🧩 Backend
- **Flask (Python)**
- **YOLOv8** for clothing segmentation  
- **MediaPipe SelfieSegmentation** for background blur  
- **OpenAI GPT-4o API** for structured pattern classification  
- **Socket.IO server** for real-time video frames  
- Modularized for integration with future recommendation models

### 🧠 AI Models
- **Segmentation:** YOLOv8 (custom weights fine-tuned on DeepFashion2)
- **Pattern Recognition:** ChatGPT-4o Structured Outputs (JSON Schema)
- **Planned:** Style coherence model combining color, pattern, and fit features

---

## 🧩 Features

### ✅ Real-Time Garment Segmentation
Detects and classifies clothing items (shirts, pants, shorts, etc.) using YOLOv8, returning bounding boxes and labels.

### ✅ Background Blur Preprocessing
Uses MediaPipe to isolate the subject and blur the background — improving model focus and visual clarity.

### ✅ AI-Driven Pattern Recognition
Crops each detected garment and sends it to GPT-4o for pattern identification (e.g., *striped*, *floral*, *graphic*).

### ✅ React Live Interface
Streams live webcam feed with overlayed bounding boxes and garment labels.
Provides “Analyze Patterns” button to pause the video and display pattern analysis results in a modal.

### ✅ Modular Flask API
Endpoints:
- `/segment_frame`: Processes an image frame and returns segmentation results.
- `/analyze_patterns`: Sends cropped garments to the AI model for pattern recognition.

### 🔜 Coming Soon
- **Style Coherence Score:** Quantifies outfit harmony across colors and patterns.  
- **Outfit Recommendation Engine:** Suggests changes or matching items for balance and contrast.  
- **User History / Style Log:** Keeps records of previous outfits for reflection and tracking improvement.

---

## 🧭 Project Structure

```bash
wear_wise/
│
├── backend/
│ ├── server.py # Flask entry point (Socket.IO + routes)
│ ├── detection/
│ │ └── yolo_detector.py # YOLOv8 clothing detector
│ ├── preprocess/
│ │ └── bg_blur.py # MediaPipe background blur
│ ├── ai/
│ │ └── pattern_analyzer.py # GPT-4o structured output calls
│ ├── utils/
│ │ └── image.py # Image encoding and resizing helpers
│ └── config.py # Model paths and environment configs
│
├── frontend/
│ ├── src/
│ │ ├── App.tsx # Main React component
│ │ ├── components/
│ │ │ ├── Overlay.tsx # SVG overlays for detections
│ │ │ └── Modal.tsx # Pattern analysis modal
│ │ ├── hooks/ # Custom hooks for socket & camera
│ │ └── utils/ # Helper functions (image handling)
│ └── package.json
│
└── README.md
```

---

## 🧰 Setup Instructions

### 1. Clone Repository
```bash
git clone https://github.com/riot662006/wear_wise.git
cd wear_wise
git checkout opencv-to-flask
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Environment Variables
```ini
OPENAI_API_KEY=your_openai_api_key
MODEL_PATH=models/yolov8_clothes.pt
DEVICE=cpu
```

### 4. Run the System
- Start Flask backend: ```cd backend && python -m server```
- Start React frontend: ```cd frontend && npm run dev```
- Visit: http://localhost:5173

### 📸 Sample Output
Step | Description | Example
-- | -- | --
Segmentation | Garments outlined and labeled | ![](examples/segmentation.png)
Pattern Detection | GPT-4o returns pattern + confidence	| ![](examples/api_response.png)
Modal View | Crops and results shown interactively | ![](examples/modal.png)

---

## Future Roadmap

- Implement color palette extraction and matching index
-  Train a small rule-based style coherence scorer
- Build “Smart Suggestions” using pattern harmony rules
- Add persistent user sessions and saved looks
- Optimize performance with batch requests to OpenAI

---

## 🤝 Contribution

Contributions and discussions are welcome!
You can fork the repository, create feature branches, and submit pull requests.

---

## 📝 License

MIT License © 2025 Onyekachi Ibekwe

This project was developed as part of the **Fisk University Computer Science Junior Seminar** under the supervision of **Dr. Yu Zhang**.