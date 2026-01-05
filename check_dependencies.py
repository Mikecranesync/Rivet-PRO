"""Check if all required dependencies are installed"""
import sys

deps = {
    'telegram': 'python-telegram-bot',
    'PIL': 'pillow',
    'groq': 'groq',
    'anthropic': 'anthropic',
    'openai': 'openai',
    'google.genai': 'google-generativeai',
    'dotenv': 'python-dotenv',
    'pydantic': 'pydantic',
    'httpx': 'httpx',
}

print('Checking dependencies...\n')
missing = []

for module, package in deps.items():
    try:
        __import__(module)
        print(f'[OK] {package}')
    except ImportError:
        missing.append(package)
        print(f'[MISSING] {package}')

print(f'\nResults: {len(deps) - len(missing)}/{len(deps)} dependencies installed')

if missing:
    print(f'\nTo install missing packages:')
    print(f'pip install {" ".join(missing)}')
else:
    print('\nAll dependencies installed!')
