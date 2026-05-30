import fitz
import os

files = [
    r'assets\MikaBot Eğitim.pdf',
    r"assets\Mikabot'u Maksimum Verimle Kullanmanın 4 Stratejisi.pdf",
]

for fname in files:
    try:
        doc = fitz.open(fname)
        print(f'\n{"="*60}')
        print(f'FILE: {fname} ({len(doc)} pages)')
        print('='*60)
        for i, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                print(f'\n--- Page {i+1} ---')
                print(text)
    except Exception as e:
        print(f'FAIL: {fname} -> {e}')
