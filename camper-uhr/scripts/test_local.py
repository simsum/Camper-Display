"""Run existing Python and JavaScript tests with temporary application data."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default=shutil.which('node'))
    args = parser.parse_args()
    if not args.node:
        parser.error('Node.js fehlt im PATH. Bitte --node <Pfad zu node.exe> angeben.')
    with tempfile.TemporaryDirectory(prefix='camper-tests-') as directory:
        env = dict(os.environ, CAMPERDISPLAY_DATA_DIR=directory,
                   CAMPERDISPLAY_VACATION_DB=str(Path(directory) / 'camperdisplay.db'))
        commands = [
            [sys.executable, '-m', 'pip', 'check'],
            [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        ]
        commands.extend([args.node, str(path)] for path in sorted((ROOT / 'tests').glob('test_*.js')))
        commands.extend([args.node, '--check', str(path)] for path in sorted((ROOT / 'frontend').rglob('*.js')))
        for command in commands:
            subprocess.run(command, cwd=ROOT, env=env, check=True)
    print('Alle lokalen Tests und JavaScript-Syntaxpruefungen bestanden.')


if __name__ == '__main__':
    main()
