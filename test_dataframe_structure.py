"""
Test the exact DataFrame structure that will be displayed in GUI
"""

import pandas as pd
from PDFProcessor_wo_ocr import recognize_instrument_type

# Simulate detection results from PDF processing
results = [
    {
        "class_name": "Check Valve",
        "texts_inside": ["CV-001"],
        "primary_instrument": "Unknown",
        "instruments_recognized": [
            {
                "raw_text": "CV-001",
                "code": None,
                "instrument_name": "Unknown",
                "tag_number": "001"
            }
        ],
        "conf_score": 0.95
    },
    {
        "class_name": "Offline Instrument",
        "texts_inside": ["PI-101"],
        "primary_instrument": "Pressure Indication",
        "instruments_recognized": [
            {
                "raw_text": "PI-101",
                "code": "PI",
                "instrument_name": "Pressure Indication",
                "tag_number": "101"
            }
        ],
        "conf_score": 0.87
    },
    {
        "class_name": "2way Valve No Pattern",
        "texts_inside": ["LSHH-03"],
        "primary_instrument": "Level Switch High High",
        "instruments_recognized": [
            {
                "raw_text": "LSHH-03",
                "code": "LSHH",
                "instrument_name": "Level Switch High High",
                "tag_number": "03"
            }
        ],
        "conf_score": 0.92
    },
]

print("="*100)
print("DISPLAY DATAFRAME TEST")
print("="*100 + "\n")

# Prepare display columns (exactly like in main.py)
display_data = []
for row in results:
    class_name = row['class_name']
    primary_instrument = row.get('primary_instrument', 'Unknown')
    texts = row.get('texts_inside', [])
    instruments = row.get('instruments_recognized', [])
    
    text_str = ', '.join(texts) if texts else 'No text'
    
    instrument_codes = []
    instrument_names = []
    tag_numbers = []
    
    for inst in instruments:
        if inst.get('code'):
            instrument_codes.append(inst['code'])
            instrument_names.append(inst['instrument_name'])
        
        if 'tag_number' in inst:
            tag = inst['tag_number']
            tag_numbers.append(tag if tag else '(no tag)')
    
    display_data.append({
        'Component Type': class_name,
        'Detected Text': text_str,
        'Instrument Code': ', '.join(instrument_codes) if instrument_codes else '-',
        'Instrument Name': primary_instrument,
        'Tag Numbers': ', '.join(tag_numbers) if tag_numbers else '-',
        'Confidence': f"{row.get('conf_score', 0):.2f}"
    })

display_df = pd.DataFrame(display_data)

print("DataFrame Structure:")
print("-" * 100)
print(display_df.to_string())
print("\n" + "-" * 100)
print(f"\nColumn Names: {list(display_df.columns)}")
print(f"DataFrame Dtypes:\n{display_df.dtypes}")
print(f"\nDataFrame Shape: {display_df.shape[0]} rows × {display_df.shape[1]} columns")
