"""
Training Script for New Field Control System Detector
Trains YOLOv11s to detect: PLC, DCS, Field, Electronikon, discrete instrument

Dataset: 26 annotated images (18 train, 8 val)
Run this after organizing data with: python organize_new_data.py
"""

from ultralytics import YOLO
import os
from pathlib import Path
from datetime import datetime

print("\n" + "=" * 80)
print(" " * 20 + "YOLOV11 FIELD CONTROL SYSTEM DETECTOR")
print("=" * 80)

# Configuration
DATA_YAML = 'data_new_field.yaml'
MODEL_NAME = 'yolo11s.pt'
EPOCHS = 100
BATCH_SIZE = 4  # Small batch for small dataset (26 images)
IMG_SIZE = 512  # Match Roboflow preprocessing (512x512)
DEVICE = 'cpu'  # Use 'cpu' for CPU training or '0' for GPU

# Paths
DATASET_PATH = 'datasets/new_field_data'

print("\n📊 CONFIGURATION:")
print(f"  Data Config: {DATA_YAML}")
print(f"  Model: {MODEL_NAME}")
print(f"  Epochs: {EPOCHS}")
print(f"  Batch Size: {BATCH_SIZE}")
print(f"  Image Size: {IMG_SIZE}×{IMG_SIZE}")
print(f"  Device: {'GPU (CUDA)' if DEVICE != 'cpu' else 'CPU'}")

# Verify dataset exists
print(f"\n📁 DATASET VERIFICATION:")
if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(f"❌ Dataset not found at {DATASET_PATH}")
print(f"  ✓ Dataset directory found: {DATASET_PATH}")

# Check train/val directories
train_images = Path(DATASET_PATH) / 'images' / 'train'
train_labels = Path(DATASET_PATH) / 'labels' / 'train'
val_images = Path(DATASET_PATH) / 'images' / 'val'
val_labels = Path(DATASET_PATH) / 'labels' / 'val'

train_count = len(list(train_images.glob('*'))) if train_images.exists() else 0
val_count = len(list(val_images.glob('*'))) if val_images.exists() else 0

print(f"  ✓ Training images: {train_count}")
print(f"  ✓ Validation images: {val_count}")

if train_count == 0:
    print("\n❌ No training images found!")
    print("   Run this first: python organize_new_data.py")
    exit(1)

# Load pretrained model
print(f"\n🤖 LOADING MODEL:")
print(f"  Model: {MODEL_NAME} (pretrained on COCO)")
model = YOLO(MODEL_NAME)

# Train
print(f"\n🚀 STARTING TRAINING:")
print(f"  Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Expected duration: 15-30 minutes on GPU\n")

results = model.train(
    data=DATA_YAML,
    epochs=EPOCHS,
    imgsz=IMG_SIZE,
    batch=BATCH_SIZE,
    device=DEVICE,
    workers=2,
    patience=50,  # Early stopping after 50 epochs with no improvement
    augment=True,
    
    # Learning rate schedule
    lr0=0.01,          # Initial learning rate
    lrf=0.01,          # Final learning rate
    momentum=0.937,
    weight_decay=0.0005,
    
    # Augmentation parameters (important for small dataset)
    hsv_h=0.015,       # HSV hue shift
    hsv_s=0.7,         # HSV saturation shift
    hsv_v=0.4,         # HSV value shift
    degrees=10,        # Rotation
    translate=0.1,     # Translation
    scale=0.5,         # Scale
    flipud=0.0,        # Flip upside-down
    fliplr=0.5,        # Flip left-right
    mosaic=0.8,        # Mosaic augmentation
    mixup=0.1,         # CutMix augmentation
    
    # Output settings
    save=True,
    save_period=10,    # Save every 10 epochs
    project='runs/detect',
    name='train_field_control_system',
    exist_ok=False,    # Create new directory
    verbose=True,
)

# Results summary
print("\n" + "=" * 80)
print(" " * 25 + "TRAINING COMPLETE!")
print("=" * 80)

best_model_path = 'runs/detect/train_field_control_system/weights/best.pt'

print(f"\n📈 RESULTS:")
print(f"  Best model: {best_model_path}")
print(f"  End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if hasattr(results, 'results_dict'):
    best_metrics = results.results_dict
    if best_metrics:
        print(f"\n  Performance Metrics:")
        if 'metrics/precision(B)' in best_metrics:
            print(f"    - Precision: {best_metrics['metrics/precision(B)']:.2%}")
        if 'metrics/recall(B)' in best_metrics:
            print(f"    - Recall: {best_metrics['metrics/recall(B)']:.2%}")
        if 'metrics/mAP50(B)' in best_metrics:
            print(f"    - mAP@0.5: {best_metrics['metrics/mAP50(B)']:.2%}")

print(f"\n📊 VISUALIZATIONS:")
print(f"  Training curves: runs/detect/train_field_control_system/results.png")
print(f"  Confusion matrix: runs/detect/train_field_control_system/confusion_matrix.png")
print(f"  PR curves: runs/detect/train_field_control_system/PR_curve.png")
print(f"  Sample predictions: runs/detect/train_field_control_system/val_batch*_pred.jpg")

print(f"\n✅ TO USE THIS MODEL:")
print(f"  1. Update PDFProcessor_wo_ocr.py model path to: {best_model_path}")
print(f"  2. Update INSTRUMENT_MAP if needed for new classes")
print(f"  3. Test with: python main.py")

print(f"\n📝 NEXT STEPS:")
print(f"  - Review results.png to see training curves")
print(f"  - Check confusion_matrix.png for class accuracy")
print(f"  - Test on real P&ID samples")
print(f"  - If accuracy is low, collect more annotated images")

print("\n" + "=" * 80 + "\n")
