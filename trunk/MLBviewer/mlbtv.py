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

import os
import subprocess
import select
from copy import deepcopy

# Set this to True if you want to see all the html pages in the logfile
#DEBUG = True
#DEBUG = None
#from __init__ import AUTHDIR

AUTHDIR = '.mlb'
COOKIEFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'cookie')
LOGFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'log')
USERAGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'

TEAMCODES = {
    'ana': ('LAA', 'Los Angeles', 'Angels', 'of Anaheim'),
    'al' : ('AL', 'American', 'League', ''),
    'ari': ('ARZ', 'Arizona', 'Diamondbacks', ''),
    'atl': ('ATL', 'Atlanta', 'Braves', ''),
    'bal': ('BAL', 'Baltimore', 'Orioles',''),
    'bc' : ('BC',  'Boston', 'College', ''),
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
    'nl' : ('NL', 'National', 'League', ''),
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
    'was': ('WAS', 'Washington', 'Nationals', ''),
    'wft': ('WFT', 'World', 'Futures', 'Team' ),
    'uft': ('UFT', 'USA', 'Futures', 'Team' ),
    'unk': ('UNK', 'Unknown', 'Teamcode'),
    }

def gameTimeConvert(datetime_tuple, time_shift=None):
    """Convert from east coast time to local time. This either uses
    the machine's localtime or if, it is given, an explicit timezone
    shift. 
    
    The timezone shift should be of the form '-0500', '+0330'. If no
    sign is given, it is assumed to be positive."""
    STANDARD = datetime.datetime(2008,11,2)
    if STANDARD <= datetime.datetime.now():
        dif = datetime.timedelta(0,18000)
    else:
        dif = datetime.timedelta(0,14400)
    utc_tuple = datetime_tuple + dif
    # We parse the explicit shift if there is one:
    if time_shift:
        pattern = re.compile(r'([+-]?)([0-9]{2})([0-9]{2})')
        parsed = re.match(pattern,time_shift)
        # So if we could parse it, we split it up.
        if parsed:
            mins = ( 60* int(parsed.groups()[1]) ) + int(parsed.groups()[2])
            secs = 60 * mins
            # here's the weird part: python does timezones in terms of
            # a difference, so we have to reverse the signs. In other
            # words, a '-' means that it's a positive difference.
            if parsed.groups()[0] in ('+', ''):
                secs *= -1
            myzone = secs
        # Otherwise we just go by the default machine time
        else:
            # If time.daylight returns 0 (false) it will choose the
            # first element; if it returns 1 (true) it will return the
            # second element.
            myzone = (time.timezone, time.altzone)[time.daylight]
    else:
        myzone = (time.timezone, time.altzone)[time.daylight]
    return utc_tuple - datetime.timedelta(0,myzone)

class Error(Exception):
    pass

class MLBUrlError(Error):
    pass

class MLBJsonError(Error):
    pass

class MLBSchedule:

    def __init__(self,ymd_tuple=None,time_shift=None):
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
        self.shift = time_shift
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
        txheaders = {'User-agent' : USERAGENT}
        data = None
        p404_pat = re.compile(r'no longer exists')
        req = urllib2.Request(self.url,data,txheaders)
        try:
            fp = urllib2.urlopen(req)
        except urllib2.HTTPError:
            raise MLBUrlError
        out = fp.read()
        if re.search(p404_pat,out):
            raise MLBUrlError
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
        # First, escape any double quotes.
        mystr = mystr.replace('\"', '\\\"')
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
        try:
            self.data = self.__jsonToPython()
        except ValueError,detail:
            raise MLBJsonError,detail

    def trimList(self,blackout=()):
        # This offers only the useful information for watching tv from
        # the getData step.
        if not self.data:
            raise MLBJsonError
        else:
            out = []
            for elem in self.data:
                # All contingent on it having a tv broadcast.
                if elem['gameid']:
                    dct = {}
                    # I'm parsing the time by hand because strptime
                    # doesn't work on windows and only works on
                    # python>=2.5. The time format is always going to
                    # be the same, so might as well just take care of
                    # it ourselves.
                    time_string = elem['event_time'].strip()
                    ampm = time_string[-2:].lower()
                    hrs, mins = time_string[:-2].split(':')
                    hrs = int(hrs) % 12
                    mins = int(mins)
                    if ampm == 'pm':
                        hrs += 12
                    # So that gives us the raw time, i.e., on the East
                    # Coast. Not knowing about DST or anything else.
                    raw_time = datetime.datetime(self.year, 
                                                 self.month, 
                                                 self.day, 
                                                 hrs,
                                                 mins)
                    # And now we convert that to the user's local, or
                    # chosen time zone.
                    dct['event_time'] = gameTimeConvert(raw_time, self.shift)
                    # The game status comes straight out of the dictionary.
                    dct['home'] = [team['code'] for team in elem['teams'] if
                                   team['isHome']][0]
                    dct['away'] = [team['code'] for team in elem['teams'] if not
                                   team['isHome']][0]
                    dct['status'] = (elem['status'],"LB")[\
                        (dct['home'] in blackout or
                         dct['away'] in blackout)\
                         and elem['status'] in ('I','W','P','IP')]
                    # A messy but effective way to join the team name
                    # together. Damn Angels making everything more
                    # difficult.
                    try:
                        text = ' '.join(TEAMCODES[dct['away']][1:]).strip()
                    except KeyError:
			t = (dct['away'],)
                        TEAMCODES[dct['away']] = TEAMCODES['unk'] + t
                        text =  ' '.join(TEAMCODES[dct['away']][1:]).strip()
                    text += ' at '
                    try:
                        text += ' '.join(TEAMCODES[dct['home']][1:]).strip()
                    except KeyError:
			t = (dct['home'],)
                        TEAMCODES[dct['home']] = TEAMCODES['unk'] + t
                        text =  ' '.join(TEAMCODES[dct['home']][1:]).strip()
                    dct['text'] = text
                    dct['teams'] = {}
                    dct['teams']['home'] = dct['home']
                    dct['teams']['away'] = dct['away']
                    dct['video'] = {}
                    try:
                        for url in elem['mlbtv']['urls']:
                            # handle 2007 season where 700K is top quality
                            # mask 700K to look like 800K
                            if str(self.year) == '2007' and url['speed'] == '700':
                                dct['video']['800'] = url['url']
                                
                            dct['video'][url['speed']] = url['url']
                            # national blackout
                            try:
                                if (url['blackout'] == 'national') and \
                                    elem['status'] in ('I','W','P','IP'):
                                    dct['status'] = 'NB'
                            except:
                                pass
                    except TypeError:
                        dct['video']['400'] = None
                        dct['video']['800'] = None
                    if dct['video'].has_key('400'):
                        if dct['video'].has_key('800') == False:
                            # don't let a black sheep ruin it for everyone
                            dct['video']['800'] = deepcopy(dct['video']['400'])
                    dct['audio'] = {}
                    for audio_feed in ('home_audio', 'away_audio','alt_home_audio', 'alt_away_audio'):
                        if elem[audio_feed]:
                            dct['audio'][audio_feed] = elem[audio_feed]['urls'][0]['url']
                        else:
                            dct['audio'][audio_feed] = None
                    # Top plays are indexed by the text since they are all 400k
                    dct['top_plays'] = {}
                    if elem['top_play_index']:
                        for url in elem['top_play_index']:
                             try:
                                 text = url['text']
                             except TypeError:
                                 # there's an error in 4/1/2008 listing
                                 continue
                             text = text.replace('\"','\'')
                             dct['top_plays']['game'] = dct['text']
                             dct['top_plays'][text] = url['urls'][0]['url']
                    try:
                        if elem['game_wrapup']:
                             text = elem['game_wrapup']['text']
                             text = text.replace('\"','\'')
                             dct['top_plays']['game'] = dct['text']
                             dct['top_plays'][text] = elem['game_wrapup']['urls'][0]['url']
                    except KeyError:
                        pass
                    try:
                        dct['condensed'] = {}
                        if elem['condensed_video']:
                             dct['status'] = 'CG'
                             dct['condensed'] = elem['condensed_video']['urls'][0]['url']
                    except KeyError:
                        pass
                    out.append((elem['gameid'], dct))
        return out

    def getCondensedVideo(self,gameid):
        out = {}
        condensed = self.trimList()

        for elem in condensed:
            if elem[0] == gameid:
                out = elem[1]['condensed']
        return out

    def getTopPlays(self,gameid):
        out = []
        plays = self.trimList()

        for elem in plays:
            if elem[0] == gameid:
                for play in elem[1]['top_plays'].keys():
                    if play != 'game':
                        dummy  = ''
                        title  = elem[1]['top_plays']['game']
                        text   = play
                        status = elem[1]['status']
                        recap_pat = re.compile(r'Recap')
                        if re.search(recap_pat,play):
                            out.insert(0,(title,text,elem[1]['top_plays'][text],status,elem[0]))   
                        else:
                            out.append((title,text,elem[1]['top_plays'][text],status,elem[0]))
        return out

    def getListings(self, myspeed, blackout, audiofollow):
        self.getData()
        listings = self.trimList(blackout)

        return  [(elem[1]['teams'],\
                      elem[1]['event_time'],
                      elem[1]['video'][str(myspeed)],\
                      (elem[1]['audio']['home_audio'],
                       elem[1]['audio']['away_audio'])[elem[1]['away'] \
                                                           in audiofollow],
                      elem[1]['status'],
                  elem[0])\
                     for elem in listings]


class GameStream:
    def __init__(self,stream, email, passwd, debug=None,\
                     auth=True, streamtype='video'):
        self.stream = stream
        self.error_str = "Uncaught error"
        try:
            self.id = self.stream['w_id']
            self.gameid = stream['gid']
        except:
            self.error_str = "No stream available for selected game."
        else:
            if self.stream['login'] == 'Y':
                self.auth = True
            else:
                self.auth = False
        self.email = email
        self.passwd = passwd
        self.session_cookies = None
        self.streamtype = streamtype
        self.log = open(LOGFILE,"a")
        self.log.write(str(datetime.datetime.now()) + '\n')
        # Determine whether we need to login from the jsp itself
        #self.auth = auth
        self.debug = debug
    
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
        txheaders = {'User-agent' : USERAGENT}
        data = None
        req = urllib2.Request(login_url,data,txheaders)
        try:
            handle = urllib2.urlopen(req)
        except:
            self.error_str = 'Error occurred in HTTP request to login page'
            raise Exception, self.error_str
        if self.debug:
            self.log.write('Did we receive a cookie from the wizard?\n')
            for index, cookie in enumerate(self.session_cookies):
                print >> self.log, index, ' : ' , cookie
        self.session_cookies.save(COOKIEFILE)

        # now authenticate
        auth_url = 'https://secure.mlb.com/authenticate.do'
        txheaders = {'User-agent' : USERAGENT,
                     'Referer' : 'https://secure.mlb.com/enterworkflow.do?flowId=registration.wizard&c_id=mlb'}
        auth_values = {'uri' : '/account/login_register.jsp',
                       'registrationAction' : 'identify',
                       'emailAddress' : self.email,
                       'password' : self.passwd}
        auth_data = urllib.urlencode(auth_values)
        req = urllib2.Request(auth_url,auth_data,txheaders)
        try:
            handle = urllib2.urlopen(req)
        except:
            self.error_str = 'Error occurred in HTTP request to auth page'
            raise Exception, self.error_str
        auth_page = handle.read()
        if self.debug:
            self.log.write('Did we receive a cookie from authenticate?\n')
            for index, cookie in enumerate(self.session_cookies):
                print >> self.log, index, ' : ' , cookie
        self.session_cookies.save(COOKIEFILE)

        pattern = re.compile(r'Welcome to your personal (MLB|mlb).com account.')
        if not re.search(pattern,auth_page):
           self.error_str = "Login was unsuccessful."
          # begin patch for maintenance operations
           maint_pat = re.compile(r'We are currently performing maintenance operations')
           if re.search(maint_pat,auth_page):
               self.error_str += "\n\nSite is performing maintenance operations"
           # end patch for maintenance operations
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
        self.log.write('Querying enterworkflow.do for { \'gameid\' : ' + self.gameid + ', \'streamid\' : ' + self.id + ', \'streamtype\' : ' + self.streamtype + ', login: ' + str(self.auth) + '}\n')
        if self.session_cookies is None:
            if self.auth:
                self.login()
        wf_url = "http://www.mlb.com/enterworkflow.do?" +\
            "flowId=media.media&keepWfParams=true&mediaId=" +\
            str(self.id)
        # The workflow urls for audio and video have slightly
        # different endings.
        if self.streamtype == 'audio':
            wf_url += "&catCode=mlb_ga&av=a"
        else:
            wf_url += "&catCode=mlb_lg&av=v"
        # Open the workflow url...
        # Referer should look something like this but we'll need to pull
        # more info from listings for this:
        """ http://mlb.mlb.com/media/player/mp_tpl_3_1.jsp?mid=200804102514514&w_id=643428&w=reflector%3A19440&pid=mlb_lg&gid=2008/04/12/tormlb-texmlb-1&fid=mlb_lg400&cid=mlb&v=3 """
        try:
            referer_str = "http://mlb.mlb.com/media/player/mp_tpl_3_1.jsp?mid=" +\
            self.stream['mid'] + '&w_id=' + self.stream['w_id'] + '&w=' + self.stream['w'] +\
            '&pid=' + self.stream['pid'] + '&fid=' + self.stream['fid'] +\
            '&cid=mlb&v=' + self.stream['v']
        except KeyError:
            referer_str = ''
        txheaders = {'User-agent' : USERAGENT,
                     'Referer'    : referer_str }
        #wf_data = None
        #req = urllib2.Request(wf_url,wf_data,txheaders)
        req = urllib2.Request(url=wf_url,headers=txheaders,data=None)
        try:
            handle = urllib2.urlopen(req)
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
            self.session_cookies.save(COOKIEFILE)
        #handle.close()
        if self.debug:
           self.log.write("DEBUG>>> writing workflow page")
           self.log.write(url_data)
        if self.auth:
            self.logout()
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
           raise Exception, self.error_str
        else:
           self.log.write('Logged out successfully!\n')
        if self.debug:
           self.log.write("DEBUG>>> writing logout page")
           self.log.write(logout_info)
        # clear session cookies since they're no longer valid
        self.log.write('Clearing session cookies\n')
        self.session_cookies.clear_session_cookies()
        # session is bogus now - force a new login each time
        self.session_cookies = None
        # END logout

    def url(self):
        # url_pattern
        game_info = self.workflow()
        # The urls for audio and video have different protocols
        if self.streamtype == 'audio':
            pattern = re.compile(r'(url:.*\")(http:\/\/[^ ]*)(".*)')
        else:
            # also match http: urls for 2007 season
            pattern = re.compile(r'(url:.*\")((mms:|http:)\/\/[^ ]*)(".*)')
        try:
           game_url = re.search(pattern, game_info).groups()[1]
        except Exception,detail:
           pattern = re.compile(r'(url:.*\")(null:(.*))')
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
           self.log.write('Try the gameid script with streamid = ' + self.id +'\n')
           self.log.close()
           self.error_str += ':' + str(detail)
           raise Exception, self.error_str 
        else:
           if self.streamtype == 'video':
               oldstyle = 'http:'
               match = re.match(oldstyle,game_url)
               if match:
                   mms_pat = re.compile(r'arl=(.*)')
                   game_url = re.search(mms_pat, game_url).groups()[0]
                   game_url = urllib.unquote(game_url)
        self.log.write('\nURL received:\n' + game_url + '\n\n')
        self.log.close()
        return game_url
