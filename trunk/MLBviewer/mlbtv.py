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
import simplejson
import re
import time
import datetime
import cookielib
import ClientForm
import os
import curses
import subprocess
import select

# Set this to True if you want to see all the html pages in the logfile
#DEBUG = True
#DEBUG = None

AUTHDIR = '.mlb'
COOKIEFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'cookie')
LOGFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'log')

TEAMCODES = {
    'ana': ('LAA', 'Los Angeles', 'Angels', 'of Anaheim'),
    'ari': ('ARZ', 'Arizona', 'Diamondbacks', ''),
    'atl': ('ATL', 'Atlanta', 'Braves', ''),
    'bal': ('BAL', 'Baltimore', 'Orioles',''),
    'bos': ('BOS', 'Boston', 'Red Sox', ''),
    'chc': ('CHC', 'Chicago', 'Cubs', ''),
    'cin': ('CIN', 'Cincinnati', 'Reds', ''),
    'cle': ('CLE', 'Cleveland', 'Indians', ''),
    'col': ('COL', 'Colorado', 'Rockies', ''),
    'cws': ('CWS', 'Chicago', 'White Sox', ''),
    'det': ('DET', 'Detroit', 'Tigers', ''),
    'fla': ('FLA', 'Florida', 'Marlins', ''),
    'hou': ('HOU', 'Houston', 'Astros', ''),
    'kc':  ('KC', 'Kansas City', 'Royals', ''),
    'la':  ('LA', 'Los Angeles', 'Dodgers', ''),
    'mil': ('MIL', 'Milwaukee', 'Brewers', ''),
    'min': ('MIN', 'Minnesota', 'Twins', ''),
    'nym': ('NYM', 'New York', 'Mets', ''),
    'nyy': ('NYY', 'New York', 'Yankees', ''),
    'oak': ('OAK', 'Oakland', 'Athletics', ''),
    'phi': ('PHI', 'Philadelphia', 'Phillies', ''),
    'pit': ('PIT', 'Pittsburgh', 'Pirates', ''),
    'sd':  ('SD', 'San Diego', 'Padres', ''),
    'sea': ('SEA', 'Seattle', 'Mariners', ''),
    'sf':  ('SF', 'San Francisco', 'Giants', ''),
    'stl': ('STL', 'St. Louis', 'Cardinals', ''),
    'tb':  ('TB', 'Tampa Bay', 'Rays', ''),
    'tex': ('TEX', 'Texas', 'Rangers', ''),
    'tor': ('TOR', 'Toronto', 'Blue Jays', ''),
    'was': ('WAS', 'Washington', 'Nationals', '')
    }

class MLBSchedule:

    def __init__(self,ymd_tuple=None):
        # Default to today
        if not ymd_tuple:
            now = datetime.datetime.now()
            dif = datetime.timedelta(1)
            # Now, we want the day to go until, say, 9 am the next
            # morning. This needs to be worked out, still...
            if now.hour < 9:
                now = now - dif
            ymd_tuple = (now.year, now.month, now.day)
        self.year = ymd_tuple[0]
        self.month = ymd_tuple[1]
        self.day = ymd_tuple[2]
        # First make the dates all strings, of the correct length
        def padstr(num):
            if len(str(num)) < 2: 
                return '0' + str(num)
            else:
                return str(num)
        self.url = "http://mlb.mlb.com/components/game/year_"\
            + padstr(self.year)\
            + "/month_" + padstr(self.month)\
            + "/day_" + padstr(self.day) + "/gamesbydate.jsp"
        self.data = []

    def __getSchedule(self):
        txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'}
        data = None
        req = urllib2.Request(self.url,data,txheaders)
        fp = urllib2.urlopen(req)
        out = fp.read()
        fp.close()
        return out

    def __scheduleToJson(self):
        # The schedule will be downloaded in JSP format, which is
        # almost the same as JSON, which python can easily import. We
        # just have to make a few cosmetic changes to make it into
        # correct JSON.

        # First, get rid of the white space (except spaces). This
        # isn't strictly necessary, but it makes the other
        # replacements easier, and makes it easier to check for
        # errors:
        mystr = re.sub(r'[\t\n]','',self.__getSchedule())
        # Take off everything up to and including the first open
        # parenthesis, and enclose the entire thing in brackets (just
        # the open bracket here. Close bracket is next.):
        mystr = '[' + '('.join(mystr.split('(')[1:])
        # Take off everything after and including the last close
        # parenthesis, and enclose the entire thing in
        # brackets. (Close bracket.):
        mystr = ')'.join(mystr.split(')')[:-1]) + ']'
        # Now turn single quotes into double quotes, which JSON
        # requires.
        mystr = mystr.replace('\'', '\"')
        # Now put double quotes around the keys, which JSP doesn't do.
        mystr = re.sub(r'([\{\[\}\]\,]+)([^ "]+)(:)', '\\1"\\2"\\3', mystr)

        return mystr

    def __jsonToPython(self):
        return simplejson.loads(self.__scheduleToJson())
        
    def getData(self):
        # This is the public method that puts together the private
        # steps above. Fills it up with data.
        self.data = self.__jsonToPython()

    def trimList(self):
        # This offers only the useful information for watching tv from
        # the getData step.
        if not self.data:
            raise Exception
        else:
            out = []
            for elem in self.data:
                # All contingent on it having a tv broadcast.
                if elem['mlbtv']:
                    dct = {}
                    time_string = elem['event_time'].strip()
                    ampm = time_string[-2:].lower()
                    hrs, mins = time_string[:-2].split(':')
                    hrs = int(hrs)
                    mins = int(mins)
                    if ampm == 'pm':
                         hrs += 12
                    dct['event_time'] = datetime.time(hrs,mins)
                    dct['status'] = elem['status']
                    dct['home'] = [team['code'] for team in elem['teams'] if
                                   team['isHome']][0]
                    dct['away'] = [team['code'] for team in elem['teams'] if not
                                   team['isHome']][0]
                    # A messy but effective way to join the team name
                    # together. Damn Angels making everything more
                    # difficult.
                    text = ' '.join(TEAMCODES[dct['away']][1:]).strip() +\
                        ' at ' +\
                        ' '.join(TEAMCODES[dct['home']][1:]).strip()
                    dct['text'] = text
                    dct['video'] = {}
                    for url in elem['mlbtv']['urls']:
                        dct['video'][url['speed']] = url['url']['id']
                    dct['audio'] = {}
                    for audio_feed in ('home_audio', 'away_audio','alt_home_audio', 'alt_away_audio'):
                        if elem[audio_feed]:
                            dct['audio'][audio_feed] = elem[audio_feed]['urls'][0]['url']['id']
                        else:
                            dct['audio'][audio_feed] = None
                    out.append((elem['gameid'], dct))
        return out

    def getListings(self, myspeed, blackout):
        self.getData()
        listings = self.trimList()

        return  [(elem[1]['text'],\
                      elem[1]['event_time'].strftime('%l:%M %p'),
                      elem[1]['video'][str(myspeed)],\
                      (elem[1]['status'], "LB")[
                                  (elem[1]['home'] in blackout or
                                   elem[1]['away'] in blackout)\
                                      and elem[1]['status'] in ('I','W','P')
                                  ])\
                     for elem in listings]


class GameStream:

    def __init__(self,game_id, email, passwd, debug, session_cookies=None):
        self.id = game_id
        self.email = email
        self.passwd = passwd
        self.debug = debug
        self.session_cookies = session_cookies
        self.error_str = "Uncaught error"
        self.log = open(LOGFILE,"w")
        self.log.write(str(datetime.datetime.now()) + '\n')

    def login(self):
        # BEGIN login()
        # meant to be called by workflow()
        self.session_cookies = cookielib.LWPCookieJar()
        if self.session_cookies != None:
           if os.path.isfile(COOKIEFILE):
              self.session_cookies.load(COOKIEFILE)
        else:
           self.error_str = "Couldn't open cookie jar"
           raise Exception,self.error_str
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.session_cookies))
        urllib2.install_opener(opener)

        # First visit the login page and get the session cookie
        login_url = 'https://secure.mlb.com/enterworkflow.do?flowId=registration.wizard&c_id=mlb'
        txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'}
        data = None
        req = urllib2.Request(login_url,data,txheaders)
        handle = urllib2.urlopen(req)
        self.log.write('Did we receive a cookie from the wizard?\n')
        for index, cookie in enumerate(self.session_cookies):
           print >> self.log, index, ' : ' , cookie
        self.session_cookies.save(COOKIEFILE)

        # now authenticate
        auth_url = 'https://secure.mlb.com/authenticate.do'
        txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13',
                     'Referer' : 'https://secure.mlb.com/enterworkflow.do?flowId=registration.wizard&c_id=mlb'}
        auth_values = {'uri' : '/account/login_register.jsp',
                       'registrationAction' : 'identify',
                       'emailAddress' : self.email,
                       'password' : self.passwd}
        auth_data = urllib.urlencode(auth_values)
        req = urllib2.Request(auth_url,auth_data,txheaders)
        handle = urllib2.urlopen(req)
        auth_page = handle.read()
        self.log.write('Did we receive a cookie from authenticate?\n')
        for index, cookie in enumerate(self.session_cookies):
           print >> self.log, index, ' : ' , cookie
        self.session_cookies.save(COOKIEFILE)

        pattern = re.compile(r'Welcome to your personal mlb.com account.')
        if not re.search(pattern,auth_page):
           self.error_str = "Login was unsuccessful."
           self.log.write(auth_page)
           raise Exception, self.error_str
        else:
           self.log.write('Logged in successfully!\n')
        if self.debug:
           self.log.write("DEBUG>>> writing login page")
           self.log.write(auth_page)
        # END login()

    def workflow(self):
        # This is the workhorse routine.
        # 1. Login
        # 2. Get the url from the workflow page
        # 3. Logout
        # 4. Return the raw workflow response page
        # The hope is that this sequence will always be the same and leave
        # it to url() to determine if an error occurs.  This way, hopefully, 
        # error or no, we'll always log out.
        if self.session_cookies is None:
            self.login()
        wf_url = "http://www.mlb.com/enterworkflow.do?" +\
            "flowId=media.media&keepWfParams=true&mediaId=" +\
            str(self.id) + "&catCode=mlb_lg&a=v"
        # Open the workflow url...
        # Referrer should look something like this but we'll need to pull
        # more info from listings for this:
        """ http://mlb.mlb.com/media/player/mp_tpl_3_1.jsp?mid=200804102514514&w_id=643428&w=reflector%3A19440&pid=mlb_lg&gid=2008/04/12/tormlb-texmlb-1&fid=mlb_lg400&cid=mlb&v=3 """
        txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'}
        wf_data = None
        req = urllib2.Request(wf_url,wf_data,txheaders)
        handle = urllib2.urlopen(req)
        url_data = handle.read()
        self.log.write('Did we receive a cookie from workflow?\n')
        for index, cookie in enumerate(self.session_cookies):
           print >> self.log, index, ' : ' , cookie
        self.session_cookies.save(COOKIEFILE)
        #handle.close()
        if self.debug:
           self.log.write("DEBUG>>> writing workflow page")
           self.log.write(url_data)
        self.logout()
        return url_data

    def logout(self): 
        """Logs out from the mlb.com session. Meant to prevent
        multiple login errors."""
        LOGOUT_URL="https://secure.mlb.com/enterworkflow.do?flowId=registration.logout&c_id=mlb"
        txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13',
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
           raise Exception, self.error_str
        else:
           self.log.write('Logged out successfully!\n')
        if self.debug:
           self.log.write("DEBUG>>> writing logout page")
           self.log.write(logout_info)
        # clear session cookies since they're no longer valid
        self.session_cookies.clear_session_cookies()
        # session is bogus now - force a new login each time
        self.session_cookies = None
        # END logout

    def url(self):
        # url_pattern
        game_info = self.workflow()
        pattern = re.compile(r'(url:.*\")(mms:\/\/[^ ]*)(".*)')
        try:
           game_url = re.search(pattern, game_info).groups()[1]
        except:
           pattern = re.compile(r'(url:.*\")(null(.*))')
           null_match = re.search(pattern,game_info)
           pattern = re.compile(r'Customers are not permitted concurrent use of a single subscription.')
           concur_match = re.search(pattern,game_info)
           pattern = re.compile(r'you are blacked out')
           blackout_match = re.search(pattern,game_info)
           if null_match:
               self.error_str = "Received a null: url, stream not available?"
           elif concur_match:
               self.error_str = "Receiving concurrent use error. :-("
           elif blackout_match:
               self.error_str = "You are blacked out from watching this game."
           else:
               self.error_str = "Unknown error in GameStream(): Check " +\
                   LOGFILE + " for details"
           self.log.write(self.error_str + '\n')
           if self.debug:
               self.log.write(game_info)
           self.log.write('Try the gameid script with gameid = ' + self.id +'\n')
           raise Exception, self.error_str 
        return game_url






