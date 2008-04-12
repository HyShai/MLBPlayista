#!/usr/bin/env python

import os
import re

class MLBConfig:

    def __init__(self, default_dct=dict()):
        self.data = default_dct

    def loads(self, authfile):
        #conf = os.path.join(os.environ['HOME'], authfile)
        fp = open(authfile)

        for line in fp:
            # Skip all the comments
            if line.startswith('#'):
                pass
            # Skip all the blank lines
            elif re.match(r'^\s*$',line):
                pass
            else:
            # Break at the first equals sign
                key, val = line.split('=')[0], '='.join(line.split('=')[1:])
                key = key.strip()
                val = val.strip()
                # These are the ones that take multiple values
                if key in ('blackout'):
                    self.data[key].append(val)
                # And these are the ones that only take one value, and so,
                # replace the defaults.
                else:
                    self.data[key] = val


