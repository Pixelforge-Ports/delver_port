"""Validate redistributable boundaries, metadata, licenses and installation layout."""
import configparser
import io
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile
from portmaster_package import settings, public_files, installed_name

def require(condition, message):
    if not condition:
        raise ValueError(message)

def verify(root):
    root = Path(root)
    config = settings(root)
    game = config['id']
    files = public_files(root)
    expected = {installed_name(n, config): data for n, data in files.items()}
    with zipfile.ZipFile(root/'dist'/config['zip']) as archive:
        require(archive.testzip() is None, 'Damaged ZIP')
        require(len(archive.namelist()) == len(expected), 'Duplicate/extra ZIP entry')
        require(set(archive.namelist()) == set(expected), 'Unexpected ZIP contents')
        for entry in archive.infolist():
            require(archive.read(entry) == expected[entry.filename], 'Stale file: '+entry.filename)
            require(entry.filename.startswith(game+'/') or entry.filename == config['script'], 'Unsafe path')
            mode = (entry.external_attr >> 16) & 0o777
            require(mode == (0o755 if entry.filename.endswith('.sh') else 0o644), 'Wrong Unix permissions')
    require(sorted(p.name for p in (root/'dist').iterdir()) == [config['zip']], 'dist must contain only the universal ZIP')
    metadata = json.loads(files['port.json'])
    attr = metadata['attr']
    require(metadata['version'] == 4 and metadata['name'] == game+'.zip', 'Wrong metadata version/name')
    require(metadata['items'] == [config['script'], game], 'Wrong items')
    require(attr['porter'] == ['Pixelforge ports (Ronax)'], 'Wrong porter')
    require(attr['availability'] == 'paid' and attr['rtr'] is False and attr['exp'] is False, 'Wrong BYO flags')
    require(attr['arch'] == ['aarch64'], 'Wrong architecture')
    require(attr['runtime'] == ['weston_pkg_0.2.squashfs', 'zulu17.54.21-ca-jre17.0.13-linux.squashfs'], 'Wrong runtimes')
    require(all(set(s) == {'name','gameurl','developerurl'} for s in attr['store']), 'Invalid store objects')
    require(files['README.md'].startswith(b'## Notes\n'), 'README must start with Notes')
    require((root/'package/testing_thread.txt').read_bytes() == (root/'testing_thread.txt').read_bytes(), 'Stale testing thread')
    for name, data in files.items():
        if name.endswith(('.sh','.ini','.inc','.md','.json','.xml','.txt')):
            require(b'\r' not in data and not data.startswith(b'\xef\xbb\xbf'), 'Use UTF-8 without BOM and LF: '+name)
    png = files['screenshot.png']
    require(png.startswith(b'\x89PNG\r\n\x1a\n'), 'Missing PNG screenshot')
    width, height = struct.unpack('>II', png[16:24])
    require(width >= 640 and height >= 480, 'Screenshot below 640x480')
    xml = ET.fromstring(files['gameinfo.xml']).find('game')
    require(xml.findtext('path') == './'+config['script'], 'Wrong gameinfo path')
    require(xml.findtext('image') == './'+game+'/screenshot.png', 'Wrong image path')
    require(xml.findtext('developer') and xml.findtext('desc'), 'Incomplete gameinfo')
    require(config['mapping'].endswith('.ini'), 'gptokeyb2 requires an INI mapping')
    launcher = files[config['script']].decode('utf-8')
    require('$GPTOKEYB2 java -c ' in launcher, 'Launcher must use gptokeyb2')
    require('$GPTOKEYB ' not in launcher and 'TEXTINPUTINTERACTIVE' not in launcher, 'Legacy mapper setup')
    require(not any(n.endswith('.gptk') for n in files), 'Legacy mapping in package')
    require('export SDL_TOUCH_MOUSE_EVENTS=0' in launcher, 'Disable touch-generated mouse events')
    mapping = files[game+'/'+config['mapping']].decode('utf-8')
    cp = configparser.ConfigParser(interpolation=None, strict=True)
    cp.read_string(mapping)
    require(cp['controls']['start'] == 'esc', 'Start must open the pause/options menu')
    if game == 'mewnbase':
        require(cp['controls']['a'] == 'mouse_left' and cp['controls']['b'] == 'mouse_right', 'MewnBase needs real mouse buttons')
    require(cp['controls'].get('overlay') == 'clear', 'Explicit root controls required')
    require(cp['controls']['right_analog'] == 'mouse_movement' and cp['controls']['r2'] == 'mouse_left', 'Mouse aim/fire mapping required')
    require(cp['controls']['l2'] == 'hold_state look' and cp['controls:look']['dpad'] == 'mouse_movement', 'Stickless look controls required')
    for section in cp.sections():
        for key, value in cp[section].items():
            require(not key.endswith('_hk'), 'Use a v2 hotkey state')
            if value.startswith(('hold_state ', 'push_state ', 'set_state ')):
                require('controls:'+value.split()[1] in cp, 'Unknown control state')
    if game == 'mewnbase':
        require(cp['controls']['back'] == 'hold_state hotkey', 'Missing hotkey state')
        require(cp['controls:hotkey']['l1'] == 'push_state text_input', 'Missing text entry')
        require(cp['controls:text_input']['start'] == 'finish_text', 'Text confirmation missing')
        require(cp['controls:text_input']['back'] == 'cancel_text', 'Text cancellation missing')
    license_root = game+'/licenses/'
    require(b'GNU GENERAL PUBLIC LICENSE' in files[license_root+'LICENSE-gptokeyb.txt'], 'Missing gptokeyb license')
    own = files[license_root+'LICENSE-'+game+'.txt']
    require(own == (root/'LICENSE').read_bytes(), 'Source/port license mismatch')
    for name in ['LICENSE-'+game+'.txt', 'LICENSE-'+game+'-host.txt']:
        data = files[license_root+name]
        require(b'Copyright (c) 2026 Pixelforge Ports contributors' in data and b'Permission is hereby granted' in data, 'Missing host/port MIT terms')
    with zipfile.ZipFile(io.BytesIO(files[game+'/runtime/'+game+'-host.jar'])) as host:
        require(bool(host.namelist()), 'Empty host')
        require(all(n.startswith('org/portmaster/'+game+'/') and n.endswith('.class') for n in host.namelist()), 'Game or compile-only classes leaked into host')
    for name, data in files.items():
        require((root/'ports'/game/name).read_bytes() == data, 'Stale public tree: '+name)
    print('PACKAGE_OK', config['zip'], len(expected), 'public files')

if __name__ == '__main__':
    verify(Path(__file__).resolve().parents[1])
