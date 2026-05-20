import cv2
import numpy as np

print("Testing Preprocessing Pipeline")
print("=" * 50)

# Test 1: Grayscale conversion
print("\n1. Grayscale Conversion")
color_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
gray_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
print(f"   ✓ BGR {color_img.shape} → Grayscale {gray_img.shape}")

# Test 2: Contrast enhancement (CLAHE)
print("\n2. Contrast Enhancement (CLAHE)")
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray_img)
print(f"   ✓ Enhanced image created: {enhanced.shape}")
print(f"   ✓ Input range: [{gray_img.min()}-{gray_img.max()}]")
print(f"   ✓ Output range: [{enhanced.min()}-{enhanced.max()}]")

# Test 3: Adaptive thresholding
print("\n3. Adaptive Thresholding")
binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                               cv2.THRESH_BINARY, blockSize=11, C=2)
print(f"   ✓ Binary image created: {binary.shape}")
print(f"   ✓ Output values: {np.unique(binary)} (black & white only)")

print("\n" + "=" * 50)
print("✓ ALL PREPROCESSING STEPS WORKING")
print("=" * 50)
print("\nPipeline Order:")
print("1. Render PDF → BGR image")
print("2. Convert BGR → Grayscale")
print("3. Enhance contrast (CLAHE)")
print("4. Apply adaptive threshold (binary)")
print("5. Pass to OCR (Tesseract/EasyOCR)")
