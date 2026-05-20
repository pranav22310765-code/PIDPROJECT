"""
Debug script to test the full recognition and display pipeline
"""

from PDFProcessor_wo_ocr import recognize_instrument_type

# Simulate what happens in the pipeline
test_detections = [
    {
        "class_name": "Check Valve",
        "texts_inside": ["CV-001", "3\""],
        "primary_instrument": None,
    },
    {
        "class_name": "Offline Instrument",
        "texts_inside": ["PI-101"],
        "primary_instrument": None,
    },
    {
        "class_name": "2way Valve",
        "texts_inside": ["LSHH-03"],
        "primary_instrument": None,
    },
    {
        "class_name": "Offline Instrument",
        "texts_inside": ["KSH"],
        "primary_instrument": None,
    },
]

print("="*80)
print("PIPELINE DEBUG TEST")
print("="*80 + "\n")

# Step 1: Recognize instruments
for idx, detection in enumerate(test_detections):
    print(f"\n[Detection {idx+1}]")
    print(f"  Class: {detection['class_name']}")
    print(f"  Texts: {detection['texts_inside']}")
    
    instruments_recognized = []
    primary_instrument = None
    
    for text in detection['texts_inside']:
        instrument_info = recognize_instrument_type(text)
        print(f"    - '{text}' → Code: {instrument_info['code']}, Name: {instrument_info['instrument_name']}, Tag: '{instrument_info['tag_number']}'")
        
        instruments_recognized.append({
            "raw_text": text,
            "code": instrument_info['code'],
            "instrument_name": instrument_info['instrument_name'],
            "tag_number": instrument_info['tag_number']
        })
        
        if primary_instrument is None and instrument_info['code'] is not None:
            primary_instrument = instrument_info['instrument_name']
    
    # Step 2: Build display row
    print(f"\n  Building display row:")
    tag_numbers = []
    codes = []
    names = []
    
    for inst in instruments_recognized:
        if inst.get('code'):
            codes.append(inst['code'])
            names.append(inst['instrument_name'])
        
        if 'tag_number' in inst:
            tag = inst['tag_number']
            tag_numbers.append(tag if tag else '(no tag)')
    
    print(f"    Codes: {', '.join(codes) if codes else '-'}")
    print(f"    Names: {', '.join(names) if names else primary_instrument if primary_instrument else '-'}")
    print(f"    Tags: {', '.join(tag_numbers) if tag_numbers else '-'}")

print("\n" + "="*80)
