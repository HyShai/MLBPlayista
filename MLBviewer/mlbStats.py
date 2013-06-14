#!/usr/bin/env python

import json
import urllib2
import datetime
import httplib

from mlbError import *

class MLBStats:

    def __init__(self):
        self.data = []
        self.last_update = ""
        self.date = datetime.datetime.now()
        self.type = 'batting'
        self.sort = 'avg'

    def getStatsData(self,statType='pitching',sortColumn='era'):
        self.url = 'http://mlb.mlb.com/pubajax/wf/flow/stats.splayer?page_type=SortablePlayer&game_type=%27R%27&player_pool=QUALIFIER&season_type=ANY&sport_code=%27mlb%27&results=1000&recSP=1&recPP=50'
        # TODO: This is how league is done.  Need to parameterize it.
        #self.url += '&league_code=%27NL%27'
        self.type = statType
        self.sort = sortColumn
        self.url += '&stat_type=%s&sort_column=%%27%s%%27' % (statType,
                                                              sortColumn)
        self.url += '&season=%s' %  self.date.year 
        if sortColumn in ( 'era', ):
            self.url += '&sort_order=%27asc%27'
        else:
            self.url += '&sort_order=%27desc%27'
        request = urllib2.Request(self.url)
        request.add_header('Referer','http://mlb.com')
        opener = urllib2.build_opener()
        try:
            f = opener.open(request)
        except urllib2.URLError:
            self.error_str = "UrlError: Could not retrieve statistics"
            raise MLBUrlError,self.url
        try:
            self.json = json.loads(f.read())
        except:
            raise Exception,MLBJsonError
        self.data = self.parseStats(statType,sortColumn)

    def parseStats(self,statType='hitting',sortColumn='avg'):
        out = []
        self.last_update = self.json['stats_sortable_player']['queryResults']['created'] + '-04:00'
        for player in self.json['stats_sortable_player']['queryResults']['row']:
            out.append(player)
        return out
