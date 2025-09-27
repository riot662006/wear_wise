# Datasets

This project uses the **DeepFashion2** dataset for training and evaluation of the YOLO models.

## 📂 Folder Structure

- `deepfashion2.zip` → Raw dataset archive (do not commit large files to git)
- `deepfashion2/` → Extracted dataset directory (contains images, annotations, splits)

## 📊 About DeepFashion2

- **Size**: 491k images with rich annotations
- **Annotations**: Bounding boxes, masks, clothing categories, landmarks
- **Categories**: 13 clothing categories (e.g., short sleeve top, long sleeve dress, trousers, etc.)
- **Tasks supported**: Detection, instance segmentation, landmark estimation

Reference: [DeepFashion2 Paper](https://arxiv.org/abs/1901.07973)

## ⚙️ How to Prepare

1. Download the dataset:
   - [DeepFashion2 Download Link](https://github.com/switchablenorms/DeepFashion2)
   - Or extract the included `deepfashion2.zip` if already available.
2. Unzip into `datasets/`:
   ```bash
   unzip deepfashion2.zip -d datasets/
   Ensure the following structure:
   ```

```bash
datasets/
└── deepfashion2/
    ├── train/
    ├── validation/
    ├── test/
    ├── annotations/
    └── ...
```

## 🏋️ Training with YOLO

The YOLO training scripts expect a config YAML file (see experiments/clothes.yaml) that points to the dataset structure.

Example snippet from clothes.yaml:

```yaml
train: datasets/deepfashion2/train
val: datasets/deepfashion2/validation
nc: 13
names:
  [
    "short_sleeve_top",
    "long_sleeve_top",
    "short_sleeve_outwear",
    "long_sleeve_outwear",
    "vest",
    "sling",
    "shorts",
    "trousers",
    "skirt",
    "short_sleeve_dress",
    "long_sleeve_dress",
    "vest_dress",
    "sling_dress",
  ]
```

## 🚨 Notes

- The dataset is large; don’t commit extracted images to git. Use .gitignore.
- Keep only small sample images in experiments/images/ for testing.
- For cloud training (Colab, AWS, etc.), upload the dataset there and adjust paths accordingly.
