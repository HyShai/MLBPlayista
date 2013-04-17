#!/usr/bin/env

from mlbConstants import *
from mlbListWin import MLBListWin
from mlbMasterScoreboard import MLBMasterScoreboard
from mlbSchedule import gameTimeConvert
import datetime
import curses

class MLBMasterScoreboardWin(MLBListWin):

    def __init__(self,myscr,mycfg,gid):
        self.myscr = myscr
        self.mycfg = mycfg
        # any gid will do
        # TODO: Change from gid to datetime, e.g. mysched.data[0][1]
        #( self.year, self.month, self.day ) = mysched.data[0][1]
        self.gameid = gid
        self.gameid = self.gameid.replace('/','_')
        self.gameid = self.gameid.replace('-','_')
        ( year, month, day ) = self.gameid.split('_')[:3]
        self.statuswin = curses.newwin(1,curses.COLS-1,curses.LINES-1,0)
        self.titlewin = curses.newwin(2,curses.COLS-1,0,0)
        self.data = []
        self.scoreboard = MLBMasterScoreboard(gid)
        self.sb = self.scoreboard.getScoreboardData()
        self.parseScoreboardData()
        wlen = curses.LINES-4
        if wlen % 2 > 0:
            wlen -= 1
        self.records = self.data[:wlen]
        self.game_cursor = 0
        self.current_cursor = 0
        self.record_cursor = 0

    def parseScoreboardData(self):
        for game in self.sb:
            gid = game.keys()[0]
            status = game[gid]['status']
            if status in ( 'In Progress', 'Delayed' ):
                self.parseInGameData(game)
            elif status in ( 'Game Over' , 'Final', 'Completed Early' ):
                self.parseFinalGameData(game)
            elif status in ( 'Preview', 'Pre-Game', 'Warmup', 'Delayed Start' ):
                self.parsePreviewGameData(game)
            elif status in ( 'Postponed' ):
                self.parsePostponedGameData(game)
            else:
                raise Exception,"What to do with this status? "+status


    def parseInGameData(self,game):
        gid = game.keys()[0]
        status = game[gid]['status']
        if game[gid]['top_inning'] == 'Y':
            away_str = ' B: %s; OD: %s; Bases: %s' % \
                ( game[gid]['in_game']['batter']['name_display_roster'],
                  game[gid]['in_game']['ondeck']['name_display_roster'],
                  RUNNERS_ONBASE_STATUS[game[gid]['in_game']['runners_on_base']['status']])
            home_str = ' P: %s; %s-%s, %s outs' % \
                ( game[gid]['in_game']['pitcher']['name_display_roster'],
                  game[gid]['b'], game[gid]['s'], game[gid]['o'] )
        else:
            home_str = ' B: %s; OD: %s; Bases: %s' % \
                ( game[gid]['in_game']['batter']['name_display_roster'],
                  game[gid]['in_game']['ondeck']['name_display_roster'],
                  RUNNERS_ONBASE_STATUS[game[gid]['in_game']['runners_on_base']['status']])
            away_str = ' P: %s; %s-%s, %s outs' % \
                ( game[gid]['in_game']['pitcher']['name_display_roster'],
                  game[gid]['b'], game[gid]['s'], game[gid]['o'] )
        if status in ( 'Delayed', ):
            inning_str = 'Delayed'
        else:
            inning_str = '%s %s' % ( game[gid]['inning_state'],
                                     game[gid]['inning'] )
        self.data.append("%-13s %3s %3s%3s%3s %s" % \
                ( inning_str, game[gid]['away_file_code'].upper(),
                  game[gid]['totals']['r']['away'],
                  game[gid]['totals']['h']['away'],
                  game[gid]['totals']['e']['away'],
                  away_str ) )
        if status in ( 'Delayed', ):
            home_pad = '%s %s' % ( game[gid]['inning_state'],
                                   game[gid]['inning'] )
        else:
            home_pad = ' '*13
        self.data.append("%-13s %3s %3s%3s%3s %s" % \
                ( home_pad, game[gid]['home_file_code'].upper(),
                  game[gid]['totals']['r']['home'],
                  game[gid]['totals']['h']['home'],
                  game[gid]['totals']['e']['home'],
                  home_str ) )


 
    def parsePreviewGameData(self,game):
        gid = game.keys()[0]
        status = game[gid]['status']
        status_str = status
        gametime=game[gid]['time']
        ampm=game[gid]['ampm']
        gt = datetime.datetime.strptime('%s %s'%(gametime, ampm),'%I:%M %p')
        lt = gameTimeConvert(gt)
        time_str = lt.strftime('%I:%M %p')
        away_str = ' AP: %s (%s-%s %s)' % \
                   ( game[gid]['pitchers']['away_probable_pitcher'][1],
                     game[gid]['pitchers']['away_probable_pitcher'][2],
                     game[gid]['pitchers']['away_probable_pitcher'][3],
                     game[gid]['pitchers']['away_probable_pitcher'][4] )
        home_str = ' HP: %s (%s-%s %s)' % \
                   ( game[gid]['pitchers']['home_probable_pitcher'][1],
                     game[gid]['pitchers']['home_probable_pitcher'][2],
                     game[gid]['pitchers']['home_probable_pitcher'][3],
                     game[gid]['pitchers']['home_probable_pitcher'][4] )
        self.data.append("%-13s %3s %3s%3s%3s %s" % \
                ( status_str, game[gid]['away_file_code'].upper(),
                  0,
                  0,
                  0,
                  away_str ) )
        self.data.append("%-13s %3s %3s%3s%3s %s" % \
                ( time_str, game[gid]['home_file_code'].upper(),
                  0,
                  0,
                  0,
                  home_str ) )

    def parsePostponedGameData(self,game):
        gid = game.keys()[0]
        status = game[gid]['status']
        status_str = status
        self.data.append("%-13s %3s %3s%3s%3s" %
                ( status_str, game[gid]['away_file_code'].upper(),
                  0,
                  0,
                  0 ) )
        self.data.append("%-13s %3s %3s%3s%3s" % \
                ( (' '*13), game[gid]['home_file_code'].upper(),
                  0,
                  0,
                  0 ) )


    def parseFinalGameData(self,game):
        gid = game.keys()[0]
        status = game[gid]['status']
        status_str = status
        if int(game[gid]['inning']) != 9:
            status_str += '/%s' % game[gid]['inning']
        if game[gid]['totals']['r']['away'] > game[gid]['totals']['r']['home']:
            away_str = ' WP: %s (%s-%s %s)' % \
                       ( game[gid]['pitchers']['winning_pitcher'][1],
                         game[gid]['pitchers']['winning_pitcher'][2],
                         game[gid]['pitchers']['winning_pitcher'][3],
                         game[gid]['pitchers']['winning_pitcher'][4] )
            if game[gid]['pitchers']['save_pitcher'][0] != "":
                away_str += '; SV: %s (%s)' % \
                       ( game[gid]['pitchers']['save_pitcher'][1],
                         game[gid]['pitchers']['save_pitcher'][5] )
            home_str = ' LP: %s (%s-%s %s)' % \
                       ( game[gid]['pitchers']['losing_pitcher'][1],
                         game[gid]['pitchers']['losing_pitcher'][2],
                         game[gid]['pitchers']['losing_pitcher'][3],
                         game[gid]['pitchers']['losing_pitcher'][4] )
        else:
            away_str = ' LP: %s (%s-%s %s)' % \
                       ( game[gid]['pitchers']['losing_pitcher'][1],
                         game[gid]['pitchers']['losing_pitcher'][2],
                         game[gid]['pitchers']['losing_pitcher'][3],
                         game[gid]['pitchers']['losing_pitcher'][4] )
            home_str = ' WP: %s (%s-%s %s)' % \
                       ( game[gid]['pitchers']['winning_pitcher'][1],
                         game[gid]['pitchers']['winning_pitcher'][2],
                         game[gid]['pitchers']['winning_pitcher'][3],
                         game[gid]['pitchers']['winning_pitcher'][4] )
            if game[gid]['pitchers']['save_pitcher'][0] != "":
                home_str += '; SV: %s (%s)' % \
                       ( game[gid]['pitchers']['save_pitcher'][1],
                         game[gid]['pitchers']['save_pitcher'][5] )
        self.data.append("%-13s %3s %3s%3s%3s %s" % \
                ( status_str, game[gid]['away_file_code'].upper(),
                  game[gid]['totals']['r']['away'],
                  game[gid]['totals']['h']['away'],
                  game[gid]['totals']['e']['away'],
                  away_str ) )
        self.data.append("%-13s %3s %3s%3s%3s %s" % \
                ( (' '*13), game[gid]['home_file_code'].upper(),
                  game[gid]['totals']['r']['home'],
                  game[gid]['totals']['h']['home'],
                  game[gid]['totals']['e']['home'],
                  home_str ) )

    def Up(self):
        if self.current_cursor - 2 < 0 and self.record_cursor - 2 > 0:
            self.current_cursor = curses.LINES-4-2
            if self.record_cursor - curses.LINES -4 < 0:
                self.record_cursor = 0
            else:
                self.record_cursor -= curses.LINES-4
                if self.record_cursor % 2 > 0:
                    self.record_cursor -= 1
            self.records = self.data[self.record_cursor:self.record_cursor+curses.LINES-4]
        elif self.current_cursor > 0:
            self.current_cursor -= 2

    def Down(self):
        if self.current_cursor + 2 >= len(self.records) and\
           self.record_cursor + self.current_cursor + 2 < len(self.data):
            self.record_cursor += self.current_cursor + 2
            self.current_cursor = 0
            if self.record_cursor + curses.LINES - 4 % 2 > 0:
                self.records = self.data[self.record_cursor:self.record_cursor+curses.LINES-3]
            else:
                self.records = self.data[self.record_cursor:self.record_cursor+curses.LINES-3]
        # Elif not at bottom of window
        elif self.current_cursor + 2 < self.records  and\
             self.current_cursor + 2  < curses.LINES-4:
            if self.current_cursor + 2 + self.record_cursor < len(self.data):
                self.current_cursor += 2
        # Silent else do nothing at bottom of window and bottom of records


    def Refresh(self):

        self.myscr.clear()
        # display even number of lines since games will be two lines
        wlen = curses.LINES-4
        if wlen % 2 > 0:
            wlen -= 1
        for n in range(wlen):
            if n < len(self.records):
                s = self.records[n]
                cursesflags = 0
                game_cursor = ( n + self.record_cursor ) / 2
                gid = self.sb[game_cursor].keys()[0]
                status = self.sb[game_cursor][gid]['status']
                if n % 2 > 0:
                    # second line of the game, underline it for division
                    # between games
                    pad = curses.COLS -1 - len(self.records[n])
                    s += ' '*pad
                    if n - 1 == self.current_cursor:
                        cursesflags |= curses.A_UNDERLINE|curses.A_REVERSE
                    else:
                        cursesflags = curses.A_UNDERLINE
                    if status in ( 'In Progress', ):
                        cursesflags |= cursesflags | curses.A_BOLD
                else:
                    pad = curses.COLS -1 - len(self.records[n])
                    s += ' '*pad
                    if n == self.current_cursor:
                        cursesflags |= curses.A_REVERSE
                    else:
                        cursesflags = 0
                    if status in ( 'In Progress', ):
                        cursesflags |= cursesflags | curses.A_BOLD
                self.myscr.addstr(n+2,0,s,cursesflags)
            else:
                s = ' '*(curses.COLS-1)
                self.myscr.addstr(n+2,0,s)
        self.myscr.refresh()
                
    def titleRefresh(self,mysched):
        titlestr = "MASTER SCOREBOARD VIEW FOR " +\
                str(mysched.month) + '/' +\
                str(mysched.day) + '/' +\
                str(mysched.year)
                # TODO: '(Use arrow keys to change days)'

        padding = curses.COLS - (len(titlestr) + 6)
        titlestr += ' '*padding
        pos = curses.COLS - 6
        self.titlewin.addstr(0,0,titlestr)
        self.titlewin.addstr(0,pos,'H', curses.A_BOLD)
        self.titlewin.addstr(0,pos+1, 'elp')
        self.titlewin.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)
        self.titlewin.refresh()

    def statusRefresh(self):
        game_cursor = ( self.current_cursor + self.record_cursor ) / 2
        gid = self.sb[game_cursor].keys()[0]
        status = self.sb[game_cursor][gid]['status']
        status_str = 'Status: %s' % status
        speedstr = SPEEDTOGGLE.get(self.mycfg.get('speed'))
        hdstr = SSTOGGLE.get(self.mycfg.get('adaptive_stream'))
        coveragestr = COVERAGETOGGLE.get(self.mycfg.get('coverage'))
        status_str_len = len(status_str) +\
                            + len(speedstr) + len(hdstr) + len(coveragestr) + 2
        if self.mycfg.get('debug'):
            status_str_len += len('[DEBUG]')
        padding = curses.COLS - status_str_len
        # shrink the status string to fit if it is too many chars wide for
        # screen
        if padding < 0:
            status_str=status_str[:padding]
        if self.mycfg.get('debug'):
            debug_str = '[DEBUG]'
        else:
            debug_str = ''
        if self.mycfg.get('use_nexdef'):
            speedstr = '[NEXDF]'
        else:
            hdstr = SSTOGGLE.get(False)
        status_str += ' '*padding + debug_str +  coveragestr + speedstr + hdstr

        self.statuswin.addstr(0,0,status_str,curses.A_BOLD)
        self.statuswin.refresh()
