#!/usr/bin/env python

# mlbviewer is free software; you can redistribute it and/or modify
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, Version 2.
#
# mlbviewer is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# For a copy of the GNU General Public License, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# 02111-1307 USA

import urllib
import urllib2
import re
import time
import datetime
import cookielib

import os
import sys

from mlbtv import MLBLog

AUTHDIR = '.mlb'
COOKIEFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'cookie')
SESSIONKEY = os.path.join(os.environ['HOME'], AUTHDIR, 'sessionkey')
LOGFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'log')
#LOGFILE = '/tmp/mlblogin.log'
USERAGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'

class Error(Exception):
    pass

class MLBNoCookieFileError(Error):
    pass

class MLBSession:

    def __init__(self,user,passwd,debug=False):
        self.user = user
        self.passwd = passwd
        self.auth = True
        self.logged_in = None
        self.cookie_jar = None
        self.session_cookies = None
        self.cookies = {}
        self.debug = debug
        try:
            self.session_key = self.readSessionKey()
        except:
            self.session_key = None
        self.log = MLBLog(LOGFILE)

    def readSessionKey(self):
        sk = open(SESSIONKEY,"r")
        self.session_key = sk.read()
        sk.close()
        return session_key

    def writeSessionKey(self,session_key):
        sk = open(SESSIONKEY,"w")
        sk.write(session_key)
        sk.close()
        return session_key

    def extractCookies(self):
        for c in self.session_cookies:
            self.cookies[c.name] = c.value

    def readCookieFile(self):
        self.session_cookies = cookielib.LWPCookieJar()
        if self.session_cookies != None:
            if os.path.isfile(COOKIEFILE):
                self.session_cookies.load(COOKIEFILE,ignore_discard=True)
                self.extractCookies()
            else:
                raise MLBNoCookieFileError
        else:
            self.error_str = "Couldn't open cookie jar"
            raise Exception,self.error_str

    def login(self):
        try:
            self.readCookieFile()
        except MLBNoCookieFileError:
            pass
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.session_cookies))
        urllib2.install_opener(opener)

        # First visit the login page and get the session cookie
        callback = str(int(time.time() * 1000))
        login_url = 'http://mlb.mlb.com/account/quick_login_hdr.jsp?'\
            'successRedirect=http://mlb.mlb.com/shared/account/v2/login_success.jsp'\
            '%3Fcallback%3Dl' + callback + '&callback=l' + callback + \
            '&stylesheet=/style/account_management/myAccountMini.css&submitImage='\
            '/shared/components/gameday/v4/images/btn-login.gif&'\
            'errorRedirect=http://mlb.mlb.com/account/quick_login_hdr.jsp%3Ferror'\
            '%3Dtrue%26successRedirect%3Dhttp%253A%252F%252Fmlb.mlb.com%252Fshared'\
            '%252Faccount%252Fv2%252Flogin_success.jsp%25253Fcallback%25253Dl' +\
            callback + '%26callback%3Dl' + callback + '%26stylesheet%3D%252Fstyle'\
            '%252Faccount_management%252FmyAccountMini.css%26submitImage%3D%252F'\
            'shared%252Fcomponents%252Fgameday%252Fv4%252Fimages%252Fbtn-login.gif'\
            '%26errorRedirect%3Dhttp%3A//mlb.mlb.com/account/quick_login_hdr.jsp'\
            '%253Ferror%253Dtrue%2526successRedirect%253Dhttp%25253A%25252F%25252F'\
            'mlb.mlb.com%25252Fshared%25252Faccount%25252Fv2%25252Flogin_success.jsp'\
            '%2525253Fcallback%2525253Dl' + callback + '%2526callback%253Dl' +\
            callback + '%2526stylesheet%253D%25252Fstyle%25252Faccount_management'\
            '%25252FmyAccountMini.css%2526submitImage%253D%25252Fshared%25252F'\
            'components%25252Fgameday%25252Fv4%25252Fimages%25252Fbtn-login.gif'
        txheaders = {'User-agent' : USERAGENT}
        data = None
        req = urllib2.Request(login_url,data,txheaders)

        try:
            handle = urllib2.urlopen(req)
        except:
            self.error_str = 'Error occurred in HTTP request to login page'
            raise Exception, self.error_str
        try:
            self.extractCookies()
        except Exception,detail:
            raise Exception,detail
        if self.debug:
            self.log.write('Did we receive a cookie from the wizard?\n')
            for index, cookie in enumerate(self.session_cookies):
                print >> self.log, index, ' : ' , cookie
        self.session_cookies.save(COOKIEFILE,ignore_discard=True)

        rdata = handle.read()

        # now authenticate
        auth_values = {'emailAddress' : self.user,
                       'password' : self.passwd,
                       'submit.x' : 25,
                       'submit.y' : 7}
        g = re.search('name="successRedirect" value="(?P<successRedirect>[^"]+)"', rdata)
        auth_values['successRedirect'] = g.group('successRedirect')
        g = re.search('name="errorRedirect" value="(?P<errorRedirect>[^"]+)"', rdata)
        auth_values['errorRedirect'] = g.group('errorRedirect')
        auth_data = urllib.urlencode(auth_values)
        auth_url = 'https://secure.mlb.com/account/topNavLogin.jsp'
        req = urllib2.Request(auth_url,auth_data,txheaders)
        try:
            handle = urllib2.urlopen(req)
            self.session_cookies.save(COOKIEFILE,ignore_discard=True)
            self.extractCookies()
        except:
            self.error_str = 'Error occurred in HTTP request to auth page'
            raise Exception, self.error_str
        auth_page = handle.read()
        if self.debug:
            self.log.write('Did we receive a cookie from authenticate?\n')
            for index, cookie in enumerate(self.session_cookies):
                print >> self.log, index, ' : ' , cookie
        self.session_cookies.save(COOKIEFILE,ignore_discard=True)
        try:
           loggedin = re.search('login_success', handle.geturl()).groups()
           self.log.write('Logged in successfully!\n')
           self.logged_in = True
        except:
           self.error_str = 'Login was unsuccessful.'
           self.log.write(auth_page)
           os.remove(COOKIEFILE)
           raise MLBAuthError, self.error_str
        if self.debug:
           self.log.write("DEBUG>>> writing login page")
           self.log.write(auth_page)
        # END login()
  
    def getSessionData(self):
        # This is the workhorse routine.
        # 1. Login
        # 2. Get the url from the workflow page
        # 3. Logout
        # 4. Return the raw workflow response page
        # The hope is that this sequence will always be the same and leave
        # it to url() to determine if an error occurs.  This way, hopefully,
        # error or no, we'll always log out.
        if self.session_cookies is None:
            if self.logged_in is None:
                login_count = 0
                while not self.logged_in:
                    try:
                        self.login()
                    except:
                        if login_count < 3:
                            login_count += 1
                            time.sleep(1)
                        else:
                            raise
                            #raise Exception,self.error_str
                # clear any login unsuccessful messages from previous failures
                if login_count > 0:
                    self.error_str = "What happened here?\nPlease enable debug with the d key and try your request again."

        wf_url = "http://www.mlb.com/enterworkflow.do?" +\
            "flowId=media.media"

        # Open the workflow url...
        # Get the session key morsel
        referer_str = ''
        txheaders = {'User-agent' : USERAGENT,
                     'Referer'    : referer_str }
        req = urllib2.Request(url=wf_url,headers=txheaders,data=None)
        try:
            handle = urllib2.urlopen(req)
            self.extractCookies()
        except Exception,detail:
            self.error_str = 'Error occurred in HTTP request to workflow page:' + str(detail)
            raise Exception, self.error_str
        url_data = handle.read()
        if self.debug:
            if self.auth:
                self.log.write('Did we receive a cookie from workflow?\n')
                for index, cookie in enumerate(self.session_cookies):
                    print >> self.log, index, ' : ' , cookie
        if self.auth:
            self.session_cookies.save(COOKIEFILE,ignore_discard=True)
        if self.debug:
           self.log.write("DEBUG>>> writing workflow page")
           self.log.write(url_data)
        return url_data

    def logout(self):
        """Logs out from the mlb.com session. Meant to prevent
        multiple login errors."""
        LOGOUT_URL="https://secure.mlb.com/enterworkflow.do?flowId=registration.logout&c_id=mlb"
        txheaders = {'User-agent' : USERAGENT,
                     'Referer' : 'http://mlb.mlb.com/index.jsp'}
        data = None
        req = urllib2.Request(LOGOUT_URL,data,txheaders)
        handle = urllib2.urlopen(req)
        logout_info = handle.read()
        handle.close()
        pattern = re.compile(r'You are now logged out.')
        if not re.search(pattern,logout_info):
           self.error_str = "Logout was unsuccessful. Check " + LOGFILE
           self.log.write(logout_info)
           raise MLBAuthError, self.error_str
        else:
           self.log.write('Logged out successfully!\n')
           self.logged_in = None
        if self.debug:
           self.log.write("DEBUG>>> writing logout page")
           self.log.write(logout_info)
        # clear session cookies since they're no longer valid
        self.log.write('Clearing session cookies\n')
        self.session_cookies.clear_session_cookies()
        # session is bogus now - force a new login each time
        self.session_cookies = None
        # END logout

