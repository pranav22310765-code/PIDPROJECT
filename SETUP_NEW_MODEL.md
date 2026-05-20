# New Field Control System Model - Setup & Training Guide

## Overview

You have **26 annotated images** containing Field control system components in these 5 classes:
- **Class 0**: PLC (Programmable Logic Controller)
- **Class 1**: DCS (Distributed Control System)
- **Class 2**: Field (Field control devices)
- **Class 3**: Electronikon (Electronic controller)
- **Class 4**: Discrete instrument

---

## 📁 Project Structure Created

```
PidDetector/
├── organize_new_data.py              ← Organize data into train/val
├── train_new_model.py                ← Training script
├── data_new_field.yaml               ← Configuration file (NEW)
├── datasets/
│   └── new_field_data/               ← Organized dataset
│       ├── images/
│       │   ├── train/                (18 images - will be populated)
│       │   └── val/                  (8 images - will be populated)
│       └── labels/
│           ├── train/                (18 labels - will be populated)
│           └── val/                  (8 labels - will be populated)
└── runs/
    └── detect/
        └── train_field_control_system/ (training outputs - created after running)
            ├── weights/
            │   ├── best.pt           ← Best model
            │   └── last.pt
            ├── results.csv
            ├── results.png           ← Training curves
            ├── confusion_matrix.png
            └── ... other visualizations
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Organize the Data
```bash
python organize_new_data.py
```

**What it does**:
- Reads 26 images from `new data/field.v1-version-1.yolov11/train/`
- Splits into 70/30 (18 train, 8 val)
- Copies to `datasets/new_field_data/` with proper structure

**Output**:
```
✅ Copied 18 training files
✅ Copied 8 validation files
Dataset organization complete!
```

### Step 2: Train the Model
```bash
python train_new_model.py
```

**What it does**:
- Loads pretrained YOLOv11s (transfer learning)
- Trains on your 18 training images
- Validates on 8 validation images
- Saves best model to `runs/detect/train_field_control_system/weights/best.pt`
- Generates training curves and confusion matrix

**Duration**:
- ~15-30 minutes on GPU
- ~2 hours on CPU

**Progress**:
- You'll see progress bars for each epoch
- Model will stop early if no improvement for 50 epochs

### Step 3: Use the New Model
Update `PDFProcessor_wo_ocr.py`:

```python
# Change this line (around line 150-200):
model = YOLO('runs/detect/train27/weights/best.pt')

# To this:
model = YOLO('runs/detect/train_field_control_system/weights/best.pt')
```

Then test with:
```bash
python main.py
```

---

## 📊 Dataset Information

### Current Dataset
- **Total images**: 26
- **Format**: YOLOv11 (normalized coordinates)
- **Image size**: 512×512 pixels
- **Sources**: P&ID screenshots and diagrams
- **Classes**: 5 (PLC, DCS, Field, Electronikon, discrete instrument)

### Split Strategy
```
26 images total
├── 18 training images (70%)  ← Train the model
└── 8 validation images (30%) ← Test during training
```

### Why This Split?
- **70/30** is standard for small datasets
- **18 images** for training is minimum viable
- **8 images** for validation is enough to prevent overfitting
- No separate test set needed (validation serves this purpose)

---

## 🔧 Configuration Details

### `data_new_field.yaml`
```yaml
path: datasets/new_field_data    # Where the dataset is
train: images/train              # Training images folder
val: images/val                  # Validation images folder
nc: 5                           # Number of classes
names:
  0: PLC
  1: DCS
  2: Field
  3: Electronikon
  4: discrete instrument
```

### Training Parameters in `train_new_model.py`

| Parameter | Value | Why |
|-----------|-------|-----|
| **Model** | yolo11s.pt | Small model for fast training |
| **Epochs** | 100 | Enough iterations for convergence |
| **Batch Size** | 4 | Small batch for small dataset |
| **Image Size** | 512 | Matches your Roboflow preprocessing |
| **Augmentation** | Enabled | Helps with small dataset (26 images) |
| **Early Stopping** | After 50 epochs no improvement | Saves training time |

### Augmentation Techniques Applied
```
├─ Rotation: ±10°
├─ Flip: 50% horizontal flip
├─ HSV shifts: Hue, saturation, brightness adjustments
├─ Scale: Random zoom 50-150%
├─ Mosaic: Combine images during training
└─ CutMix: Mix images together for robustness
```

---

## 📈 Expected Results

### With 26 Images (Small Dataset)
- **Expected mAP@0.5**: 60-80% (good for small dataset)
- **Expected Precision**: 70-85%
- **Expected Recall**: 65-80%
- **Training time**: 15-30 minutes on GPU

### How to Improve
1. **Collect more data** (100+ per class = 500+ total)
   - mAP will jump to 85-95%
2. **Use fine-tuning** instead of training from scratch
   - Already implemented in training script
3. **Increase augmentation** for small datasets
   - Already maximized in training script

---

## 📊 Understanding Training Output

### `results.png`
Shows 6 graphs:
```
- Box Loss (should ↓)           - Training quality
- Class Loss (should ↓)          - Classification accuracy
- dfl Loss (should ↓)            - Bounding box quality
- Precision (should ↑)           - Correct detections
- Recall (should ↑)              - Find all objects
- mAP (should ↑)                 - Overall performance
```

### `confusion_matrix.png`
Shows per-class accuracy:
```
Rows = True class
Cols = Predicted class
Diagonal = Correct predictions
Off-diagonal = Misclassifications
```

### `PR_curve.png`
Precision-Recall curve (most important):
```
Higher & rightward = Better model
Area under curve = Overall performance
```

---

## ⚠️ Troubleshooting

### Error: "No training images found!"
```
Solution: Run step 1 first:
  python organize_new_data.py
```

### Training is very slow
```
Possible causes & solutions:
1. Using CPU → Use GPU instead (check DEVICE = 0 in train script)
2. Too many workers → Reduce workers=2 (done)
3. Large batch size → Batch=4 is correct for 26 images

If using CPU, expect 2-4 hours instead of 15-30 min
```

### Low validation accuracy (mAP < 50%)
```
Causes with 26 images:
1. Very small dataset (normal, expected 60-80% mAP)
2. Poor annotations → Review label quality
3. Classes too similar → Check if PLC/DCS look different

Solutions:
1. Collect more images (500+ for good accuracy)
2. Verify annotations are correct
3. Check image quality (512×512 is good)
```

### "CUDA out of memory" error
```
Solution: Reduce batch size
  batch=2  (instead of 4)
Or use CPU:
  device='cpu'
```

---

## 🔄 Full Workflow Examples

### Example 1: Complete Fresh Start
```bash
# Step 1: Organize data
python organize_new_data.py
# ✓ Output: datasets/new_field_data populated

# Step 2: Train model
python train_new_model.py
# ✓ Output: runs/detect/train_field_control_system/weights/best.pt

# Step 3: Update PDFProcessor
# Edit: PDFProcessor_wo_ocr.py
# Change: model = YOLO('runs/detect/train_field_control_system/weights/best.pt')

# Step 4: Test
python main.py
# Load a P&ID PDF with the 5 new components
```

### Example 2: Collect More Data & Retrain
```bash
# 1. Annotate more images using Roboflow
# 2. Export as YOLOv11 format to new data/field.v2.../
# 3. Update organize_new_data.py to point to new folder
# 4. Run organize_new_data.py
# 5. Run train_new_model.py (will create train_field_control_system_2)
# 6. Update PDFProcessor with new best.pt path
```

---

## 📚 Key Files Explained

### `organize_new_data.py` (Data Preparation)
- **Purpose**: Split 26 images into 18 train + 8 val
- **Input**: `new data/field.v1-version-1.yolov11/train/`
- **Output**: `datasets/new_field_data/images/train` & `/val`
- **Run once**: Before first training
- **Time**: < 1 second

### `train_new_model.py` (Model Training)
- **Purpose**: Train YOLOv11s on your dataset
- **Input**: `datasets/new_field_data/` (organized by step 1)
- **Output**: `runs/detect/train_field_control_system/weights/best.pt`
- **Run every time**: You want to retrain with new data
- **Time**: 15-30 min (GPU) or 2-4 hours (CPU)

### `data_new_field.yaml` (Configuration)
- **Purpose**: Tell YOLO where data is and what classes exist
- **Edit if**: Dataset path changes or class names change
- **Used by**: Both training script and inference script

---

## 🎯 Next Steps

### ✅ Immediate (Today)
1. Run `python organize_new_data.py` (< 1 second)
2. Run `python train_new_model.py` (15-30 min)
3. Check `runs/detect/train_field_control_system/results.png`

### 📊 Short-term (This Week)
1. Review training results in visualization images
2. Test model on real P&ID samples
3. If accuracy < 60%:
   - Review image quality and annotations
   - Check if images represent actual field components
   - Consider collecting more samples

### 🚀 Long-term (This Month)
1. Collect 100+ new annotated images per class
2. Retrain with larger dataset
3. Achieve 85-95% mAP (production quality)
4. Deploy in production environment

---

## 📞 Quick Reference

```bash
# Organize data (first time only)
python organize_new_data.py

# Train model
python train_new_model.py

# View results
# Open: runs/detect/train_field_control_system/results.png

# Use model
# Update: PDFProcessor_wo_ocr.py model path
# Run: python main.py
```

---

## 📋 Checklist Before Training

- [ ] 26 images in `new data/field.v1-version-1.yolov11/train/images`
- [ ] 26 label files in `new data/field.v1-version-1.yolov11/train/labels`
- [ ] `data_new_field.yaml` created with class names
- [ ] `train_new_model.py` script ready
- [ ] GPU available (or willing to wait for CPU training)
- [ ] At least 2 GB disk space free

---

**Everything is ready! Run Step 1 to get started.** 🚀
