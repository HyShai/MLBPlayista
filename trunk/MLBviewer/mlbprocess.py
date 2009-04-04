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

import subprocess
import signal
import os

class MLBprocess:

    def __init__(self,cmd_str,retries=None):
        self.cmd_str = cmd_str
        self.retries = retries
        self.retcode = None
        self.process = None

    def open(self):
        self.process = subprocess.Popen(self.cmd_str,shell=True,
                                                     preexec_fn=os.setsid)
        self.retcode = None
        return self.process

    def close(self,signal=signal.SIGTERM):
        try:
            os.killpg(self.process.pid,signal)
            retcode = self.process.wait()
        except:
            retcode = -1
        self.retries -= 1
        self.process = None
        return retcode

    def poll(self):
        if self.process is not None:
            retcode = self.process.poll()
        else:
            return -1
        if retcode is not None:
            retcode = self.process.wait()
            self.retries -= 1
            self.process = None
            return retcode
        else:
            return None
            
