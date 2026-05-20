"""
═══════════════════════════════════════════════════════════════════════════════
                    QUICK START GUIDE & SUMMARY
═══════════════════════════════════════════════════════════════════════════════
"""

SUMMARY_TEXT = """

📦 PROJECT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main.py                      → GUI application (user interface)
PDFProcessor_wo_ocr.py       → Core processing engine

sample_yolo.py              → Model training script (already trained)
data.yaml                   → Dataset configuration
requirements.txt            → Python dependencies

runs/detect/train27/weights/best.pt  → Trained YOLO model

────────────────────────────────────────────────────────────────────────────────


🎯 COMPLETE WORKFLOW (In 7 Steps)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  USER LAUNCHES GUI
     python main.py
     → Tkinter window opens with drag-drop zone

2️⃣  USER LOADS PDF
     Drag PDF to window OR click Browse
     → GUI shows settings (DPI, Confidence)
     → Background processing starts

3️⃣  PDF → IMAGE RENDERING
     PDF page (612pt × 792pt) → 2550 × 3300 pixels (at 300 DPI)
     → High resolution for YOLO detection

4️⃣  YOLO DETECTS COMPONENTS
     ✓ Check Valve
     ✓ 2way Valve
     ✓ Offline Instrument
     → Bounding boxes in PIXELS

5️⃣  TEXT EXTRACTION (NEW FEATURE #1 - OCR FALLBACK)
     Try in order:
       1. pdfplumber    (best for native PDFs)
       2. PyMuPDF       (built-in fallback)
       3. Tesseract     (OCR for scanned)
       4. EasyOCR       (ML-based final fallback)
     → Guaranteed text extraction from ANY PDF type

6️⃣  INSTRUMENT RECOGNITION (NEW FEATURE #2)
     Detected text: "PI-101"
       → Extract code: "PI"
       → Lookup database: "Pressure Indication"
       → Extract tag: "101"
     Result: {"code": "PI", "name": "Pressure Indication", "tag": "101"}

7️⃣  DISPLAY & EXPORT
     Show results in table:
       - Component Type | Detected Text | Instrument Code | Name | Tag # | Conf
     Export to Excel with one click

────────────────────────────────────────────────────────────────────────────────


🤖 TECH STACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Computer Vision:        PyMuPDF, OpenCV, YOLO
Data Processing:        Pandas, NumPy
Text Extraction:        pdfplumber, PyMuPDF, pytesseract, EasyOCR
GUI:                    Tkinter, tkinterdnd2
Visualization:          Matplotlib, tqdm
ML Model:               YOLOv11s (custom trained)

────────────────────────────────────────────────────────────────────────────────


⚡ KEY FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Automatic YOLO Detection     → 5 P&ID component types
✓ Intelligent Text Extraction  → 4 methods with automatic fallback
✓ Instrument Recognition       → 36 codes + full names
✓ Tag Number Extraction        → Automatic code-tag separation
✓ Coordinate Transform         → Pixel ↔ PDF points conversion
✓ Text-to-Shape Matching       → Finds text inside/near shapes
✓ Modern GUI                   → Drag-drop, real-time progress
✓ Excel Export                 → Professional output format
✓ Debug Visualization          → See detections in bbox overlay
✓ Multi-page PDF Support       → Processes entire documents
✓ Confidence Filtering         → Adjustable detection threshold
✓ Auto DPI Optimization        → Renders pages optimally for YOLO

────────────────────────────────────────────────────────────────────────────────


💾 INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Required
pip install -r requirements.txt

# Optional (for OCR fallback)
pip install easyocr         # ML-based OCR
pip install pytesseract     # Tesseract OCR

# If pytesseract: also need system tesseract-ocr
# Windows: Download from: https://github.com/UB-Mannheim/tesseract/wiki

────────────────────────────────────────────────────────────────────────────────


🚀 QUICK START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Launch GUI
python main.py

# Or process PDF from command line
python PDFProcessor_wo_ocr.py input.pdf runs/detect/train27/weights/best.pt

────────────────────────────────────────────────────────────────────────────────


📊 EXAMPLE OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component Type    | Detected Text | Code | Instrument Name          | Tag # | Conf
─────────────────────────────────────────────────────────────────────────────────
Check Valve       | CV-001        | -    | Unknown                  | CV-001| 0.97
Offline Instrument| PI-101        | PI   | Pressure Indication      | 101   | 0.95
2way Valve        | LSHH-03       | LSHH | Level Switch High High   | 03    | 0.92
                  | (Additional   | PT   | Pressure Transmitter     | 50    | 0.88
                  |  text found)  |      |                          |       |

────────────────────────────────────────────────────────────────────────────────


🧪 TEST SCRIPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

python test_instrument_recognition.py
  → Test instrument code recognition

python test_pipeline_debug.py
  → Debug the complete pipeline

python test_dataframe_structure.py
  → Verify DataFrame display structure

python test_ocr_fallback_explanation.py
  → Show OCR fallback system overview

python PROJECT_OVERVIEW.py
  → Display complete overview

────────────────────────────────────────────────────────────────────────────────


🎛️  ADJUSTABLE SETTINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In GUI:
  • DPI (150-600): Higher = better detail but slower
  • Confidence Threshold (0.1-1.0): Lower = more detections

In Code (PDFProcessor_wo_ocr.py):
  • DEFAULT_DPI = 300
  • YOLO_CONF = 0.25
  • TEXT_MARGIN_PTS = 6.0
  • FLIP_Y = False (coordinate flipping)
  • DEBUG_BBOX = True (show debug visualization)

────────────────────────────────────────────────────────────────────────────────


📈 PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Native PDF (with text layer):
  • Per page: 2-3 seconds
  • 10 pages: ~20-30 seconds

Scanned PDF (needs OCR):
  • Per page: 5-13 seconds (depending on OCR method)
  • 10 pages: ~50-130 seconds

Factors affecting speed:
  ✓ Page complexity
  ✓ Text amount
  ✓ PDF quality
  ✓ Text extraction method used
  ✓ GPU vs CPU (GPU faster for YOLO)

────────────────────────────────────────────────────────────────────────────────


🔍 DEBUGGING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

View console output for:
  • Which PDF is being processed
  • Pages being analyzed
  • YOLO detections count
  • Which text extraction method was used
  • Text extraction count
  • Instrument recognition results

Debug visualization:
  • Check DEBUG_BBOX = True
  • First page generates bbox_debug.png
  • Shows both pixel and PDF coordinates

────────────────────────────────────────────────────────────────────────────────


💡 TIPS & BEST PRACTICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Start with default settings (DPI=300, Conf=0.25)
✓ Lower confidence if missing detections
✓ Higher confidence if getting false positives
✓ Install EasyOCR for best reliability on complex PDFs
✓ Use native PDFs when possible (faster than scanned)
✓ Review Excel output for accuracy
✓ Test with test scripts before processing large batches

────────────────────────────────────────────────────────────────────────────────


🆘 TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Issue: No text extracted
  → Check if PDF is scanned or native
  → Install EasyOCR: pip install easyocr
  → Check TEXT_MARGIN_PTS setting

Issue: Few detections
  → Lower confidence threshold
  → Check page quality
  → Verify YOLO model is loaded

Issue: Wrong instrument recognized
  → Check first 2-4 letters of text
  → Verify text is extracted correctly
  → Check INSTRUMENT_MAP in code

Issue: Slow processing
  → Try lower DPI
  → Use native PDF instead of scanned
  → Disable DEBUG_BBOX
  → Use GPU if available

────────────────────────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════════════════
                          READY TO USE! 🎉
═══════════════════════════════════════════════════════════════════════════════
"""

print(SUMMARY_TEXT)
