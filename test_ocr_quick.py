#!/usr/bin/env python
"""
Quick OCR Test - Check if Tesseract/EasyOCR can extract text from PDF
"""

import sys
import cv2
import numpy as np
import fitz
from pathlib import Path

def quick_ocr_test(pdf_path):
    """Test OCR on first page of PDF"""
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    print(f"\n{'='*70}")
    print(f"QUICK OCR TEST: {pdf_path.name}")
    print(f"{'='*70}\n")
    
    # Open PDF and render first page at 300 DPI
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    mat = fitz.Matrix(300 / 72.0, 300 / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    
    if pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    
    print(f"Rendered: {img.shape[1]} × {img.shape[0]} pixels")
    
    # Preprocess
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)
    
    print(f"Contrast range: {contrast.min()}-{contrast.max()}\n")
    
    # Test Tesseract
    print("1️⃣  TESSERACT OCR")
    print("-" * 70)
    try:
        import pytesseract
        from PIL import Image
        
        pil_img = Image.fromarray(contrast)
        
        # Standard extraction
        print("  Attempting standard extraction...")
        text = pytesseract.image_to_string(pil_img)
        if text.strip():
            print(f"  ✓ Standard: Found {len(text.split())} words")
            print(f"    Sample: {text.strip()[:100]}...")
        else:
            print(f"  ✗ Standard: No text found")
        
        # Detailed extraction with aggressive config
        print("  Attempting detailed extraction with --psm 6...")
        custom_config = r'--psm 6 --oem 3'
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, config=custom_config)
        
        words = [data['text'][i] for i in range(len(data['text'])) if data['text'][i].strip()]
        if words:
            print(f"  ✓ Detailed: Found {len(words)} words")
            print(f"    Sample: {words[:5]}")
        else:
            print(f"  ✗ Detailed: No text found")
            
    except ImportError:
        print("  ✗ pytesseract not installed")
        print("    Install: pip install pytesseract")
        print("    Then install system Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
    except Exception as e:
        print(f"  ✗ Tesseract failed: {e}")
    
    # Test EasyOCR
    print("\n2️⃣  EASYOCR")
    print("-" * 70)
    try:
        import easyocr
        
        img_rgb = cv2.cvtColor(contrast, cv2.COLOR_GRAY2BGR)
        img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)
        
        print("  Initializing EasyOCR reader (first run may take 30-60s)...")
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        
        print("  Running OCR...")
        results = reader.readtext(img_rgb, detail=1)
        
        if results:
            texts = [r[1] for r in results]
            print(f"  ✓ EasyOCR: Found {len(texts)} text elements")
            print(f"    Sample: {texts[:5]}")
        else:
            print(f"  ✗ EasyOCR: No text found")
            
    except ImportError:
        print("  ✗ easyocr not installed")
        print("    Install: pip install easyocr")
    except Exception as e:
        print(f"  ✗ EasyOCR failed: {str(e)[:100]}")
    
    # Test native PDF text
    print("\n3️⃣  NATIVE PDF TEXT (PyMuPDF)")
    print("-" * 70)
    try:
        words = page.get_text("words")
        if words:
            print(f"  ✓ PyMuPDF: Found {len(words)} words")
            print(f"    Sample: {[w[4] for w in words[:5]]}")
        else:
            print(f"  ✗ PyMuPDF: No text layer found (scanned PDF)")
    except Exception as e:
        print(f"  ✗ PyMuPDF failed: {e}")
    
    doc.close()
    print(f"\n{'='*70}\n")
    
    # Summary
    print("DIAGNOSIS:")
    print("- If only native PDF text works: Document is native text (not scanned)")
    print("- If only OCR works: Document is scanned/image-based")
    print("- If neither works: Could be unusual format or very faint text")
    print("- Try higher DPI (600) for small text\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ocr_quick.py <pdf_path>")
        print("Example: python test_ocr_quick.py P_ID_1.pdf")
        sys.exit(1)
    
    quick_ocr_test(sys.argv[1])
