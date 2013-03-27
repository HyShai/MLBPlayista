#!/usr/bin/env python

import curses
import curses.textpad
import datetime
import re
import select
import sys
import time
from MLBviewer import *

def doinstall(config,dct,dir=None):
    print "Creating configuration files"
    if dir:
        try:
            os.mkdir(dir)
        except:
            print 'Could not create directory: ' + dir + '\n'
            print 'See README for configuration instructions\n'
            sys.exit()
    # now write the config file
    try:
        fp = open(config,'w')
    except:
        print 'Could not write config file: ' + config
        print 'Please check directory permissions.'
        sys.exit()
    fp.write('# See README for explanation of these settings.\n')
    fp.write('# user and pass are required except for Top Plays\n')
    fp.write('user=\n')
    fp.write('pass=\n\n')
    for k in dct.keys():
        if type(dct[k]) == type(list()):
            if len(dct[k]) > 0:
                for item in dct[k]:
                    fp.write(k + '=' + str(dct[k]) + '\n')
                fp.write('\n')
            else:
                fp.write(k + '=' + '\n\n')
        else:
            fp.write(k + '=' + str(dct[k]) + '\n\n')
    fp.close()
    print
    print 'Configuration complete!  You are now ready to use mlbviewer.'
    print
    print 'Configuration file written to: '
    print
    print config
    print
    print 'Please review the settings.  You will need to set user and pass.'
    sys.exit()

def prompter(win,prompt):
    win.clear()
    win.addstr(0,0,prompt,curses.A_BOLD)
    win.refresh()

    responsewin = win.derwin(0, len(prompt))
    responsebox = curses.textpad.Textbox(responsewin)
    responsebox.edit()
    output = responsebox.gather()

    return output

def mainloop(myscr,mycfg):

    # some initialization
    log = open(LOGFILE, "a")
    DISABLED_FEATURES = []
    CURRENT_SCREEN = 'listings'
    RESTORE_SPEED = mycfg.get('speed')

    # not sure if we need this for remote displays but couldn't hurt
    if mycfg.get('x_display'):
        os.environ['DISPLAY'] = mycfg.get('x_display')

    try:
        curses.curs_set(0)
    except curses.error:
        pass

    # initialize the color settings
    if hasattr(curses, 'use_default_colors'):
        try:
            curses.use_default_colors()
            if mycfg.get('use_color'):
                try:
                    if mycfg.get('fg_color'):
                        mycfg.set('favorite_color', mycfg.get('fg_color'))
                    curses.init_pair(1, COLORS[mycfg.get('favorite_color')],
                                        COLORS[mycfg.get('bg_color')])
                except KeyError:
                    mycfg.set('use_color', False)
                    curses.init_pair(1, -1, -1)
        except curses.error:
            pass

    # initialize the input
    inputlst = [sys.stdin]

    available = []
    listwin = MLBListWin(myscr,mycfg,available)
    topwin = MLBTopWin(myscr,mycfg,available)
    mywin = listwin
    mywin.Splash()
    mywin.statusWrite('Logging into mlb.com...',wait=0)
    
    session = MLBSession(user=mycfg.get('user'),passwd=mycfg.get('pass'),
                         debug=mycfg.get('debug'))
    try:
        session.getSessionData()
    except MLBAuthError:
        error_str = 'Login was unsuccessful.  Check user and pass in ' + myconf
        mywin.statusWrite(error_str,wait=2)
    except Exception,detail:
        error_str = str(detail)
        mywin.statusWrite(detail,wait=2)

    mycfg.set('cookies', {})
    mycfg.set('cookies', session.cookies)
    mycfg.set('cookie_jar' , session.cookie_jar)
    try:
        log.write('session-key from cookie file: '+session.cookies['ftmu'] +\
                  '\n')
    except:
        log.write('no session-key found in cookie file\n')

    # Listings
    mysched = MLBSchedule(ymd_tuple=startdate,
                          time_shift=mycfg.get('time_offset'),
                          use_wired_web=mycfg.get('use_wired_web'))
    # We'll make a note of the date, to return to it later.
    today_year = mysched.year
    today_month = mysched.month
    today_day = mysched.day

    try:
        available = mysched.getListings(mycfg.get('speed'),
                                        mycfg.get('blackout'))
    except (KeyError, MLBXmlError), detail:
        if mycfg.get('debug'):
            raise Exception, detail
        available = []

    mywin.data = available
    mywin.titleRefresh(mysched)
    
    # PLACEHOLDER - LircConnection() goes here

    while True:
        myscr.clear()

        mywin.Refresh()
        mywin.titleRefresh(mysched)
        mywin.statusRefresh()
        if mywin == listwin:
            prefer = mysched.getPreferred(available[mywin.current_cursor],mycfg)

        # And now we do input.
        inputs, outputs, excepts = select.select(inputlst, [], [])
        
        if sys.stdin in inputs:
            c = myscr.getch()

        # NAVIGATION
        if c in ('Up', curses.KEY_UP):
            mywin.Up()
        
        if c in ('Down', curses.KEY_DOWN):
            mywin.Down()

        if c in ('Page Down', curses.KEY_NPAGE):
            mywin.PgDown()

        if c in ('Page Up', curses.KEY_PPAGE):
            mywin.PgUp()

        if c in ('Jump', ord('j')):
            if mywin != listwin:
                continue
            jump_prompt = 'Date (m/d/yy)? '
            if datetime.datetime(mysched.year,mysched.month,mysched.day) <> \
                    datetime.datetime(today_year,today_month,today_day):
                jump_prompt += '(<enter> returns to today) '
            query = listwin.prompter(listwin.statuswin, jump_prompt)
            # Special case. If the response is blank, we jump back to
            # today.
            if query == '':
                listwin.statusWrite('Jumping back to today',wait=1)
                listwin.statusWrite('Refreshing listings...',wait=1)
                try:
                    ymd_tuple = (today_year, today_month, today_day)
                    available = mysched.Jump(ymd_tuple,
                                             mycfg.get('speed'),
                                             mycfg.get('blackout'))
                    mywin.data = available
                    mywin.current_cursor = 0
                except (KeyError,MLBXmlError),detail:
                    if cfg['debug']:
                        raise Exception,detail
                    available = []
                    listwin.statusWrite("There was a parser problem with the listings page",wait=2)
                    listwin.data = []
                    listwin.current_cursor = 0
                continue
            pattern = re.compile(r'([0-9]{1,2})(/)([0-9]{1,2})(/)([0-9]{2})')
            parsed = re.match(pattern,query)
            if not parsed:
                listwin.statusWrite("Date not in correct format",wait=2)
		continue
            listwin.statusWrite('Refreshing listings...',wait=1)
            split = parsed.groups()
            prev_tuple = (mysched.year,mysched.month, mysched.day)
            mymonth = int(split[0])
            myday = int(split[2])
            myyear = int('20' + split[4])
            try:
                available = mysched.Jump((myyear, mymonth, myday),
                                          mycfg.get('speed'),
                                          mycfg.get('blackout'))
                mywin.data = available
                mywin.current_cursor = 0
            except (KeyError,MLBXmlError),detail:
                if cfg['debug']:
                    raise Exception,detail
                available = []
                listwin.statusWrite("There was a parser problem with the listings page",wait=2)
                listwin.current_cursor = 0
            

        if c in ('Left', curses.KEY_LEFT, ord('?') ,
                 'Right', curses.KEY_RIGHT, ord('!')):
            if mywin != listwin:
                continue
            listwin.statusWrite('Refreshing listings...',wait=1)
            try:
                if c in ('Left', curses.KEY_LEFT, ord('?')):
                    available = mysched.Back(mycfg.get('speed'), 
                                             mycfg.get('blackout'))
                else:
                    available = mysched.Forward(mycfg.get('speed'), 
                                                mycfg.get('blackout'))
            except (KeyError, MLBXmlError), detail:
                if mycfg.get('debug'):
                    raise Exception,detail
                available = []
                status_str = "There was a parser problem with the listings page"
                mywin.statusWrite(status_str,wait=2)
            mywin.data = available
            mywin.current_cursor = 0

        # DEBUG
        if c in ('Zdebug', ord('z')):
            if mywin == topwin:
                gameid = available[topwin.current_cursor][4]
            else:
                gameid = available[listwin.current_cursor][6]
            myscr.clear()
            mywin.titlewin.clear()
            mywin.titlewin.addstr(0,0,'LISTINGS DEBUG FOR ' + gameid)
            mywin.titlewin.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)
            myscr.addstr(2,0,'getListings() for current_cursor:')
            myscr.addstr(3,0,repr(available[mywin.current_cursor]))
            myscr.addstr(11,0,'preferred media for current cursor:')
            myscr.addstr(12,0,repr(prefer))
            myscr.refresh()
            mywin.titlewin.refresh()
            mywin.statusWrite('Press a key to continue...',wait=-1)

        # SCREENS
        if c in ('Help', ord('h')):
            mywin.helpScreen()

        if c in ('OptionsDebug', ord('o')):
            myscr.clear()
            mywin.titlewin.addstr(0,0,'CURRENT OPTIONS SETTINGS')
            mywin.titlewin.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)
            i = 2
            for elem in OPTIONS_DEBUG:
                optstr = elem + ' = ' + str(mycfg.get(elem))
                myscr.addstr(i,0,optstr[0:curses.COLS-1])
                i+=1
            myscr.refresh()
            mywin.titlewin.refresh()
            mywin.statusWrite('Press a key to continue...',wait=-1)
            continue

        if c in ('Highlights', ord('t')):
            try:
                GAMEID = available[mywin.current_cursor][6]
            except IndexError:
                continue
            topwin.data = available
            listwin.statusWrite('Fetching Top Plays list...')
            try:
                available = mysched.getTopPlays(GAMEID)
            except:
                listwin.statusWrite('Could not fetch highlights.',wait=2)
                available = listwin.data
                continue
            mywin = topwin
            mywin.current_cursor = 0
            mywin.data = available

        if c in ('AllHighlights', ord('y')):
            try:
                GAMEID = listwin.data[listwin.current_cursor][6]
            except IndexError:
                listwin.statusWrite('Could not find gameid for highlights',wait=2)
                continue
            listwin.statusWrite('Creating Top Plays Playlist...')
            try:
                temp = mysched.getTopPlays(GAMEID)
            except:
                listwin.statusWrite('Could not build highlights playlist.',wait=2)
            fp = open(HIGHLIGHTS_LIST, 'w')
            for highlight in temp:
                fp.write(highlight[2]+'\n')
            fp.close()
            mediaUrl = '-playlist %s' % HIGHLIGHTS_LIST
            eventId = listwin.data[listwin.current_cursor][6]
            streamtype = 'highlight'
            mediaStream = MediaStream(prefer['video'], session, mycfg,
                                      prefer['video'][1], 
                                      streamtype=streamtype)
            cmdStr = mediaStream.preparePlayerCmd(mediaUrl, eventId,streamtype)
            if mycfg.get('show_player_command'):
                myscr.clear()
                myscr.addstr(0,0,cmdStr)
                if mycfg.get('use_nexdef') and streamtype != 'audio':
                   pos=6
                else:
                   pos=14
                myscr.hline(pos,0,curses.ACS_HLINE, curses.COLS-1)
                myscr.addstr(pos+1,0,'')
                myscr.refresh()
                time.sleep(1)

            play = MLBprocess(cmdStr)
            play.open()
            play.waitInteractive(myscr)


        if c in ('Innings', ord('i')):
            if mycfg.get('use_nexdef') or \
               available[listwin.current_cursor][5] in ('F', 'CG')  or \
               available[listwin.current_cursor][7] == 'media_archive':
                pass
            else:
                error_str = 'ERROR: Jump to innings only supported for NexDef mode and archived games.'
                listwin.statusWrite(error_str,wait=2)
                continue

            innwin = MLBInningWin(myscr, mycfg, 
                                  listwin.data[listwin.current_cursor],
                                  mysched)
            innwin.Refresh()
            try:
                start_time = innwin.selectToPlay()
            except:
                raise
            if start_time is not None:
                mediaStream = MediaStream(available[listwin.current_cursor][2][0], 
                                          session,mycfg,coverage=0,
                                          streamtype='video',
                                          start_time=start_time)
                mediaUrl = mediaStream.locateMedia()
                mediaUrl = mediaStream.prepareMediaPlayer(mediaUrl)
                cmdStr = mediaStream.preparePlayerCmd(mediaUrl,
                                        available[listwin.current_cursor][6])
                play = MLBprocess(cmdStr)
                play.open()
                play.waitInteractive(myscr)
                
        if c in ('Listings', ord('l'), ord('L'), 27, 'Refresh', ord('r')):
            mywin = listwin
            # refresh
            mywin.statusWrite('Refreshing listings...',wait=1)

            try:
                available = mysched.getListings(mycfg.get('speed'),
                                                mycfg.get('blackout'))
            except:
                pass
            mywin.data = available

        # TOGGLES
        if c in ('Nexdef', ord('n')):
            if mywin != listwin:
                continue
            # there's got to be an easier way to do this
            if mycfg.get('use_nexdef'):
                mycfg.set('use_nexdef', False)
            else:
                mycfg.set('use_nexdef', True)

        if c in ('Coverage', ord('s')):
            if mywin != listwin:
                continue
            # there's got to be an easier way to do this
            temp = COVERAGETOGGLE.copy()
            del temp[mycfg.get('coverage')]
            for coverage in temp:
                mycfg.set('coverage', coverage)
            del temp

        if c in ('Speed', ord('p')):
            if mywin != listwin:
                continue
            # there's got to be an easier way to do this
            if mycfg.get('use_nexdef'):
                if mycfg.get('adaptive_stream'):
                    mycfg.set('adaptive_stream', False)
                else:
                    mycfg.set('adaptive_stream', True)
                continue
            speeds = map(int, SPEEDTOGGLE.keys())
            speeds.sort()
            newspeed = (speeds.index(int(mycfg.get('speed')))+1) % len(speeds)
            mycfg.set('speed', str(speeds[newspeed]))
            mywin.statuswin.clear()
            mywin.statuswin.addstr(0,0,'Refreshing listings...')
            mywin.statuswin.refresh()
            try:
                available = mysched.getListings(mycfg.get('speed'),
                                                mycfg.get('blackout'))
            except Exception,detail:
                myscr.clear()
                myscr.addstr(0,0,'ERROR: %s' % str(detail))
                myscr.addstr(3,0,'See %s for more details.'%LOGFILE)
                myscr.refresh()
                time.sleep(2)
                continue
            mywin.data = available

        if c in ('Debug', ord('d')):
            if mycfg.get('debug'):
                mycfg.set('debug', False)
            else:
                mycfg.set('debug', True)

        # ACTIONS
        # The Big Daddy Action  
        # With luck, it can handle audio, video, condensed, and highlights
        if c in ('Enter', 10, 'Audio', ord('a'), 'Condensed', ord('c')):
            if c in ('Audio', ord('a')):
                if mywin == topwin:
                    listwin.statusWrite(UNSUPPORTED,wait=2)
                    continue
                streamtype = 'audio'
            elif c in ('Condensed', ord('c')):
                if mywin == topwin:
                    listwin.statusWrite(UNSUPPORTED,wait=2)
                    continue
                streamtype = 'condensed'
                try:
                    prefer[streamtype] = listwin.data[listwin.current_cursor][4][0]
                except:
                    mywin.errorScreen('ERROR: Requested media not available.')
                    continue
            else:
                streamtype = 'video'

            # for nexdef, use the innings list to find the correct start time
            if mycfg.get('use_nexdef'):
                start_time = mysched.getStartOfGame(listwin.data[listwin.current_cursor],mycfg)
            else:
                start_time = 0
            if prefer[streamtype] is None:
                mywin.errorScreen('ERROR: Requested media not available.')
                continue
            mediaStream = MediaStream(prefer[streamtype], session, mycfg,
                                      prefer[streamtype][1], 
                                      streamtype=streamtype,
                                      start_time=start_time)
            myscr.clear()
            myscr.addstr(0,0,'Requesting media: %s'% repr(prefer[streamtype]))
            myscr.refresh()
            if mywin == topwin:
                # top plays are handled just a bit differently from video
                streamtype = 'highlight'
                mediaUrl = topwin.data[topwin.current_cursor][2]
                eventId  = topwin.data[topwin.current_cursor][4]
            else:
                try:
                    mediaUrl = mediaStream.locateMedia()
                except Exception,detail:
                    if mycfg.get('debug'):
                        raise
                    myscr.clear()
                    myscr.addstr(0,0,'ERROR: %s' % str(detail))
                    myscr.addstr(3,0,'See %s for more details.'%LOGFILE)
                    myscr.refresh()
                    time.sleep(2)
                    continue
                if not mycfg.get('free_condensed'):
                    mediaUrl = mediaStream.prepareMediaPlayer(mediaUrl)
                eventId  = available[listwin.current_cursor][6]

            cmdStr = mediaStream.preparePlayerCmd(mediaUrl, eventId,streamtype)
            if mycfg.get('show_player_command'):
                myscr.clear()
                myscr.addstr(0,0,cmdStr)
                if mycfg.get('use_nexdef') and streamtype != 'audio':
                   pos=6
                else:
                   pos=14
                myscr.hline(pos,0,curses.ACS_HLINE, curses.COLS-1)
                myscr.addstr(pos+1,0,'')
                myscr.refresh()
                time.sleep(1)
                                        
            play = MLBprocess(cmdStr)
            play.open()
            play.waitInteractive(myscr)
            # END OF Big Daddy Action
        
        if c in ('ReloadCfg', ord('R')):
            # reload the configuration
            mycfg = MLBConfig(mydefaults)
            mycfg.loads(myconf)
            status_str = "Reloading " + str(myconf) + "..."
            mywin.statusWrite(status_str,wait=2)

            # Defensive code to insure speed is set correctly
            if not SPEEDTOGGLE.has_key(mycfg.get('speed')):
                s = 'Invalid speed in ' + str(myconf) +'.  Using speed=1200'
                mycfg.set('speed', '1200')
                mywin.statusWrite(s,wait=2)

            try:
                available = mysched.getListings(mycfg.get('speed'),
                                                mycfg.get('blackout'))
            except (KeyError,MLBXmlError),detail:
                if mycfg.get('debug'):
                    raise Exception,detail
                available = []
                status_str = "There was a parser problem with the listings page"
                mywin.statusWrite(status_str,wait=2)

        if c in ('Quit', ord('q')):
            curses.nocbreak()
            myscr.keypad(0)
            curses.echo()
            curses.endwin()
            break

if __name__ == "__main__":
    myconfdir = os.path.join(os.environ['HOME'],AUTHDIR)
    myconf =  os.path.join(myconfdir,AUTHFILE)
    mydefaults = {'speed': DEFAULT_SPEED,
                  'video_player': DEFAULT_V_PLAYER,
                  'audio_player': DEFAULT_A_PLAYER,
                  'audio_follow': [],
                  'video_follow': [],
                  'blackout': [],
                  'favorite': [],
                  'use_color': 0,
                  'favorite_color': 'cyan',
                  'bg_color': 'xterm',
                  'show_player_command': 0,
                  'debug': 0,
                  'x_display': '',
                  'top_plays_player': '',
                  'time_offset': '',
                  'max_bps': 1200000,
                  'min_bps': 500000,
                  'live_from_start': 0,
                  'use_nexdef': 0,
                  'use_wired_web': 0,
                  'adaptive_stream': 0,
                  'coverage' : 'home',
                  'show_inning_frames': 1,
                  'use_librtmp': 0,
                  'no_lirc': 0,
                  'postseason': 0,
                  'free_condensed': 0,
                  'flash_browser': DEFAULT_FLASH_BROWSER}
    
    try:
        os.lstat(myconf)
    except:
        try:
            os.lstat(myconfdir)
        except:
            dir=myconfdir
        else:
            dir=None
        doinstall(myconf,mydefaults,dir)

    mycfg = MLBConfig(mydefaults)
    mycfg.loads(myconf)


    # check to see if the start date is specified on command-line
    if len(sys.argv) > 1:
        pattern = re.compile(r'(.*)=(.*)')
        parsed = re.match(pattern,sys.argv[1])
        if not parsed:
            print 'Error: Arguments should be specified as variable=value'
            sys.exit()
        split = parsed.groups()
        if split[0] not in ('startdate'):
            print 'Error: unknown variable argument: '+split[0]
            sys.exit()

        pattern = re.compile(r'startdate=([0-9]{1,2})(/)([0-9]{1,2})(/)([0-9]{2})')
        parsed = re.match(pattern,sys.argv[1])
        if not parsed:
            print 'Error: listing start date not in mm/dd/yy format.'
            sys.exit()
        split = parsed.groups()
        startmonth = int(split[0])
        startday  = int(split[2])
        startyear  = int('20' + split[4])
        startdate = (startyear, startmonth, startday)
    else:
        now = datetime.datetime.now()
        dif = datetime.timedelta(1)
        if now.hour < 9:
            now = now - dif
        startdate = (now.year, now.month, now.day)

    curses.wrapper(mainloop, mycfg)
