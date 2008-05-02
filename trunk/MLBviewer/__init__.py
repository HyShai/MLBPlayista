__all__ = ["MLBSchedule", "Gamestream", "LircConnection", "MLBConfig"]

__author__ = "Jesse Rosenthal"
__email__ = "jesse.k.rosenthal@gmail.com"

VERSION ="0.1alpha6svn"
URL = "http://sourceforge.net/projects/mlbviewer"

AUTHDIR = '.mlb'
AUTHFILE = 'config'



from mlbtv import MLBSchedule
from mlbtv import GameStream
from config import MLBConfig
from mlbtv import MLBUrlError
from mlbtv import MLBJsonError
from LIRC import LircConnection




