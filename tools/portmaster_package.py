"""Export the unchanged public package files into a PortMaster ZIP and source tree."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import shutil
import stat
import zipfile


def settings(root):
    return json.loads((Path(root)/'tools/port-config.json').read_text(encoding='utf-8'))


def game_data_path(root, config):
    root = Path(root)
    metadata = json.loads((root/'package/port.json').read_text(encoding='utf-8'))
    attr = metadata.get('attr')
    if not isinstance(attr, dict):
        raise ValueError('package/port.json must contain an attr object')
    marker = '<ports directory>/' + config['id'] + '/'
    found = set()
    for text in (attr.get('inst'), attr.get('inst_md')):
        if not isinstance(text, str):
            continue
        for match in re.finditer(re.escape(marker) + r'([^\s`]+)', text):
            found.add(match.group(1).rstrip('.,;:'))

    configured = PurePosixPath(str(config['game_file']).replace('\\', '/'))
    if configured.is_absolute() or not configured.parts or any(part in ('', '.', '..') for part in configured.parts):
        raise ValueError('Unsafe game-data destination in tools/port-config.json')
    if found:
        if len(found) != 1:
            raise ValueError('port.json must specify one consistent game-data destination')
        relative = PurePosixPath(found.pop())
        if relative.is_absolute() or not relative.parts or any(part in ('', '.', '..') for part in relative.parts):
            raise ValueError('Unsafe game-data destination in package/port.json')
        if relative.as_posix() != configured.as_posix():
            raise ValueError('Game-data destination in package/port.json does not match port-config.json')
    else:
        relative = configured
    return Path(*relative.parts)


def _host_name(config):
    return config['id']+'/runtime/'+config['id']+'-host.jar'


def _generated_host(root, config, generated_host):
    if generated_host is not None:
        return Path(generated_host)
    built = Path(root)/'build/artifacts'/(config['id']+'-host.jar')
    return built if built.is_file() else None



def runtime_entries(root, config):
    if not config.get('generated_runtime'):
        return []
    manifest = Path(root)/'build/artifacts/runtime-files.json'
    if not manifest.is_file():
        manifest = Path(root)/'build/runtime-files.json'
    if not manifest.is_file():
        raise ValueError('Generated runtime manifest missing; run a full build first')
    return json.loads(manifest.read_text(encoding='utf-8'))


def library_entries(root, config):
    if not config.get('runtime_libraries'):
        return []
    return json.loads((Path(root)/'tools'/config.get('library_lock', 'runtime-lock.json')).read_text(encoding='utf-8'))


def library_name(game, entry):
    directory = PurePosixPath(str(entry.get('directory', 'runtime/lib')).replace('\\', '/'))
    filename = str(entry['name'])
    if directory.is_absolute() or '..' in directory.parts or '/' in filename or '\\' in filename or filename in ('', '.', '..'):
        raise ValueError('Unsafe runtime library path: '+str(entry))
    return (PurePosixPath(game)/directory/filename).as_posix()


def public_files(root, generated_host=None):
    root = Path(root)
    config = settings(root)
    package = root/'package'
    game = config['id']
    host_name = _host_name(config)
    game_data = (PurePosixPath(game)/game_data_path(root, config).as_posix()).as_posix()
    files = {}
    runtimes = runtime_entries(root, config)
    runtime_names = {library_name(game, entry) for entry in runtimes}
    private = {game+'/save', game+'/saves', game+'/cache', game+'/userdata'}

    for source in sorted(package.rglob('*')):
        if source.is_symlink():
            raise ValueError('Package must not contain symlinks: '+str(source))
        if not source.is_file():
            continue
        name = source.relative_to(package).as_posix()
        if source.name.lower() == 'testing_thread.txt':
            continue
        if any(name == directory or name.startswith(directory+'/') for directory in private):
            continue
        if name in (game+'/log.txt', game+'/resolution.txt'):
            continue
        if name.startswith(game+'/gamedata/') and source.name != 'PLACE_GAMEDATA_HERE.txt':
            continue
        # Only the fresh host and checksum-pinned runtime JARs are redistributable.
        if name == game_data or (name.lower().endswith('.jar') and name != host_name and name not in runtime_names):
            continue
        if source.name in ('.DS_Store', 'Thumbs.db', 'desktop.ini'):
            continue
        relative = PurePosixPath(name)
        if relative.is_absolute() or not relative.parts or any(part in ('', '.', '..') for part in relative.parts):
            raise ValueError('Unsafe path in package: '+name)
        files[name] = source.read_bytes()

    artifact = _generated_host(root, config, generated_host)
    if artifact is not None:
        if not artifact.is_file():
            raise ValueError('Generated host JAR is missing: '+str(artifact))
        files[host_name] = artifact.read_bytes()
    for entry in runtimes:
        name = library_name(game, entry)
        staged = root/'build/artifacts'/entry.get('directory', 'runtime/lib')/entry['name']
        if staged.is_file():
            files[name] = staged.read_bytes()
        if name not in files or hashlib.sha256(files[name]).hexdigest() != entry['sha256']:
            raise ValueError('Generated runtime checksum mismatch: '+name)
    for entry in library_entries(root, config):
        if entry.get('test_only'):
            continue
        name = library_name(game, entry)
        if name not in files or hashlib.sha256(files[name]).hexdigest() != entry['sha256']:
            raise ValueError('Bundled library checksum mismatch: '+name)
    required = {
        config['script'], 'port.json', 'README.md', 'gameinfo.xml', 'screenshot.png', 'cover.png',
        game+'/display.inc', game+'/'+config['mapping'], host_name,
        *[game+'/'+name for name in config.get('extra_files', [])],
    }
    missing = sorted(required-set(files))
    if missing:
        raise ValueError('Missing required package file(s): '+', '.join(missing))

    try:
        json.loads(files['port.json'].decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid package/port.json; fix the source file directly') from error
    return files


def public_directories(root):
    root = Path(root)
    config = settings(root)
    package = root/'package'
    game = config['id']
    result = set()
    for source in package.rglob('*'):
        if source.is_symlink():
            raise ValueError('Package must not contain symlinks: '+str(source))
        if not source.is_dir():
            continue
        relative = source.relative_to(package).as_posix()
        if relative == game or any(relative == game+'/'+name or relative.startswith(game+'/'+name+'/')
                                   for name in ('save', 'saves', 'cache', 'userdata')):
            continue
        if not relative.startswith(game+'/'):
            relative = game+'/'+relative
        result.add(relative+'/')
    for raw in config.get('directories', []):
        name = str(raw).replace('\\', '/').strip('/')
        parts = name.split('/') if name else []
        if not parts or any(part in ('', '.', '..') for part in parts):
            raise ValueError('Invalid package directory: '+str(raw))
        result.add(game+'/'+name+'/')
    return sorted(result)


def installed_name(name, config):
    if name == config['script']:
        return name
    if name.startswith(config['id']+'/'):
        return name
    return config['id']+'/'+name


def export(root, generated_host=None):
    root = Path(root)
    config = settings(root)
    game = config['id']
    files = public_files(root, generated_host)
    directories = public_directories(root)
    tree = root/'ports'/game
    ports_root = root/'ports'
    ports_root.mkdir(parents=True, exist_ok=True)
    ports_resolved = ports_root.resolve()
    tree_resolved = tree.resolve()
    try:
        tree_resolved.relative_to(ports_resolved)
    except ValueError as error:
        raise ValueError('Generated port path escapes ports/: '+str(tree)) from error
    if tree_resolved == ports_resolved or tree.is_symlink():
        raise ValueError('Refusing unsafe generated port path: '+str(tree))
    tree.mkdir(parents=True, exist_ok=True)

    data_path = game_data_path(root, config)
    data_directory = (tree/game/data_path.parent).resolve()
    data_directory.relative_to(tree.resolve())
    manifest = root/'build/portmaster-export.json'
    previous = []
    if manifest.is_file():
        saved = json.loads(manifest.read_text(encoding='utf-8'))
        previous = saved.get('files', []) if isinstance(saved, dict) else saved
        if not isinstance(previous, list) or not all(isinstance(name, str) for name in previous):
            raise ValueError('Invalid generated port manifest: '+str(manifest))

    for name in previous:
        if name in files:
            continue
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('Unsafe path in generated port manifest: '+name)
        target = tree.joinpath(*relative.parts)
        resolved = target.resolve()
        resolved.relative_to(tree.resolve())
        if resolved == data_directory or data_directory in resolved.parents:
            continue
        if target.is_symlink():
            raise ValueError('Refusing to remove generated path through a symlink: '+str(target))
        if target.is_file():
            target.chmod(target.stat().st_mode | stat.S_IWRITE)
            target.unlink()

    for name in directories:
        target = (tree/name.rstrip('/')).resolve()
        target.relative_to(tree.resolve())
        target.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = tree/name
        target.resolve().relative_to(tree.resolve())
        if target.is_symlink():
            raise ValueError('Refusing to overwrite generated path through a symlink: '+str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.chmod(target.stat().st_mode | stat.S_IWRITE)
        target.write_bytes(data)

    for directory in sorted((path for path in tree.rglob('*') if path.is_dir()),
                            key=lambda path: len(path.parts), reverse=True):
        resolved = directory.resolve()
        if resolved == data_directory or data_directory in resolved.parents or resolved in data_directory.parents:
            continue
        try:
            directory.rmdir()
        except OSError:
            pass

    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = manifest.with_suffix('.json.tmp')
    temporary_manifest.write_text(json.dumps({'files': sorted(files)}), encoding='utf-8')
    os.replace(temporary_manifest, manifest)
    destination_dir = root/'dist'
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir/config['zip']
    temporary = root/'build'/config['zip']
    temporary.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted([*files, *directories]):
            installed = installed_name(name, config)
            info = zipfile.ZipInfo(installed, (2026, 9, 12, 0, 0, 0))
            info.create_system = 3
            if name.endswith('/'):
                info.external_attr = (0o40755 << 16) | 0x10
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, b'')
            else:
                info.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, files[name])
    temporary.replace(destination)
    print('Built', destination)


if __name__ == '__main__':
    export(Path(__file__).resolve().parents[1])
