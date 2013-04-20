#!/usr/bin/env python

import urllib2, httplib
import StringIO
import gzip
from xml.dom.minidom import parseString

class MLBStandings:

    def __init__(self):
        self.data = []
        self.xml = ""
        self.url = 'https://erikberg.com/mlb/standings.xml'

        # some decoder strings from sportsML to plain-text
        self.DIVISIONS={
            'MLB.AL.E':  'AL East',
            'MLB.AL.C':  'AL Central',
            'MLB.AL.W':  'AL West',
            'MLB.NL.E':  'NL East',
            'MLB.NL.C':  'NL Central',
            'MLB.NL.W':  'NL West',
        }

    def getDataFromFile(self):
        # For development purposes, let's parse from a file (activate web
        # code later)
        f = open('standings.xml')
        self.xml = f.read()
        f.close()

    def getStandingsData(self,offline=True):
        # To limit test requests until permission has been obtained
        # from data provider
        if offline:
            print "Offline is True, using local file"
            self.getDataFromFile()
            self.parseStandingsXml()
            return
        #print "Offline is False, requesting from network"
        request = urllib2.Request(self.url)
        request.add_header('Accept-encoding', 'gzip')
        request.add_header('User-agent', 'mlbviewer/2013sf3 https://sourceforge.net/projects/mlbviewer/   (straycat000@yahoo.com)')
        opener = urllib2.build_opener()
        f = opener.open(request)
        compressedData = f.read()
        compressedStream = StringIO.StringIO(compressedData)
        gzipper = gzip.GzipFile(fileobj=compressedStream)
        self.xml = gzipper.read()
        self.parseStandingsXml()

    def parseStandingsXml(self):
        xp = parseString(self.xml)
        for metadata in xp.getElementsByTagName('sports-metadata'):
            self.last_update = metadata.getAttribute('date-time')
        for standing in xp.getElementsByTagName('standing'):
            for div in standing.getElementsByTagName('sports-content-code'):
                type=div.getAttribute('code-type')
                if type == "division":
                    key = div.getAttribute('code-key')
                    division = self.DIVISIONS[key] 
            self.data.append((division,self.parseDivisionData(standing)))

    def parseDivisionData(self,xp):
        out = []
        for tptr in xp.getElementsByTagName('team'):
            out.append(self.parseTeamData(tptr))
        return out


    def parseTeamData(self,tptr):
        tmp = dict()
        for name in tptr.getElementsByTagName('name'):
            tmp['first'] = name.getAttribute('first')
            tmp['last']  = name.getAttribute('last')
        for teamStats in tptr.getElementsByTagName('team-stats'):
            tmp['G'] = teamStats.getAttribute('events-played')
            tmp['GB'] = teamStats.getAttribute('games-back')
            for totals in teamStats.getElementsByTagName('outcome-totals'):
                scope = totals.getAttribute('alignment-scope')
                if scope == "events-all":
                    tmp['W'] = totals.getAttribute('wins')
                    tmp['L'] = totals.getAttribute('losses')
                    tmp['WP'] = totals.getAttribute('winning-percentage')
                    streak = totals.getAttribute('streak-type')
                    if streak == 'win':
                        tmp['STRK'] = 'W'
                    else:
                        tmp['STRK'] = 'L'
                    tmp['STRK'] += str(totals.getAttribute('streak-total'))
                    tmp['RS'] = totals.getAttribute('points-scored-for')
                    tmp['RA'] = totals.getAttribute('points-scored-against')
                elif scope == "events-home":
                    tmp['HW'] = totals.getAttribute('wins')
                    tmp['HL'] = totals.getAttribute('losses')
                elif scope == "events-away":
                    tmp['AW'] = totals.getAttribute('wins')
                    tmp['AL'] = totals.getAttribute('losses')
                elif scope == "":
                    scope = totals.getAttribute('duration-scope')
                    if scope == 'events-most-recent-5':
                        tmp['L5_W'] = totals.getAttribute('wins')
                        tmp['L5_L'] = totals.getAttribute('losses')
                    elif scope == 'events-most-recent-10':
                        tmp['L10_W'] = totals.getAttribute('wins')
                        tmp['L10_L'] = totals.getAttribute('losses')
        return tmp
                        
                    

                
