"""Validate the packaged PortMaster files and their exported copies."""
import configparser
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from portmaster_package import settings, public_files, public_directories, installed_name, game_data_path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root, generated_host=None):
    root = Path(root)
    config = settings(root)
    game = config['id']
    package = root/'package'
    files = public_files(root, generated_host)
    require(files[config['script']] == (package/config['script']).read_bytes(),
            'Launcher copy differs from package source')
    require(files['port.json'] == (package/'port.json').read_bytes(),
            'port.json copy differs from package source')
    require(installed_name('README.md', config) == game+'/README.md',
            'README.md must keep its filename in the ZIP')

    directories = public_directories(root)
    expected = {installed_name(name, config): data for name, data in files.items()}
    expected_directories = {installed_name(name, config) for name in directories}
    with zipfile.ZipFile(root/'dist'/config['zip']) as archive:
        require(archive.testzip() is None, 'Damaged ZIP')
        names = archive.namelist()
        require(len(names) == len(expected)+len(expected_directories), 'Duplicate or extra ZIP entries')
        require(set(names) == set(expected)|expected_directories, 'ZIP contents do not match package files')
        for entry in archive.infolist():
            require(entry.filename.startswith(game+'/') or entry.filename == config['script'],
                    'Unsafe ZIP path: '+entry.filename)
            mode = (entry.external_attr >> 16) & 0o777
            if entry.is_dir():
                require(entry.filename in expected_directories and archive.read(entry) == b'',
                        'Unexpected ZIP directory: '+entry.filename)
                require(mode == 0o755, 'Wrong directory permissions')
            else:
                require(archive.read(entry) == expected[entry.filename], 'Stale ZIP file: '+entry.filename)
                require(mode == (0o755 if entry.filename.endswith('.sh') else 0o644),
                        'Wrong Unix permissions')
    require(sorted(path.name for path in (root/'dist').iterdir()) == [config['zip']],
            'dist must contain only the PortMaster ZIP')

    metadata = json.loads(files['port.json'])
    require(metadata.get('version') == 4 and metadata.get('name') == config['zip'],
            'Wrong PortMaster metadata version/name')
    require(metadata.get('items') == [config['script'], game] and metadata.get('items_opt') == [],
            'Wrong PortMaster metadata items')
    attr = metadata.get('attr')
    require(isinstance(attr, dict), 'Missing PortMaster metadata attributes')
    require(attr.get('title') == config['title'], 'Wrong PortMaster title')
    require(isinstance(attr.get('porter'), list) and attr['porter'] and
            all(isinstance(name, str) and name.strip() for name in attr['porter']), 'Missing porter')
    require(attr.get('availability') == 'paid' and attr.get('rtr') is False and attr.get('exp') is False,
            'Wrong BYO-data flags')
    require(attr.get('arch') == ['aarch64'], 'Wrong architecture')
    require(attr.get('runtime') == ['weston_pkg_0.2.squashfs', 'zulu17.54.21-ca-jre17.0.13-linux.squashfs'],
            'Wrong runtimes')
    require(all(isinstance(store, dict) and set(store) == {'name', 'gameurl', 'developerurl'}
                for store in attr.get('store', [])), 'Invalid store metadata')

    destination = '<ports directory>/'+game+'/'+game_data_path(root, config).as_posix()
    instructions = [value for value in (attr.get('inst'), attr.get('inst_md')) if isinstance(value, str)]
    require(any(destination in text for text in instructions),
            'Installation instructions must show the exact game-data destination')
    source_build = (root/'tools/build.py').read_text(encoding='utf-8')
    hash_line = next((line for line in source_build.splitlines() if line.startswith('SHA256 =')), '')
    fingerprint = hash_line.partition('=')[2].strip().strip(chr(39)+chr(34))
    require(re.fullmatch(r'[0-9a-f]{64}', fingerprint) is not None, 'Missing game-data fingerprint')
    readme = files['README.md']
    require(readme.startswith(b'## Notes\n'), 'README.md must start with Notes')
    require(b'SHA-256' in readme and fingerprint.encode('ascii') in readme,
            'README.md must identify the supported game data')
    require(not any(name.endswith('testing_thread.txt') for name in files),
            'Testing thread must not be included in the installed port')
    require((package/'testing_thread.txt').is_file(), 'Keep testing_thread.txt in package source')
    require(game+'/'+game_data_path(root, config).as_posix() not in files,
            'Owned game data must not be packaged')
    require(not any(name.endswith('/'+Path(config['game_file']).name) for name in files), 'Do not package the owned game JAR')
    require((root/'README.md').read_text(encoding='utf-8').find('## Build the PortMaster package') >= 0,
            'Source README must include the package build instructions')

    for name, data in files.items():
        if name.endswith(('.sh', '.ini', '.inc', '.md', '.json', '.xml', '.txt')):
            require(b'\r' not in data and not data.startswith(b'\xef\xbb\xbf'),
                    'Use UTF-8 without BOM and LF: '+name)
    screenshot = files['screenshot.png']
    cover = files['cover.png']
    require(screenshot.startswith(b'\x89PNG\r\n\x1a\n'), 'Missing screenshot PNG')
    require(cover.startswith(b'\x89PNG\r\n\x1a\n'), 'Missing cover PNG')
    require(struct.unpack('>II', screenshot[16:24])[0] >= 640 and
            struct.unpack('>II', screenshot[16:24])[1] >= 480, 'Screenshot below 640x480')
    require(struct.unpack('>II', cover[16:24]) == (640, 480), 'Cover must be 640x480')

    gameinfo = ET.fromstring(files['gameinfo.xml']).find('game')
    require(gameinfo.findtext('path') == './'+config['script'], 'Wrong gameinfo path')
    require(gameinfo.findtext('image') == './'+game+'/cover.png', 'Wrong gameinfo cover path')
    require(gameinfo.findtext('developer') and gameinfo.findtext('desc'), 'Incomplete gameinfo')
    mapping_name = game+'/'+config['mapping']
    require(config['mapping'].endswith('.ini') and mapping_name in files, 'Missing gptokeyb2 INI mapping')
    launcher = files[config['script']].decode('utf-8')
    require('$GPTOKEYB2 java -c ' in launcher, 'Launcher must use gptokeyb2')
    require('$GPTOKEYB ' not in launcher and 'TEXTINPUTINTERACTIVE' not in launcher,
            'Legacy mapper setup')
    game_data = game_data_path(root, config).as_posix()
    data_dir = PurePosixPath(game_data).parent.as_posix()
    require(f'GAMEDATADIR="$GAMEDIR/{data_dir}"' in launcher,
            'Launcher data directory disagrees with port.json')
    require('"$GAMEDATADIR/$jar_filename"' in launcher,
            'Launcher must validate and run the game JAR from gamedata/')
    controls = configparser.ConfigParser(interpolation=None, strict=True)
    controls.read_string(files[mapping_name].decode('utf-8'))
    require(controls['controls']['start'] == 'esc', 'Start must open the game menu')
    require(controls['controls'].get('overlay') == 'clear', 'Explicit root controls required')
    for section in controls.sections():
        for key, value in controls[section].items():
            require(not key.endswith('_hk'), 'Use a v2 hotkey state')
            if value.startswith(('hold_state ', 'push_state ', 'set_state ')):
                require('controls:'+value.split()[1] in controls, 'Unknown control state')

    require(controls['controls']['right_analog'] == 'mouse_movement', 'Right stick must only move the mouse')
    require(controls['controls']['l2'] == 'q' and controls['controls']['r2'] == 'mouse_left', 'R2 must click menus and attack')
    require(controls['controls']['b'] == 'space', 'Jump must be mapped')
    main_source = (root/'src/org/portmaster/delver/Main.java').read_text(encoding='utf-8')
    require('mouseButton1Action").set(options.getField("instance").get(null),valueOf.invoke(null,"ATTACK"))' in main_source, 'Mouse clicks must activate gameplay attack')
    require('Input.Keys.CONTROL_LEFT,Input.Keys.Q,Input.Keys.SPACE' in main_source, 'Jump must stay independently bound to Space')
    mapped_source = (root/'src/org/portmaster/delver/MappedInput.java').read_text(encoding='utf-8')
    require('case 29:return Input.Keys.CONTROL_LEFT' in mapped_source and 'case 57:return Input.Keys.SPACE' in mapped_source, 'Mapped Ctrl/Space events must reach the game correctly')
    defaults = json.loads(files[game+'/options.txt'])
    require(defaults.get('key_jump') == 62, 'Packaged options must map jump to Space')
    require(defaults.get('mouseXSensitivity') == 3 and defaults.get('mouseYSensitivity') == 3, 'Packaged options must include default mouse sensitivity')
    require('boolean fresh=!java.nio.file.Files.exists(savedOptions)' in main_source and 'Files.copy(defaultOptions,savedOptions)' in main_source, 'Default options must copy to a missing save file only')
    require('-Ddelver.mappedInput=true' in launcher and 'export SDL_TOUCH_MOUSE_EVENTS=0' in launcher,
            'Keep Delver mapped keyboard and mouse delivery')
    require(game+'/runtime/lib/gdx-controllers-lwjgl3-1.9.9.jar' in files,
            'Missing Delver controller API')
    for component in ('libGDX', 'LWJGL', 'GLFW', 'OpenAL-Soft', 'STB'):
        require(game+'/licenses/LICENSE-'+component+'.txt' in files, 'Missing runtime license: '+component)

    license_root = game+'/licenses/'
    license_names = {name[len(license_root):] for name in files if name.startswith(license_root)}
    require('LICENSE-delver-host.txt' in license_names and 'LICENSE-libjpeg-turbo.txt' in license_names,
            'Missing host or compatibility-library license')
    host_license = files[license_root+'LICENSE-delver-host.txt']
    require(b'MIT License' in host_license and b'Permission is hereby granted' in host_license,
            'Invalid host license')
    require(b'GNU GENERAL PUBLIC LICENSE' in files[license_root+'LICENSE-gptokeyb.txt'],
            'Keep the gptokeyb license')
    require(files[license_root+'LICENSE-'+game+'.txt'] == (root/'LICENSE').read_bytes(),
            'Source and packaged port licenses must agree')
    host_name = game+'/runtime/'+game+'-host.jar'
    with zipfile.ZipFile(io.BytesIO(files[host_name])) as host:
        require(bool(host.namelist()), 'Empty host JAR')
        require(all(name.startswith('org/portmaster/'+game+'/') and name.endswith('.class')
                    for name in host.namelist()), 'Game or compile-only classes leaked into host JAR')

    tree = root/'ports'/game
    data_directory = (PurePosixPath(game)/PurePosixPath(game_data).parent).as_posix()
    for name, data in files.items():
        require((tree/name).read_bytes() == data, 'Stale exported port file: '+name)
    expected_tree_files = set(files)
    actual_tree_files = {
        path.relative_to(tree).as_posix() for path in tree.rglob('*') if path.is_file()
        and (not path.relative_to(tree).as_posix().startswith(data_directory+'/')
             or path.relative_to(tree).as_posix() in expected_tree_files)
    }
    require(actual_tree_files == expected_tree_files, 'Port folder must contain package files and no stale files')
    expected_tree_directories = {name.rstrip('/') for name in directories}
    for name in expected_tree_files:
        parent = Path(name).parent
        while str(parent) not in ('', '.'):
            expected_tree_directories.add(parent.as_posix())
            parent = parent.parent
    actual_tree_directories = {
        path.relative_to(tree).as_posix() for path in tree.rglob('*') if path.is_dir()
        and path.relative_to(tree).as_posix() != data_directory
        and not path.relative_to(tree).as_posix().startswith(data_directory+'/')
    }
    if (tree/data_directory).is_dir():
        actual_tree_directories.add(data_directory)
    require(actual_tree_directories == expected_tree_directories, 'Port folder contains stale directories')
    print('PACKAGE_OK', config['zip'], len(expected), 'files and', len(expected_directories), 'directories')


if __name__ == '__main__':
    verify(Path(__file__).resolve().parents[1])
