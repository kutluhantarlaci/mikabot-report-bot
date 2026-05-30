"""
Auto-updates README.md before each commit.
Rebuilds the Project Structure section based on actual files in the project.
Run manually: python update_readme.py
Runs automatically via .git/hooks/pre-commit
"""
import os
import re

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


def update_readme():
    with open(README, 'r', encoding='utf-8') as f:
        content = f.read()

    new_structure = build_structure()
    pattern = r'(## Project Structure\n\n)```[\s\S]*?```'
    new_content = re.sub(pattern, r'\g<1>' + new_structure, content)

    if new_content == content:
        print('README.md — no changes needed.')
        return

    with open(README, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print('README.md updated.')


if __name__ == '__main__':
    update_readme()
