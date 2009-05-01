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
import sys

from mlbprocess import MLBprocess


try:
    from xml.dom.minidom import parse
    from suds.client import Client
    from suds import WebFault
except:
    print "The requirements for the 2009 season have changed."
    print "Please read the REQUIREMENTS-2009.txt file."
    sys.exit()

# Set this to True if you want to see all the html pages in the logfile
#DEBUG = True
#DEBUG = None
#from __init__ import AUTHDIR

DEFAULT_F_RECORD = 'rtmpdump -f \"LNX 10,0,22,87\" -o %f -r %s'

AUTHDIR = '.mlb'
COOKIEFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'cookie')
SESSIONKEY = os.path.join(os.environ['HOME'], AUTHDIR, 'sessionkey')
LOGFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'log')
USERAGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'
TESTXML = os.path.join(os.environ['HOME'], AUTHDIR, 'test_epg.xml')

SOAPCODES = {
    "1"    : "OK",
    "-1000": "Requested Media Not Found",
    "-1500": "Other Undocumented Error",
    "-1600": "Requested Media Not Archived Yet.",
    "-2000": "Authentication Error",
    "-2500": "Blackout Error",
    "-3000": "Identity Error",
    "-3500": "Sign-on Restriction Error",
    "-4000": "System Error",
}

# Status codes: Reverse mapping of status strings back to the status codes
# that were used in the json days.  Oh, those were the days. ;-)
STATUSCODES = {
    "In Progress"     : "I",
    "Final"           : "F",
    "Preview"         : "P",
    "Postponed"       : "PO",
    "Game Over"       : "GO",
    "Delayed"         : "D",
    "Pre-Game"        : "IP",
    "Suspended"       : "S",
    "Warm-up"         : "IP",
}



# We've never used the first field, so I'm going to expand its use for 
# audio and video follow functionality.  The first field will contain a tuple
# of call letters for the various media outlets that cover that team.
TEAMCODES = {
    'ana': ('108', 'Los Angeles Angels of Anaheim'),
    'al' : ( None, 'American League', ''),
    'ari': ('109', 'Arizona Diamondbacks', ''),
    'atl': ('144', 'Atlanta Braves', ''),
    'bal': ('110', 'Baltimore Orioles',''),
    'bos': ('111', 'Boston Red Sox', ''),
    'chc': ('112', 'Chicago Cubs', ''),
    'chn': ('112', 'Chicago Cubs', ''),
    'cin': ('113', 'Cincinnati Reds', ''),
    'cle': ('114', 'Cleveland Indians', ''),
    'col': ('115', 'Colorado Rockies', ''),
    'cws': ('145', 'Chicago White Sox', ''),
    'cha': ('145', 'Chicago White Sox', ''),
    'det': ('116', 'Detroit Tigers', ''),
    'fla': ('146', 'Florida Marlins', ''),
    'flo': ('146', 'Florida Marlins', ''),
    'hou': ('117', 'Houston Astros', ''),
    'kc':  ('118', 'Kansas City Royals', ''),
    'kca': ('118', 'Kansas City Royals', ''),
    'la':  ('119', 'Los Angeles Dodgers', ''),
    'lan': ('119', 'Los Angeles Dodgers', ''),
    'mil': ('158', 'Milwaukee Brewers', ''),
    'min': ('142', 'Minnesota Twins', ''),
    'nl' : ( None, 'National League', ''),
    'nym': ('121', 'New York Mets', ''),
    'nyn': ('121', 'New York Mets', ''),
    'nyy': ('147', 'New York Yankees', ''),
    'nya': ('147', 'New York Yankees', ''),
    'oak': ('133', 'Oakland Athletics', ''),
    'phi': ('143', 'Philadelphia Phillies', ''),
    'pit': ('134', 'Pittsburgh Pirates', ''),
    'sd':  ('135', 'San Diego Padres', ''),
    'sdn': ('135', 'San Diego Padres', ''),
    'sea': ('136', 'Seattle Mariners', ''),
    'sf':  ('137', 'San Francisco Giants', ''),
    'sfn': ('137', 'San Francisco Giants', ''),
    'stl': ('138', 'St. Louis Cardinals', ''),
    'sln': ('138', 'St. Louis Cardinals', ''),
    'tb':  ('139', 'Tampa Bay Rays', ''),
    'tba': ('139', 'Tampa Bay Rays', ''),
    'tex': ('140', 'Texas Rangers', ''),
    'tor': ('141', 'Toronto Blue Jays', ''),
    'was': ('120', 'Washington Nationals', ''),
    'wft': ('WFT', 'World', 'Futures', 'Team' ),
    'uft': ('UFT', 'USA', 'Futures', 'Team' ),
    'cif': ('CIF', 'Cincinnati Futures Team'),
    'unk': ( None, 'Unknown', 'Teamcode'),
    'tbd': ( None, 'TBD'),
    't235': ('T235', 'Memphis Redbirds'),
    't249': ('T249', 'Carolina Mudcats'),
    't784': ('T784', 'WBC Canada'),
    't805': ('T805', 'WBC Dominican Republic'),
    't841': ('T841', 'WBC Italy'),
    't878': ('T878', 'WBC Netherlands'),
    't890': ('T890', 'WBC Panama'),
    't897': ('T897', 'WBC Puerto Rico'),
    't944': ('T944', 'WBC Venezuela'),
    't940': ('T940', 'WBC United States'),
    't918': ('T918', 'WBC South Africa'),
    't867': ('T867', 'WBC Mexico'),
    't760': ('T760', 'WBC Australia'),
    't790': ('T790', 'WBC China'),
    't843': ('T843', 'WBC Japan'),
    't791': ('T791', 'WBC Taipei'),
    't798': ('T798', 'WBC Cuba'),
    't1171': ('T1171', 'WBC Korea'),
    't1193': ('T1193', 'WBC Venezuela'),
    't2290': ('T2290', 'University of Michigan'),
    't2330': ('T3330', 'Georgetown University'),
    't2330': ('T3330', 'Georgetown University'),
    't2291': ('T2291', 'St. Louis University'),
    't2292': ('T2292', 'University of Southern Florida'),
    'uga' : ('UGA',  'University of Georgia'),
    'mcc' : ('MCC', 'Manatee Community College'),
    'fso' : ('FSO', 'Florida Southern College'),
    'fsu' : ('FSU', 'Florida State University'),
    'mia' : ('MIA', 'University of Miami'),
    'neu' : ('NEU',  'Northeastern University'),
    'bc' : ('BC',  'Boston', 'College', ''),
    }


def gameTimeConvert(datetime_tuple, time_shift=None):
    """Convert from east coast time to local time. This either uses
    the machine's localtime or if, it is given, an explicit timezone
    shift. 
    
    The timezone shift should be of the form '-0500', '+0330'. If no
    sign is given, it is assumed to be positive."""
    DAYLIGHT = {
        '2007': (datetime.datetime(2007,3,11),datetime.datetime(2007,11,4)),
        '2008': (datetime.datetime(2008,3,9),datetime.datetime(2008,11,2)),
        '2009': (datetime.datetime(2009,3,8),datetime.datetime(2009,11,1)),
        '2010': (datetime.datetime(2009,3,14),datetime.datetime(2009,11,7)),
               }
    now = datetime.datetime.now()            
    if (now >= DAYLIGHT[str(now.year)][0]) \
       and (now < DAYLIGHT[str(now.year)][1]):
        dif = datetime.timedelta(0,14400)
    else:
        dif = datetime.timedelta(0,18000)

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

class MLBAuthError(Error):
    pass

class MLBLog:

    def __init__(self,logfile):
        self.logfile = logfile
        self.log = None

    def open(self):
        self.log = open(self.logfile,"a")
    
    def close(self):
        if self.log is not None:
            self.log.close()
        self.log = None

    def flush(self):
        pass
    
    def write(self,logmsg):
        if self.log is None:
            self.open()
        self.log.write(logmsg)
        self.close()

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
        self.epg = "http://gdx.mlb.com/components/game/mlb/year_"\
            + padstr(self.year)\
            + "/month_" + padstr(self.month)\
            + "/day_" + padstr(self.day) + "/grid.xml"
        # For BETA testing, use my own xml
        #self.epg = "http://eds.org/~straycat/wbc_epg.xml"
        self.xmltime = datetime.datetime(2009, 3, 30)
        mytime = datetime.datetime(self.year, self.month, self.day)
        if mytime >= self.xmltime:
            self.use_xml = True
        else:
            self.use_xml = False
        self.log = MLBLog(LOGFILE)
        self.data = []

    def __getSchedule(self):
        txheaders = {'User-agent' : USERAGENT}
        data = None
        p404_pat = re.compile(r'no longer exists')
        p404_pat_epg = re.compile(r'404 Not Found')
        # 2009 marks the end of the jsp page, so use epg page instead
        if self.use_xml:
            req = urllib2.Request(self.epg,data,txheaders)
        else:
            req = urllib2.Request(self.url,data,txheaders)
        try:
            fp = urllib2.urlopen(req)
            if self.use_xml:
                return fp
        except urllib2.HTTPError:
            raise MLBUrlError
        out = fp.read()
        if re.search(p404_pat_epg,out):
            raise MLBUrlError
        if re.search(p404_pat,out):
            raise MLBUrlError
        fp.close()
        return out

    def __scheduleFromXml(self):
        out = []
        gameinfo = dict()
        fp = parse(self.__getSchedule())
        for node in fp.getElementsByTagName('game'):
            id = node.getAttribute('id')
            gameinfo[id] = dict()
            for attr in node.attributes.keys():
                gameinfo[id][attr] = node.getAttribute(attr)
            media = node.getElementsByTagName('game_media')[0]
            try:
                media_detail = media.getElementsByTagName('media')[0]
                gameinfo[id]['state'] = media_detail.getAttribute('media_state')
            except:
                #raise
                gameinfo[id]['media_state'] = 'media_dead'
            try:
                gameinfo[id]['time']
            except:
                gameinfo[id]['time'] = gameinfo[id]['event_time'].split()[0]
                gameinfo[id]['ampm'] = gameinfo[id]['event_time'].split()[1]
            home = node.getAttribute('home_team_id')
            away = node.getAttribute('away_team_id')
            gameinfo[id]['content'] = self.parse_media_grid(node,away,home)
            #raise Exception,repr(gameinfo[id]['content'])
            out.append(gameinfo[id])
        #raise Exception,repr(out)
        return out

    def parse_media_grid(self,xp,away,home):
        content = {}
        content['audio'] = []
        content['video'] = {}
        content['video']['400'] = []
        content['video']['800'] = []
        content['video']['swarm'] = []
        content['condensed'] = []
        event_id = str(xp.getAttribute('calendar_event_id'))
        for media in xp.getElementsByTagName('media'):
           tmp = {}
           for attr in media.attributes.keys():
               tmp[attr] = str(media.getAttribute(attr))
           out = []
           if tmp['type'] in ('home_audio','away_audio'):
               if tmp['playback_scenario'] == 'MLB_FMS_AUDIO_32K_STREAM':
                   if tmp['type'] == 'away_audio':
                       coverage = away
                   elif tmp['type'] == 'home_audio':
                       coverage = home
                   out = (tmp['display'], coverage, tmp['id'], event_id)
                   #print 'Found audio: ' + repr(out)
                   content['audio'].append(out)
           elif tmp['type'] in ('mlbtv_national', 'mlbtv_home', 'mlbtv_away'):
               if tmp['playback_scenario'] in \
                     ('MLB_FLASH_600K_STREAM', 'MLB_FLASH_800K_STREAM',
                      'MLB_FLASH_SWARMCLOUD'):
                   if tmp['blackout'] == 'MLB_NATIONAL_BLACKOUT':
                       content['blackout'] = tmp['blackout']
                   else:
                       content['blackout'] = None
                   if tmp['type'] == 'mlbtv_national':
                       coverage = 0
                   elif tmp['type'] == 'mlbtv_away':
                       coverage = away
                   else:
                       coverage = home
                   out = (tmp['display'], coverage, tmp['id'], event_id)
                   #print 'Found video: ' + repr(out)
                   if tmp['playback_scenario'] == 'MLB_FLASH_SWARMCLOUD':
                       content['video']['swarm'].append(out)
                   elif tmp['playback_scenario'] == 'MLB_FLASH_800K_STREAM':
                       content['video']['800'].append(out)
                   else:
                       content['video']['400'].append(out)
           elif tmp['type'] == 'condensed_game':
               out = ('CG',0,tmp['id'], event_id)
               #print 'Found condensed: ' + repr(out)
               content['condensed'].append(out)
        return content
    
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

    def __xmlToPython(self):
        return self.__scheduleFromXml()
        
    def getData(self):
        # This is the public method that puts together the private
        # steps above. Fills it up with data.
        try:
            if self.use_xml:
                self.data = self.__xmlToPython()
            else:
                self.data = self.__jsonToPython()
        except ValueError,detail:
            raise MLBJsonError,detail

    def trimXmlList(self,blackout=()):
        # This is the XML version of trimList
        # easier to write a new method than adapt the old one
        if not self.data:
            raise MLBJsonError
        out = []
        for game in self.data:
            dct = {}
            dct['home'] = game['home_file_code']
            dct['away'] = game['away_file_code']
            dct['teams'] = {}
            dct['teams']['home'] = dct['home']
            dct['teams']['away'] = dct['away']
            dct['event_id'] = game['calendar_event_id']
            if dct['event_id'] == "":
                 dct['event_id'] = None
            dct['ind']   = game['ind']
            try:
                dct['status'] = STATUSCODES[game['status']]
            except:
                dct['status'] = game['status'] 
            if game['status'] in ('In Progress','Preview','Delayed','Warm-up'):
                if game['content']['blackout'] == 'MLB_NATIONAL_BLACKOUT':
                    dct['status'] = 'NB'
            dct['gameid'] = game['id']
            # I'm parsing the time by hand because strptime
            # doesn't work on windows and only works on
            # python>=2.5. The time format is always going to
            # be the same, so might as well just take care of
            # it ourselves.
            time_string = game['time'].strip()
            ampm = game['ampm'].lower()
            hrs, mins = time_string.split(':')
            hrs = int(hrs) % 12
            try:
                mins = int(mins)
            except:
                raise Exception,repr(mins)
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
            if not TEAMCODES.has_key(dct['away']):
                TEAMCODES[dct['away']] = TEAMCODES['unk'] + t
            if not TEAMCODES.has_key(dct['home']):
                TEAMCODES[dct['home']] = TEAMCODES['unk'] + t
            #raise Exception,repr(game)
            dct['video'] = {}
            dct['video']['400'] = []
            dct['video']['800'] = []
            dct['video']['swarm'] = []
            dct['condensed'] = []
            for key in ('400', '800', 'swarm'):
                try:
                    dct['video'][key] = game['content']['video'][key]
                except KeyError:
                    dct['video'][key] = None
            dct['audio'] = []
            try:
                dct['audio'] = game['content']['audio']
            except KeyError:
                dct['audio'] = None
            try:
                dct['condensed'] = game['content']['condensed']
            except KeyError:
                dct['condensed'] = None
            if dct['condensed']:
                dct['status'] = 'CG'
            dct['media_state'] = game['media_state']
            #dct['text'] = text
            out.append((dct['gameid'], dct))
        #raise Exception,repr(out)
        return out

 

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
                    if dct['home'] is None:
                        dct['home'] = 'tbd'
                    dct['away'] = [team['code'] for team in elem['teams'] if not
                                   team['isHome']][0]
                    if dct['away'] is None:
                        dct['away'] = 'tbd'
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

                            # Wtf!? Why is WBC 600?  Why not 400 or 800?
                            if str(self.year) == '2009' and url['speed'] == '600':
                                dct['video']['400'] = url['url']
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
        listtime = datetime.datetime(self.year, self.month, self.day)
        if listtime >= self.xmltime:
            self.use_xml = True
        else:
            self.use_xml = False

        if self.use_xml:
            return self.getXmlCondensedVideo(gameid)
        else:
            return self.getJsonCondensedVideo(gameid)

    def getJsonCondensedVideo(self,gameid):
        out = {}

        condensed = self.trimList()

        for elem in condensed:
            if elem[0] == gameid:
                out = elem[1]['condensed']
        return out

    def getXmlCondensedVideo(self,gameid):
        out = ''
        condensed = self.trimXmlList()
        for elem in condensed:
            #raise Exception,repr(condensed)
            if elem[0] == gameid:
                content_id = elem[1]['condensed'][0][2]
        url = 'http://mlb.mlb.com/gen/multimedia/detail/' 
        url += content_id[4] + '/' + content_id[5] + '/' + content_id[6]
        url += '/' + content_id + '.xml'
        try:
            req = urllib2.Request(url)
            rsp = urllib2.urlopen(req)
        except Exception,detail:
            self.error_str = 'Error while locating condensed game:'
            self.error_str = '\n\n' + str(detail)
            raise
        try:
            media = parse(rsp)
        except Exception,detail:
            self.error_str = 'Error parsing condensed game location'
            self.error_str += '\n\n' + str(detail)
            raise
        out = str(media.getElementsByTagName('url')[0].childNodes[0].data)
        return out
            
        

    def getJsonTopPlays(self,gameid):
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
        #raise Exception,out
        return out

    def getXmlTopPlays(self,gameid):
        gid = gameid
        gid = gid.replace('/','_')
        gid = gid.replace('-','_')
        #url = self.epg.replace('epg.xml','gid_' + gid + '/media/highlights.xml')
        url = self.epg.replace('grid.xml','gid_' + gid + '/media/highlights.xml')
        #raise Exception,url
        out = []
        try:
            req = urllib2.Request(url)
            rsp = urllib2.urlopen(req)
        except:
            return out
            self.error_str = "Could not find highlights.xml for " + gameid
            raise Exception,self.error_str
        try:
            xp  = parse(rsp)
        except:
            return out
            self.error_str = "Could not parse highlights.xml for " + gameid

        away = gid.split('_')[3].replace('mlb','')
        home = gid.split('_')[4].replace('mlb','')
        title  = ' '.join(TEAMCODES[away][1:]).strip() + ' at '
        title += ' '.join(TEAMCODES[home][1:]).strip()

        for highlight in xp.getElementsByTagName('media'):
            selected = 0
            type = highlight.getAttribute('type')
            id   = highlight.getAttribute('id')
            v    = highlight.getAttribute('v')
            headline = highlight.getElementsByTagName('headline')[0].childNodes[0].data
            for urls in highlight.getElementsByTagName('url'):
                scenario = urls.getAttribute('playback_scenario')
                state    = urls.getAttribute('state')
                speed_pat = re.compile(r'MLB_FLASH_([1-9][0-9]*)K')
                speed = int(re.search(speed_pat,scenario).groups()[0])
                if speed > selected:
                    selected = speed
                    url = urls.childNodes[0].data
            out.append(( title, headline, url, state, gameid)) 
        #raise Exception,out
        return out

    def getTopPlays(self,gameid):
        listtime = datetime.datetime(self.year, self.month, self.day)
        if listtime >= self.xmltime:
            self.use_xml = True
        else:
            self.use_xml = False

        if self.use_xml:
            return self.getXmlTopPlays(gameid)
        else:
            return self.getJsonTopPlays(gameid)
        

    def getListings(self, myspeed, blackout, audiofollow):
        listtime = datetime.datetime(self.year, self.month, self.day)
        if listtime >= self.xmltime:
            self.use_xml = True
        else:
            self.use_xml = False

        if self.use_xml:
            return self.getXmlListings(myspeed, blackout, audiofollow)
        else:
            return self.getJsonListings(myspeed, blackout, audiofollow)

    def getXmlListings(self, myspeed, blackout, audiofollow):
        self.getData()
        listings = self.trimXmlList(blackout)

        return [(elem[1]['teams'],\
                     elem[1]['event_time'],
                     elem[1]['video'][str(myspeed)],
                     elem[1]['audio'],
                     elem[1]['status'],
                     elem[0],
                     elem[1]['media_state'])\
                         for elem in listings]

    def getJsonListings(self, myspeed, blackout, audiofollow):
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
    def __init__(self,stream, email, passwd, debug=None,
                 auth=True, streamtype='video',use_soap=False,speed=800,
                 coverage=None,use_nexdef=False,max_bps=800000,start_time=0):
        self.use_nexdef = use_nexdef
        self.rec_process = None
        self.start_time = start_time
        self.max_bps = max_bps
        self.stream = stream
        self.streamtype = streamtype
        self.speed = speed
        self.log = MLBLog(LOGFILE)
        self.error_str = "Uncaught error"
        self.use_soap = use_soap
        try:
            if self.use_soap:
                ( self.call_letters, 
                  self.team_id, 
                  self.content_id, 
                  self.event_id ) = self.stream
            else:
                self.id = self.stream['w_id']
                self.gameid = stream['gid']
        except:
            self.error_str = "No stream available for selected game."
        else:
            if use_soap:
                self.auth = True
            elif self.stream['login'] == 'Y':
                self.auth = True
            else:
                self.auth = False
        self.email = email
        self.passwd = passwd
        self.session_cookies = None
        self.streamtype = streamtype
        self.coverage = coverage
        self.log.write(str(datetime.datetime.now()) + '\n')
        try:
            self.session_key = self.read_session_key()
        except:
            self.session_key = None
        # Determine whether we need to login from the jsp itself
        #self.auth = auth
        self.debug = debug
        if self.streamtype == 'audio':
            self.scenario = "MLB_FMS_AUDIO_32K_STREAM"
            self.subject  = "MLBCOM_GAMEDAY_AUDIO"
        else:
            if self.use_nexdef:
                self.scenario = 'MLB_FLASH_SWARMCLOUD'
            elif str(self.speed) == '400':
                self.scenario = "MLB_FLASH_600K_STREAM"
            else:
                self.scenario = "MLB_FLASH_800K_STREAM"
            self.subject  = "LIVE_EVENT_COVERAGE"
        self.cookies = {}
        self.content_id = None
        self.play_path = None
        self.tc_url = None
        self.app = None
        self.sub_path = None
        self.logged_in = None
        self.current_encoding = None

    def read_session_key(self):
        sk = open(SESSIONKEY,"r")
        self.session_key = sk.read()
        sk.close()
        return session_key

    def write_session_key(self,session_key):
        sk = open(SESSIONKEY,"w")
        sk.write(session_key)
        sk.close()
        return session_key

    def extract_cookies(self,response):
        ns_headers = response.headers.getheaders("Set-Cookie")
        attrs_set = cookielib.parse_ns_headers(ns_headers)
        cookie_tuples = cookielib.CookieJar()._normalized_cookie_tuples(attrs_set)
        for tup in cookie_tuples:
            name, value, standard, rest = tup
            self.cookies[name] = value
    
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
        try:
            self.extract_cookies(handle)
        except Exception,detail:
            raise Exception,detail
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
            self.extract_cookies(handle)
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
           raise MLBAuthError, self.error_str
        else:
           self.log.write('Logged in successfully!\n')
           self.logged_in = True
        if self.debug:
           self.log.write("DEBUG>>> writing login page")
           self.log.write(auth_page)
        # END login()
 
    def workflow(self,use_soap=False):
        # This is the workhorse routine.
        # 1. Login
        # 2. Get the url from the workflow page
        # 3. Logout
        # 4. Return the raw workflow response page
        # The hope is that this sequence will always be the same and leave
        # it to url() to determine if an error occurs.  This way, hopefully, 
        # error or no, we'll always log out.
        if not self.use_soap:
            self.log.write('Querying enterworkflow.do for { \'gameid\' : ' + self.gameid + ', \'streamid\' : ' + self.id + ', \'streamtype\' : ' + self.streamtype + ', login: ' + str(self.auth) + '}\n')
        if self.session_cookies is None:
            if self.auth and self.logged_in is None:
                self.login()
        
        wf_url = "http://www.mlb.com/enterworkflow.do?" +\
            "flowId=media.media"
        if not self.use_soap:
            wf_url += "&keepWfParams=true&mediaId=" + str(self.id)

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
        except (KeyError,TypeError):
            referer_str = ''
        txheaders = {'User-agent' : USERAGENT,
                     'Referer'    : referer_str }
        #wf_data = None
        #req = urllib2.Request(wf_url,wf_data,txheaders)
        req = urllib2.Request(url=wf_url,headers=txheaders,data=None)
        try:
            handle = urllib2.urlopen(req)
            self.extract_cookies(handle)
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
        #if self.auth:
        #    self.logout()
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

    def parse_innings_xml(self):
        gameid = self.event_id.split('-')[1]
        url = 'http://mlb.mlb.com/mlb/mmls2009/' + gameid + '.xml'
        req = urllib2.Request(url)
        rsp = urllib2.urlopen(req)
        try:
            iptr = parse(rsp)
        except:
            self.error_str = "Could not parse the innings xml."
            raise Exception,self.error_str
        out = []
        for inning in iptr.getElementsByTagName('inningTimes'):
            number = inning.getAttribute('inning_number')
            is_top = inning.getAttribute('top')
            for inning_time in inning.getElementsByTagName('inningTime'):
                type = inning_time.getAttribute('type')
                if type == 'SCAST':
                    time = inning_time.getAttribute('start')
                    out.append((number, is_top, time))
        return out

    def parse_soap_content(self,reply):
        # iterate over all the media items
        content_list = []
        for stream in reply[0][0]['user-verified-content']:
            # for each media item, if it matches the streamtype, build a dictionary of domain-attributes
            # for selection of coverage
            dict = {}
            if stream['type'] == self.streamtype:
                for i in range(len(stream['domain-specific-attributes']['domain-attribute'])):
                    domain_attr = stream['domain-specific-attributes']['domain-attribute'][i]
                    dict[domain_attr._name] = domain_attr
                try:
                    cov_pat = re.compile(r'([0-9][0-9]*)')
                    coverage = re.search(cov_pat, str(dict['coverage_association'])).groups()[0]
                except:
                    coverage = None
                call_letters = str(dict['call_letters'])
                try:
                    letters_pat = re.compile(r'"(.*)"')
                    call_letters = re.search(letters_pat, call_letters).groups()[0]
                except:
                    raise Exception,repr(call_letters)
                for media in stream['user-verified-media-item']:
                    #raise Exception,repr(media['media-item']['state'])
                    state = media['media-item']['state']
                    scenario = media['media-item']['playback-scenario']
                    if scenario == self.scenario and\
                                state in ( 'MEDIA_ARCHIVE', 'MEDIA_ON', 'MEDIA_DONE', 'MEDIA_OFF' ):
                        content_list.append( ( call_letters, coverage, stream['content-id'] , self.event_id ) )
        return content_list


    def soapurl(self):
        # return of workflow is useless for here, but it still calls all the 
        # necessary steps to login and get cookies
        if self.stream is None:
             self.error_str = "No event-id to locate media streams."
             raise
        # (re-)initialize some variables to make retries possible
        self.content_id = None
        self.play_path  = None
        self.sub_path   = None
        self.app        = None
 
        # call the workhorse
        self.workflow()

        # now some soapy fun
        wsdl_file = os.path.join(os.environ['HOME'], AUTHDIR, 'MediaService.wsdl')
        soap_url = 'file://' + str(wsdl_file)
        client = Client(soap_url)
        soapd = {'event-id':str(self.event_id), 'subject':self.subject}
        reply = client.service.find(**soapd)
        # if the reply is unsuccessful, log it and raise an exception
        if reply['status-code'] != "1":
            self.log.write("DEBUG (SOAPCODES!=1)>> writing unsuccessful soap response event_id = " + str(self.event_id) + "\n")
            self.log.write(repr(reply) + '\n')
            self.error_str = SOAPCODES[reply['status-code']]
            raise Exception,self.error_str
        # moving all the soap reply parsing to a routine that returns a list of valid streams
        # based on streamtype
        content_list = self.parse_soap_content(reply)
        # now iterate over the content_list with the following rules:
        # 1. if coverage association is zero, use it (likely a national broadcast)
        # 2. if preferred coverage is available use it
        # 3. if coverage association is non-zero and preferred not available, then what?
        for content in content_list:
            ( call_letters, coverage, content_id , event_id ) = content
            if coverage == '0':
                self.content_id = content_id
                self.call_letters = call_letters
            elif coverage == self.coverage:
                self.content_id = content_id
                self.call_letters = call_letters
        # if we preferred coverage and national coverage not available,
        # select any coverage available
        if self.content_id is None:
            try:
                ( call_letters, coverage, content_id, event_id ) = content_list[0]
                self.content_id = content_id
                self.call_letters = call_letters
            except:
                self.content_id = None
                self.call_letters = None
        if self.content_id is None:
            self.error_str = "Requested stream is not available."
            self.error_str += "\n\nRequested coverage association: " + str(self.coverage)
            self.error_str += "\n\nAvailable content list = \n" + repr(content_list)
            raise Exception,self.error_str
        if self.debug:
            self.log.write("DEBUG>> writing soap response\n")
            self.log.write(repr(reply) + '\n')
        if self.content_id is None:
            self.error_str = "Requested stream is not yet available."
            raise Exception,self.error_str
        if self.debug:
            self.log.write("DEBUG>> soap event-id:" + str(self.stream) + '\n')
            self.log.write("DEBUG>> soap content-id:" + str(self.content_id) + '\n')
        ip = client.factory.create('ns0:IdentityPoint')
        ip.__setitem__('identity-point-id', self.cookies['ipid'])
        ip.__setitem__('fingerprint', urllib.unquote(self.cookies['fprt']))
        try:
            self.session_key = urllib.unquote(self.cookies['ftmu'])
            self.write_session_key(self.session_key)
        except:
            self.session_key = None

        soapd = {'event-id':self.event_id, 
                 'subject':self.subject,
                 'playback-scenario': self.scenario,
                 'content-id':self.content_id, 
                 'fingerprint-identity-point':ip , 
                 'session-key':self.session_key}
        try:
            reply = client.service.find(**soapd)
        except WebFault,e:
            self.error_str = str(e)
            raise
        if self.debug:
            self.log.write("DEBUG>> writing soap response\n")
            self.log.write(repr(reply))
        if reply['status-code'] != "1":
            self.log.write("DEBUG (SOAPCODES!=1)>> writing soap response\n")
            self.log.write(repr(reply))
            self.error_str = SOAPCODES[reply['status-code']]
            raise Exception,self.error_str
        try:
            self.session_key = reply['session-key']
            self.write_session_key(self.session_key)
        except:
            self.session_key = None
        game_url = reply[0][0]['user-verified-content'][0]['user-verified-media-item'][0]['url']
        if self.use_nexdef:
            #raise Exception,self.nexdef_url(game_url)
            return self.nexdef_url(game_url)
        else:
            return self.flash_url(game_url)


    def nexdef_url(self,game_url):
        self.nexdef_media_url = None
        nexdef_base = 'http://local.swarmcast.net:8001/protected/content/adaptive-live/'
        nexdef_use  = 'http://local.swarmcast.net:8001/protected/content/adaptive-live/base64:'
        # build the first url for stream descriptions

        """ BEGIN PAIN IN THE ASS CODE """
        url = nexdef_base + 'describe' + '/base64:' + game_url + '&refetch=true'
        req = urllib2.Request(url)
        rsp = urllib2.urlopen(req)
        # parse the stream descriptions for time of head of stream
        try:
            xp = parse(rsp)
        except:
            try:
                req = urllib2.Request(url)
                rsp = urllib2.urlopen(req)
                text = rsp.read()
            except:
                self.error_str = "Could not retry request to NexDef for stream list."
                self.error_str += str(text)
                raise Exception,self.error_str
            self.error_str = "Could not parse NexDef stream list.  Try alternate coverage."
            self.error_str += "\n\n" + str(text)
            raise Exception,self.error_str
        for time in xp.getElementsByTagName('streamHead'):
            timestamp = time.getAttribute('timeStamp')
        try:
            (hrs, min, sec) = timestamp.split(':')
            milliseconds = 1000 * ( int(hrs) * 3600 + int(min) * 60 + int(sec) )
            # nexdef plugin appears to be off by an hour
            milliseconds += 3600*1000
        except:
            self.start_time = None
        # return the media url with the correct timestamp
        self.nexdef_media_url = nexdef_use + game_url + '&max_bps=' + str(self.max_bps) 
        if self.start_time is not None:
            self.nexdef_media_url += '&start_time=' + str(milliseconds) + '&v=0'
        else:
            self.nexdef_media_url += '&v=0'
        """ END PAIN IN THE ASS CODE """
        
        return self.nexdef_media_url

    def control(self,action='ping',encoding=None):
        if self.use_nexdef:
            #self.log.write('DEBUG>> calling nexdef_control \n')
            self.nexdef_control(action,encoding)
        else:
            #self.log.write('DEBUG>> calling rtmpdump_control \n')
            self.rtmpdump_control(action)

    def rtmpdump_control(self,action='ping'):
        # todo: move the recording process monitor code to here
        return

    def nexdef_control(self,action='ping',encoding=None):
        url = self.nexdef_media_url.split('&')[0]
        url = url.replace('base64:','control/base64:')
        if action == 'select' and encoding is not None:
            url += '&encoding_group=' + encoding[0]
            url += '&height=' + encoding[3]
            url += '&width=' + encoding[2]
            url += '&strict=true'
        # not sure what their random algorithm is but we'll just cat the
        # seconds with the microseconds of the current time.
        rand  = str(datetime.datetime.now().second)
        rand += str(datetime.datetime.now().microsecond)
        url += '&rand=' + rand + '&v=0'
        try:
            req = urllib2.Request(url)
            rsp = urllib2.urlopen(req)
        except IOError,e:
            self.error_str = 'Error in making nexdef control request:\n'
            self.error_str += ' Url = ' + str(url) + '\n'
            self.error_str += e.msg
            raise Exception,self.error_str
        self.parse_nexdef_control_response(rsp)
        
    
    def parse_nexdef_describe_response(self,rsp):
        try:
            xp = parse(rsp)
        except:
            self.error_str = 'Could not parse nexdef describe response.'
            raise Exception,self.error_str
        selected = (None, 0, 0, 0)
        self.encodings = []
        for enc in xp.getElementsByTagName('encoding'):
            id  = str(enc.getAttribute('id'))
            bps = int(enc.getAttribute('bps'))
            width = int(enc.getAttribute('width'))
            height = int(enc.getAttribute('height'))
            if bps <= int(self.max_bps) and bps > selected[1]:
                selected = ( id , bps , width, height )
                self.encodings.append( selected )

 
    def parse_nexdef_control_response(self,rsp):
        try:
            xp = parse(rsp)
        except:
            self.error_str = 'Could not parse nexdef control response.'
            raise Exception,self.error_str
        self.encoding_group = []
        for enc_group in xp.getElementsByTagName('encodingGroup'):
            for enc in enc_group.getElementsByTagName('encoding'):
                id = str(enc.getAttribute('id'))
                bps_pat = re.compile(r'FLASH_([1-9][0-9]*)K_STREAM')
                bps = re.search(bps_pat, id).groups()[0]
                self.encoding_group.append(( bps, id ))
        for pos in xp.getElementsByTagName('currentPosition'):
            msec = pos.getAttribute('millis')
        for current in xp.getElementsByTagName('currentEncoding'):
            id = str(current.getAttribute('id'))
            bps_pat = re.compile(r'FLASH_([1-9][0-9]*)K_STREAM')
            bps = re.search(bps_pat, id).groups()[0]
            self.current_encoding = ( id, bps, msec )
         
        

    def flash_url(self,game_url):
        try:
            #play_path_pat = re.compile(r'ondemand\/(.*)\?')
            play_path_pat = re.compile(r'ondemand\/(.*)$')
            self.play_path = re.search(play_path_pat,game_url).groups()[0]
            app_pat = re.compile(r'ondemand\/(.*)\?(.*)$')
            querystring = re.search(app_pat,game_url).groups()[1]
            self.app = "ondemand?_fcs_vhost=cp65670.edgefcs.net&akmfv=1.6" + querystring
            # not sure if we need this
            try:
                req = urllib2.Request('http://cp65670.edgefcs.net/fcs/ident')
                page = urllib2.urlopen(req)
                fp = parse(page)
                ip = fp.getElementsByTagName('ip')[0].childNodes[0].data
                self.tc_url = 'http://' + str(ip) + ':1935/' + self.app
            except:
                self.tc_url = None
        except:
            self.play_path = None
        try:
            live_pat = re.compile(r'live\/mlb')
            if re.search(live_pat,game_url):
                if self.streamtype == 'audio':
                    live_sub_pat = re.compile(r'live\/mlb_ga(.*)\?')
                    self.sub_path = re.search(live_sub_pat,game_url).groups()[0]
                    self.sub_path = 'mlb_ga' + self.sub_path
                    live_play_pat = re.compile(r'live\/mlb_ga(.*)$')
                    self.play_path = re.search(live_play_pat,game_url).groups()[0]
                    self.play_path = 'mlb_ga' + self.play_path
                    self.app = "live?_fcs_vhost=cp65670.live.edgefcs.net&akmfv=1.6"
                else:
                    try:
                        live_sub_pat = re.compile(r'live\/mlb_s800(.*)\?')
                        self.sub_path = re.search(live_sub_pat,game_url).groups()[0]
                        self.sub_path = 'mlb_s800' + self.sub_path
                    except Exception,detail:
                        self.error_str = 'Could not parse the stream subscribe path: ' + str(detail)
                        raise Exception,self.error_str
                    try:
                        live_path_pat = re.compile(r'live\/mlb_s800(.*)$')
                        self.play_path = re.search(live_path_pat,game_url).groups()[0]
                        self.play_path = 'mlb_s800' + self.play_path
                    except Exception,detail:
                        self.error_str = 'Could not parse the stream play path: ' + str(detail)
                        raise Exception,self.error_str
                    self.app = 'live?_fcs_vhost=cp65670.live.edgefcs.net&akmfv=1.6'
            if self.debug:
                self.log.write("DEBUG>> sub_path = " + str(self.sub_path) + "\n")
                self.log.write("DEBUG>> play_path = " + str(self.play_path) + "\n")
                self.log.write("DEBUG>> app = " + str(self.app) + "\n")
        except Exception,e:
            self.error_str = str(e)
            raise Exception,e
            self.app = None
        if self.debug:
            self.log.write("DEBUG>> soap url = \n" + str(game_url) + '\n')
        self.log.write("DEBUG>> soap url = \n" + str(game_url) + '\n')

        self.filename = os.path.join(os.environ['HOME'], 'mlbdvr_games')
        self.filename += '/' + str(self.event_id)
        if self.streamtype == 'audio':
            self.filename += '.mp3'
        else:
            self.filename += '.mp4'
        recorder = DEFAULT_F_RECORD
        self.rec_cmd_str = self.prepare_rec_str(recorder,self.filename,game_url)
        ''' NOT NEEDED
        outlog = open('/tmp/rtmpdump.log','w')
        errlog = open('/tmp/rtmpdump-error.log','w')
        self.rec_process = MLBprocess(self.rec_cmd_str,retries=5,
                                      stdout=outlog,errlog=errlog)
        NOT NEEDED '''
        return self.rec_cmd_str


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
        return game_url

    def prepare_rec_str(self,rec_cmd_str,filename,streamurl):
        # remove short files
        try:
            filesize = long(os.path.getsize(filename))
        except:
            filesize = 0
        if filesize <= 5:
            try:
                os.remove(filename)
                self.log.write('\nRemoved short file: ' + str(filename) + '\n')
            except:
                pass

        #rec_cmd_str = rec_cmd_str.replace('%f', filename)
        rec_cmd_str = rec_cmd_str.replace('%f', '-')
        rec_cmd_str = rec_cmd_str.replace('%s', '"' + streamurl + '"')
        if self.play_path is not None:
            rec_cmd_str += ' -y "' + str(self.play_path) + '"'
        if self.app is not None:
            rec_cmd_str += ' -a "' + str(self.app) + '"'
        if self.use_soap:
            rec_cmd_str += ' -s http://mlb.mlb.com/flash/mediaplayer/v4/RC91/MediaPlayer4.swf?v=4'
        if self.tc_url is not None:
            rec_cmd_str += ' -t "' + self.tc_url + '"'
        if self.sub_path is not None:
            rec_cmd_str += ' -d ' + str(self.sub_path) + ' -v'
        self.log.write("\nDEBUG>> rec_cmd_str" + '\n' + rec_cmd_str + '\n\n')
        return rec_cmd_str
        
    def prepare_play_str(self,play_cmd_str,filename,resume=None,elapsed=0):
        play_cmd_str = play_cmd_str.replace('%s', filename)
        if resume:
            play_cmd_str += ' ' + str(resume) + ' ' + str(elapsed)
        self.log.write("\nDEBUG>> play_cmd_str" + '\n' + play_cmd_str + '\n\n')
        return play_cmd_str

