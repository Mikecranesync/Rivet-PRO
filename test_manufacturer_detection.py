"""Test manufacturer detection patterns"""
from rivet.workflows.sme_router import detect_manufacturer

test_cases = [
    ('Siemens S7-1200 F0002 fault', 'siemens'),
    ('ControlLogix 1756-L73 major fault', 'rockwell'),
    ('ABB ACS880 drive alarm 2710', 'abb'),
    ('Schneider M340 PLC network issue', 'schneider'),
    ('Mitsubishi FX3U ladder logic', 'mitsubishi'),
    ('FANUC robot R-30iA alarm', 'fanuc'),
]

print('Testing manufacturer detection...\n')
passed = 0
failed = 0

for query, expected in test_cases:
    result = detect_manufacturer(query, None)
    status = 'PASS' if result == expected else 'FAIL'
    if result == expected:
        passed += 1
    else:
        failed += 1
    print(f'[{status}] {query[:40]:40} -> {result:12} (expected: {expected})')

print(f'\nResults: {passed}/{len(test_cases)} passed')
if failed == 0:
    print('All tests PASSED!')
