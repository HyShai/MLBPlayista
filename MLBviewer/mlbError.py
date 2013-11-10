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

class Error(Exception):
    pass

class MLBUrlError(Error):
    pass

class MLBXmlError(Error):
    pass

class MLBAuthError(Error):
    pass

class MLBCursesError(Error):
    pass

class MLBJsonError(Error):
    pass

class MLBScreenTooSmall(Error):
    pass
