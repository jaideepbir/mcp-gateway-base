from datetime import datetime
from pathlib import Path

def main():
    repo = Path('projects/mcp-gateway')
    repo.mkdir(parents=True, exist_ok=True)

    checkpoint = repo / 'checkpoint.md'
    if not checkpoint.exists():
        checkpoint.write_text(
            '# Project Checkpoint Log\n\n'
            'Rules:\n'
            '1. Always follow this format per update:\n'
            '   - [YYYY-MM-DD HH:MM:SS TZ] Brief summary for each entry\n'
            '2. After each task is completed, update the checkpoint file.\n'
            '3. Try to ensure checkpoint file is read at the beginning of each chat session.\n'
            '4. Always append - never over write the file.\n\n'
            '---\n'
        )

    now = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
    summary = (
        f"- [{now}] "
    )

    with checkpoint.open('a', encoding='utf-8') as f:
        f.write(summary)

    gitignore = repo / '.gitignore'
    lines = gitignore.read_text(encoding='utf-8').splitlines() if gitignore.exists() else []
    if 'checkpoint.md' not in lines:
        with gitignore.open('a', encoding='utf-8') as f:
            if lines and not gitignore.read_text().endswith('\n'):
                f.write('\n')
            f.write('checkpoint.md\n')

    print('checkpoint.md updated and .gitignore ensured')

if __name__ == '__main__':
    main()
