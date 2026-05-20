import os
import json
import argparse #to create CLI
from pathlib import Path 
from tqdm import tqdm #for progress bars
from matplotlib import patches #
import matplotlib.pyplot as plt 

import fitz # PyMuPDF
import numpy as np
import cv2

# ultralytics YOLO API
from ultralytics import YOLO

# OCR library (optional)
try:
    import pytesseract
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    easyocr = None
    OCR_AVAILABLE = False

# pdfplumber for better text extraction (PRIMARY METHOD)
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False

# ---------------------------
# Utility / configuration
# ---------------------------
DEFAULT_DPI = 300  # Default DPI for PDF rendering (will be automatically adjusted for YOLO)
USE_OCR = False  # Set to True to use OCR instead of PDF text extraction
OCR_METHOD = "tesseract"  # Options: "tesseract", "easyocr"
DEBUG_BBOX = True  # Set to True to display bounding boxes on PDF and image for debugging
# If your PDF text coordinates appear vertically flipped vs image coords, set FLIP_Y = True.
# In my experience with PyMuPDF, both image pixel origin and page.get_text("words") share top-left origin,
# so flipping usually isn't needed. If results look vertically mirrored, try enabling FLIP_Y.
FLIP_Y = False

# When associating text to a symbol box, also consider nearby text within `text_margin_pts`.
TEXT_MARGIN_PTS = 6.0  # points (~1/12 inch) — adjust as needed

# Minimum confidence threshold for YOLO detection
YOLO_CONF = 0.25

# ---------------------------
# Instrument Recognition Database
# ---------------------------
# Comprehensive mapping of 2-letter instrument codes to full names
INSTRUMENT_MAP = {
    # Measurement Instruments
    'PG': 'Pressure Gauge',
    'TE': 'Temperature Element',
    'PI': 'Pressure Indication',
    'PDT': 'Differential Pressure Transmitter',
    'PDI': 'Differential Pressure Indication',
    'TI': 'Temperature Indication',
    'LG': 'Level Gauge',
    'QFI': 'Volume Indication',
    'SI': 'Speed Indication',
    'LS': 'Level Switch',
    'SSA': 'Sensor Error',
    'ESHH': 'Overprotection Relay',
    'KSH': 'Oil Filter Warning Indication',
    'VT': 'Vibration Transmitter',
    'VI': 'Vibration Indicator',
    'VE': 'Vibration Element',
    'KE': 'Key Phasor',
    'KT': 'Key Phasor Transmitter',
    'VZT': 'Axial Vibration Proximitor',
    'KI': 'Key Phasor Indicator',
    'VZI': 'Axial Vibration Indicator',
    'VZE': 'Axial Vibration Element',
    
    # Control & Transmission
    'PT': 'Pressure Transmitter',
    'LCV': 'Level Control Valve',
    'FT': 'Flow Transmitter',
    'FE': 'Flow Element',
    'LSHH': 'Level Switch High High',
    'ZSO': 'Open Limit Switch',
    'ZSC': 'Close Limit Switch',
    'AT': 'Conductivity Transmitter',
    'AE': 'Conductivity Sensor',
    'TT': 'Temperature Transmitter',
    'PY': 'Positioner',
    'TG': 'Temperature Gauge',
    'LT': 'Level Transmitter',
    'PCV': 'Pressure Control Valve',
}

def enhance_image_contrast(image):
    """
    Increase contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Removes lighting variations and enhances text visibility.
    
    Args:
        image: Grayscale image
    
    Returns:
        Enhanced grayscale image
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(image)

def apply_adaptive_threshold(image):
    """
    Apply adaptive thresholding to separate text from background.
    Converts grayscale to binary image.
    
    Args:
        image: Grayscale image
    
    Returns:
        Binary thresholded image
    """
    return cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, blockSize=11, C=2)

def recognize_instrument_type(text):
    """
    Recognize instrument type from detected text by matching first 2-4 letters.
    
    Logic:
        1. FIRST: Try to match against known instrument codes (2, 3, or 4 letters)
           - If found: extract instrument name and everything after as tag
        2. THEN: If no match, extract first 2 letters + rest as tag
    
    Args:
        text (str): Detected text from PDF (e.g., "PI-101", "TE-05", "LSHH-02", "KSH")
    
    Returns:
        dict: {
            'code': 'PI',
            'instrument_name': 'Pressure Indication',
            'tag_number': '101'
        }
    """
    if not text or not isinstance(text, str):
        return {'code': None, 'instrument_name': 'Unknown', 'tag_number': str(text)}
    
    text_upper = text.upper().strip()
    
    # STEP 1: Check longest matches first in INSTRUMENT_MAP to avoid partial matches
    # For codes in database, try lengths 4, 3, 2 in order
    for code_len in [4, 3, 2]:
        if len(text_upper) >= code_len:
            code = text_upper[:code_len]
            if code in INSTRUMENT_MAP:
                # Found a match! Extract everything after it as tag
                tag_number = text_upper[code_len:].lstrip('-').strip()
                return {
                    'code': code,
                    'instrument_name': INSTRUMENT_MAP[code],
                    'tag_number': tag_number if tag_number else ''  # Empty if no tag
                }
    
    # STEP 2: No database match - try to extract code + tag if there's a clear separator
    # Look for patterns like "AB12", "AB-12", "AB 12" where tag starts with digit
    if len(text_upper) > 2:
        code = text_upper[:2]
        if code.isalpha():  # Only if first 2 chars are letters
            rest = text_upper[2:].lstrip('-').strip()
            # Only split if the rest starts with a digit (indicates a real tag)
            if rest and rest[0].isdigit():
                return {
                    'code': None,
                    'instrument_name': 'Unknown',
                    'tag_number': rest
                }
    
    # Last resort: return whole text as tag (for unrecognized codes like "ABC" or "UNN-VAL")
    return {
        'code': None,
        'instrument_name': 'Unknown',
        'tag_number': text_upper
    }

# Overlap criterion: word center inside expanded box => considered inside
def rect_contains_point(rect, x, y):
    x0, y0, x1, y1 = rect
    return (x >= x0) and (x <= x1) and (y >= y0) and (y <= y1)

# ---------------------------
# PDF rendering & text extraction
# ---------------------------

def calculate_optimal_dpi(page, target_size=1280):
    """
    Calculate optimal DPI to render PDF page close to YOLO's training size.
    
    Args:
        page: PyMuPDF page object
        target_size: Target pixel size for the longer edge (default 1280 for YOLO)
    
    Returns:
        Optimal DPI value
    
    Note:
        YOLO will resize to exactly 1280px during inference, but rendering at 
        a similar size improves coordinate mapping accuracy.
    """
    page_w = page.rect.width  # in points (1/72 inch)
    page_h = page.rect.height
    
    # Determine longer edge
    longer_edge_pts = max(page_w, page_h)
    
    # Calculate DPI to make longer edge approximately target_size pixels
    # DPI = (target_pixels * 72) / points
    optimal_dpi = (target_size * 72.0) / longer_edge_pts
    
    # Round to nearest 10 for cleaner values
    optimal_dpi = round(optimal_dpi / 10) * 10
    
    # Clamp between reasonable bounds
    optimal_dpi = max(150, min(600, optimal_dpi))
    
    return int(optimal_dpi)

def render_pdf_page_to_image(page, dpi=DEFAULT_DPI):
    """
    Render a PyMuPDF page to an OpenCV image (BGR) using pixmap rendering.
    Optimized for YOLO inference at 1280px.
    
    Returns: (img_bgr, img_width_px, img_height_px)
    """
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    
    # Convert to BGR for OpenCV
    if pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    
    return img, pix.width, pix.height

def extract_text_from_pdfplumber_page(pdf_plumber_doc, page_num):
    """
    Extract text words from an already-open pdfplumber document.
    
    Args:
        pdf_plumber_doc: Open pdfplumber PDF document object
        page_num: Page number (1-indexed)
    
    Returns:
        List of word entries: [(x0, y0, x1, y1, "text", block_no, line_no, word_no), ...]
        Coordinates are in PDF points; origin is top-left.
    """
    words = []
    
    try:
        # pdfplumber uses 0-indexed pages
        page = pdf_plumber_doc.pages[page_num - 1]
        
        # Extract words with their bounding boxes
        # pdfplumber returns: {'text': str, 'x0': float, 'top': float, 'x1': float, 'bottom': float}
        extracted_words = page.extract_words()
        
        for word_dict in extracted_words:
            text = word_dict.get('text', '').strip()
            if not text:
                continue
            
            # pdfplumber coordinates: x0, top, x1, bottom
            x0 = word_dict['x0']
            y0 = word_dict['top']
            x1 = word_dict['x1']
            y1 = word_dict['bottom']
            
            # Convert to PyMuPDF format: (x0, y0, x1, y1, text, block_no, line_no, word_no)
            words.append((x0, y0, x1, y1, text, 0, 0, 0))
        
        return words
        
    except Exception as e:
        print(f"[WARNING] pdfplumber extraction failed for page {page_num}: {e}")
        return []

def extract_text_words_from_page(page):
    """
    Returns list of word entries:
      [(x0, y0, x1, y1, "text", block_no, line_no, word_no), ...]
    Coordinates are in PDF points; origin is top-left (PyMuPDF).
    
    This function tries multiple extraction methods for better results:
    1. "words" - Standard word extraction (fast)
    2. "dict" - Detailed extraction with better positioning
    3. "rawdict" - Most detailed, includes character-level info
    """
    words = []
    
    # Method 1: Try standard word extraction (fastest)
    try:
        words = page.get_text("words")
        if words and len(words) > 0:
            return words
    except Exception as e:
        print(f"Warning: Standard word extraction failed: {e}")
    
    # Method 2: Try dict extraction (better for complex layouts)
    try:
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        text = span.get("text", "").strip()
                        if text:  # Only add non-empty text
                            # Format: (x0, y0, x1, y1, text, block_no, line_no, word_no)
                            words.append((bbox[0], bbox[1], bbox[2], bbox[3], 
                                        text, block.get("number", 0), 0, 0))
        if words:
            return words
    except Exception as e:
        print(f"Warning: Dict extraction failed: {e}")
    
    # Method 3: Try rawdict extraction (most detailed)
    try:
        text_dict = page.get_text("rawdict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        text = span.get("text", "").strip()
                        if text:
                            words.append((bbox[0], bbox[1], bbox[2], bbox[3], 
                                        text, block.get("number", 0), 0, 0))
        if words:
            return words
    except Exception as e:
        print(f"Warning: Rawdict extraction failed: {e}")
    
    return words

# ---------------------------
# OCR Text Extraction (Fallback methods)
# ---------------------------

def extract_text_with_pytesseract(image, img_size, page_rect, dpi):
    """
    Extract text from rendered image using Tesseract OCR.
    
    Args:
        image: BGR or Grayscale image from rendered PDF
        img_size: (width, height) of image in pixels
        page_rect: PyMuPDF page rectangle (contains PDF coordinates)
        dpi: DPI used for rendering
    
    Returns:
        List of word entries: [(x0, y0, x1, y1, text, block_no, line_no, word_no), ...]
        Coordinates converted to PDF points
    """
    if pytesseract is None:
        return []
    
    try:
        from PIL import Image
        
        # Convert to proper format for Tesseract
        # If grayscale (2D), use directly; if BGR/RGB (3D), convert to RGB
        if len(image.shape) == 2:
            # Already grayscale
            pil_image = Image.fromarray(image, mode='L')
        else:
            # Convert BGR to RGB for Tesseract
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(img_rgb)
        
        # Get detailed data from Tesseract with lower confidence threshold
        # Use --psm 6 (uniform block of text) and --oem 3 (both legacy and LSTM)
        custom_config = r'--psm 6 --oem 3'
        data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT, config=custom_config)
        
        words = []
        img_w, img_h = img_size
        page_w = page_rect.width
        page_h = page_rect.height
        
        # Scale factors to convert pixels to PDF points
        scale_x = page_w / img_w
        scale_y = page_h / img_h
        
        # Extract words with low confidence threshold (0 = accept all)
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if not text:  # Skip empty
                continue
            
            conf = int(data['conf'][i])
            # Lower threshold for text detection - accept even low confidence
            if conf < -1:  # -1 = no detection, accept 0+
                continue
            
            # Get pixel coordinates
            x0_px = int(data['left'][i])
            y0_px = int(data['top'][i])
            x1_px = x0_px + int(data['width'][i])
            y1_px = y0_px + int(data['height'][i])
            
            # Convert to PDF points
            x0_pt = x0_px * scale_x
            y0_pt = y0_px * scale_y
            x1_pt = x1_px * scale_x
            y1_pt = y1_px * scale_y
            
            words.append((x0_pt, y0_pt, x1_pt, y1_pt, text, 0, 0, 0))
        
        if words:
            print(f"[OCR] Tesseract extracted {len(words)} words")
        return words
        
    except Exception as e:
        print(f"[WARNING] Tesseract OCR failed: {e}")
        return []

def extract_text_with_easyocr(image, img_size, page_rect, dpi, lang=['en']):
    """
    Extract text from rendered image using EasyOCR.
    
    Args:
        image: BGR or Grayscale image from rendered PDF
        img_size: (width, height) of image in pixels
        page_rect: PyMuPDF page rectangle (contains PDF coordinates)
        dpi: DPI used for rendering
        lang: Language codes for OCR (default: English)
    
    Returns:
        List of word entries: [(x0, y0, x1, y1, text, block_no, line_no, word_no), ...]
        Coordinates converted to PDF points
    """
    if easyocr is None:
        return []
    
    try:
        # EasyOCR works with both grayscale and color images
        # Convert grayscale to BGR if needed (EasyOCR expects 3-channel)
        if len(image.shape) == 2:
            # Convert grayscale to BGR
            image_for_ocr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            image_for_ocr = image
        
        # Convert BGR to RGB for EasyOCR
        img_rgb = cv2.cvtColor(image_for_ocr, cv2.COLOR_BGR2RGB)
        
        # Initialize reader (cached after first use)
        reader = easyocr.Reader(lang, gpu=False, verbose=False)
        
        # Perform OCR
        results = reader.readtext(img_rgb, detail=1)
        
        words = []
        img_w, img_h = img_size
        page_w = page_rect.width
        page_h = page_rect.height
        
        # Scale factors to convert pixels to PDF points
        scale_x = page_w / img_w
        scale_y = page_h / img_h
        
        # Extract words with confidence > 0.3
        for (bbox, text, confidence) in results:
            if confidence < 0.3 or not text.strip():
                continue
            
            # bbox has 4 points: top-left, top-right, bottom-right, bottom-left
            # Extract min/max to get bounding rectangle
            points = np.array(bbox, dtype=np.float32)
            x_coords = points[:, 0]
            y_coords = points[:, 1]
            
            x0_px = int(np.min(x_coords))
            x1_px = int(np.max(x_coords))
            y0_px = int(np.min(y_coords))
            y1_px = int(np.max(y_coords))
            
            # Convert to PDF points
            x0_pt = x0_px * scale_x
            y0_pt = y0_px * scale_y
            x1_pt = x1_px * scale_x
            y1_pt = y1_px * scale_y
            
            words.append((x0_pt, y0_pt, x1_pt, y1_pt, text.strip(), 0, 0, 0))
        
        if words:
            print(f"[OCR] EasyOCR extracted {len(words)} words")
        return words
        
    except Exception as e:
        print(f"[WARNING] EasyOCR failed: {e}")
        return []

# ---------------------------
# Coordinate transforms
# ---------------------------

def image_bbox_to_pdf_bbox(img_bbox, page_rect, img_size, dpi):
    """
    Convert bbox expressed in image pixel coordinates (x0,y0,x1,y1) ->
    PDF point coordinates (points; 1 pt = 1/72 inch).
    
    Arguments:
      img_bbox: (x0_px, y0_px, x1_px, y1_px) - YOLO detection bbox in pixels
      page_rect: fitz.Rect or (width_pts, height_pts) via page.rect
      img_size: (img_w_px, img_h_px) - rendered image dimensions
      dpi: rendering dpi used (for documentation/validation)
      
    Returns:
      pdf_bbox: (x0_pt, y0_pt, x1_pt, y1_pt) - bbox in PDF points
      
    How it works:
      1. PDF is rendered at specified DPI: img_size = page_size * (dpi/72)
      2. YOLO detects symbols in the rendered image at that resolution
      3. We convert back: pdf_coords = pixel_coords * (page_size/img_size)
      
    Example with 300 DPI:
      - PDF page: 612pt × 792pt (8.5" × 11")
      - Rendered image: 2550px × 3300px (612 × 300/72)
      - Scale factor: 612/2550 = 0.24 (points per pixel)
      - YOLO bbox at (100, 100, 200, 200) pixels
      - PDF bbox = (24, 24, 48, 48) points
    
    Note:
      The DPI parameter is implicit in img_size. Higher DPI creates larger
      images with more pixels, which improves YOLO detection accuracy and
      provides more precise coordinate mapping.
    """
    img_w, img_h = img_size
    page_w = page_rect.width  # in points (1 point = 1/72 inch)
    page_h = page_rect.height

    # Calculate scale factors (points per pixel)
    # These factors implicitly account for the DPI used during rendering
    scale_x = page_w / img_w
    scale_y = page_h / img_h
    
    # Validate that the scale factors are reasonable
    # At 72 DPI: scale ≈ 1.0 (1 pixel = 1 point)
    # At 300 DPI: scale ≈ 0.24 (4.17 pixels = 1 point)
    # At 600 DPI: scale ≈ 0.12 (8.33 pixels = 1 point)
    expected_scale = 72.0 / dpi
    if abs(scale_x - expected_scale) > 0.01 or abs(scale_y - expected_scale) > 0.01:
        # This could indicate a mismatch between DPI and actual image size
        import warnings
        warnings.warn(
            f"Scale factor mismatch! Expected ~{expected_scale:.3f} for {dpi} DPI, "
            f"but got scale_x={scale_x:.3f}, scale_y={scale_y:.3f}. "
            f"Image may not have been rendered at the specified DPI."
        )

    x0_px, y0_px, x1_px, y1_px = img_bbox
    x0_pt = x0_px * scale_x
    x1_pt = x1_px * scale_x
    y0_pt = y0_px * scale_y
    y1_pt = y1_px * scale_y

    # Depending on origin conventions, you may need to flip Y. PyMuPDF uses top-left origin for get_text("words"),
    # and the rendered image pixel origin is top-left, so no flip is generally needed.
    # If you observe vertical inversion, set FLIP_Y = True at top of file.
    if FLIP_Y:
        # flip vertically
        y0_pt, y1_pt = page_h - y1_pt, page_h - y0_pt

    # normalize to (x0,y0,x1,y1)
    x0n, x1n = min(x0_pt, x1_pt), max(x0_pt, x1_pt)
    y0n, y1n = min(y0_pt, y1_pt), max(y0_pt, y1_pt)
    return (x0n, y0n, x1n, y1n)

# ---------------------------
# Associate text to symbol boxes
# ---------------------------

def find_words_inside_pdf_bbox(pdf_bbox, words, margin_pts=TEXT_MARGIN_PTS):
    """
    words: list from extract_text_words_from_page
      each word is (x0,y0,x1,y1, text, block_no, line_no, word_no)
    pdf_bbox: (x0,y0,x1,y1) in PDF points
    margin_pts: expand bbox by margin to catch nearby labels
    Returns: list of strings (words) inside or near the bbox
    """
    x0, y0, x1, y1 = pdf_bbox
    # expand
    x0m = x0 - margin_pts
    y0m = y0 - margin_pts
    x1m = x1 + margin_pts
    y1m = y1 + margin_pts

    found = []
    regex = ['H','L','O','C','NOTE','PUSH','BUTTON']
    for wx0, wy0, wx1, wy1, wtext, *rest in words:
        # choose word center
        cx = (wx0 + wx1) / 2.0
        cy = (wy0 + wy1) / 2.0
        if rect_contains_point((x0m, y0m, x1m, y1m), cx, cy) and not any(r in wtext.upper() for r in regex):
            found.append((wx0, wy0, wx1, wy1, wtext))
    # Sort found words by vertical then horizontal order (top-left sweep)
    found_sorted = sorted(found, key=lambda w: (w[1], w[0]))
    texts = [w[4] for w in found_sorted]
    return texts

def plot_detections_matplotlib(image, boxes, model, figsize=(15, 10),
                               font_size=10, linewidth=2, show_conf=True):
    """
    Plot detections using Matplotlib with customizable font and line thickness
    
    Args:
        image: Image as numpy array (RGB or BGR)
        boxes: Ultralytics Boxes object containing detections
        model: YOLO model with class names
        figsize: Figure size (width, height)
        font_size: Font size for labels
        linewidth: Line width for bounding boxes
        show_conf: Whether to show confidence scores
    """
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    ax.axis('off')

    colors = ['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'purple', 'orange']

    # Iterate through each detection box
    for i, box in enumerate(boxes):
        # Extract coordinates, confidence, and class from the box object
        xyxy = box.xyxy.cpu().numpy()[0]  # [x1, y1, x2, y2]
        conf = float(box.conf.cpu().numpy())
        cls_id = int(box.cls.cpu().numpy())
        
        x1, y1, x2, y2 = xyxy
        color = colors[cls_id % len(colors)]

        # Draw bounding box
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1,
                                 linewidth=linewidth, edgecolor=color, facecolor='none')
        ax.add_patch(rect)

        # Create label with optional confidence score
        label = model.names[cls_id]
        if show_conf:
            label = f'{label} {conf:.2f}'

        # Add text label above the box
        ax.text(x1, y1 - 5, label, fontsize=font_size, color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=color,
                          edgecolor='none', alpha=0.7))

    plt.tight_layout()
    return fig

def debug_bbox_overlay(page, image, detections_data, img_size, dpi, save_prefix="debug"):
    """
    Create side-by-side visualization of bounding boxes on PDF and image.
    
    Args:
        page: PyMuPDF page object
        image: Rendered image (BGR)
        detections_data: List of detection dicts with bbox_pdf and bbox_pixels
        img_size: (width, height) of rendered image
        dpi: DPI used for rendering
        save_prefix: Prefix for saved debug images
    
    Returns:
        Matplotlib figure showing both PDF and image with overlays
    """
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    
    # Convert image to RGB for display
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Display image on left
    ax1.imshow(img_rgb)
    ax1.set_title(f'Image Space (Pixels) - {img_size[0]}x{img_size[1]}', fontsize=12, fontweight='bold')
    ax1.axis('off')
    
    # Display image on right (will overlay PDF coordinates)
    ax2.imshow(img_rgb)
    ax2.set_title(f'PDF Space (Points) Mapped to Image - DPI: {dpi}', fontsize=12, fontweight='bold')
    ax2.axis('off')
    
    colors = ['red', 'blue', 'green', 'cyan', 'magenta', 'yellow', 'orange', 'purple']
    
    # Overlay bounding boxes
    for i, det in enumerate(detections_data):
        color = colors[i % len(colors)]
        
        # Left: Image pixel coordinates (from YOLO)
        x0_px, y0_px, x1_px, y1_px = det['bbox_pixels']
        rect_img = patches.Rectangle((x0_px, y0_px), x1_px - x0_px, y1_px - y0_px,
                                     linewidth=2, edgecolor=color, facecolor='none', linestyle='-')
        ax1.add_patch(rect_img)
        ax1.text(x0_px, y0_px - 5, f"#{i+1} IMG", fontsize=8, color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7))
        
        # Right: PDF coordinates converted back to pixels for visualization
        pdf_bbox = det['bbox_pdf']
        page_w = page.rect.width
        page_h = page.rect.height
        img_w, img_h = img_size
        
        # Convert PDF points back to pixels for display
        scale_x = img_w / page_w
        scale_y = img_h / page_h
        
        x0_pdf_px = pdf_bbox[0] * scale_x
        y0_pdf_px = pdf_bbox[1] * scale_y
        x1_pdf_px = pdf_bbox[2] * scale_x
        y1_pdf_px = pdf_bbox[3] * scale_y
        
        rect_pdf = patches.Rectangle((x0_pdf_px, y0_pdf_px), 
                                     x1_pdf_px - x0_pdf_px, y1_pdf_px - y0_pdf_px,
                                     linewidth=2, edgecolor=color, facecolor='none', linestyle='--')
        ax2.add_patch(rect_pdf)
        
        # Show class name and text
        class_name = det.get('class_name', 'Unknown')
        texts = det.get('texts_inside', [])
        text_str = ', '.join(texts[:2]) if texts else 'No text'
        label = f"#{i+1} {class_name}\n{text_str}"
        
        ax2.text(x0_pdf_px, y0_pdf_px - 5, label, fontsize=8, color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7))
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='none', edgecolor='red', linewidth=2, label='Image pixels (solid)'),
        Patch(facecolor='none', edgecolor='red', linewidth=2, linestyle='--', label='PDF points (dashed)')
    ]
    ax2.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    
    # Save debug image
    debug_path = f"{save_prefix}_bbox_debug.png"
    fig.savefig(debug_path, dpi=150, bbox_inches='tight')
    print(f"Debug visualization saved to: {debug_path}")
    
    return fig



# ---------------------------
# Main pipeline
# ---------------------------

def process_pdf_with_yolo(pdf_path, yolo_model_path, out_json_path=None, dpi=None, conf=YOLO_CONF, progress_callback=None):
    """
    Process PDF with YOLO object detection and text extraction.
    
    Args:
        pdf_path: Path to input PDF
        yolo_model_path: Path to YOLO model weights
        out_json_path: Path to save JSON results
        dpi: Rendering DPI (None = auto-calculate optimal DPI for YOLO 1280px)
        conf: YOLO confidence threshold
        progress_callback: Optional callback function for progress updates
    
    Returns:
        List of detection dictionaries
    """
    doc = fitz.open(pdf_path)
    model = YOLO(yolo_model_path)
    
    # Open pdfplumber document if available (keep it open for all pages)
    pdf_plumber_doc = None
    if PDFPLUMBER_AVAILABLE:
        try:
            pdf_plumber_doc = pdfplumber.open(pdf_path)
        except Exception as e:
            print(f"[WARNING] Could not open PDF with pdfplumber: {e}")
            pdf_plumber_doc = None

    results_all = []
    
    try:
        # Calculate optimal DPI if not specified
        if dpi is None:
            first_page = doc.load_page(0)
            dpi = calculate_optimal_dpi(first_page, target_size=1280)
            print(f"[Auto DPI] Calculated optimal DPI: {dpi} (for ~1280px rendering)")
        
        # Log rendering configuration
        print(f"\n{'='*60}")
        print(f"PDF PROCESSING CONFIGURATION")
        print(f"{'='*60}")
        print(f"PDF: {Path(pdf_path).name}")
        print(f"Pages: {doc.page_count}")
        print(f"Rendering DPI: {dpi}")
        print(f"YOLO model: {Path(yolo_model_path).name}")
        print(f"YOLO input size: 1280px (images resized during inference)")
        print(f"YOLO confidence: {conf}")
        print(f"Debug visualization: {DEBUG_BBOX}")
        
        # Text extraction method
        print(f"\nText Extraction Methods (in priority order):")
        print(f"  1. pdfplumber      → {'✓ Available' if PDFPLUMBER_AVAILABLE else '✗ Not installed'}")
        print(f"  2. PyMuPDF         → ✓ Available (built-in)")
        print(f"  3. Tesseract OCR   → {'✓ Available' if pytesseract else '✗ Not installed'}")
        print(f"  4. EasyOCR         → {'✓ Available' if easyocr else '✗ Not installed'}")
        print(f"\n📋 Strategy: Try each method in order until text is found")
        
        # Warn if no OCR available and PDF is likely scanned
        if not pytesseract and not easyocr:
            print(f"\n⚠️  WARNING: No OCR engines installed!")
            print(f"   For scanned/image PDFs, install: pip install easyocr")
            print(f"   OR for Tesseract: pip install pytesseract (+ system tesseract-ocr)")
        
        if pdf_plumber_doc:
            print(f"✓ pdfplumber successfully opened PDF")
        else:
            if PDFPLUMBER_AVAILABLE:
                print(f"⚠ pdfplumber installed but failed to open - will use PyMuPDF → OCR")
            else:
                print(f"ℹ pdfplumber not installed - will use PyMuPDF → OCR fallback")

        for page_num in tqdm(range(1, doc.page_count + 1), desc="Pages"):
            page = doc.load_page(page_num - 1)
            
            # Update progress: page loading
            if progress_callback:
                progress = int((page_num - 1) / doc.page_count * 100)
                progress_callback(progress)
            
            # Render page for YOLO inference
            img, img_w, img_h = render_pdf_page_to_image(page, dpi=dpi)
            
            if page_num == 1:
                print(f"[Render] Page 1: {img_w} × {img_h} pixels at {dpi} DPI")

            # Convert to grayscale for improved text extraction (removes color noise)
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if page_num == 1:
                print(f"[Preprocess] Converted to grayscale for text extraction")
            
            # Increase contrast using CLAHE (adaptive histogram equalization)
            img_contrast = enhance_image_contrast(img_gray)
            if page_num == 1:
                print(f"[Preprocess] Enhanced contrast for better text visibility")
            
            # Binary thresholding (for reference, but OCR prefers contrast-enhanced grayscale)
            img_thresh = apply_adaptive_threshold(img_contrast)
            if page_num == 1:
                print(f"[Preprocess] Applied adaptive thresholding (for visualization only)")

            # Save to temp file if ultralytics needs file; but it can accept numpy array.
            # Convert BGR -> RGB (ultralytics expects PIL or ndarray in RGB)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # YOLO inference - model will resize to 1280px internally
            preds = model(source=img_rgb, conf=conf, imgsz=1280, verbose=False)
            
            # Get text words from PDF page with multiple fallback methods
            # Priority order: pdfplumber -> PyMuPDF -> Tesseract -> EasyOCR
            words = []
            extraction_method = None
            
            # Method 1: Try pdfplumber (best for structured PDFs)
            if pdf_plumber_doc:
                words = extract_text_from_pdfplumber_page(pdf_plumber_doc, page_num)
                if words:
                    extraction_method = "pdfplumber"
                    if page_num == 1:
                        print(f"[Text] pdfplumber extracted {len(words)} words")
                else:
                    if page_num == 1:
                        print(f"[Text] pdfplumber found 0 words")
            
            # Method 2: Fallback to PyMuPDF native extraction
            if not words:
                words = extract_text_words_from_page(page)
                if words:
                    extraction_method = "PyMuPDF"
                    if page_num == 1:
                        print(f"[Text] PyMuPDF extracted {len(words)} words")
                else:
                    if page_num == 1:
                        print(f"[Text] PyMuPDF found 0 words - likely SCANNED/IMAGE PDF")
            
            # Method 3: Fallback to Tesseract OCR (use contrast-enhanced grayscale, not binary)
            if not words:
                if page_num == 1:
                    print(f"[Text] Attempting Tesseract OCR...")
                words = extract_text_with_pytesseract(img_contrast, (img_w, img_h), page.rect, dpi)
                if words:
                    extraction_method = "Tesseract OCR"
                    if page_num == 1:
                        print(f"[Text] Tesseract OCR extracted {len(words)} words")
                else:
                    if page_num == 1:
                        print(f"[Text] Tesseract OCR found 0 words")
            
            # Method 4: Final fallback to EasyOCR (use contrast-enhanced grayscale, not binary)
            if not words:
                if page_num == 1:
                    print(f"[Text] Attempting EasyOCR (higher accuracy ML-based)...")
                words = extract_text_with_easyocr(img_contrast, (img_w, img_h), page.rect, dpi)
                if words:
                    extraction_method = "EasyOCR"
                    if page_num == 1:
                        print(f"[Text] EasyOCR extracted {len(words)} words")
                else:
                    if page_num == 1:
                        print(f"[Text] EasyOCR found 0 words")
            
            if page_num == 1 and extraction_method:
                print(f"[Page {page_num}] Using {extraction_method} for text extraction")
            
            if page_num == 1 and not words:
                print(f"[WARNING] No text extraction method succeeded on page {page_num}")
                print(f"  → PDF might be scanned/image-based (requires OCR)")
                print(f"  → Possible solutions:")
                print(f"     1. Install EasyOCR: pip install easyocr")
                print(f"     2. Install Tesseract: pip install pytesseract")
                print(f"     3. Check PDF type: native text vs. scanned image")
                print(f"     4. Run diagnostics: python test_ocr_quick.py {Path(pdf_path).name}")
            else:
                if page_num == 1 and words:
                    print(f"[Text Summary] Page {page_num}: Total text elements = {len(words)}")
                    sample_texts = [w[4] for w in words[:10]]
                    print(f"                Sample texts: {sample_texts}")

            # Process detection results
            res = preds[0]
            
            if not hasattr(res, "boxes") or len(res.boxes) == 0:
                # No detections on this page
                if page_num == 1:
                    print(f"[Page {page_num}] No detections (try lowering confidence: current={conf})")
                continue

            num_detections = len(res.boxes)
            if page_num == 1:
                print(f"[Page {page_num}] Found {num_detections} detections, {len(words)} text elements")
            
            # Store detections for this page (for debug visualization)
            page_detections = []
        
            for i, box in enumerate(res.boxes):
                # box.xyxy is a tensor-like; convert to list
                xyxy = box.xyxy.cpu().numpy().tolist()[0]  # shape (1, 4) -> (4,)
                x0_px, y0_px, x1_px, y1_px = xyxy
                cls_id = int(box.cls.cpu().numpy())
                conf_score = float(box.conf.cpu().numpy())
                cls_name = model.names.get(cls_id, str(cls_id))

                # Map pixel bbox to PDF points
                pdf_bbox = image_bbox_to_pdf_bbox((x0_px, y0_px, x1_px, y1_px), page.rect, (img_w, img_h), dpi)

                # Find words inside/near this bbox
                texts = find_words_inside_pdf_bbox(pdf_bbox, words, margin_pts=TEXT_MARGIN_PTS)
                
                # Debug: Show which detections have text
                if page_num == 1 and i < 5:  # Show first 5 detections
                    if texts:
                        print(f"  [Detection #{i+1}] {cls_name}: Found texts = {texts}")
                    else:
                        print(f"  [Detection #{i+1}] {cls_name}: No text found in bbox")

                # Recognize instrument types from detected texts
                instruments_recognized = []
                primary_instrument = None
                
                for text in texts:
                    instrument_info = recognize_instrument_type(text)
                    instruments_recognized.append({
                        "raw_text": text,
                        "code": instrument_info['code'],
                        "instrument_name": instrument_info['instrument_name'],
                        "tag_number": instrument_info['tag_number']
                    })
                    
                    # Set primary instrument as the first recognized one
                    if primary_instrument is None and instrument_info['code'] is not None:
                        primary_instrument = instrument_info['instrument_name']

                detection_entry = {
                    "class_name": cls_name,
                    "conf_score": float(round(conf_score, 4)),
                    "bbox_pdf": [float(round(v, 3)) for v in pdf_bbox],  # x0,y0,x1,y1 in PDF points
                    "bbox_pixels": [float(round(x0_px, 1)), float(round(y0_px, 1)), float(round(x1_px, 1)), float(round(y1_px, 1))],
                    "texts_inside": texts,
                    "primary_instrument": primary_instrument if primary_instrument else "Unknown",
                    "instruments_recognized": instruments_recognized
                }
                results_all.append(detection_entry)
                page_detections.append(detection_entry)
            
            # Debug visualization for first page
            if DEBUG_BBOX and page_num == 1 and len(page_detections) > 0:
                print(f"\n[Debug] Generating bbox visualization for page 1...")
                pdf_base = Path(pdf_path).stem
                debug_fig = debug_bbox_overlay(page, img, page_detections, (img_w, img_h), dpi, 
                                              save_prefix=f"{pdf_base}_page{page_num}")
                plt.show()
                plt.close(debug_fig)
                print(f"[Debug] Visualization saved")
            
            # Update progress: page completed
            if progress_callback:
                progress = int(page_num / doc.page_count * 100)
                progress_callback(progress)

        # Summary
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total detections: {len(results_all)}")
        if doc.page_count > 0:
            print(f"Average per page: {len(results_all) / doc.page_count:.1f}")
        
        # Count by class
        if results_all:
            class_counts = {} 
            for det in results_all:
                cls = det['class_name']
                class_counts[cls] = class_counts.get(cls, 0) + 1
            
            print(f"\nDetections by class:")
            for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {cls}: {count}")
        
        if out_json_path:
            with open(out_json_path, "w", encoding="utf-8") as f:
                json.dump(results_all, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {out_json_path}")
        
        print(f"{'='*60}\n")

    finally:
        # Always close documents
        doc.close()
        if pdf_plumber_doc:
            pdf_plumber_doc.close()

    return results_all

# ---------------------------
# CLI
# ---------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Detect P&ID symbols in PDF using YOLO and extract associated text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python PDFProcessor_wo_ocr.py input.pdf model.pt
  python PDFProcessor_wo_ocr.py input.pdf model.pt --conf 0.3 --out results.json
  python PDFProcessor_wo_ocr.py input.pdf model.pt --dpi 250
        """
    )
    parser.add_argument("pdf", type=str, help="Input PDF path")
    parser.add_argument("yolo_model", type=str, help="YOLO model weights (e.g., best.pt)")
    parser.add_argument("--dpi", type=int, default=None, 
                       help="Render DPI (default: auto-calculate for optimal 1280px)")
    parser.add_argument("--conf", type=float, default=YOLO_CONF, 
                       help=f"YOLO confidence threshold (default: {YOLO_CONF})")
    parser.add_argument("--out", type=str, default="pid_detections.json", 
                       help="Output JSON file (default: pid_detections.json)")
    args = parser.parse_args()
    
    pdf_path = args.pdf
    yolo_model_path = args.yolo_model

    assert os.path.exists(pdf_path), f"PDF not found: {pdf_path}"
    assert os.path.exists(yolo_model_path), f"YOLO model not found: {yolo_model_path}"

    results = process_pdf_with_yolo(
        pdf_path, 
        yolo_model_path, 
        out_json_path=args.out, 
        dpi=args.dpi, 
        conf=args.conf
    )

if __name__ == "__main__":
    main()
