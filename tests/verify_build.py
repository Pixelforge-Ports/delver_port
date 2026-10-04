"""Build in an isolated fixture without game JARs; leave package/ and release ZIPs untouched."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def hashes(folder):
    return {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob('*') if path.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    args = parser.parse_args()
    parent = ROOT/'build/build-tests'
    parent.mkdir(parents=True, exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix='run-', dir=parent)).resolve()
    fixture.relative_to(parent.resolve())
    for folder in ('tools', 'src', 'compile-api'):
        source = ROOT/folder
        if source.is_dir():
            for path in source.rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    target = fixture/path.relative_to(ROOT)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
    for path in (ROOT/'package').rglob('*'):
        if path.is_file() and path.suffix.lower() != '.jar':
            target = fixture/path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    for name in ('README.md', 'LICENSE', 'testing_thread.txt'):
        shutil.copyfile(ROOT/name, fixture/name)
    cache = fixture/'build/dependencies'
    cache.mkdir(parents=True, exist_ok=True)
    for path in (ROOT/'build/dependencies').glob('*.jar'):
        shutil.copyfile(path, cache/path.name)
    config = json.loads((fixture/'tools/port-config.json').read_text(encoding='utf-8'))
    game = config['id']
    package = fixture/'package'
    before = hashes(package)
    command = [os.sys.executable, str(fixture/'tools/build.py'), '--jdk', str(args.jdk.resolve()), '--offline']
    subprocess.run(command, cwd=fixture, check=True)
    assert hashes(package)==before, 'Full build changed its package inputs'
    archive_path = fixture/'dist'/config['zip']
    with zipfile.ZipFile(archive_path) as archive:
        assert game+'/README.md' in archive.namelist()
        assert game+'/'+game+'.md' not in archive.namelist()
        assert not any(name.endswith('testing_thread.txt') for name in archive.namelist())
        assert game+'/gamedata/PLACE_GAMEDATA_HERE.txt' in archive.namelist()
        assert game+'/libs.aarch64/libjpeg.so.8' in archive.namelist()
    staged = fixture/'build/artifacts'/(game+'-host.jar')
    assert staged.is_file() and not (package/game/'runtime'/(game+'-host.jar')).exists()
    # A full build must remove stale bytecode and replace an obsolete staged host.
    stale = fixture/'build/classes/org/portmaster'/game/'Removed.class'
    stale.write_bytes(b'stale class')
    staged.write_bytes(b'stale host')
    subprocess.run(command, cwd=fixture, check=True)
    assert not stale.exists() and staged.read_bytes()!=b'stale host'
    assert hashes(package)==before, 'Second full build changed its package inputs'
    # Export updates changed package bytes and removes only previous generated files.
    readme = package/'README.md'
    readme.write_bytes(readme.read_bytes()+b'\nPackaging fixture note.\n')
    readme_after = readme.read_bytes()
    obsolete = package/game/'obsolete-fixture.txt'
    obsolete.write_text('old generated file', encoding='utf-8')
    package_only = [os.sys.executable, str(fixture/'tools/build.py'), '--package-only']
    subprocess.run(package_only, cwd=fixture, check=True)
    obsolete.unlink()
    owned = package/game/config['game_file']
    owned.parent.mkdir(parents=True, exist_ok=True)
    owned.write_bytes(b'owned fixture; must never be packaged')
    preserved = fixture/'ports'/game/game/config['game_file']
    preserved.parent.mkdir(parents=True, exist_ok=True)
    preserved.write_bytes(b'user supplied data; preserve on re-export')
    before_export = hashes(package)
    subprocess.run(package_only, cwd=fixture, check=True)
    assert hashes(package)==before_export, 'Package-only build changed its package inputs'
    assert preserved.read_bytes()==b'user supplied data; preserve on re-export'
    assert not (fixture/'ports'/game/game/'obsolete-fixture.txt').exists()
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.read(game+'/README.md')==readme_after
        assert not any(name.endswith('/'+Path(config['game_file']).name) for name in archive.namelist())
        assert archive.read(config['script'])==(package/config['script']).read_bytes()
        assert archive.read(game+'/port.json')==(package/'port.json').read_bytes()
    print('BUILD_REGRESSION_OK',game,'fresh host, unchanged inputs, exact export, BYO exclusion and data preservation')


if __name__ == '__main__':
    main()
