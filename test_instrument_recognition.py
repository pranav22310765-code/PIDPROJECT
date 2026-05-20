"""
Test script to demonstrate instrument recognition functionality
"""

from PDFProcessor_wo_ocr import recognize_instrument_type, INSTRUMENT_MAP

# Test cases with various instrument codes
test_cases = [
    "PI-101",
    "TE-05",
    "TI-2022",
    "LCV-10",
    "LSHH-03",         # 4-letter code
    "VZT-15",          # 3-letter code
    "KSH",             # Code without tag number
    "PT-99",
    "Unknown-123",     # Not in database
    "ABC",             # Short unknown code
    "PDT-001",         # 3-letter code
    "ESHH-50",         # 4-letter code
]

print("="*80)
print("INSTRUMENT RECOGNITION TEST")
print("="*80)
print(f"\nTotal instruments in database: {len(INSTRUMENT_MAP)}\n")

print("Testing instrument recognition:\n")
print(f"{'Raw Text':<20} {'Code':<10} {'Instrument Name':<40} {'Tag #':<15}")
print("-" * 85)

for test_text in test_cases:
    result = recognize_instrument_type(test_text)
    code = result['code'] or '-'
    name = result['instrument_name']
    tag = result['tag_number'] or '(none)'
    
    print(f"{test_text:<20} {code:<10} {name:<40} {tag:<15}")

print("\n" + "="*80)
print("QUICK LEGEND")
print("="*80)
print("""
✓ Recognized: Code found in database → shows instrument name
- Unknown: Code not in database → shows "Unknown" + tag from extracted suffix
(none): No tag number found after code
""")

