#!/usr/bin/env python

from xml.dom import *
from xml.dom.minidom import *
import sys

try:
  xmlfile = sys.argv[1]
except:
  print "%s: Please specify an xml filename to parse" % sys.argv[0]
  sys.exit()

try:
  xp = parse(xmlfile)
except:
  print "%s %s: Could not parse xmlfile." % (sys.argv[0], xmlfile)
  sys.exit()

IL = 0

def printChildNodes(node,IL):
  if node.hasChildNodes():
    print "%s %s:" % (IL*' ', node.nodeName)
    IL += 1
    for child in node.childNodes:
      printChildNodes(child,IL)
  else:
    print "%s %s: %s" % (IL*' ', node.nodeName, node.nodeValue)
    IL -= 1

printChildNodes(xp,IL)
