#!/usr/bin/env python

from distutils.core import setup

setup(name = "mlbviewer",
      version = "0.1alpha12svn",
      description = "Tools to watch and listen to baseball on MLB.tv",
      author = "Jesse Rosenthal, Matthew D. Aftcat",
      author_email = "jesse.k.rosenthal@gmail.com",
      url = "http://sourceforge.net/projects/mlbviewer/",
      packages = ['MLBviewer'],
      scripts = ['mlbviewer.py'])
      
