### MLBPlayista
---
#### Overview

**MLBPlayista** is a stripped down version of [mlbviewer](https://sourceforge.net/projects/mlbviewer/) modified to run on Pythonista for iOS. 

[**mlbviewer**](https://sourceforge.net/projects/mlbviewer/) is an awesome project - check it out for an alternate viewing experience to the mlb.tv website. Full credit to Matthew Levine and Jesse Rosenthal for completely reverse engineering the mlb.tv media process. Paypal donations can be sent to them via _straycat000(at)yahoo(dot)com_. mlbviewer is in no way affiliated with MLBPlayista. 

**Pythonista** is a wonderful app that can run Python applications on an iOS device - it's not strictly necessary for MLBPlayista - but I highly recommend it.

MLBPlayista has one objective - play _live_ (currently playing) mlb.tv games on an iOS device without using the MLB AtBat app. This can be useful for some people; I won't enumerate the reason(s) - they may fall into the gray area of the Terms Of Service. (You are still required to [purchase](http://mlb.mlb.com/mlb/subscriptions/) an mlb.tv Premium or Single Team subscription in order to use MLBPlayista.)

MLBPlayista is based on the [`mlbplay.py`](https://sourceforge.net/p/mlbviewer/code/HEAD/tree/trunk/mlbplay.py) script that is included in the `mlbviewer` project.

#### Installation

- [Subscribe](http://mlb.mlb.com/mlb/subscriptions/) to mlb.tv Premium or Single Team
- Install [Live Player](https://itunes.apple.com/us/app/live-player-professional-streaming/id1099439153?mt=8&uo=4&at=11l6hc) (Free; $4.99 IAP to remove ads etc.)
- Install [Pythonista](https://itunes.apple.com/us/app/pythonista/id528579881?mt=8&uo=4&at=11l6hc) ($9.99)
- If you don't want to install Pythonista (though you probably should install it - it's seriously a great app), there's an xcode project included that can be used to sideload MLBPlayista on to your device (See http://bouk.co/blog/sideload-iphone/ for more information on how to sideload.)
- Clone this repo and copy the files to your device and/or sideload the xcode project.

#### Configuration

For MLBPlayista there are only a few config options that are useful (complete config options are explained [here](https://sourceforge.net/p/mlbviewer/wiki/Configuration%20File%20Options/)):
  - `user` - mlb.tv username
  - `pass` - mlb.tv password
  - `speed` -  ( '450', '800', '1200', '1800', '2500' ) default video stream speed
  - `favorite` - teamcode, pins your favorite team(s) to the top of the list
  - `time_offset` - can be used to specify local time offset from US/Eastern (UTC-4) if default time conversion fails (e.g. _-03:00_ to indicate US/Eastern-3 or US/Pacific)
  - `international` - True/False, prune -NAT from listings to allow international users to see the correct -INT streams instead
  - `postseason` - True/False, for international users, this setting ignores US blackout statuses that appear during postseason
  - `debug` - True/False, display the media URL only; does not launch player; also produces crashes with stack traces for failures instead of handling errors gracefully
