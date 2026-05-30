"""
Auto-updates README.md before each commit.
- Rebuilds the Project Structure section based on actual files in the project.
- Rebuilds the Features section from # README: markers in .py files.
Run manually: python update_readme.py
Runs automatically via .git/hooks/pre-commit
"""
import os
import re
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(ROOT, 'README.md')

# Descriptions for known files
FILE_DESC = {
    'runner.py':           'Mode launcher with restart/stop control',
    'monitor.py':          'Continuous monitor + Groq AI analysis',
    'discovery.py':        'One-time command discovery',
    'main.py':             'Quick one-off test',
    'commands.py':         'Command lists and monitor schedule',
    'read_pdfs.py':        'PDF reader utility',
    'start-discovery.bat': 'Double-click to start Discovery mode',
    'start-monitor.bat':   'Double-click to start Monitor mode',
    'start-main.bat':      'Double-click to start Main mode',
    'requirements.txt':    '',
    '.env':                'Your secrets (not committed)',
    '.env.example':        'Template for .env',
    'update_readme.py':    'Auto-updates this README before each commit',
}

# Preferred display order
ORDER = [
    'runner.py', 'monitor.py', 'discovery.py', 'main.py',
    'commands.py', 'read_pdfs.py',
    'start-discovery.bat', 'start-monitor.bat', 'start-main.bat',
    'requirements.txt', '.env', '.env.example', 'update_readme.py',
]

SKIP = {'.git', '__pycache__', 'data', 'assets', 'session.session',
        'session.session-journal', 'known_hosts', 'README.md', '.gitignore'}


# ── Features ─────────────────────────────────────────────────────────────────

def collect_features() -> list:
    """Scan all .py files for # README: markers and return feature lines."""
    features = []
    seen = set()
    py_files = sorted(glob.glob(os.path.join(ROOT, '*.py')))
    for filepath in py_files:
        filename = os.path.basename(filepath)
        if filename == 'update_readme.py':
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r'\s*#\s*README:\s*(.+)', line)
                if m:
                    feature = m.group(1).strip()
                    if feature not in seen:
                        features.append(feature)
                        seen.add(feature)
    return features


def build_features(features: list) -> str:
    lines = ['## Features', '']
    for feature in features:
        lines.append(f'- {feature}')
    return '\n'.join(lines)


def update_features(content: str) -> str:
    features = collect_features()
    if not features:
        return content
    new_section = build_features(features)
    pattern = r'## Features\n[\s\S]*?(?=\n## )'
    return re.sub(pattern, new_section + '\n', content)


# ── Project Structure ─────────────────────────────────────────────────────────

def build_structure():
    all_files = set(
        f for f in os.listdir(ROOT)
        if os.path.isfile(os.path.join(ROOT, f)) and f not in SKIP
    )

    # Build ordered list: known order first, then remaining alphabetically
    seen = set()
    ordered = []
    for f in ORDER:
        if f in all_files or f in ('.env', '.env.example'):
            ordered.append(f)
            seen.add(f)
    for f in sorted(all_files):
        if f not in seen:
            ordered.append(f)

    lines = ['```', 'MikabotReportBot/']
    for f in ordered:
        desc = FILE_DESC.get(f, '')
        comment = f'   # {desc}' if desc else ''
        lines.append(f'├── {f}{comment}')

    lines.append('├── data/')
    lines.append('│   ├── knowledge_base.json   # Discovery output')
    lines.append('│   └── market_log.json       # Monitor log (last 500 entries)')
    lines.append('└── assets/                   # MikaBot PDF guides')
    lines.append('```')
    return '\n'.join(lines)


def update_structure(content: str) -> str:
    new_structure = build_structure()
    pattern = r'(## Project Structure\n\n)```[\s\S]*?```'
    return re.sub(pattern, r'\g<1>' + new_structure, content)


# ── Main ──────────────────────────────────────────────────────────────────────

def update_readme():
    with open(README, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = update_features(content)
    new_content = update_structure(new_content)

    if new_content == content:
        print('README.md — no changes needed.')
        return

    with open(README, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print('README.md updated.')


if __name__ == '__main__':
    update_readme()
