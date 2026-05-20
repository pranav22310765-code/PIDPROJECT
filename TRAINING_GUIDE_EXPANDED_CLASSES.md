# Training YOLOv11s to Detect More P&ID Components

## Overview

This guide explains how to expand your current model from detecting 5 component types to detecting more P&ID components (valves, pumps, compressors, heat exchangers, etc.).

---

## Step 1: Plan New Components to Detect

### Current Model (5 classes)
```yaml
0: Offline Instrument
1: 2way Valve No Pattern
2: 2way Gate Valve
3: Check Valve
4: Offline Instrument NL
```

### Example Expansion (10-15 classes)

You might want to add:

**Valves** (currently 2, expand to 6+):
- 3-way Valve
- Globe Valve
- Ball Valve
- Needle Valve
- Solenoid Valve
- Butterfly Valve
- Relief Valve

**Equipment** (currently 0, add 3+):
- Pump
- Compressor
- Heat Exchanger

**Instruments** (currently 2, expand to 3+):
- Pressure Gauge
- Temperature Sensor
- Flow Meter

**Pipes/Connections** (optional):
- Pipe Junction
- Dead Leg
- Orifice

---

## Step 2: Collect & Annotate Training Data

### Data Collection Requirements

**For Each New Component Type:**
- **Minimum**: 100-150 samples per class
- **Recommended**: 300-500 samples per class
- **Ideal**: 500-1000+ samples per class

**Why?** YOLO needs diverse examples:
- Different sizes (small, medium, large components)
- Different locations (top, middle, bottom of P&ID)
- Different contexts (with/without connected pipes)
- Different styles (single-line, double-line diagrams)
- Different line weights and colors

### Data Sources

**Option 1: Manual Collection**
```
Sources:
├─ Existing P&ID archives (company documents)
├─ Public ISA Standard P&ID examples
├─ Industrial engineering textbooks (PDFs)
├─ YouTube technical videos (screenshot P&IDs)
└─ Industry databases (ASME, DIN standards)
```

**Option 2: Data Augmentation** (for small datasets)
```
If you have 50 samples → Generate 200+ through:
├─ Rotation (0°, 45°, 90°, 270°)
├─ Flipping (horizontal, vertical)
├─ Color shifts (simulate different line colors)
├─ Scaling (zoom in/out)
└─ Adding noise (simulate paper/scan artifacts)
```

### Annotation Tools

**Tool 1: Roboflow** (Easiest)
```
Steps:
1. Upload images to Roboflow.com
2. Draw bounding boxes around components
3. Label with component type
4. Export in YOLO format
5. Download pre-split train/val sets
```
**Cost**: Free tier has limits; paid for unlimited

**Tool 2: LabelImg** (Free, Desktop)
```
Installation:
pip install labelImg

Usage:
labelImg /path/to/images
- Draw boxes around components
- Assign class label
- Save as .xml (converts to YOLO format)
```

**Tool 3: CVAT** (Professional, Self-hosted)
```
Installation:
# Docker installation
docker run -it -p 8080:8080 cvat/cvat

Access: http://localhost:8080
- Batch annotation
- Team collaboration
- QA verification
```

**Tool 4: Makesense.ai** (Web-based, free)
```
Steps:
1. Go to makesense.ai
2. Upload images
3. Create labels matching your classes
4. Draw bounding boxes
5. Export as YOLO dataset
```

### Annotation Format

YOLO expects `.txt` files (one per image):

**Format**: `class_id center_x center_y width height` (normalized 0-1)

**Example** (`image_001.txt`):
```
0 0.45 0.50 0.10 0.12    # Class 0 (Offline Instrument)
2 0.65 0.35 0.08 0.10    # Class 2 (2way Gate Valve)
5 0.72 0.68 0.06 0.08    # Class 5 (NEW: 3-way Valve)
```

**Conversion from pixel coordinates**:
```python
# If you have pixel coordinates (x_min, y_min, x_max, y_max)
# and image size (img_width, img_height)

center_x = (x_min + x_max) / 2 / img_width
center_y = (y_min + y_max) / 2 / img_height
width = (x_max - x_min) / img_width
height = (y_max - y_min) / img_height

# Write to file
with open('image_001.txt', 'w') as f:
    f.write(f"{class_id} {center_x} {center_y} {width} {height}\n")
```

---

## Step 3: Organize Dataset Directory

Create proper folder structure:

```
datasets/
├── images/
│   ├── train/
│   │   ├── image_001.jpg
│   │   ├── image_002.jpg
│   │   ├── image_003.txt  (YOLO annotations)
│   │   ├── image_004.jpg
│   │   └── ... (600-700 images for training)
│   │
│   └── val/
│       ├── image_701.jpg
│       ├── image_702.jpg
│       ├── image_703.txt
│       └── ... (200-300 images for validation)
│
└── labels/
    ├── train/
    │   ├── image_001.txt
    │   ├── image_002.txt
    │   └── ...
    │
    └── val/
        ├── image_701.txt
        ├── image_702.txt
        └── ...
```

**Train/Val Split Recommendation**:
- **Train**: 70% of data (use to train model)
- **Val**: 30% of data (use to validate during training)
- **Test**: Optional additional 10-20% (separate final evaluation)

---

## Step 4: Update data.yaml Configuration

### Current data.yaml
```yaml
path: datasets
train: images/train
val: images/val
names:
  0: Offline Instrument
  1: 2way Valve No Pattern
  2: 2way Gate Valve
  3: Check Valve
  4: Offline Instrument NL
```

### Updated data.yaml (10 classes example)
```yaml
path: datasets
train: images/train
val: images/val

nc: 10  # Number of classes (added this line)

names:
  0: Offline Instrument
  1: 2way Valve No Pattern
  2: 2way Gate Valve
  3: Check Valve
  4: Offline Instrument NL
  5: 3-way Valve
  6: Globe Valve
  7: Ball Valve
  8: Pump
  9: Heat Exchanger
```

**Important**: 
- Class IDs start at 0
- Must be sequential (0, 1, 2, 3, ...)
- Count should match `nc` value

### For even more classes (20+):
```yaml
path: datasets
train: images/train
val: images/val

nc: 15

names:
  0: Offline Instrument
  1: 2way Valve No Pattern
  2: 2way Gate Valve
  3: Check Valve
  4: Offline Instrument NL
  5: 3-way Valve
  6: Globe Valve
  7: Ball Valve
  8: Needle Valve
  9: Solenoid Valve
  10: Butterfly Valve
  11: Pump
  12: Compressor
  13: Heat Exchanger
  14: Pressure Gauge
```

---

## Step 5: Update Training Script

### Original sample_yolo.py
```python
from ultralytics import YOLO

model = YOLO('yolo11s.pt')

results = model.train(
    data='data.yaml',
    epochs=200,
    imgsz=1280,
    batch=8,
    device=0,
    workers=4,
    patience=100,
    augment=True
)
```

### Updated Version for More Classes

#### Scenario A: More Data (500+ images per class)
```python
from ultralytics import YOLO

# Start with pretrained YOLOv11s (transfer learning)
# Pretrained on COCO → learns general features
model = YOLO('yolo11s.pt')

results = model.train(
    data='data.yaml',
    epochs=300,           # Increase epochs (more classes need more training)
    imgsz=1280,
    batch=8,
    device=0,
    workers=4,
    patience=150,         # Increase patience (takes longer to converge)
    augment=True,
    
    # Hyperparameters for better multi-class learning
    lr0=0.01,            # Initial learning rate
    optimizer='auto',     # Auto-select optimizer
    weight_decay=0.0005,
    momentum=0.937,
    close_mosaic=15,     # Close mosaic augmentation in last 15 epochs
    
    # Enhanced augmentation for more robustness
    hsv_h=0.015,         # HSV hue
    hsv_s=0.7,           # HSV saturation
    hsv_v=0.4,           # HSV value
    degrees=0,           # Rotation
    translate=0.1,       # Translation
    scale=0.5,           # Scale
    flipud=0.0,          # Flip upside-down
    fliplr=0.5,          # Flip left-right
    mosaic=0.8,          # Mosaic augmentation
    
    # Early stopping to save time
    patience=150,
    
    # Logging & saving
    save=True,
    save_period=10,      # Save every 10 epochs
    project='runs/detect',
    name='train_multi_class'
)
```

#### Scenario B: Less Data (100-200 images per class)
```python
from ultralytics import YOLO

# Use pretrained model (better for small datasets)
model = YOLO('yolo11s.pt')

results = model.train(
    data='data.yaml',
    epochs=200,
    imgsz=1280,
    batch=4,             # Reduce batch size (less data available)
    device=0,
    workers=2,
    patience=80,         # Early stopping if no improvement
    augment=True,
    
    # Aggressive augmentation (to prevent overfitting)
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=30,          # Increase rotation
    translate=0.2,       # More translation
    scale=0.7,           # More scaling
    flipud=0.5,          # Both flip directions
    fliplr=0.5,
    mosaic=0.9,          # Heavy mosaic
    mixup=0.1,           # CutMix augmentation
    
    # Learning rate schedule (helps with convergence)
    lr0=0.001,           # Lower initial learning rate
    lrf=0.001,           # Final learning rate
    
    project='runs/detect',
    name='train_multi_class_small_data'
)
```

#### Scenario C: Continuing from Existing Model
```python
from ultralytics import YOLO

# Load your previously trained model (NOT pretrained)
# This initializes with weights from your epoch 49 model
model = YOLO('runs/detect/train27/weights/best.pt')

results = model.train(
    data='data.yaml',    # NEW data.yaml with 10+ classes
    epochs=150,          # Continue training
    imgsz=1280,
    batch=8,
    device=0,
    workers=4,
    patience=100,
    
    # Lower learning rate (already trained, fine-tune)
    lr0=0.001,           # 10x lower than from scratch
    lrf=0.0001,
    
    # Moderate augmentation (already learned features)
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    translate=0.1,
    scale=0.5,
    
    resume=True,         # Resume training
    project='runs/detect',
    name='train_expanded_classes'
)
```

---

## Step 6: Train the Model

### Option A: Train from Scratch (Recommended for exploration)
```python
# 1. Create new training script: train_expanded.py
from ultralytics import YOLO

model = YOLO('yolo11s.pt')  # Pretrained model
results = model.train(
    data='data.yaml',
    epochs=300,
    imgsz=1280,
    batch=8,
    device=0,
    patience=150
)

# 2. Run training
# python train_expanded.py
```

**Timing**:
- ~30-50 seconds per epoch (with 10-15 classes)
- 300 epochs × 40 sec = 200 minutes (3.3 hours) on GPU
- 5-10 hours on CPU (not recommended)

### Option B: Fine-tune Existing Model (Faster)
```python
# Load your trained model
model = YOLO('runs/detect/train27/weights/best.pt')

# Train only on new classes (with original 5 classes included)
results = model.train(
    data='data.yaml',     # NEW data.yaml
    epochs=100,           # Fewer epochs needed
    imgsz=1280,
    batch=8,
    device=0,
    lr0=0.0001,          # Very low learning rate
    patience=100
)
```

**Advantage**: Uses learned features from original training, converges faster

**Timing**:
- ~2 hours for 100 epochs

### Running Training

**From Python Terminal**:
```python
# In Python REPL
from ultralytics import YOLO

model = YOLO('yolo11s.pt')
results = model.train(
    data='data.yaml',
    epochs=200,
    imgsz=1280,
    batch=8,
    device=0,
    patience=100
)

# Check results
print(f"Best mAP: {results.results.best_map}")
```

**From Command Line**:
```bash
# Using YOLO CLI
yolo detect train data=data.yaml model=yolo11s.pt epochs=200 imgsz=1280 batch=8 device=0

# Or Python script
python train_expanded.py
```

**Monitor Training**:
```bash
# In separate terminal, monitor GPU usage
nvidia-smi -l 1

# Monitor CPU
top  # Linux/Mac
tasklist  # Windows
```

---

## Step 7: Evaluate Results

### Check Training Output

After training, you'll have:

```
runs/detect/train_multi_class/
├── weights/
│   ├── best.pt         # Best model (use this!)
│   └── last.pt         # Final epoch model
├── results.csv         # Metrics per epoch
├── results.png         # Training curves
├── confusion_matrix.png # For each class
├── P_curve.png         # Precision per class
├── R_curve.png         # Recall per class
├── F1_curve.png        # F1 score per class
├── train_batch0.jpg    # Training visualizations
└── val_batch0_pred.jpg # Validation results
```

### Key Metrics to Check

```python
import pandas as pd

# Read training results
results_df = pd.read_csv('runs/detect/train_multi_class/results.csv')

# Get best metrics
best_row = results_df.loc[results_df['metrics/mAP50'].idxmax()]
print(f"Best mAP50: {best_row['metrics/mAP50']:.2%}")
print(f"Precision: {best_row['metrics/precision']:.2%}")
print(f"Recall: {best_row['metrics/recall']:.2%}")
print(f"F1 Score: {best_row['metrics/f1']:.2%}")

# Expected values
# mAP50: 85-95% (good model)
# mAP50-95: 60-75% (more strict metric)
# Recall: 90%+ (finding most components)
# Precision: 85%+ (most detections are correct)
```

### Check Per-Class Performance

From `confusion_matrix.png`:
```
Expected:
├─ Diagonal values high (correct classifications)
├─ Off-diagonal values low (few misclassifications)
└─ New classes (classes 5-N) should have clean rows/cols

Problem signs:
├─ Class X row: scattered across multiple columns → confused with other classes
├─ Class Y column: values in multiple rows → others mistaken for this class
└─ Solution: Collect more training data for problematic classes
```

---

## Step 8: Use the New Model in PDFProcessor

### Update PDFProcessor_wo_ocr.py

**Original code**:
```python
def process_pdf_with_yolo(pdf_path, dpi=300, yolo_conf=0.25, progress_callback=None):
    # ...
    model = YOLO('runs/detect/train27/weights/best.pt')  # Old model
    # ...
```

**Updated code**:
```python
def process_pdf_with_yolo(pdf_path, dpi=300, yolo_conf=0.25, progress_callback=None):
    # ...
    model = YOLO('runs/detect/train_multi_class/weights/best.pt')  # New model
    # ...
```

### Update INSTRUMENT_MAP for New Classes

If your new classes include more instrument types, update the recognition:

**Original**:
```python
INSTRUMENT_MAP = {
    'PI': 'Pressure Indication',
    'TE': 'Temperature Element',
    'FT': 'Flow Transmitter',
    'LT': 'Level Transmitter',
    'PT': 'Pressure Transmitter',
    # ... 36 codes
}
```

**New version** (if detecting more instruments):
```python
INSTRUMENT_MAP = {
    # Pressure
    'PI': 'Pressure Indication',
    'PT': 'Pressure Transmitter',
    'PDT': 'Differential Pressure Transmitter',
    
    # Temperature
    'TE': 'Temperature Element',
    'TI': 'Temperature Indication',
    'TT': 'Temperature Transmitter',
    
    # Flow
    'FT': 'Flow Transmitter',
    'FE': 'Flow Element',
    'SI': 'Flow Indication',
    
    # Level
    'LT': 'Level Transmitter',
    'LI': 'Level Indication',
    'LG': 'Level Gauge',
    
    # Add more as needed
    # ... 50+ codes possible
}
```

---

## Step 9: Troubleshooting

### Problem: Model Converges Too Slowly

**Symptoms**: Loss stays high, mAP doesn't improve after 50+ epochs

**Solutions**:
```python
# 1. Increase learning rate
lr0=0.01  # Default 0.01, try 0.05 for faster learning

# 2. Reduce image size (trains faster, less accurate)
imgsz=640  # Instead of 1280

# 3. Increase batch size (if GPU memory allows)
batch=16  # Instead of 8

# 4. Use different optimizer
optimizer='SGD'  # Default 'auto', try SGD for stability

# 5. Check if data is corrupted
# Verify all .txt files have proper format
```

### Problem: Model Overfits (trains well, validates poorly)

**Symptoms**: Training mAP = 95%, Validation mAP = 60%

**Solutions**:
```python
# 1. Increase augmentation
hsv_h=0.05   # Bigger hue shift
hsv_s=0.9    # Bigger saturation shift
degrees=45   # Rotate more

# 2. Add mixup/mosaic
mixup=0.2  # CutMix augmentation
mosaic=1.0  # Maximum mosaic

# 3. Add dropout (reduces overfitting)
dropout=0.3  # Random feature drop

# 4. Collect more validation data
# Validate on larger, more diverse dataset

# 5. Reduce model complexity
# Use yolo11n.pt (nano) instead of yolo11s (small)
```

### Problem: Some Classes Have Low Recall

**Symptoms**: From confusion_matrix.png, class 8 (Pump) only detects 60%

**Solutions**:
```python
# 1. Collect more training data for that class
# 300+ samples minimum, 500+ preferred

# 2. Use class weights
# Penalize misses on underrepresented classes
class_weights=[1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.0, 1.0, 1.5, 1.0]
# 1.5 = give 50% more weight to class 8 (Pump)

# 3. Lower confidence threshold for that class
# Detect more, even if less confident
inference_conf=0.15  # Detect more, may get false positives

# 4. Increase model capacity
# Use yolo11m.pt (medium) instead of yolo11s (small)
# More parameters = learns better
```

### Problem: Dataset Size Issues

**Too small** (<200 images per class):
```python
# Use heavy augmentation + pretrained model
model = YOLO('yolo11s.pt')  # Pretrained
augment=True
mixup=0.2
mosaic=1.0
epochs=100  # Don't overfit
```

**Too large** (>5000 images per class):
```python
# Use larger model + more epochs
model = YOLO('yolo11l.pt')  # Large instead of small
epochs=500
patience=200
batch=32  # Bigger batches
```

---

## Step 10: Practical Example

### Complete Training Script (copy & use)

**File: `train_multi_component.py`**

```python
"""
Training script for expanded P&ID component detection
Detects 10 component types instead of 5
"""

from ultralytics import YOLO
import os

# Configuration
DATA_YAML = 'data.yaml'  # Updated with 10 classes
MODEL_NAME = 'yolo11s.pt'
EPOCHS = 250
BATCH_SIZE = 8
IMG_SIZE = 1280
DEVICE = 0

# Paths
DATASET_PATH = 'datasets'  # Populated with new annotated data

print("=" * 60)
print("P&ID Multi-Component Detection Training")
print("=" * 60)

# Verify dataset exists
if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")

# Load model (pretrained)
print(f"Loading model: {MODEL_NAME}")
model = YOLO(MODEL_NAME)

# Train
print(f"Starting training... (this may take 2-4 hours)")
print(f"Epochs: {EPOCHS}, Batch: {BATCH_SIZE}, Image Size: {IMG_SIZE}")

results = model.train(
    data=DATA_YAML,
    epochs=EPOCHS,
    imgsz=IMG_SIZE,
    batch=BATCH_SIZE,
    device=DEVICE,
    workers=4,
    patience=150,
    augment=True,
    
    # Learning parameters
    lr0=0.01,
    lrf=0.01,
    momentum=0.937,
    weight_decay=0.0005,
    
    # Augmentation
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    translate=0.1,
    scale=0.5,
    flipud=0.0,
    fliplr=0.5,
    mosaic=0.8,
    
    # Output settings
    save=True,
    save_period=10,
    project='runs/detect',
    name='train_multi_component',
    exist_ok=False,  # Create new directory
    
    # Callbacks
    patience=150,
    verbose=True
)

# Results
print("\n" + "=" * 60)
print("Training Complete!")
print("=" * 60)

# Get best model path
best_model_path = 'runs/detect/train_multi_component/weights/best.pt'

print(f"\nBest model saved to:")
print(f"  {best_model_path}")

# Print best metrics
if hasattr(results, 'results'):
    print(f"\nBest Performance:")
    print(f"  mAP50: {results.results.best_map:.2%}")
    if hasattr(results.results, 'best_fitness'):
        print(f"  F1 Score: {results.results.best_fitness:.2%}")

print("\nTo use this model in PDFProcessor:")
print(f"  - Update model path in PDFProcessor_wo_ocr.py")
print(f"  - Update INSTRUMENT_MAP if detecting new instrument types")
print(f"  - Test on sample P&IDs")
```

**Run it**:
```bash
python train_multi_component.py
```

---

## Best Practices Checklist

✅ **Data Preparation**
- [ ] Collect 300-500 images per new class
- [ ] Use multiple annotation tools to verify accuracy
- [ ] Check for duplicate/corrupted images
- [ ] Balance class distribution (no class <100 images)

✅ **Before Training**
- [ ] Update data.yaml with all classes
- [ ] Verify train/val folder structure
- [ ] Check annotation .txt file format
- [ ] Test data.yaml with: `from ultralytics import YOLO; YOLO('yolo11s.pt').to('cpu')`

✅ **During Training**
- [ ] Monitor GPU memory (nvidia-smi)
- [ ] Check loss curves in real-time
- [ ] Watch for overfitting (val loss diverges from train loss)
- [ ] Save trained models regularly

✅ **After Training**
- [ ] Compare results.csv metrics
- [ ] Review confusion_matrix.png for misclassifications
- [ ] Test on unseen P&ID examples
- [ ] Check inference speed (should be <1 sec per page)

✅ **Production Deployment**
- [ ] Use best.pt (not last.pt)
- [ ] Update PDFProcessor model path
- [ ] Test with real-world P&IDs
- [ ] Log false positives/negatives for retraining

---

## Summary

| Step | Action | Time |
|------|--------|------|
| 1 | Plan new components (5-10 new classes) | 1 hour |
| 2 | Collect & annotate training data (300-500 per class) | 10-20 hours |
| 3 | Organize dataset structure | 1 hour |
| 4 | Update data.yaml | 15 minutes |
| 5 | Create/modify training script | 30 minutes |
| 6 | Train model | 3-6 hours (GPU) |
| 7 | Evaluate results & troubleshoot | 2-4 hours |
| 8 | Deploy in PDFProcessor | 1 hour |
| **Total** | | **18-32 hours** |

---

## Next Steps

1. **Decide components**: Which 5-10 new component types to detect?
2. **Collect data**: Gather 300+ images per new component type
3. **Annotate**: Use Roboflow, LabelImg, or Makesense.ai
4. **Update config**: Modify data.yaml with new classes
5. **Train**: Run training script (3-6 hours on GPU)
6. **Validate**: Check metrics and real-world P&ID examples
7. **Deploy**: Update PDFProcessor and test end-to-end

**Questions?**
- Check training curves in `runs/detect/train_multi_component/results.png`
- Review confusion matrix to identify problematic classes
- Collect more data for low-performing classes
- Consider class weighting or threshold adjustment

