#!/usr/bin/env python

from mlbStandings import MLBStandings

s=MLBStandings()
s.getStandingsData(offline=True)

longest=0
for standing in s.data:
    division = standing[0]
    standings = standing[1]
    print ""
    print division
    print "%-14s %5s %5s %5s %5s %5s %5s %5s %5s" % \
                                 ('Team', 'W', 'L', 'WP', 'GB','L10', 'STRK',
                                  'HOME', 'ROAD' )
    for team in standings:
        #tlen=len(team['first']+' '+team['last'])
        tlen=len(team['first'])
        if tlen > longest:
            longest=tlen
        print "%-14s %5s %5s %5s %5s %5s %5s %5s %5s" % \
                                 (team['first'],
                                  team['W'], team['L'], team['WP'], 
                                  team['GB'],
                                  team['L10_W']+ '-' +team['L10_L'],
                                  team['STRK'],
                                  team['HW']+'-'+team['HL'],
                                  team['AW']+'-'+team['AL'])
print ""
print "Last updated: %s" % s.last_update
