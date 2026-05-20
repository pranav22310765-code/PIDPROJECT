"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║           COMPLETE PREPROCESSING PIPELINE EXPLANATION                        ║
║                                                                               ║
║  This document details EVERY preprocessing step applied to the P&ID PDF      ║
║  before object detection and text extraction                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

PREPROCESSING_FLOW = """

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STAGE 1: PDF LOADING & INITIALIZATION                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Step 1.1: Load PDF Document
  ├─ Tool: PyMuPDF (fitz.open())
  ├─ Input: PDF file path
  ├─ Output: Document object with page count
  └─ Details: Opens PDF in memory, preserves page structure

Step 1.2: Open Secondary PDF Parser
  ├─ Tool: pdfplumber.open()
  ├─ Status: Optional (graceful fallback if unavailable)
  ├─ Purpose: Better text extraction for native PDFs
  └─ Benefit: Higher accuracy text coordinates and layout preservation

═══════════════════════════════════════════════════════════════════════════════

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STAGE 2: OPTIMAL DPI CALCULATION                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Step 2.1: Get First Page Dimensions
  ├─ Input: First PDF page
  ├─ Get: page.rect.width, page.rect.height (in PDF points)
  │   └─ Standard letter: 612 × 792 points (8.5" × 11")
  └─ Output: Page dimensions

Step 2.2: Calculate Optimal DPI
  ├─ Formula: optimal_dpi = (target_pixels × 72) / dimension_in_points
  ├─ Target: ~1280 pixels (YOLO input standard)
  │   └─ Ratio for letter: 1280 / 612 ≈ 2.09x scale
  ├─ Result: optimal_dpi ≈ 250-300 DPI
  └─ Function: calculate_optimal_dpi()
  
  Example Calculation
  ─────────────────────
  Letter page width  = 612 points
  Target width       = 1280 pixels
  Scale factor       = 1280 / 612 = 2.09
  
  YOLO model expects 1280px input
  → DPI needed = 2.09 × 72 DPI = 150 DPI
  
  BUT: Higher DPI captures more detail for accurate detection
  → Typically adjusted to 250-300 DPI for better component recognition
  
  Output Image:     612 × 2.09 = 1280 px (width)
                    792 × 2.09 = 1656 px (height)

═══════════════════════════════════════════════════════════════════════════════

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STAGE 3: PAGE RENDERING (PDF → IMAGE)                                      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Step 3.1: Create Rendering Matrix
  ├─ Matrix calculation:
  │   mat = fitz.Matrix(dpi/72.0, dpi/72.0)
  │   Example: mat = fitz.Matrix(300/72, 300/72) = Matrix(4.167, 4.167)
  └─ Purpose: Scale PDF vectors from 72 DPI to target DPI

Step 3.2: Render Page to Pixmap
  ├─ Tool: page.get_pixmap(matrix=mat, alpha=False)
  ├─ Process:
  │   ├─ Vectorized PDF → Rasterized pixels
  │   ├─ Matrix transforms all coordinates: new_pixel = old_pixel × matrix
  │   ├─ Color space maintained (RGB or RGBA)
  │   └─ No transparency (alpha=False)
  └─ Output: Pixmap object (pixel buffer)

Step 3.3: Convert to NumPy Array
  ├─ Extract raw bytes: np.frombuffer(pix.samples, dtype=np.uint8)
  ├─ Reshape: (height, width, channels)
  │   └─ Channels: 3 for RGB, 4 for RGBA
  └─ Output: NumPy array (memory-efficient)

Step 3.4: Color Space Conversion
  ├─ PyMuPDF produces RGB image
  ├─ OpenCV expects BGR format
  ├─ Conversion: cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
  └─ Output: BGR image ready for OpenCV/YOLO
  
  Before:  [Red]  [Green] [Blue]
  After:   [Blue] [Green] [Red]
  
  Why BGR? Historical - OpenCV uses BGR from old video standards

═══════════════════════════════════════════════════════════════════════════════

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STAGE 4: TEXT EXTRACTION (PARALLEL - 4 Methods)                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Method 1: pdfplumber (BEST - if available)
───────────────────────────────────────────
Purpose:  Extract text from native PDFs with intact structure
Process:  
  1. Access text layer: page.extract_words()
  2. Get bbox for each word: (x0, top, x1, bottom)
  3. Preserve PDF point coordinates (no conversion needed)
  4. Filter empty text and whitespace
Output:   [(x0, y0, x1, y1, "text", block_no, line_no, word_no), ...]
Speed:    ~0.1-0.5s per page
Quality:  BEST - uses actual text layer
Limitation: Only works on native PDFs (not scanned)
Files:    extract_text_from_pdfplumber_page()

Method 2: PyMuPDF Native (FAST - built-in fallback)
────────────────────────────────────────────────────
Purpose:  Extract text from PDF using built-in PDF library
Priority: Try 3 internal methods:
  1. Standard "words" extraction
  2. "dict" extraction (better for complex layouts)
  3. "rawdict" extraction (character-level detail)
Process:
  1. Try page.get_text("words")  → Fast, may miss some text
  2. If fails, try page.get_text("dict") → Detailed with spans
  3. If fails, try page.get_text("rawdict") → Most detailed
Output:   [(x0, y0, x1, y1, "text", block_no, line_no, word_no), ...]
Speed:    ~0.05-0.2s per page
Quality:  GOOD - uses original PDF structures
Limitation: May not preserve exact coordinates on all PDFs
Files:    extract_text_words_from_page()

Method 3: Tesseract OCR (OCR - for scanned PDFs)
─────────────────────────────────────────────────
Purpose:  Extract text from images/scanned PDFs
Prerequisites: Tesseract engine installed + pytesseract Python package
Process:
  1. Convert image to PIL format
  2. Pass to pytesseract.image_to_data()
  3. Get text boxes with coordinates (in PIXELS)
  4. Convert pixel coords to PDF points:
     scale_x = page_width_pts / image_width_px
     x_pdf = x_pixel × scale_x
Output:   Pixel coords → PDF points conversion
Speed:    ~1-2s per page (slower due to OCR)
Quality:  FAIR - depends on image quality and font
Limitation: Requires Tesseract installation
Files:    extract_text_with_pytesseract()

Method 4: EasyOCR (ML-based OCR - final fallback)
──────────────────────────────────────────────────
Purpose:  ML-based OCR with 80+ language support
Prerequisites: easyocr Python package
Process:
  1. Convert BGR to RGB (EasyOCR requirement)
  2. Initialize reader: easyocr.Reader(['en'])
  3. Run inference: results = reader.readtext()
  4. Extract text + confidence + coordinates (PIXELS)
  5. Convert to PDF points using scale factors
Output:   [([x0,y0], [x1,y1], "text", conf), ...] → PDF points
Speed:    ~2-5s per page (ML inference time)
Quality:  EXCELLENT - handles complex fonts and angles
Limitation: Slower but most reliable
Files:    extract_text_with_easyocr()

Text Extraction Fallback Chain
───────────────────────────────
Try in this order until text is found:

┌─────────────────────────┐
│ pdfplumber detected?    │
│ words found?            │ YES → USE pdfplumber ✓
└────────────┬────────────┘
             │ NO
┌────────────▼────────────┐
│ PyMuPDF available?      │
│ words found?            │ YES → USE PyMuPDF ✓
└────────────┬────────────┘
             │ NO
┌────────────▼────────────┐
│ Tesseract available?    │
│ words found?            │ YES → USE Tesseract ✓
└────────────┬────────────┘
             │ NO
┌────────────▼────────────┐
│ EasyOCR available?      │
│ words found?            │ YES → USE EasyOCR ✓
└────────────┬────────────┘
             │ NO
┌────────────▼────────────┐
│ NO EXTRACTION POSSIBLE  │
│ (Rare case - log warning)
└────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STAGE 5: YOLO OBJECT DETECTION                                              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Step 5.1: Prepare Image for YOLO
  ├─ Input: BGR image from rendering (variable size, e.g., 1280×1656)
  ├─ Convert: BGR → RGB (YOLO expects RGB)
  ├─ Method: cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
  └─ Output: RGB numpy array

Step 5.2: YOLO Inference
  ├─ Model: YOLOv11s (trained on custom P&ID components)
  ├─ Input:
  │   source = RGB image (numpy array)
  │   imgsz = 1280  (resize image to 1280px during inference)
  │   conf = 0.25   (confidence threshold for detections)
  ├─ Processing:
  │   1. Resize image to 1280×1280 (with padding if needed)
  │   2. Forward pass through YOLOv11s network
  │   3. Extract detections above confidence threshold
  │   4. Resize coordinates back to original image size
  └─ Call: preds = model(source=img_rgb, conf=0.25, imgsz=1280)

Step 5.3: Extract Detection Results
  ├─ Output format: Ultralytics Results object
  ├─ Contains:
  │   res.boxes.xyxy  → Bounding box coordinates (x0, y0, x1, y1) in PIXELS
  │   res.boxes.conf  → Confidence score (0.0-1.0)
  │   res.boxes.cls   → Class ID (0-4 for 5 component types)
  └─ Classes:
      0 = Offline Instrument
      1 = 2way Valve No Pattern
      2 = 2way Gate Valve
      3 = Check Valve
      4 = Offline Instrument NL

Step 5.4: Filter Detections
  ├─ Keep only: conf >= 0.25
  ├─ Result: List of valid detections
  └─ If none: Continue to next page

═══════════════════════════════════════════════════════════════════════════════

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STAGE 6: COORDINATE TRANSFORMATION                                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Problem:
────────
  • YOLO detections are in PIXEL coordinates
  • Text extraction is in PDF POINT coordinates
  • We need to map pixel bboxes to PDF space to find nearby text

Why Different Coordinate Systems?
─────────────────────────────────
  PDF Points:      Document-based (fixed, independent of rendering)
  Image Pixels:    Render-based (changes with DPI)

  PDF dimensions (letter):     612 × 792 points
  Rendered at 300 DPI:         1280 × 1656 pixels
  
  Scale factor = rendered_size / pdf_size
               = 1280 / 612
               = 2.09 pixels per point

Pixel to PDF Conversion
───────────────────────
Input:  Bounding box from YOLO in pixels
        x0_px=100, y0_px=50, x1_px=200, y1_px=150

Function: image_bbox_to_pdf_bbox()

Step 1: Calculate scale factors
  page_width_pts = 612.0
  page_height_pts = 792.0
  img_width_px = 1280
  img_height_px = 1656
  
  scale_x = 612.0 / 1280 ≈ 0.478
  scale_y = 792.0 / 1656 ≈ 0.478

Step 2: Convert pixel to PDF points
  x0_pt = x0_px × scale_x = 100 × 0.478 = 47.8 points
  y0_pt = y0_px × scale_y = 50  × 0.478 = 23.9 points
  x1_pt = x1_px × scale_x = 200 × 0.478 = 95.6 points
  y1_pt = y1_px × scale_y = 150 × 0.478 = 71.7 points

Step 3: Normalize (ensure x0<x1, y0<y1)
  x0 = min(47.8, 95.6) = 47.8
  x1 = max(47.8, 95.6) = 95.6
  y0 = min(23.9, 71.7) = 23.9
  y1 = max(23.9, 71.7) = 71.7

Output: PDF bbox = (47.8, 23.9, 95.6, 71.7)

Validation:
───────────
Expected scale = 72 DPI / render_DPI
               = 72 / 300 = 0.24  (approximately)

Actual scale ≈ 0.478 (at 300 DPI, actual scale closer to 0.24)
If mismatch: Warning logged - possible DPI/image size mismatch

═══════════════════════════════════════════════════════════════════════════════

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STAGE 7: TEXT-TO-SHAPE SPATIAL MATCHING                                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Purpose: Find which text words are inside/near each detected component

Function: find_words_inside_pdf_bbox()

Input:
  • Detection bbox: (47.8, 23.9, 95.6, 71.7) in PDF points
  • All extracted text: [(x0, y0, x1, y1, "text"), ...]
  • Margin: 6.0 points (~1/12 inch)

Algorithm:
──────────
Step 1: Expand bbox with margin
  x0m = 47.8 - 6.0 = 41.8
  y0m = 23.9 - 6.0 = 17.9
  x1m = 95.6 + 6.0 = 101.6
  y1m = 71.7 + 6.0 = 77.7
  
  Expanded region: (41.8, 17.9, 101.6, 77.7)

Step 2: For each text word, check if centered inside expanded bbox
  For text "PI":
    Word bbox: (48, 25, 62, 35)
    Center: ((48+62)/2, (25+35)/2) = (55, 30)
    
    Inside check:
      41.8 < 55 < 101.6? YES
      17.9 < 30 < 77.7? YES
    → "PI" is INSIDE ✓

  For text "BUTTON":
    (filtered out by regex - known non-instrument words)

Step 3: Sort results (top-left → bottom-right sweep)
  Sort by: (y0, x0)  → vertical then horizontal
  Ensures natural reading order

Step 4: Extract and return text strings
  Result: ["PI", "101", ...]

Filtering:
──────────
Regex exclusion patterns: H, L, O, C, NOTE, PUSH, BUTTON
  → Removes common non-instrument annotations

═══════════════════════════════════════════════════════════════════════════════

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STAGE 8: INSTRUMENT RECOGNITION (TEXT → INSTRUMENT TYPE)                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Purpose: Convert detected text to instrument code + instrument name + tag number

Function: recognize_instrument_type()

Input: "PI-101"

Process:
────────
Step 1: Normalize text (uppercase, trim)
  "PI-101" → "PI-101"

Step 2: Try code lengths (4, 3, 2 letters in order)
  Try 4 letters: "PI-1" → Not in database
  Try 3 letters: "PI-" → Not in database
  Try 2 letters: "PI"  → FOUND in database ✓

Step 3: Look up code in INSTRUMENT_MAP
  INSTRUMENT_MAP = {
    'PI': 'Pressure Indication',
    'PT': 'Pressure Transmitter',
    'TE': 'Temperature Element',
    ...
  }
  
  Code "PI" → "Pressure Indication"

Step 4: Extract tag number (remaining text after code)
  Original text: "PI-101"
  Code length: 2
  Remaining: "-101"
  Remove leading dash: "101"
  
  Tag = "101"

Output:
───────
{
  'code': 'PI',
  'instrument_name': 'Pressure Indication',
  'tag_number': '101'
}

Fallback Behavior:
──────────────────
If code not found:
  {
    'code': None,
    'instrument_name': 'Unknown',
    'tag_number': original_text
  }
  
Example: "ABC-999" (not in database)
  → code='None', name='Unknown', tag='ABC-999'

Database: 36 Instruments
──────────────────────────
Measurement (23):
  PG, TE, PI, PDT, PDI, TI, LG, QFI, SI, LS, SSA, ESHH, KSH,
  VT, VI, VE, KE, KT, VZT, KI, VZI, VZE

Control (13):
  PT, LCV, FT, FE, LSHH, ZSO, ZSC, AT, AE, TT, PY, TG, LT, PCV

═══════════════════════════════════════════════════════════════════════════════

COMPLETE EXAMPLE
════════════════

Input PDF: "P_ID_001.pdf"

┌────────────────────────────────────────────────────────────────────┐
│ PREPROCESSING PIPELINE - FULL WALKTHROUGH                         │
└────────────────────────────────────────────────────────────────────┘

1. LOAD PDF
   Input:  "P_ID_001.pdf"
   Output: Document with 3 pages

2. CALCULATE DPI
   First page: 612 × 792 points
   Target:     1280 pixels
   Result:     DPI = 250 (auto-calculated)

3. RENDER PAGE 1
   Input:  Page 1 (612×792 pt)
   Matrix: 250/72 = 3.47x scale
   Output: 2123 × 2750 pixels
   Format: BGR image

4. TEXT EXTRACTION (Try in order)
   ✓ pdfplumber: Extracts 45 text items
   Method used: pdfplumber
   
   Sample texts: ["PI", "101", "PT", "50", "LCV", "FV1", ...]
   Coordinates in PDF points: (47.8, 23.9, 62.4, 35.1)

5. YOLO DETECTION
   Input:  2123×2750 pixel RGB image
   Model:  YOLOv11s trained on P&IDs
   Resize: 1280×1280 (internal)
   Result: 8 detections found
   
   Detection 1:
     Class:  2 (2way Gate Valve)
     Conf:   0.94
     Bbox (pixels): (450, 120, 620, 280)

6. COORDINATE TRANSFORM
   Pixel bbox: (450, 120, 620, 280)
   Scale:      612/2123 = 0.288
   PDF bbox:   (129.6, 34.6, 178.6, 80.6) points

7. TEXT MATCHING
   Found inside bbox:
     Text 1: "LCV" at (130, 35, 155, 45)
     Text 2: "FV1" at (132, 50, 150, 62)

8. INSTRUMENT RECOGNITION
   Text "LCV":
     Code: "LCV" (not 2-letter, try earlier... no)
     Try 2-letter: "LC" → Not found
     → code=None, name=Unknown, tag=LCV
   
   Text "FV1":
     Try codes... not found
     → code=None, name=Unknown, tag=FV1

9. BUILD DETECTION ENTRY
   {
     "class_name": "2way Gate Valve",
     "conf_score": 0.94,
     "bbox_pdf": [129.6, 34.6, 178.6, 80.6],
     "bbox_pixels": [450, 120, 620, 280],
     "texts_inside": ["LCV", "FV1"],
     "primary_instrument": "Unknown",
     "instruments_recognized": [
       {"raw_text": "LCV", "code": None, "instrument_name": "Unknown", "tag_number": "LCV"},
       {"raw_text": "FV1", "code": None, "instrument_name": "Unknown", "tag_number": "FV1"}
     ]
   }

10. REPEAT for all detections and pages

11. OUTPUT to DataFrame for GUI display ✓

═══════════════════════════════════════════════════════════════════════════════

PERFORMANCE METRICS
═══════════════════

Step Timing (per page, typical letter-size PDF):
──────────────────────────────────────────────────
1. PDF Load:              ~0.01s  (negligible)
2. DPI Calculation:       ~0.1s   
3. Page Rendering:        ~0.8s   (at 300 DPI)
4. Text Extraction:       
   - pdfplumber:          ~0.1s (best case)
   - Tesseract OCR:       ~1-2s (if used)
   - EasyOCR:             ~2-5s (if used)
5. YOLO Inference:        ~2-3s   (fixed, model size)
6. Coordinate Transform:  ~0.01s  (negligible)
7. Text Matching:         ~0.05s
8. Instrument Recognition: ~0.01s

Total per page:
  Native PDF:             ~3-4 seconds
  With OCR fallback:      ~5-10 seconds
  With EasyOCR:           ~7-13 seconds

10-page document:
  Best case (native):     30-40 seconds
  Worst case (EasyOCR):   70-130 seconds

═══════════════════════════════════════════════════════════════════════════════

KEY PREPROCESSING INSIGHTS
═══════════════════════════

✓ No pixel normalization
  → YOLO handles 0-255 byte range natively
  → More realistic pipeline

✓ DPI optimization
  → Balances detail vs. processing speed
  → Auto-calculated for consistent results

✓ Multi-method text extraction
  → Handles any PDF type (native, scanned, mixed)
  → Automatic intelligent fallback

✓ Coordinate transformation
  → Critical bridge between image & PDF spaces
  → Enables accurate text-to-shape matching

✓ Spatial filtering
  → Only text inside/near detection box used
  → Prevents false matches from distant text

✓ Instrument database lookup
  → Smart code extraction (2-4 letters)
  → Graceful fallback for unknown codes

═══════════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(PREPROCESSING_FLOW)
