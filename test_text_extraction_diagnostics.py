#!/usr/bin/env python
"""
Text Extraction Diagnostics for P&ID PDFs
Helps identify why text extraction is failing on specific documents
"""

import sys
import cv2
import numpy as np
import fitz
from pathlib import Path

def diagnose_pdf_text_extraction(pdf_path):
    """Run complete diagnostics on a PDF file"""
    
    print("=" * 70)
    print("P&ID TEXT EXTRACTION DIAGNOSTICS")
    print("=" * 70)
    
    # File check
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    print(f"\n📄 File: {pdf_path.name}")
    print(f"   Size: {pdf_path.stat().st_size / (1024*1024):.2f} MB")
    
    # 1. Check OCR availability
    print(f"\n{'─' * 70}")
    print("1️⃣  OCR ENGINE AVAILABILITY")
    print('─' * 70)
    
    try:
        import pytesseract
        print("✓ pytesseract module available")
        try:
            result = pytesseract.get_tesseract_version()
            print(f"  ✓ Tesseract system library found")
        except:
            print(f"  ❌ Tesseract system library NOT found (pip install pytesseract is not enough!)")
            print(f"     Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    except ImportError:
        print("✗ pytesseract NOT installed → pip install pytesseract")
    
    try:
        import easyocr
        print("✓ easyocr module available")
    except ImportError:
        print("✗ easyocr NOT installed → pip install easyocr")
    
    try:
        import pdfplumber
        print("✓ pdfplumber module available")
    except ImportError:
        print("✗ pdfplumber NOT installed → pip install pdfplumber")
    
    # 2. Test PDF opening
    print(f"\n{'─' * 70}")
    print("2️ PDF OPENING & STRUCTURE")
    print('─' * 70)
    
    try:
        doc = fitz.open(pdf_path)
        print(f"✓ PDF opened successfully")
        print(f"  Pages: {doc.page_count}")
        
        page = doc[0]
        print(f"  Page 1 size: {page.rect.width:.0f} × {page.rect.height:.0f} points")
        
        doc.close()
    except Exception as e:
        print(f" Failed to open PDF: {e}")
        return
    
    # 3. Test native text extraction
    print(f"\n{'─' * 70}")
    print("3️⃣  NATIVE TEXT EXTRACTION (PyMuPDF)")
    print('─' * 70)
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        
        # Try words method
        words = page.get_text("words")
        if words:
            print(f"✓ PyMuPDF 'words' extraction: {len(words)} words found")
            print(f"  Sample text: {words[0][4] if words else '(empty)'}")
        else:
            print(f"✗ PyMuPDF 'words' extraction: No text found")
            
            # Try dict method
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            text_blocks = [b for b in blocks if b.get("type") == 0]
            
            if text_blocks:
                total_text = sum(len(b.get("lines", [])) for b in text_blocks)
                print(f"  → But 'dict' method found {total_text} text lines")
                print(f"     (Possible issue with text structure)")
            else:
                print(f"  → PDF appears to be a SCANNED IMAGE or has no text layer")
                print(f"     OCR will be required")
        
        doc.close()
    except Exception as e:
        print(f"❌ PyMuPDF test failed: {e}")
    
    # 4. Test image rendering
    print(f"\n{'─' * 70}")
    print("4️⃣  IMAGE RENDERING & PREPROCESSING")
    print('─' * 70)
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        
        # Render at different DPIs
        for dpi in [150, 300]:
            mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            
            print(f"✓ Rendered at {dpi} DPI: {img.shape[1]} × {img.shape[0]} pixels")
            
            # Test preprocessing
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            contrast = clahe.apply(gray)
            
            print(f"  Grayscale range: {gray.min()}-{gray.max()}")
            print(f"  After CLAHE: {contrast.min()}-{contrast.max()}")
        
        doc.close()
    except Exception as e:
        print(f"❌ Rendering test failed: {e}")
    
    # 5. Test OCR if available
    print(f"\n{'─' * 70}")
    print("5️⃣  OCR EXTRACTION TEST")
    print('─' * 70)
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        
        # Render at 300 DPI
        mat = fitz.Matrix(300 / 72.0, 300 / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        # Preprocess
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(gray)
        
        # Test Tesseract
        try:
            import pytesseract
            from PIL import Image
            
            pil_img = Image.fromarray(contrast)
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
            
            text_count = sum(1 for t in data['text'] if t.strip() and int(data['conf'][data['text'].index(t)]) > 0)
            if text_count > 0:
                print(f"✓ Tesseract OCR: {text_count} text elements found")
                sample = [t for t in data['text'] if t.strip()][:3]
                print(f"  Sample: {sample}")
            else:
                print(f"✗ Tesseract OCR: No text found in image")
        except Exception as e:
            print(f"✗ Tesseract OCR failed: {str(e)[:80]}")
        
        # Test EasyOCR
        try:
            import easyocr
            
            img_rgb = cv2.cvtColor(contrast, cv2.COLOR_GRAY2BGR)
            img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)
            
            reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            results = reader.readtext(img_rgb, detail=1)
            
            if results:
                print(f"✓ EasyOCR: {len(results)} text elements found")
                sample = [r[1] for r in results[:3]]
                print(f"  Sample: {sample}")
            else:
                print(f"✗ EasyOCR: No text found in image")
        except Exception as e:
            print(f"✗ EasyOCR failed: {str(e)[:80]}")
        
        doc.close()
    except Exception as e:
        print(f"❌ OCR test setup failed: {e}")
    
    # 6. Recommendations
    print(f"\n{'─' * 70}")
    print("💡 RECOMMENDATIONS")
    print('─' * 70)
    
    print("\nIf text extraction is failing:")
    print("1. Is this a scanned/image PDF?")
    print("   → Install EasyOCR: pip install easyocr")
    print("   → Or install Tesseract OCR")
    print("")
    print("2. Is this a native text PDF but native extraction failed?")
    print("   → Try forcing OCR as fallback")
    print("")
    print("3. Is text very small or in unusual font?")
    print("   → Try higher DPI rendering (600 instead of 300)")
    print("")
    print("4. Text is being detected but not extracted?")
    print("   → Preprocessing might be too aggressive")
    print("   → Use contrast-enhanced grayscale instead of binary threshold")
    
    print(f"\n{'=' * 70}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_text_extraction_diagnostics.py <pdf_path>")
        print("Example: python test_text_extraction_diagnostics.py P_ID_1.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    diagnose_pdf_text_extraction(pdf_path)
