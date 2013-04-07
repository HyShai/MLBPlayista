from xml.dom.minidom import parse
from xml.dom.minidom import parseString
from xml.dom import *
import urllib2
import datetime

class MLBLineScore:

    def __init__(self,gameid):
        self.gameid = gameid
        self.gameid = self.gameid.replace('/','_')
        self.gameid = self.gameid.replace('-','_')
        ( year, month, day ) = self.gameid.split('_')[:3]
        self.boxUrl = 'http://gdx.mlb.com/components/game/mlb/year_%s/month_%s/day_%s/gid_%s/linescore.xml' % ( year, month, day, self.gameid )
        self.linescore = None


    def getLineData(self):
        try: 
            req = urllib2.Request(self.boxUrl)
            rsp = urllib2.urlopen(req)
        except:
            raise
        try:
            xp = parse(rsp)
        except:
            raise
        # if we got this far, initialize the data structure
        self.linescore = dict()
        self.linescore['game'] = dict()
        self.linescore['innings'] = dict()
        self.linescore['pitchers'] = dict()
        self.linescore['game'] = self.parseGameData(xp)
        try:
            self.linescore['innings'] = self.parseLineScore(xp)
        except:
            self.linescore['innings'] = None
        status = self.linescore['game']['status']
        if status in ('Final', 'Game Over'):
            self.linescore['pitchers'] = self.parseWinLossPitchers(xp)
        elif status == 'In Progress':
            self.linescore['pitchers'] = self.parseCurrentPitchers(xp)
        else:
            self.linescore['pitchers'] = self.parseProbablePitchers(xp)
        return self.linescore

    def parseGameData(self,xp):
        out = dict()
        
        for node in xp.getElementsByTagName('game'):
            for attr in node.attributes.keys():
                out[attr] = node.getAttribute(attr)
        return out
        

    def parseLineScore(self,xp):
        out = dict()

        for iptr in xp.getElementsByTagName('linescore'):
            inning = iptr.getAttribute('inning')
            out[inning] = dict()
            for team in ( 'home', 'away' ):
                out[inning][team] = iptr.getAttribute("%s_inning_runs"%team)
        return out
                    

    def parseWinLossPitchers(self,xp):
        out = dict()
    
        for pitcher in ( 'winning_pitcher' , 'losing_pitcher' , 'save_pitcher'):
            for p in xp.getElementsByTagName(pitcher):
                tmp = dict()
                for attr in p.attributes.keys():
                    tmp[attr] = p.getAttribute(attr)
                if pitcher == 'save_pitcher':
                    out[pitcher] = ( tmp['id'], tmp['last_name'], 
                                     tmp['wins'], tmp['losses'], tmp['era'], 
                                     tmp['saves'] )
                else:
                    out[pitcher] = ( tmp['id'], tmp['last_name'], 
                                     tmp['wins'], tmp['losses'], tmp['era'] )
        return out

    def parseProbablePitchers(self,xp):
        out = dict()
    
        for pitcher in ( 'home_probable_pitcher', 'away_probable_pitcher'):
            for p in xp.getElementsByTagName(pitcher):
                tmp = dict()
                for attr in p.attributes.keys():
                    tmp[attr] = p.getAttribute(attr)
                out[pitcher] = ( tmp['id'], tmp['last_name'],
                                 tmp['wins'], tmp['losses'], tmp['era'] )
        return out

    def parseCurrentPitchers(self,xp):
        out = dict()
    
        for pitcher in ( 'current_pitcher', 'opposing_pitcher'):
            for p in xp.getElementsByTagName(pitcher):
                tmp = dict()
                for attr in p.attributes.keys():
                    tmp[attr] = p.getAttribute(attr)
                out[pitcher] = ( tmp['id'], tmp['last_name'],
                                 tmp['wins'], tmp['losses'], tmp['era'] )
        for b in xp.getElementsByTagName('current_batter'):
            tmp = dict()
            for attr in b.attributes.keys():
                tmp[attr] = b.getAttribute(attr)
            out['current_batter'] = ( tmp['id'], tmp['last_name'], tmp['avg'] )
        return out
