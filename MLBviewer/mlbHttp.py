#!/usr/bin/env python

import urllib2, httplib
import StringIO
import gzip
import datetime
from mlbConstants import *

class MLBHttp:

    def __init__(self,accept_gzip=True):
        self.accept_gzip = accept_gzip
        self.opener = urllib2.build_opener()
        self.cache = dict()

    def getUrl(self,url):
        request = urllib2.Request(url)
        if self.accept_gzip:
            request.add_header('Accept-encoding', 'gzip')
        request.add_header('User-agent', USERAGENT)
        # for now, let errors drop through to the calling class
        rsp = self.opener.open(request)
        if rsp.headers.get('Content-Encoding') == 'gzip':
            compressedData = rsp.read()
            compressedStream = StringIO.StringIO(compressedData)
            gzipper = gzip.GzipFile(fileobj=compressedStream)
            return gzipper.read()
        return rsp.read()
    
