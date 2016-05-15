# this script is a conglomeration of
# the getstash installation script (https://github.com/ywangd/stash/blob/master/getstash.py)
# and the shortcutgenerator script by omz (https://gist.github.com/omz/7870550)
# full credit to the authors
# the icon was made by Vicent Pla (https://www.iconfinder.com/icons/204717/mlb_icon)


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import requests
import zipfile
import console

TMPDIR = os.environ.get('TMPDIR', os.environ.get('TMP'))
URL_ZIPFILE = 'https://github.com/hyshai/mlbplayista/archive/master.zip'
TEMP_ZIPFILE = os.path.join(TMPDIR, 'mlbplayista.zip')


print('Downloading {} ...'.format(URL_ZIPFILE))

try:
    r = requests.get(URL_ZIPFILE, stream=True)
    file_size = r.headers.get('Content-Length')
    if file_size is not None:
        file_size = int(file_size)

    with open(TEMP_ZIPFILE, 'wb') as outs:
        block_sz = 8192
        for chunk in r.iter_content(block_sz):
            outs.write(chunk)


except Exception as e:
    sys.stderr.write('{}\n'.format(e))
    sys.stderr.write('Download failed! Please make sure internet connection is available.\n')
    sys.exit(1)

BASE_DIR = os.path.expanduser('~')
TARGET_DIR = os.path.join(BASE_DIR, 'Documents/MLBPlayista')
if not os.path.exists(TARGET_DIR):
    os.makedirs(TARGET_DIR)
print('Unzipping into %s ...' % TARGET_DIR)

with open(TEMP_ZIPFILE, 'rb') as ins:
    try:
        zipfp = zipfile.ZipFile(ins)
        for name in zipfp.namelist():
            data = zipfp.read(name)
            name = name.split('MLBPlayista-master/', 1)[-1]  # strip the top-level directory
            if name == '':  # skip top-level directory
                continue

            fname = os.path.join(TARGET_DIR, name)
            if fname.endswith('/'):  # A directory
                if not os.path.exists(fname):
                    os.makedirs(fname)
            else:
                fp = open(fname, 'wb')
                try:
                    fp.write(data)
                finally:
                    fp.close()
    except:
        sys.stderr.write('The zip file is corrupted. Pleases re-run the script.\n')
        sys.exit(1)

print('Preparing the folder structure ...')

# Remove setup files and possible legacy files
try:
    os.remove(TEMP_ZIPFILE)
except:
    pass


print('Setup completed.')
install_shortcut = console.alert('Would you like to install the MLBPlayista shortcut on your homescreen?', message='This is a regular webclip installed as a profile, which will give you quick access to MLBPlayista.', button1='Yes', button2='No', hide_cancel_button=True)
if install_shortcut == 2:
    print('Please run mlbplayista.py in the MLBPlayista directory to start MLBPlayista.')
    sys.exit()

#---- Create homescreen shortcut
import plistlib
import BaseHTTPServer
import webbrowser
import uuid
import notification
import cStringIO
import plistlib

ICON_STRING = 'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgBAMAAAAQtmoLAAAAMFBMVEX///8xMTH19fUeKp3OJCQVHW6QGRkiIiKysrL///8KCgoLCwsMDAwNDQ0ODg4PDw9rzF0PAAAACnRSTlMA////////////fokUVgAAALBJREFUeJxjYBgFgwYIEgmGmQYhJYJAcThqMMYKjJSUXEBgVMOw1QBODqMahrsGI+TcP+w1KCkpY2hQUlIZ3hpCQ4NBlGloKFStWhoQpBCdlsCGk5L4BlgDITD8NIiXl3d0tJdDAJgF5VZ0QEB5eSF682fmzInQVg6YBeVKzoQALO2lQakBLA5WgaIBSgxTDRMxCIT+4awBTSvhUBpuGhAphcgMNAQ1EAGGlYZRMOAAANi2WZGK6JkyAAAAAElFTkSuQmCC'

class ConfigProfileHandler (BaseHTTPServer.BaseHTTPRequestHandler):
	config = None
	def do_GET(s):
		s.send_response(200)
		s.send_header('Content-Type', 'application/x-apple-aspen-config')
		s.end_headers()
		plist_string = plistlib.writePlistToString(ConfigProfileHandler.config)
		s.wfile.write(plist_string)
	def log_message(self, format, *args):
		pass

def run_server(config):
	ConfigProfileHandler.config = config
	server_address = ('', 0)
	httpd = BaseHTTPServer.HTTPServer(server_address, ConfigProfileHandler)
	sa = httpd.socket.getsockname()
	webbrowser.open('safari-http://localhost:' + str(sa[1]))
	httpd.handle_request()
	notification.schedule('Tap "Install" to add the shortcut to your homescreen.', 0.75)


console.show_activity('Preparing shortcut...')
data_buffer = cStringIO.StringIO()
data_buffer.write(ICON_STRING.decode('base64'))
icon_data = data_buffer.getvalue()
unique_id = uuid.uuid4().urn[9:].upper()
plist = plistlib.readPlist(os.path.abspath(os.path.join(sys.executable, '..', 'Info.plist')))
config = {'PayloadContent': [{'FullScreen': True,
            'Icon': plistlib.Data(icon_data), 'IsRemovable': True,
            'Label': 'MLBPlayista', 'PayloadDescription': 'Configures Web Clip',
            'PayloadDisplayName': 'MLBPlayista',
            'PayloadIdentifier': 'com.hyshai.mlbplayista.' + unique_id,
            'PayloadOrganization': 'hyshai:software',
            'PayloadType': 'com.apple.webClip.managed',
            'PayloadUUID': unique_id, 'PayloadVersion': 1,
            'Precomposed': True, 'URL': '{CFBundleURLTypes[0].CFBundleURLSchemes[0]}://MLBPlayista/mlbplayista?action=run'.format(**plist)}],
            'PayloadDescription': 'MLBPlayista',
            'PayloadDisplayName': 'MLBPlayista (Shortcut)',
            'PayloadIdentifier': 'com.hyshai.mlbplayista.' + unique_id,
            'PayloadOrganization': 'hyshai:software',
            'PayloadRemovalDisallowed': False, 'PayloadType':
            'Configuration', 'PayloadUUID': unique_id, 'PayloadVersion': 1}

run_server(config)
