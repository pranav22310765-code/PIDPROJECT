"""
Script to reorganize Roboflow dataset into train/val split
Transfers data from new data folder to organized datasets folder
"""

import os
import shutil
from pathlib import Path

# Source paths (Roboflow dataset)
source_images = Path('new data/field.v1-version-1.yolov11/train/images')
source_labels = Path('new data/field.v1-version-1.yolov11/train/labels')

# Destination paths
dest_base = Path('datasets/new_field_data')
dest_train_images = dest_base / 'images' / 'train'
dest_train_labels = dest_base / 'labels' / 'train'
dest_val_images = dest_base / 'images' / 'val'
dest_val_labels = dest_base / 'labels' / 'val'

print("=" * 70)
print("ORGANIZING ROBOFLOW DATASET INTO TRAIN/VAL SPLIT")
print("=" * 70)

# Get all image files
image_files = sorted([f for f in source_images.glob('*') if f.suffix in ['.jpg', '.png', '.jpeg']])
print(f"\nFound {len(image_files)} images")

# Split: 70% train, 30% val
train_count = int(len(image_files) * 0.7)
train_files = image_files[:train_count]
val_files = image_files[train_count:]

print(f"Split: {len(train_files)} train images, {len(val_files)} val images\n")

# Copy training files
print("Copying TRAINING files...")
for img_file in train_files:
    label_file = source_labels / img_file.stem / '.txt' if (source_labels / f"{img_file.stem}.txt").exists() else source_labels / f"{img_file.stem}.txt"
    
    # Find the correct label file (handle the long Roboflow naming)
    label_candidates = list(source_labels.glob(f"{img_file.stem}*"))
    if label_candidates:
        label_file = label_candidates[0]
    else:
        print(f"  ⚠️  Label not found for {img_file.name}, skipping")
        continue
    
    # Copy image
    shutil.copy2(img_file, dest_train_images / img_file.name)
    
    # Copy label
    shutil.copy2(label_file, dest_train_labels / label_file.name)
    print(f"  ✓ {img_file.name}")

print(f"\n✅ Copied {len(train_files)} training files")

# Copy validation files
print("\nCopying VALIDATION files...")
for img_file in val_files:
    # Find the correct label file
    label_candidates = list(source_labels.glob(f"{img_file.stem}*"))
    if label_candidates:
        label_file = label_candidates[0]
    else:
        print(f"  ⚠️  Label not found for {img_file.name}, skipping")
        continue
    
    # Copy image
    shutil.copy2(img_file, dest_val_images / img_file.name)
    
    # Copy label
    shutil.copy2(label_file, dest_val_labels / label_file.name)
    print(f"  ✓ {img_file.name}")

print(f"\n✅ Copied {len(val_files)} validation files")

print("\n" + "=" * 70)
print("DATASET ORGANIZATION COMPLETE!")
print("=" * 70)
print(f"\nDataset structure:")
print(f"  datasets/new_field_data/")
print(f"  ├── images/")
print(f"  │   ├── train/ ({len(train_files)} images)")
print(f"  │   └── val/ ({len(val_files)} images)")
print(f"  └── labels/")
print(f"      ├── train/ ({len(train_files)} labels)")
print(f"      └── val/ ({len(val_files)} labels)")
print("\n✅ Ready to train! Run: python train_new_model.py")
