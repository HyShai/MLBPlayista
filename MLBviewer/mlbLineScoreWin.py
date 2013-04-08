#!/usr/bin/env python

import curses
import curses.textpad
import time
from mlbListWin import MLBListWin
from mlbConstants import *

class MLBLineScoreWin(MLBListWin):

    def __init__(self,myscr,mycfg,data):
        self.data = data
        # data is everything, records is only what's visible
        self.records = []
        self.mycfg = mycfg
        self.myscr = myscr
        self.current_cursor = 0
        self.statuswin = curses.newwin(1,curses.COLS-1,curses.LINES-1,0)
        self.titlewin = curses.newwin(2,curses.COLS-1,0,0)

    # no navigation key support yet
    def Up(self):
        return
    
    def Down(self):
        return
    
    def PgUp(self):
        return

    def PgDown(self):
        return
    
    def Refresh(self):
        if len(self.data) == 0:
            self.titlewin.refresh()
            self.myscr.refresh()
            self.statuswin.refresh()
            return

        self.myscr.clear()
        self.records = []
        self.prepareLineScoreFrames()
        self.prepareActionLines()
        self.prepareHrLine()
        n = 2
        for s in self.records:
            self.myscr.addstr(n,0,s)
            n+=1

        self.myscr.refresh()

    def titleRefresh(self,mysched):
        if len(self.data) == 0:
            titlestr = "NO LINE SCORE AVAILABLE FOR THIS GAME"
        else:
            titlestr = "LINE SCORE FOR  " +\
                self.data['game']['id'] +\
                ' (' +\
                str(mysched.month) + '/' +\
                str(mysched.day) + '/' +\
                str(mysched.year) + ' ' +\
                ')'

        padding = curses.COLS - (len(titlestr) + 6)
        titlestr += ' '*padding
        pos = curses.COLS - 6
        self.titlewin.addstr(0,0,titlestr)
        self.titlewin.addstr(0,pos,'H', curses.A_BOLD)
        self.titlewin.addstr(0,pos+1, 'elp')
        self.titlewin.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)
        self.titlewin.refresh()

    def statusRefresh(self):
        n = self.current_cursor

        status_str = 'Press L to return to listings...'

        # And write the status
        try:
            self.statuswin.addstr(0,0,status_str,curses.A_BOLD)
        except:
            rows = curses.LINES
            cols = curses.COLS
            slen = len(status_str)
            raise Exception,'(' + str(slen) + '/' + str(cols) + ',' + str(n) + '/' + str(rows) + ') ' + status_str
        self.statuswin.refresh()

    # adds the line score frames to self.records
    def prepareLineScoreFrames(self):
        status = self.data['game']['status']
        if status in ( 'In Progress', ):
            status_str = "%s %s" % ( self.data['game']['inning_state'] ,
                                     self.data['game']['inning'] )
        elif status in ( 'Final', 'Game Over' ):
            status_str = status
            # handle extra innings
            if self.data['game']['inning'] != '9':
                status_str += "/%s" % self.data['game']['inning']
        else:
            status_str = status
        self.records.append(status_str)
        # insert blank line before header row
        self.records.append("")
        
        # now for the frames - could fix it to 32 or leave it 'variable' for
        # now...
        team_strlen = 32
        team_sfmt = '%-' + '%s' % team_strlen + 's'

        # header string has inning numbers and R H E headers
        header_str = team_sfmt % ( ' '*team_strlen )
        # TODO: fixing it to 9 innings until we figure a better way to handle
        # extras
        for i in range(1,10):
            header_str += "%3s" % str(i)
        header_str += "%2s%3s%3s%3s" % ( "", "R", "H", "E" )
        self.records.append(header_str)
    
        # now to fill out the actual frames
        for team in ( 'away', 'home' ):
            team_str = TEAMCODES[self.data['game']['%s'%team+"_file_code"]][1]
            team_str += " (%s-%s)" %\
                ( self.data['game']["%s_win"%team], 
                  self.data['game']["%s_loss"%team] )
            s = team_sfmt % team_str
            for inn in range(1,10):
                if self.data['innings'].has_key(str(inn)):
                    if self.data['innings'][str(inn)].has_key(team):
                        if self.data['innings'][str(inn)][team] == "" and \
                                                                   inn == 9:
                            if team == "home" and status in ('Game Over',
                                                             'Final' ):
                                # all of this just to fill in the bot 9 home win
                                    s+= "%3s" % "X"
                            else:
                                # not game over yet, print empty frame
                                s += "%3s" % (' '*3)
                        else:
                            s += "%3s" % self.data['innings'][str(inn)][team]
                    else:
                        s += "%3s" % (' '*3)
                else:
                    s += "%3s" % (' '*3)
            try:
                s += "%2s%3s%3s%3s" % ( " "*2, 
                                       self.data['game']["%s_team_runs"%team],
                                       self.data['game']["%s_team_hits"%team],
                                       self.data['game']["%s_team_errors"%team])
            except:
                s += '%2s%3s%3s%3s' % ( '', '0', '0', '0' )
            self.records.append(s)
        # insert a blank line before win/loss, currents, or probables
        self.records.append("")

    # this will contain:
    #     for in progress games, current pitcher, hitter, on base status, outs
    #         the count and eventually home runs
    #     for final and game over, display winning/losing/save pitchers, and 
    #         eventually home runs
    #     for future games, print the probable pitchers
    def prepareActionLines(self):
        status = self.data['game']['status']
        if status in ( 'In Progress', ):
            self.prepareActionInProgress()
        elif status in ( 'Final', 'Game Over', 'Completed Early' ):
            self.prepareActionFinal()
        elif status in ( 'Preview', 'Pre-Game', 'Warmup' ):
            self.prepareActionPreview()
        else:
            raise Exception,status

    def prepareActionInProgress(self):
        status = self.data['game']['status']
        if self.data['game']['inning_state'] == 'Top':
            ( pteam, bteam ) = ( 'home', 'away' )
        else:
            ( pteam, bteam ) = ( 'away', 'home' )
        s = "Pitching: %s (%s); Batting: %s (%s)" % \
            ( self.data['pitchers']['current_pitcher'][1],
              self.data['game']["%s"%pteam+"_file_code"].upper(),
              self.data['pitchers']['current_batter'][1],
              self.data['game']["%s"%bteam+"_file_code"].upper() )
        self.records.append(s)
        self.records.append("")
        s = "Runners on base: " +\
            RUNNERS_ONBASE_STATUS[self.data['game']['runner_on_base_status']]
        self.records.append(s)
        s = "%s-%s, %s outs" % \
            ( self.data['game']['balls'], self.data['game']['strikes'],
              self.data['game']['outs'] )
        self.records.append(s)

    def prepareActionFinal(self):
        wp_str = "W: %s (%s-%s %s)" %\
            ( self.data['pitchers']['winning_pitcher'][1],
              self.data['pitchers']['winning_pitcher'][2],
              self.data['pitchers']['winning_pitcher'][3],
              self.data['pitchers']['winning_pitcher'][4] )
        lp_str = "L: %s (%s-%s %s)" %\
            ( self.data['pitchers']['losing_pitcher'][1],
              self.data['pitchers']['losing_pitcher'][2],
              self.data['pitchers']['losing_pitcher'][3],
              self.data['pitchers']['losing_pitcher'][4] )
        s = "%-35s%-35s" % ( wp_str, lp_str )
        self.records.append(s)
        if self.data['pitchers']['save_pitcher'][0] != "":
            self.records.append("SV: %s (%s)" %\
                ( self.data['pitchers']['save_pitcher'][1],
                  self.data['pitchers']['save_pitcher'][5] ) )

    def prepareActionPreview(self):
        hp_str = '%3s: %s (%s-%s %s)' %\
            ( self.data['game']['home_file_code'].upper(),
              self.data['pitchers']['home_probable_pitcher'][1],
              self.data['pitchers']['home_probable_pitcher'][2],
              self.data['pitchers']['home_probable_pitcher'][3],
              self.data['pitchers']['home_probable_pitcher'][4] )
        ap_str = '%3s: %s (%s-%s %s)' %\
            ( self.data['game']['away_file_code'].upper(),
              self.data['pitchers']['away_probable_pitcher'][1],
              self.data['pitchers']['away_probable_pitcher'][2],
              self.data['pitchers']['away_probable_pitcher'][3],
              self.data['pitchers']['away_probable_pitcher'][4] )
        self.records.append("Probables: %s" % ap_str)
        self.records.append("%11s" % (' '*11) + hp_str)

    def prepareHrLine(self):
        if not self.data.has_key('hr'):
            return
        ( away , home ) = ( self.data['game']['away_file_code'].upper(),
                            self.data['game']['home_file_code'].upper() )
        # start with a blank line before
        self.records.append("")
        self.records.append("HR:")
        for team in ( away, home ):
            s = ""
            if not self.data['hr'].has_key(team):
                continue
            s += "%3s: " % team
            for player in self.data['hr'][team]:
                hr = len(self.data['hr'][team][player])
                if hr > 1:
                    hr_str = "%s %s (%s), " %\
                        ( self.data['hr'][team][player][hr][1],
                          str(hr),
                          self.data['hr'][team][player][hr][4] )
                else:
                    hr_str = "%s (%s), " %\
                        ( self.data['hr'][team][player][hr][1],
                          self.data['hr'][team][player][hr][4] )
                if len(s) + len(hr_str) < curses.COLS-1:
                    s += hr_str
                else:
                    # start a new line
                    self.records.append(s)
                    s = hr_str
            self.records.append(s.strip(", "))


