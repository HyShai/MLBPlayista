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
        fp = urllib.urlopen(self.url)
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

    def trimTvList(self):
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
                    dct['event_time'] = elem['event_time']
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
                    for url in elem['mlbtv']['urls']:
                        dct[url['speed']] = url['url']['id']
                    out.append((elem['gameid'], dct))
        return out

    def getListings(self, myspeed, blackout):
        self.getData()
        listings = self.trimTvList()

        return  [(elem[1]['text'],elem[1]['event_time'],\
                      elem[1][str(myspeed)],\
                      (elem[1]['status'], "LB")[
                                  (elem[1]['home'] in blackout or
                                   elem[1]['away'] in blackout)\
                                      and elem[1]['status'] in ('I','W','P')
                                  ])\
                     for elem in listings]


class GameStream:
    def __init__(self,game_id, email, passwd, session_cookies=None):
        self.id = game_id
        self.email = email
        self.passwd = passwd
        self.session_cookies = session_cookies
    
    def __getInfo(self):
        # Make the workflow url
        url = "http://www.mlb.com/enterworkflow.do?" +\
            "flowId=media.media&keepWfParams=true&mediaId=" +\
            str(self.id) + "&catCode=mlb_lg&av=v"
        # Some preliminary setup...
        if not self.session_cookies:
            self.session_cookies = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.session_cookies))
        urllib2.install_opener(opener)
        # Open the workflow url...
        fp = urllib2.urlopen(url)

        if 'mp_login' in fp.url:
            forms = ClientForm.ParseResponse(fp, backwards_compat=False)
            fp.close()
    
            # Now set up the login info
            form = forms[0]
            form["emailAddress"]  = self.email
            form["password"] = self.passwd
            # And submit
            fp = urllib2.urlopen(form.click())
        
        data = fp.read()
        fp.close()
        return data

    def logout(self):
        """Logs out from the mlb.com session. Meant to prevent
        multiple login errors."""
        if not self.session_cookies:
            self.session_cookies = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.session_cookies))
        urllib2.install_opener(opener)
        LOGOUT_URL="https://secure.mlb.com/enterworkflow.do?flowId=registration.logout&c_id=mlb"
        urllib2.urlopen(LOGOUT_URL)


    def url(self):
        # url_pattern
        pattern = re.compile(r'(url:.*\")(mms:\/\/[^ ]*)(".*)')
        game_url = re.search(pattern, self.__getInfo()).groups()[1]
        return game_url

    def urlDebug(self):
        # url_pattern
        pattern = re.compile(r'(url:.*\")(mms:\/\/[^ ]*)(".*)')
        game_info = self.__getInfo()
        try:
            game_url = re.search(pattern, game_info).groups()[1]
        except:
            self.logout()
            raise Exception, game_info
        return game_url




