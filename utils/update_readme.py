"""
Auto-updates README.md before each commit.
- Rebuilds the Project Structure section based on actual files in the project.
- Rebuilds the Features section from # README: markers in .py files.
Run manually: python utils/update_readme.py
Runs automatically via .git/hooks/pre-commit
"""
import os
import re
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, 'README.md')

FILE_DESC = {
    'runner.py':                'Mode launcher with restart/stop control',
    'monitor.py':               'Continuous monitor + Groq AI analysis',
    'discovery.py':             'One-time command discovery',
    'main.py':                  'Quick one-off test',
    'commands.py':              'Command lists and monitor schedule',
    'read_pdfs.py':             'PDF reader utility',
    'generate_commands_pdf.py': '',
    'update_readme.py':         'Auto-updates this README before each commit',
    'discovery.bat':            'Double-click to start Discovery mode',
    'monitor.bat':              'Double-click to start Monitor mode',
    'main.bat':                 'Double-click to start Main mode',
    'requirements.txt':         '',
    '.env':                     'Your secrets (not committed)',
    '.env.example':             'Template for .env',
}

SRC_ORDER     = ['runner.py', 'monitor.py', 'discovery.py', 'main.py', 'commands.py']
UTILS_ORDER   = ['read_pdfs.py', 'generate_commands_pdf.py', 'update_readme.py']
SCRIPTS_ORDER = ['discovery.bat', 'monitor.bat', 'main.bat']
ROOT_ORDER    = ['requirements.txt', '.env', '.env.example']

ROOT_SKIP = {'.git', '__pycache__', 'data', 'assets', 'session.session',
             'session.session-journal', 'README.md', '.gitignore', '.claude',
             'src', 'utils', 'scripts'}


# ── Features ─────────────────────────────────────────────────────────────────

def collect_features() -> list:
    features = []
    seen = set()
    for subdir in ('src', 'utils'):
        py_files = sorted(glob.glob(os.path.join(ROOT, subdir, '*.py')))
        for filepath in py_files:
            if os.path.basename(filepath) == 'update_readme.py':
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

def _subdir_lines(subdir: str, order: list, prefix: str = '│   ') -> list:
    subdir_path = os.path.join(ROOT, subdir)
    if not os.path.isdir(subdir_path):
        return []
    all_files = {
        f for f in os.listdir(subdir_path)
        if os.path.isfile(os.path.join(subdir_path, f))
        and not f.startswith('__') and not f.endswith('.pyc')
    }
    seen = set()
    ordered = []
    for f in order:
        if f in all_files:
            ordered.append(f)
            seen.add(f)
    for f in sorted(all_files):
        if f not in seen:
            ordered.append(f)

    lines = []
    for i, f in enumerate(ordered):
        desc = FILE_DESC.get(f, '')
        comment = f'   # {desc}' if desc else ''
        connector = '└── ' if i == len(ordered) - 1 else '├── '
        lines.append(f'{prefix}{connector}{f}{comment}')
    return lines


def build_structure() -> str:
    lines = ['```', 'MikabotReportBot/']

    lines.append('├── src/')
    lines += _subdir_lines('src', SRC_ORDER)

    lines.append('├── utils/')
    lines += _subdir_lines('utils', UTILS_ORDER)

    lines.append('├── scripts/')
    lines += _subdir_lines('scripts', SCRIPTS_ORDER)

    lines.append('├── data/')
    lines.append('│   ├── knowledge_base.json   # Discovery output')
    lines.append('│   └── market_log.json       # Monitor log (last 500 entries)')
    lines.append('├── assets/                   # MikaBot PDF guides')

    root_files = {
        f for f in os.listdir(ROOT)
        if os.path.isfile(os.path.join(ROOT, f)) and f not in ROOT_SKIP
    }
    seen = set()
    ordered = []
    for f in ROOT_ORDER:
        if f in root_files or f in ('.env', '.env.example'):
            ordered.append(f)
            seen.add(f)
    for f in sorted(root_files):
        if f not in seen:
            ordered.append(f)

    for i, f in enumerate(ordered):
        desc = FILE_DESC.get(f, '')
        comment = f'   # {desc}' if desc else ''
        connector = '└── ' if i == len(ordered) - 1 else '├── '
        lines.append(f'{connector}{f}{comment}')

    lines.append('```')
    return '\n'.join(lines)


def update_structure(content: str) -> str:
    new_structure = build_structure()
    pattern = r'(## Project Structure\n\n)```[\s\S]*?```'
    return re.sub(pattern, r'\g<1>' + new_structure, content)


# ── Monitor interval ──────────────────────────────────────────────────────────

def _read_monitor_interval() -> int | None:
    """Parse MONITOR_INTERVAL value from src/commands.py."""
    commands_path = os.path.join(ROOT, 'src', 'commands.py')
    with open(commands_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^MONITOR_INTERVAL\s*=\s*(\d+)', line)
            if m:
                return int(m.group(1))
    return None


def update_interval(content: str) -> str:
    interval = _read_monitor_interval()
    if interval is None:
        return content
    minutes = interval // 60
    return re.sub(r'Every \d+ minutes', f'Every {minutes} minutes', content)


# ── Main ──────────────────────────────────────────────────────────────────────

def update_readme():
    with open(README, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = update_features(content)
    new_content = update_structure(new_content)
    new_content = update_interval(new_content)

    if new_content == content:
        print('README.md — no changes needed.')
        return

    with open(README, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print('README.md updated.')


if __name__ == '__main__':
    update_readme()
