# the installation script was copied from the getstash installation script (https://github.com/ywangd/stash/blob/master/getstash.py)
# the shortcut script uses omz's shortuct html
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

cached_config = None
if os.path.exists(os.path.join(TARGET_DIR,'config.txt')):
  cached_config = open(os.path.join(TARGET_DIR,'config.txt'),'r+').read()

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
        if cached_config:
          open(os.path.join(TARGET_DIR,'config.txt'),'w').write(cached_config)
    except:
        sys.stderr.write('The zip file is corrupted. Pleases re-run the script.\n')
        sys.exit(1)



# Remove setup files and possible legacy files
try:
    os.remove(TEMP_ZIPFILE)
except:
    pass


print('Setup completed.')
install_shortcut = console.alert('Would you like to install the MLBPlayista shortcut on your homescreen?', message='This is a regular webclip, which will give you quick access to MLBPlayista.', button1='Yes', button2='No', hide_cancel_button=True)
if install_shortcut == 2:
    print('Please run mlbplayista.py in the MLBPlayista directory to start MLBPlayista.')
    sys.exit()

#---- Create homescreen shortcut
import base64
import webbrowser
import BaseHTTPServer
import base64
icons = {'icon' : 'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgBAMAAAAQtmoLAAAAMFBMVEX///8xMTH19fUeKp3OJCQVHW6QGRkiIiKysrL///8KCgoLCwsMDAwNDQ0ODg4PDw9rzF0PAAAACnRSTlMA////////////fokUVgAAALBJREFUeJxjYBgFgwYIEgmGmQYhJYJAcThqMMYKjJSUXEBgVMOw1QBODqMahrsGI+TcP+w1KCkpY2hQUlIZ3hpCQ4NBlGloKFStWhoQpBCdlsCGk5L4BlgDITD8NIiXl3d0tJdDAJgF5VZ0QEB5eSF682fmzInQVg6YBeVKzoQALO2lQakBLA5WgaIBSgxTDRMxCIT+4awBTSvhUBpuGhAphcgMNAQ1EAGGlYZRMOAAANi2WZGK6JkyAAAAAElFTkSuQmCC'}
html = '''
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
    <head>
        <meta charset="utf-8">
        <title>
            mlbplayista
        </title>
        <link rel="apple-touch-icon" sizes="76x76" href="data:image/png;base64,{icon}">
        <link rel="apple-touch-icon" sizes="120x120" href="data:image/png;base64,{icon}">
        <link rel="apple-touch-icon" sizes="152x152" href="data:image/png;base64,{icon}">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black">
        <meta name="viewport" content="initial-scale=1 maximum-scale=1 user-scalable=no">
        <style type="text/css">
        body {{
            background-color: #023a4e;
            -webkit-text-size-adjust: 100%;
            -webkit-user-select: none;
        }}
        #help {{
            display: none;
            color: white;
            font-family: "Avenir Next", helvetica, sans-serif;
            padding: 40px;
        }}
        .help-step {{
            border-radius: 8px;
            background-color: #047ea9;
            color: white;
            font-size: 20px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .icon {{
            background-image: url(data:image/png;base64,{icon});
            width: 76px;
            height: 76px;
            background-size: 76px 76px;
            border-radius: 15px;
            margin: 0 auto;
        }}
        .share-icon {{
            width: 32px;
            height: 27px;
            display: inline-block;
            background-image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAA2CAQAAADdG1eJAAAAyElEQVRYw+3YvQrCMBSG4a/SKxC8M6dOnQShk9BJKAi9OcFLKrwuaamDRRtMLHxnCBySch7yR6i07aCjy1seyEbgxhhd3vI5CKH8ddamJNAD0EoAEm1SQijfSCNAoklGoAcG6pAFgMQpCYELMFBN+QSQqBmA828BBx4cZ/kMIFFxZ5/2NLwA1sQu92VuQHZAubTB3vcVRfz4/5+BZfnnY5cPqjehAQYYYIABBhhQxn3+zYPFS2CAAQYYYIABBqx6kMT+htzADDwBk2GVUD9m13YAAAAASUVORK5CYII=);
            background-size: 32px 27px;
            vertical-align: -4px;
        }}
        .icon-title {{
            font-family: "Helvetica Neue", helvetica, sans-serif;
            text-align: center;
            font-size: 16px;
            margin-top: 10px;
            margin-bottom: 30px;
        }}
        @media only screen and (max-width: 767px) {{
            #help {{
                padding: 30px 0px 10px 0px;
            }}
            .help-step {{
                padding: 10px;
            }}
        }}
        </style>
    </head>
    <body>
        <div id="help">
            <div class="icon"></div>
            <div class="icon-title">
                mlbplayista
            </div>
            <div class="help-step">
                <strong>1.</strong> Tap the
                <div class="share-icon"></div>button in the toolbar
            </div>
            <div class="help-step">
                <strong>2.</strong> Select "Add to Home Screen"
            </div>
            <div class="help-step">
                <strong>3.</strong> Tap "Add"
            </div>
        </div><script type="text/javascript">
if (navigator.standalone) {{
          window.location = "pythonista3://MLBPlayista/mlbplayista.py?action=run&source=homescreen";
        }} else {{
          var helpDiv = document.getElementById("help");
          helpDiv.style.display = "block";
        }}
        </script>
    </body>
</html>
'''
html = html.format(**icons)


class ShortcutHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    html = None

    def do_GET(s):
        s.send_response(301)
        s.send_header('Location', 'data:text/html;base64,' + base64.b64encode(html))
        s.end_headers()


def run_server(html):
    ShortcutHandler.html = html
    server_address = ('', 0)
    httpd = BaseHTTPServer.HTTPServer(server_address, ShortcutHandler)
    sa = httpd.socket.getsockname()
    webbrowser.open('http://localhost:' + str(sa[1]))
    httpd.handle_request()

run_server(html)
