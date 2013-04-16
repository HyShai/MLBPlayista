#!/usr/bin/env python

import curses

DEFAULT_KEYBINDINGS = {
    'UP'                 : [ curses.KEY_UP, ],
    'DOWN'               : [ curses.KEY_DOWN, ],
    'LEFT'               : [ curses.KEY_LEFT, ],
    'RIGHT'              : [ curses.KEY_RIGHT, ],
    'VIDEO'              : [ 10, ],
    'AUDIO'              : [ ord('a') ],
    'HELP'               : [ ord('h') ],
    'JUMP'               : [ ord('j') ],
    'MEDIA_DEBUG'        : [ ord('z') ],
    'OPTIONS'            : [ ord('o') ],
    'LINE_SCORE'         : [ ord('b') ],
    'BOX_SCORE'          : [ ord('x') ],
    'MASTER_SCOREBOARD'  : [ ord('m') ],
    'HIGHLIGHTS'         : [ ord('t') ],
    'HIGHLIGHTS_PLAYLIST': [ ord('y') ],
    'INNINGS'            : [ ord('i') ],
    'LISTINGS'           : [ ord('l') ],
    'REFRESH'            : [ ord('r') ],
    'NEXDEF'             : [ ord('n') ],
    'COVERAGE'           : [ ord('s') ],
    'SPEED'              : [ ord('p') ],
    'CONDENSED_GAME'     : [ ord('c') ],
    'RELOAD_CONFIG'      : [ ord('R') ],
    'QUIT'               : [ ord('q') ],
    'DEBUG'              : [ ord('d') ],
}
