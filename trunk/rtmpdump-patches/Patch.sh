#!/bin/bash

curdir=`pwd`
patch=`/bin/ls *.patch`
patchfile=$curdir/$patch


echo -n "Enter path to rtmpdump source directory: "
read sourcedir
if [ ! -d $sourcedir ] ; then
	echo "Could not find rtmpdump directory at $sourcedir"
	exit 1
fi

if [ ! -f $sourcedir/rtmpdump.cpp ]; then
	echo "$sourcedir does not look like a valid rtmpdump source directory."
	exit 1
fi

echo "Source directory : $sourcedir" 
echo "Patch file       : $patchfile"
echo "Applying patch..."
cd $sourcedir
patch -p1 < $patchfile
retcode=$?
if [ $retcode -ne 0 ]; then
	echo "Patch returned an unsuccessful return code: $retcode"
	echo "Patch may have failed."
else
	echo "Patch succeeded.  Please run 'make clean' before 'make'."
	echo "Remember to cp rtmpdump to a directory in your path."
fi

exit $retcode
