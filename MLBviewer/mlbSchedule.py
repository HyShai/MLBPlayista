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

from mlbProcess import MLBprocess
from mlbConstants import *
from mlbLog import MLBLog
from mlbError import *

try:
    from xml.dom.minidom import parse
except:
    print "Missing python external dependencies."
    print "Please read the REQUIREMENTS-2012.txt file."
    sys.exit()


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
	'2013': (datetime.datetime(2013,3,10),datetime.datetime(2013,11,3)),
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

def padstr(num):
    if len(str(num)) < 2: 
        return '0' + str(num)
    else:
        return str(num)

class MLBSchedule:

    def __init__(self,ymd_tuple=None,time_shift=None,use_wired_web=False):
        # maybe the answer for nexdef for basic subscribers
        self.use_wired_web = use_wired_web
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
        self.grid = "http://gdx.mlb.com/components/game/mlb/year_"\
            + padstr(self.year)\
            + "/month_" + padstr(self.month)\
            + "/day_" + padstr(self.day) + "/grid.xml"
        self.multiangle = "http://gdx.mlb.com/components/game/mlb/year_"\
            + padstr(self.year)\
            + "/month_" + padstr(self.month)\
            + "/day_" + padstr(self.day) + "/multi_angle_epg.xml"
        self.log = MLBLog(LOGFILE)
        self.data = []

    def __getSchedule(self):
        txheaders = {'User-agent' : USERAGENT}
        data = None
        req = urllib2.Request(self.grid,data,txheaders)
        try:
            fp = urllib2.urlopen(req)
            return fp
        except urllib2.HTTPError:
            raise MLBUrlError

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
            gameinfo[id]['content'] = self.parseMediaGrid(node,away,home)
            #raise Exception,repr(gameinfo[id]['content'])
            out.append(gameinfo[id])
        #raise Exception,repr(out)
        return out

    def parseMediaGrid(self,xp,away,home):
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
                   content['audio'].append(out)
           elif tmp['type'] in ('mlbtv_national', 'mlbtv_home', 'mlbtv_away'):
               if tmp['playback_scenario'] in \
                     ( 'HTTP_CLOUD_WIRED', 'HTTP_CLOUD_WIRED_WEB', 'FMS_CLOUD'):
                   # candidate for new procedure: determine whether game is 
                   # national blackout
                   try:
                       tmp['blackout']
                   except:
                       tmp['blackout'] = ""
                   nb_pat = re.compile(r'MLB_NATIONAL_BLACKOUT')
                   if re.search(nb_pat,tmp['blackout']) is not None:
                       content['blackout'] = 'MLB_NATIONAL_BLACKOUT'
                   else:
                       content['blackout'] = None

                   # candidate for new procedure: determine the coverage
                   if tmp['type'] == 'mlbtv_national':
                       coverage = '0'
                   elif tmp['type'] == 'mlbtv_away':
                       coverage = away
                   else:
                       coverage = home

                   # each listing is a tuple of display, coverage, content id
                   # and event-id
                   out = (tmp['display'], coverage, tmp['id'], event_id)

                   # determine where to store this tuple - trimList will 
                   # return only the listings for a given speed/stream type
                   if tmp['playback_scenario'] == 'HTTP_CLOUD_WIRED':
                       if not self.use_wired_web:
                           content['video']['swarm'].append(out)
                   elif tmp['playback_scenario'] == 'HTTP_CLOUD_WIRED_WEB':
                       if self.use_wired_web:
                           content['video']['swarm'].append(out)
                   elif tmp['playback_scenario'] == 'FMS_CLOUD':
                       for s in ('300', '500', '1200', '1800', '2400'):
                           content['video'][s].append(out)
                   else:
                       continue
           elif tmp['type'] == 'condensed_game':
               out = ('CG',0,tmp['id'], event_id)
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
            raise MLBXmlError,detail

    def trimXmlList(self,blackout=()):
        # This is the XML version of trimList
        # easier to write a new method than adapt the old one
        if not self.data:
            raise MLBXmlError, "No games available today."
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
            dct['start_time'] = raw_time.strftime('%H:%M:%S')
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
            out.append((dct['gameid'], dct))
        return out

 
    def getCondensedVideo(self,gameid):
        listtime = datetime.datetime(self.year, self.month, self.day)
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
        url = self.grid.replace('grid.xml','gid_' + gid + '/media/highlights.xml')
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
        return out

    def getTopPlays(self,gameid):
        listtime = datetime.datetime(self.year, self.month, self.day)
        return self.getXmlTopPlays(gameid)

    def getListings(self, myspeed, blackout):
        listtime = datetime.datetime(self.year, self.month, self.day)
        return self.getXmlListings(myspeed, blackout)

    def getPreferred(self,available,cfg):
        prefer = {}
        media  = {}
        media['video'] = {}
        media['audio'] = {}
        home = available[0]['home']
	away = available[0]['away']
        homecode = TEAMCODES[home][0]
        awaycode = TEAMCODES[away][0]
        # build dictionary for home and away video
        for elem in available[2]:
            if homecode and homecode in elem[1]:
                media['video']['home'] = elem
            elif awaycode and awaycode in elem[1]:
                media['video']['away'] = elem
            else:
                # handle game of the week
                media['video']['home'] = elem
                media['video']['away'] = elem
        # same for audio
        for elem in available[3]:
            if homecode and homecode in elem[1]:
                media['audio']['home'] = elem
            elif awaycode and awaycode in elem[1]:
                media['audio']['away'] = elem
            else:
                # handle game of the week
                media['audio']['home'] = elem
                media['audio']['away'] = elem
        # now build dictionary based on coverage and follow settings
        for type in ('audio' , 'video'):
            follow='%s_follow'%type
            # if home is in follow and stream available, use it, elif away, else
            # None
            if home in cfg.get(follow):
                try:
                    prefer[type] = media[type]['home']
                except:
                    if media[type].has_key('away'):
                        prefer[type] = media[type]['away']
                    else:
                        prefer[type] = None
            # same logic reversed for away in follow
            elif away in cfg.get(follow):
                try:
                    prefer[type] = media[type]['away']
                except:
                    try:
                        prefer[type] = media[type]['home']
                    except:
                        prefer[type] = None
            # if home or away not in follow, prefer coverage, if present, then
            # try first available, else None
            else:
                try:
                    prefer[type] = media[type][cfg.get('coverage')]
                except:
                    try:
                        if type == 'video':
                            prefer[type] = available[2][0]
                        else:
                            prefer[type] = available[3][0]
                    except:
                        prefer[type] = None
        return prefer
 
    def Jump(self, ymd_tuple, myspeed, blackout):
        self.year = ymd_tuple[0]
        self.month = ymd_tuple[1]
        self.day = ymd_tuple[2]
        self.grid = "http://gdx.mlb.com/components/game/mlb/year_"\
            + padstr(self.year)\
            + "/month_" + padstr(self.month)\
            + "/day_" + padstr(self.day) + "/grid.xml"
        return self.getListings(myspeed, blackout)
           
    def Back(self, myspeed, blackout):
        t = datetime.datetime(self.year, self.month, self.day)
        dif = datetime.timedelta(1)
        t -= dif
        self.year = t.year
        self.month = t.month
        self.day = t.day
        self.grid = "http://gdx.mlb.com/components/game/mlb/year_"\
            + padstr(self.year)\
            + "/month_" + padstr(self.month)\
            + "/day_" + padstr(self.day) + "/grid.xml"
        #raise MLBXmlError
        return self.getListings(myspeed, blackout)

    def Forward(self, myspeed, blackout):
        t = datetime.datetime(self.year, self.month, self.day)
        dif = datetime.timedelta(1)
        t += dif
        self.year = t.year
        self.month = t.month
        self.day = t.day
        self.grid = "http://gdx.mlb.com/components/game/mlb/year_"\
            + padstr(self.year)\
            + "/month_" + padstr(self.month)\
            + "/day_" + padstr(self.day) + "/grid.xml"
        return self.getListings(myspeed, blackout)

    def getXmlListings(self, myspeed, blackout):
        self.getData()
        listings = self.trimXmlList(blackout)

        return [(elem[1]['teams'],\
                     elem[1]['event_time'],
                     elem[1]['video'][str(myspeed)],
                     elem[1]['audio'],
                     elem[1]['condensed'],
                     elem[1]['status'],
                     elem[0],
                     elem[1]['media_state'],
                     elem[1]['start_time'])\
                         for elem in listings]


    def parseInningsXml(self,event_id,use_nexdef):
	gameid, year, month, day = event_id.split('-')[1:5]
        url = 'http://mlb.mlb.com/mlb/mmls%s/%s.xml' % (year, gameid)
        self.log.write('parseInningsXml(): url = %s\n'%url)
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
        game = iptr.getElementsByTagName('game')[0]
        start_timecode = game.getAttribute('start_timecode')
        if use_nexdef:
            out.append((0,'true',start_timecode))
        for inning in iptr.getElementsByTagName('inningTimes'):
            number = inning.getAttribute('inning_number')
            is_top = inning.getAttribute('top')
            for inning_time in inning.getElementsByTagName('inningTime'):
                type = inning_time.getAttribute('type')
                if use_nexdef and type == 'SCAST':
                    time = inning_time.getAttribute('start')
                    out.append((number, is_top, time))
                elif use_nexdef == False and type == "FMS":
                    time = inning_time.getAttribute('start')
                    out.append((number, is_top, time))
        return out

    def getStartOfGame(self,listing,cfg):
        start_time = 0
        try:
            innings = self.parseInningsXml(listing[2][0][3],
                                              cfg.get('use_nexdef'))
        except:
            return None
        if listing[5] in ('I', 'D') and start_time == 0:
            if cfg.get('live_from_start') and cfg.get('use_nexdef'):
                if innings is not None:
                    for i in range(len(innings)):
                        if int(innings[i][0]) == 0:
                            start_time = innings[i][2]
                            continue
                        else:
                            start_time = 0
        else:
            if cfg.get('use_nexdef'):
                if innings is not None:
                    for i in range(len(innings)):
                        if int(innings[i][0]) == 0:
                            start_time = innings[i][2]
                            # hack to make sure mlbhls can start at the correct
                            # timestamp - add five seconds to published time
                            #d=datetime.datetime.strptime(start_time, "%H:%M:%S")
                            #t=datetime.timedelta(seconds=5)
                            #n=d+t
                            #start_time=n.strftime("%H:%M:%S")
                            continue
                else:
                    start_time=listing[8]

        return start_time

