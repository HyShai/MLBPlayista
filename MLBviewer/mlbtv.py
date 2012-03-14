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
import subprocess
import select
from copy import deepcopy
import sys

from mlbprocess import MLBprocess


try:
    from xml.dom.minidom import parse
except:
    print "Missing python external dependencies."
    print "Please read the REQUIREMENTS-2010.txt file."
    sys.exit()

# Set this to True if you want to see all the html pages in the logfile
#DEBUG = True
#DEBUG = None
#from __init__ import AUTHDIR

# Change this line if you want to use flvstreamer instead
DEFAULT_F_RECORD = 'rtmpdump -f \"LNX 10,0,22,87\" -o %f -r %s'

# Change the next two settings to tweak mlbhd behavior
DEFAULT_HD_PLAYER = 'mlbhls -B %B -b %P'
HD_ARCHIVE_OFFSET = '48'

AUTHDIR = '.mlb'
COOKIEFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'cookie')
SESSIONKEY = os.path.join(os.environ['HOME'], AUTHDIR, 'sessionkey')
LOGFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'log')
USERAGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'
TESTXML = os.path.join(os.environ['HOME'], AUTHDIR, 'test_epg.xml')
BLACKFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'blackout')

SOAPCODES = {
    "1"    : "OK",
    "-1000": "Requested Media Not Found",
    "-1500": "Other Undocumented Error",
    "-1600": "Requested Media Not Available Yet.",
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
    "Completed Early" : "E",
    "Cancelled"       : "C",
    "Final"           : "F",
    "Preview"         : "P",
    "Postponed"       : "PO",
    "Game Over"       : "GO",
    "Delayed Start"   : "D",
    "Delayed"         : "D",
    "Pre-Game"        : "IP",
    "Suspended"       : "S",
    "Warmup"          : "IP",
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
    'mia': ('146', 'Miami Marlins', ''),
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
    'nyf': ('NYF', 'New York Yankees Futures Team'),
    't3944': ( 'T3944', 'CPBL All-Stars' ),
    'unk': ( None, 'Unknown', 'Teamcode'),
    'tbd': ( None, 'TBD'),
    't102': ('T102', 'Round Rock Express'),
    't103': ('T103', 'Lake Elsinore Storm'),
    't234': ('T234', 'Durham Bulls'),
    't235': ('T235', 'Memphis Redbirds'),
    't249': ('T249', 'Carolina Mudcats'),
    't260': ('T260', 'Tulsa Drillers'),
    't445': ('T445', 'Columbus Clippers'),
    't477': ('T477', 'Greensboro Grasshoppers'),
    't494': ('T493', 'Charlotte Knights'),
    't564': ('T564', 'Jacksonville Suns'),
    't569': ('T569', 'Quintana Roo Tigres'),
    't580': ('T580', 'Winston-Salem Dash'),
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
    't2510': ('T2510', 'Team Canada'),
    'uga' : ('UGA',  'University of Georgia'),
    'mcc' : ('MCC', 'Manatee Community College'),
    'fso' : ('FSO', 'Florida Southern College'),
    'fsu' : ('FSU', 'Florida State University'),
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
        '2010': (datetime.datetime(2010,3,14),datetime.datetime(2010,11,7)),
        '2011': (datetime.datetime(2011,3,13),datetime.datetime(2011,11,6)),
	'2012': (datetime.datetime(2012,3,11),datetime.datetime(2012,11,4)),
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
        self.multiangle = "http://gdx.mlb.com/components/game/mlb/year_"\
            + padstr(self.year)\
            + "/month_" + padstr(self.month)\
            + "/day_" + padstr(self.day) + "/multi_angle_epg.xml"
        # For BETA testing, use my own xml
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

    def getMultiAngleFromXml(self,event_id):
        out = []
        camerainfo = dict()
        txheaders = {'User-agent' : USERAGENT}
        data = None
        req = urllib2.Request(self.multiangle,data,txheaders)
        try:
            fp = urllib2.urlopen(req)
        except urllib2.HTTPError:
            raise MLBUrlError
        xp = parse(fp)
        for node in xp.getElementsByTagName('game'):
            id = node.getAttribute('calendar_event_id')
            if id != event_id:
                continue
            home = node.getAttribute('home_file_code')
            away = node.getAttribute('away_file_code')
            title  = ' '.join(TEAMCODES[away][1:]).strip() + ' at '
            title += ' '.join(TEAMCODES[home][1:]).strip()
            camerainfo[id] = dict()
            camerainfo[id]['angles'] = []
            for attr in node.attributes.keys():
                camerainfo[id][attr] = node.getAttribute(attr)
            for angle in node.getElementsByTagName('angle'):
                cdict = dict()
                for attr in angle.attributes.keys():
                    cdict[attr] = angle.getAttribute(attr)
                media = angle.getElementsByTagName('media')[0]
                platform = media.getAttribute('platform')
                if platform != 'WEB_MEDIAPLAYER':
                    continue 
                cdict['content_id'] = media.getAttribute('content_id')
                if cdict['name'] == '':
                    cdict['name'] = 'Unknown Camera Angle'
                camerainfo[id]['angles'].append(cdict)
            out.append(camerainfo[id])
        #raise Exception,repr(out)
        return out

    def getMultiAngleListing(self,event_id):
        out = []
        teams = dict()
        angles = []
        null = []
        raw = self.getMultiAngleFromXml(event_id)[0]
        id = raw['id']
        desc = raw['description']
        teams['home'] = raw['home_file_code']
        teams['away'] = raw['away_file_code']
        for angle in raw['angles']:
            out.append((teams, 0, (angle['name'], 0, angle['content_id'], event_id), null, null, 'NB', event_id, 0))
        #raise Exception,repr(out)
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
        content['video']['300'] = []
        content['video']['500'] = []
        content['video']['1200'] = []
        content['video']['1800'] = []
        content['video']['2400'] = []
        content['video']['swarm'] = []
        content['condensed'] = []
        event_id = str(xp.getAttribute('calendar_event_id'))
        for media in xp.getElementsByTagName('media'):
           tmp = {}
           for attr in media.attributes.keys():
               tmp[attr] = str(media.getAttribute(attr))
           out = []
           try:
               tmp['playback_scenario']
           except:
               continue
               raise Exception,repr(tmp)
           if tmp['type'] in ('home_audio','away_audio'):
               if tmp['playback_scenario'] == 'AUDIO_FMS_32K':
                   if tmp['type'] == 'away_audio':
                       coverage = away
                   elif tmp['type'] == 'home_audio':
                       coverage = home
                   out = (tmp['display'], coverage, tmp['id'], event_id)
                   #print 'Found audio: ' + repr(out)
                   content['audio'].append(out)
           elif tmp['type'] in ('mlbtv_national', 'mlbtv_home', 'mlbtv_away'):
               if tmp['playback_scenario'] in \
                     ( 'HTTP_CLOUD_WIRED', 'FMS_CLOUD'):
                   try:
                       tmp['blackout']
                   except:
                       tmp['blackout'] = ""
                   nb_pat = re.compile(r'MLB_NATIONAL_BLACKOUT')
                   if re.search(nb_pat,tmp['blackout']) is not None:
                       content['blackout'] = 'MLB_NATIONAL_BLACKOUT'
                   else:
                       content['blackout'] = None
                   if tmp['type'] == 'mlbtv_national':
                       coverage = '0'
                   elif tmp['type'] == 'mlbtv_away':
                       coverage = away
                   else:
                       coverage = home
                   out = (tmp['display'], coverage, tmp['id'], event_id)
                   #print 'Found video: ' + repr(out) + tmp['playback_scenario']
                   if tmp['playback_scenario'] == 'HTTP_CLOUD_WIRED':
                       content['video']['swarm'].append(out)
                   elif tmp['playback_scenario'] == 'FMS_CLOUD':
                       for s in ('300', '500', '1200', '1800', '2400'):
                           content['video'][s].append(out)
                   else:
                       continue
           elif tmp['type'] == 'condensed_game':
               out = ('CG',0,tmp['id'], event_id)
               #print 'Found condensed: ' + repr(out)
               content['condensed'].append(out)
        return content
    
    def __xmlToPython(self):
        return self.__scheduleFromXml()
        
    def getData(self):
        # This is the public method that puts together the private
        # steps above. Fills it up with data.
        try:
            self.data = self.__xmlToPython()
        except ValueError,detail:
            raise MLBJsonError,detail

    def trimXmlList(self,blackout=()):
        # This is the XML version of trimList
        # easier to write a new method than adapt the old one
        if not self.data:
            raise MLBJsonError, "No games available today."
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
                try:
                    game['content']['blackout']
                except:
                    # damn bogus WBC entries
                    game['content']['blackout'] = ""
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
                TEAMCODES[dct['away']] = TEAMCODES['unk']
            if not TEAMCODES.has_key(dct['home']):
                TEAMCODES[dct['home']] = TEAMCODES['unk']
            #raise Exception,repr(game)
            dct['video'] = {}
            dct['video']['128'] = []
            dct['video']['500'] = []
            dct['video']['800'] = []
            dct['video']['1200'] = []
            dct['video']['1800'] = []
            dct['video']['swarm'] = []
            dct['condensed'] = []
            #raise Exception,repr(game['content']['video'])
            for key in ('300', '500', '1200', '1800', '2400', 'swarm'):
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
                    if dct['video'].has_key('800'):
                        if dct['video'].has_key('1200') == False:
                            # don't let a black sheep ruin it for everyone
                            dct['video']['1200'] = deepcopy(dct['video']['800'])
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

        return self.getXmlCondensedVideo(gameid)

    def getXmlCondensedVideo(self,gameid):
        out = ''
        condensed = self.trimXmlList()
        for elem in condensed:
            #raise Exception,repr(condensed)
            if elem[0] == gameid:
                content_id = elem[1]['condensed'][0][2]
        url = 'http://mlb.mlb.com/gen/multimedia/detail/' 
        url += content_id[-3] + '/' + content_id[-2] + '/' + content_id[-1]
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
        for url in media.getElementsByTagName('url'):
            if url.getAttribute('playback_scenario') == 'FLASH_1000K_640X360':
                
                out = str(url.childNodes[0].data)
        return out
            

    def getXmlTopPlays(self,gameid):
        gid = gameid
        gid = gid.replace('/','_')
        gid = gid.replace('-','_')
        url = self.epg.replace('grid.xml','gid_' + gid + '/media/highlights.xml')
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
                speed_pat = re.compile(r'FLASH_([1-9][0-9]*)K')
                speed = int(re.search(speed_pat,scenario).groups()[0])
                if speed > selected:
                    selected = speed
                    url = urls.childNodes[0].data
            out.append(( title, headline, url, state, gameid, '0')) 
        #raise Exception,out
        return out

    def getTopPlays(self,gameid):
        listtime = datetime.datetime(self.year, self.month, self.day)
        if listtime >= self.xmltime:
            self.use_xml = True
        else:
            self.use_xml = False

        return self.getXmlTopPlays(gameid)

    def getListings(self, myspeed, blackout, audiofollow):
        listtime = datetime.datetime(self.year, self.month, self.day)
        if listtime >= self.xmltime:
            self.use_xml = True
        else:
            self.use_xml = False

        return self.getXmlListings(myspeed, blackout, audiofollow)


    def getXmlListings(self, myspeed, blackout, audiofollow):
        self.getData()
        listings = self.trimXmlList(blackout)

        return [(elem[1]['teams'],\
                     elem[1]['event_time'],
                     elem[1]['video'][str(myspeed)],
                     elem[1]['audio'],
                     elem[1]['condensed'],
                     elem[1]['status'],
                     elem[0],
                     elem[1]['media_state'])\
                         for elem in listings]


    def parse_innings_xml(self,event_id,use_nexdef):
	gameid, year, month, day = event_id.split('-')[1:5]
        url = 'http://mlb.mlb.com/mlb/mmls%s/%s.xml' % (year, gameid)
        req = urllib2.Request(url)
        try:
            rsp = urllib2.urlopen(req)
        except:
            self.error_str = "Could not open " + url
            raise Exception,self.error_str
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
                if use_nexdef and type == 'SCAST':
                    time = inning_time.getAttribute('start')
                    try:
                        ( hrs, min, sec ) = time.split(':')
                    except:
                        self.error_str = "Could not parse time = " + time
                        raise Exception, self.error_str
                    msec = 1000 * ( 3600 * int(hrs) + 60 * int(min) + int(sec)) 
                    # inning times seem to be off by one hour
                    #msec += 3600 * 1000
                    # don't know why this works, but this seems to be what mlb
                    # does, rounding down to nearest 5 seconds
                    msec -= (int(sec)%5) * 1000
                    # one other correction needs to be made...
                    # if the hrs is less than 8, this must be an extra innings
                    # game that has gone into the next day.  add 24 hrs.
                    # why 8?  there is never an 8am EST start time
                    # nor an extra hours game that goes this late
                    if int(hrs) <= 8:
                        msec += 3600 * 24 * 1000
                    out.append((number, is_top, msec))
                    #tc_str = '%s/%s/%s %s' % (year, month, day, time)
                    #timecode = urllib.quote(tc_str)
                    #out.append((number, is_top, time))
                elif use_nexdef == False and type == "FMS":
                    out.append((number, is_top, inning_time.getAttribute('start')))
        return out


class GameStream:
    def __init__(self,stream, email, passwd, debug=None,
                 auth=True, streamtype='video',use_soap=True,speed=800,
                 coverage=None,use_nexdef=False,max_bps=800000,start_time=0,
                 strict=False,condensed=False,postseason=False,camera=0,
                 use_librtmp=False,use_mlbhd=False):
        self.strict = strict
        self.condensed = condensed
        self.postseason = postseason
        self.use_librtmp = use_librtmp
        self.use_mlbhd = use_mlbhd
        self.auth = auth
        self.camera = camera
        self.this_camera = 0
        self.use_nexdef = use_nexdef
        self.rec_process = None
        self.start_time = start_time
        self.max_bps = max_bps
        self.stream = stream
        self.streamtype = streamtype
        self.speed = speed
        self.log = MLBLog(LOGFILE)
        self.error_str = "What happened here?\nPlease enable debug with the d key and try your request again."
        self.use_soap = use_soap
        try:
            ( self.call_letters, 
              self.team_id, 
              self.content_id, 
              self.event_id ) = self.stream
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
            self.scenario = "AUDIO_FMS_32K"
            self.subject  = "MLBCOM_GAMEDAY_AUDIO"
        else:
            if self.use_nexdef:
                self.scenario = 'HTTP_CLOUD_WIRED'
            else:
                self.scenario = 'FMS_CLOUD'
            self.subject  = "LIVE_EVENT_COVERAGE"
        self.cookies = {}
        #self.content_id = None
        self.play_path = None
        self.tc_url = None
        self.app = None
        self.rtmp_url = None
        self.rtmp_host = None
        self.rtmp_port = None
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
        """ BEGIN Is any of this necessary?
        ns_headers = response.headers.getheaders("Set-Cookie")
        attrs_set = cookielib.parse_ns_headers(ns_headers)
        cookie_tuples = cookielib.CookieJar()._normalized_cookie_tuples(attrs_set)
        for tup in cookie_tuples:
            name, value, standard, rest = tup
            self.cookies[name] = value
        END Is any of this necessary? """
        # let's also try a different method
        for c in self.session_cookies:
            self.cookies[c.name] = c.value
    
    def login(self):
        # BEGIN login()
        # meant to be called by workflow()
        self.session_cookies = cookielib.LWPCookieJar()
        if self.session_cookies != None:
           if os.path.isfile(COOKIEFILE):
              #self.session_cookies.load(COOKIEFILE,ignore_discard=True)
              os.remove(COOKIEFILE)
        else:
           self.error_str = "Couldn't open cookie jar"
           raise Exception,self.error_str
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
            self.extract_cookies(handle)
        except Exception,detail:
            raise Exception,detail
        if self.debug:
            self.log.write('Did we receive a cookie from the wizard?\n')
            for index, cookie in enumerate(self.session_cookies):
                print >> self.log, index, ' : ' , cookie
        self.session_cookies.save(COOKIEFILE,ignore_discard=True)

        rdata = handle.read()

        # now authenticate
        auth_values = {'emailAddress' : self.email,
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
            self.extract_cookies(handle)
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
 
    def workflow(self,use_soap=True):
        # This is the workhorse routine.
        # 1. Login
        # 2. Get the url from the workflow page
        # 3. Logout
        # 4. Return the raw workflow response page
        # The hope is that this sequence will always be the same and leave
        # it to url() to determine if an error occurs.  This way, hopefully, 
        # error or no, we'll always log out.
        if self.session_cookies is None:
            if self.auth and self.logged_in is None:
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

    def parse_media_request(self,reply):
        # Abort if the status is not "1"
        status_code = str(reply.getElementsByTagName('status-code')[0].childNodes[0].data)
        if status_code != "1":
            self.log.write("DEBUG (SOAPCODES!=1)>> writing unsuccessful soap response event_id = " + str(self.event_id) + "\n")
            df = open('/tmp/unsuccessful.xml','w')
            reply.writexml(df)
            df.close()
            df = open('/tmp/unsuccessful.xml')
            msg = df.read()
            df.close()
            self.log.write(msg + '\n')
            self.error_str = SOAPCODES[status_code]
            raise Exception,self.error_str

        ### TEST CODE BLOCK - COMMENT AFTER TESTING
        #blackout_status = reply.getElementsByTagName('blackout-status')[0]
        #success_status = blackout_status.getElementsByTagName('successStatus')
        #raise Exception,repr(success_status)
        ### END TEST CODE BLOCK - COMMENT AFTER TESTING

        ### TEST CODE BLOCK - COMMENT AFTER TESTING
        #bf = open(BLACKFILE, 'w')
        #reply.writexml(bf)
        #bf.close()
        ### END TEST CODE BLOCK - COMMENT AFTER TESTING

        try:
            blackout_status = reply.getElementsByTagName('blackout')[0].childNodes[0].data
	    #raise Exception,repr(blackout_status)
        except:
            blackout_status = reply.getElementsByTagName('blackout-status')[0]
            try:
                success_status = blackout_status.getElementsByTagName('successStatus')
                blackout_status = None
            except:
                try:
                    location_status = blackout_status.getElementsByTagName('locationCannotBeDeterminedStatus')
                except:
                    blackout_status = 'LOCATION CANNOT BE DETERMINED.'

        media_type = reply.getElementsByTagName('type')[0].childNodes[0].data
        media_state = reply.getElementsByTagName('state')[0].childNodes[0].data
        self.media_state = media_state
        if blackout_status is not None and self.streamtype == 'video':
            inmarket_pat = re.compile(r'INMARKET')
            if re.search(inmarket_pat,blackout_status) is not None:
                pass
            elif media_state == 'MEDIA_ON' and not self.postseason:
                self.error_str = 'BLACKOUT: ' + str(blackout_status)
                bf = open(BLACKFILE, 'w')
                reply.writexml(bf)
                bf.close()
                raise Exception,self.error_str

        content_list = []
        for content in reply.getElementsByTagName('user-verified-content'):
            type = content.getElementsByTagName('type')[0].childNodes[0].data
            if type != self.streamtype:
               continue
            content_id = content.getElementsByTagName('content-id')[0].childNodes[0].data
            if content_id != self.content_id:
                continue
            # First, collect all the domain-attributes
            dict = {}
            for node in content.getElementsByTagName('domain-attribute'):
                name = str(node.getAttribute('name'))
                value = node.childNodes[0].data
                dict[name] = value
            # There are a series of checks to trim the content list
            # 1. Trim out 'in-market' listings like Yankees On Yes
            if dict.has_key('coverage_type'):
                if 'in-market' in dict['coverage_type']:
                    continue
            # 2. Trim out all non-English language broadcasts
            if dict.has_key('language'):
                if dict['language'] != 'EN':
                    continue
            # 3. For post-season, trim out multi-angle listings
            if self.postseason:
                if dict['in_epg'] != 'mlb_multiangle_epg':
                    continue
            else:
                if dict['in_epg'] == 'mlb_multiangle_epg':
                    continue
            # 4. Get coverage association and call_letters
            try:
                cov_pat = re.compile(r'([0-9][0-9]*)')
                coverage = re.search(cov_pat, dict['coverage_association']).groups()[0]
            except:
                 coverage = None
            try:
                call_letters = dict['call_letters']
            except:
                if self.postseason == False:
                    raise Exception,repr(dict)
                else:
                    call_letters = 'MLB'
            #raise Exception,repr(dict)
            #try:
            #    letters_pat = re.compile(r'"(.*)"')
            #    call_letters = re.search(letters_pat, call_letters).groups()[0]
            #except:
            #    raise Exception,repr(call_letters)
            for media in content.getElementsByTagName('user-verified-media-item'):
                state = media.getElementsByTagName('state')[0].childNodes[0].data
                scenario = media.getElementsByTagName('playback-scenario')[0].childNodes[0].data
                if scenario == self.scenario and \
                    state in ('MEDIA_ARCHIVE', 'MEDIA_ON', 'MEDIA_OFF'):
                    content_list.append( ( call_letters, coverage, content_id, self.event_id ) )
        return content_list
                    

    def parse_fms_cloud_response(self,url):
        out = ''
        req = urllib2.Request(url)
        handle = urllib2.urlopen(req)
        rsp = parse(handle)
        rtmp_base = rsp.getElementsByTagName('meta')[0].getAttribute('base')
        for elem in rsp.getElementsByTagName('video'):
            speed = int(elem.getAttribute('system-bitrate'))/1000
            if int(self.speed) == int(speed):
               src = elem.getAttribute('src').replace('mp4:','/')
               out = rtmp_base + src
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
                if self.postseason == True:
                    if 'mlb_mp4_epg' in str(dict['in_epg']):
                        continue
                else:
                    if 'mlb_multiangle_epg' in str(dict['in_epg']):
                        continue
                if 'in-market' in str(dict['coverage_type']):
                    continue
                if dict.has_key('language'):
                    if dict['language']['value'] != 'EN':
                        continue
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
                    if self.postseason == True:
                        if self.this_camera != self.camera:
                            self.this_camera += 1
                            continue
                    state = media['media-item']['state']
                    scenario = media['media-item']['playback-scenario']
                    if scenario == self.scenario and\
                                state in ( 'MEDIA_ARCHIVE', 'MEDIA_ON', 'MEDIA_OFF' ):
                        content_list.append( ( call_letters, coverage, stream['content-id'] , self.event_id ) )
        return content_list

    def getCondensedVideo(self):
        condensed = ''
        url = 'http://mlb.mlb.com/gen/multimedia/detail/'
        url += self.content_id[-3] + '/' + self.content_id[-2] + '/' + self.content_id[-1]
        url += '/' + self.content_id + '.xml'
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
        #raise Exception,url
        for url in media.getElementsByTagName('url'):
            if url.getAttribute('playback_scenario') == 'FLASH_1200K_640X360':

                condensed = str(url.childNodes[0].data)
        return condensed


    def url(self):
        # Overload url to handle condensed games now that condensed games
        # use FMS.
        if self.condensed:
            game_url = self.getCondensedVideo()
            return self.flash_url(game_url)

        # return of workflow is useless for here, but it still calls all the 
        # necessary steps to login and get cookies
        if self.stream is None:
             self.error_str = "No event-id to locate media streams."
             raise
        # (re-)initialize some variables to make retries possible
        #self.content_id = None
        self.play_path  = None
        self.sub_path   = None
        self.app        = None
 
        # call the workhorse
        self.workflow()

        # July 28, 2010 - SOAP services stopped working.
        # SOAP being replaced with a GET url, response should be nearly
        # identical, but different strategy for request/parse now.
        base_url = 'https://secure.mlb.com/pubajaxws/bamrest/MediaService2_0/op-findUserVerifiedEvent/v-2.3?'
        try:
            sessionKey = urllib.unquote(self.cookies['ftmu'])
        except:
            sessionKey = None
        query_values = {
            'eventId': self.event_id,
            'sessionKey': sessionKey,
            'fingerprint': urllib.unquote(self.cookies['fprt']),
            'identityPointId': self.cookies['ipid'],
            'subject': self.subject
        }
        url = base_url + urllib.urlencode(query_values)
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        reply = parse(response)

        content_list = self.parse_media_request(reply)

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
        try:
            sessionkey = urllib.unquote(self.cookies['ftmu'])
        except:
            sessionkey = None
        query_values = {
            'subject': self.subject,
            'sessionKey': sessionkey,
            'identityPointId': self.cookies['ipid'],
            'contentId': self.content_id,
            'playbackScenario': self.scenario,
            'eventId': self.event_id,
            'fingerprint': urllib.unquote(self.cookies['fprt'])
        }
        url = base_url + urllib.urlencode(query_values)
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        reply = parse(response)

        status_code = str(reply.getElementsByTagName('status-code')[0].childNodes[0].data)
        if status_code != "1":
            self.log.write("DEBUG (SOAPCODES!=1)>> writing unsuccessful soap response event_id = " + str(self.event_id) + " contend-id = " + self.content_id + "\n")
            df = open('/tmp/unsuccessful.xml','w')
            reply.writexml(df)
            df.close()
            df = open('/tmp/unsuccessful.xml')
            msg = df.read()
            df.close()
            self.error_str = SOAPCODES[status_code]
            raise Exception,self.error_str
        try:
            self.session_key = reply['session-key']
            self.write_session_key(self.session_key)
        except:
            self.session_key = None
        try:
            game_url = reply.getElementsByTagName('url')[0].childNodes[0].data
        except:
            self.error_str = "Stream URL not found in reply.  Stream may not be available yet."
            raise Exception,self.error_str
        self.log.write("DEBUG>> URL received: " + game_url + '\n')
        if self.use_nexdef:
            #raise Exception,self.nexdef_url(game_url)
            if self.use_mlbhd:
                return self.prepare_hd_str(game_url)
            else:
                return self.nexdef_flash_url(self.nexdef_url(game_url))
        else:
            if self.streamtype == 'video':
                game_url = self.parse_fms_cloud_response(game_url)
            return self.flash_url(game_url)


    def nexdef_url(self,game_url):
        self.nexdef_url = game_url
        self.nexdef_media_url = None
        nexdef_base = 'http://local.swarmcast.net:8001/protected/content/adaptive-live/'
        # build the first url for stream descriptions

        url = nexdef_base + 'describe' + '/base64:' + game_url + '&refetch=true'
        req = urllib2.Request(url)
        try:
            rsp = urllib2.urlopen(req)
        except IOError,e:
            try:
                if hasattr(e, 'code') and e.code == 400:
                    self.error_str = 'Nexdef reports that requested stream is not available.'
                else:
                    self.error_str = e.msg
            except:
                self.error_str = "Could not connect to NexDef.  Is autobahn.jar running?"
            raise Exception,self.error_str
        # parse the stream descriptions for time of head of stream
        try:
            return self.parse_nexdef_describe_response(rsp,game_url)
        except:
            #raise
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
        
        return self.nexdef_media_url

    def control(self,action='ping',encoding=None,strict=False):
        if self.use_nexdef:
            #self.log.write('DEBUG>> calling nexdef_control \n')
            self.nexdef_control(action,encoding,strict)
        else:
            #self.log.write('DEBUG>> calling rtmpdump_control \n')
            self.rtmpdump_control(action)

    def rtmpdump_control(self,action='ping'):
        # todo: move the recording process monitor code to here
        return

    def nexdef_control(self,action='ping',encoding=None, strict=False):
        url = self.nexdef_media_url.split('&')[0]
        url = url.replace('base64:','control/base64:')
        if action == 'select' and encoding is not None:
            url += '&encoding_group=' + str(encoding[0])
            #url += '&height=' + str(encoding[3])
            #url += '&width=' + str(encoding[2])
        if strict:
            url += '&strict=true'
        # not sure what their random algorithm is but we'll just cat the
        # seconds with the microseconds of the current time.
        #rand  = str(datetime.datetime.now().second)
        #rand += str(datetime.datetime.now().microsecond)
        #url += '&rand=' + rand + '&v=0'
        #url += '&v=0'
        try:
            req = urllib2.Request(url)
            rsp = urllib2.urlopen(req)
        except IOError,e:
            self.error_str = 'Error in making nexdef control request:\n'
            self.error_str += ' Url = ' + str(url) + '\n'
            self.error_str += e.msg
            raise Exception,self.error_str
        self.parse_nexdef_control_response(rsp)
        
    
    def parse_nexdef_describe_response(self,rsp,game_url):
        nexdef_use  = 'http://local.swarmcast.net:8001/protected/content/adaptive-live/base64:'
        try:
            xp = parse(rsp)
        except:
            self.error_str = 'Could not parse NexDef stream list. Try alternate coverage.'
            raise Exception,self.error_str
        selected = (None, 0, 0, 0)
        for time in xp.getElementsByTagName('streamHead'):
            timestamp = time.getAttribute('timeStamp')
            milliseconds = int(time.getAttribute('timeStamp'))
            milliseconds += 3600*1000
            milliseconds -= (int(milliseconds))%5000
            # if we get a non-zero, non-null start_time from init, use it
            if self.start_time is not None and self.start_time > 0:
                milliseconds = self.start_time
        # return the media url with the correct timestamp
        self.nexdef_media_url = 'base64:' + game_url + '?max_bps=' + str(self.max_bps)
        if self.strict:
            self.nexdef_media_url += '&strict=true'
        # start_time = 0 is the same as "look it up" 
        # whereas start_time = None means "don't include start_time at all"
        if self.start_time is not None:
            self.nexdef_media_url += '&start_time=' + str(milliseconds) 
        

        self.encodings = {}
        for enc in xp.getElementsByTagName('encoding'):
            id  = str(enc.getAttribute('id'))
            bps = int(enc.getAttribute('bps'))
            if bps <= int(self.max_bps):
                self.encodings[bps] = ( id , bps )
        return self.nexdef_media_url

 
    def parse_nexdef_control_response(self,rsp):
        try:
            xp = parse(rsp)
        except:
            self.error_str = 'Could not parse nexdef control response.'
            raise Exception,self.error_str
        self.encoding_group = {}
        for enc_group in xp.getElementsByTagName('encodingGroup'):
            for enc in enc_group.getElementsByTagName('encoding'):
                id = str(enc.getAttribute('id'))
                bps_pat = re.compile(r'([1-9][0-9]*)_complete')
                bps = re.search(bps_pat, id).groups()[0]
                self.encoding_group[bps] = id
        for pos in xp.getElementsByTagName('currentPosition'):
            msec = pos.getAttribute('millis')
        for current in xp.getElementsByTagName('currentEncoding'):
            id = str(current.getAttribute('id'))
            bps_pat = re.compile(r'([1-9][0-9]*)_complete')
            bps = re.search(bps_pat, id).groups()[0]
            self.current_encoding = ( id, bps, msec )
        
    def nexdef_flash_url(self,game_url):
        self.play_path = self.nexdef_media_url
        self.rtmp_path = 'rtmp://127.0.0.1:1935/live/' + self.play_path
        self.app = 'live'
        self.rtmp_host = '127.0.0.1'
        self.rtmp_port = '1935'
        recorder = DEFAULT_F_RECORD
        self.filename = '-'
        if self.use_librtmp:
            self.rec_cmd_str = self.prepare_mplayer_str(recorder,self.filename,self.rtmp_path)
        else:
            self.rec_cmd_str = self.prepare_rec_str(recorder,self.filename,self.rtmp_path)
        return self.rec_cmd_str

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
                        live_sub_pat = re.compile(r'live\/mlb_c(.*)\?')
                        self.sub_path = re.search(live_sub_pat,game_url).groups()[0]
                        self.sub_path = 'mlb_c' + self.sub_path
                    except Exception,detail:
                        self.error_str = 'Could not parse the stream subscribe path: ' + str(detail)
                        raise Exception,self.error_str
                    try:
                        live_path_pat = re.compile(r'live\/mlb_c(.*)$')
                        self.play_path = re.search(live_path_pat,game_url).groups()[0]
                        self.play_path = 'mlb_c' + self.play_path
                    except Exception,detail:
                        self.error_str = 'Could not parse the stream play path: ' + str(detail)
                        raise Exception,self.error_str
                    sec_pat = re.compile(r'mlbsecurelive')
                    if re.search(sec_pat,game_url) is not None:
                        self.app = 'mlbsecurelive-live'
                    else:
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
        if self.use_librtmp:
            self.rec_cmd_str = self.prepare_mplayer_str(recorder,self.filename,game_url)
        else:
            self.rec_cmd_str = self.prepare_rec_str(recorder,self.filename,game_url)
        return self.rec_cmd_str

    def prepare_hd_str(self,streamUrl):
        self.hd_str = DEFAULT_HD_PLAYER
        self.hd_str = self.hd_str.replace('%B', streamUrl)
        self.hd_str = self.hd_str.replace('%P', self.max_bps)
        if self.media_state != 'MEDIA_ON':
            self.hd_str += ' -f ' + str(HD_ARCHIVE_OFFSET)
        self.hd_str += ' -o -'
        return self.hd_str
        

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
        if self.rtmp_host is not None:
            rec_cmd_str += ' -n ' + str(self.rtmp_host)
        if self.rtmp_port is not None:
            rec_cmd_str += ' -c ' + str(self.rtmp_port)
        if self.start_time is not None and self.streamtype != 'audio':
            if self.use_nexdef == False:
                rec_cmd_str += ' -A ' + str(self.start_time)
        self.log.write("\nDEBUG>> rec_cmd_str" + '\n' + rec_cmd_str + '\n\n')
        return rec_cmd_str

    def prepare_mplayer_str(self,rec_cmd_str,filename,streamurl):
        mplayer_str = '"' + streamurl
        if self.play_path is not None:
            mplayer_str += ' playpath=' + self.play_path
        if self.app is not None:
            if self.sub_path is not None:
                mplayer_str += ' app=' + self.app
                mplayer_str += ' subscribe=' + self.sub_path + ' live=1'
            else:
                mplayer_str += ' app=' + self.app
        mplayer_str += '"'
        self.log.write("\nDEBUG>> mplayer_str" + '\n' + mplayer_str + '\n\n')
        return mplayer_str
        
    def prepare_play_str(self,play_cmd_str,filename,resume=None,elapsed=0):
        play_cmd_str = play_cmd_str.replace('%s', filename)
        if resume:
            play_cmd_str += ' ' + str(resume) + ' ' + str(elapsed)
        self.log.write("\nDEBUG>> play_cmd_str" + '\n' + play_cmd_str + '\n\n')
        return play_cmd_str

