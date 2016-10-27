### MLBPlayista
---
#### Overview

**MLBPlayista** is a stripped down version of [mlbviewer](https://sourceforge.net/projects/mlbviewer/) modified to run on Pythonista for iOS. It has one objective - to allow the watching of _live_ (currently playing) MLB.tv games on an iOS device **without** using the MLB AtBat app. (You are still required to [purchase](http://mlb.mlb.com/mlb/subscriptions/) an MLB.tv Premium or Single Team subscription.) This can be useful for some people; I won't enumerate the reason(s) - they may fall into the gray area of the Terms Of Service. 

MLBPlayista is based on the [`mlbplay.py`](https://sourceforge.net/p/mlbviewer/code/HEAD/tree/trunk/mlbplay.py) script that is included in the `mlbviewer` project.

#### Installation

1. [Subscribe](http://mlb.mlb.com/mlb/subscriptions/) to MLB.tv Premium or Single Team
1. Install [Live Player](https://itunes.apple.com/us/app/live-player-professional-streaming/id1099439153?mt=8&uo=4&at=11l6hc) (Free with $4.99 IAP to remove ads etc.) - **MLBPlayista will not work without Live Player.**
1. Install [Pythonista](https://itunes.apple.com/us/app/pythonista/id528579881?mt=8&uo=4&at=11l6hc) ($9.99)
1. Install **MLBPlayista** with a one line python command:

    ```Python
    import requests as r; exec r.get('http://rawgit.com/HyShai/MLBPlayista/master/get_mlbplayista.py').text
    ``` 
    --> Simply copy the above line, paste into Pythonista interactive prompt and execute. It installs MLBPlayista to the `~/Documents/MLBPlayista` folder, and optionally installs a homecreen shortcut to MLBPlayista.
1. Edit the `MLBPlayista/config.txt` file - see [below](#configuration) for config options. You will probably, at the least, want to set the `user` and `pass` options - instead of manually entering them each time.

#### Usage

1. Launch MLBPlayista either via the homescreen shortcut (if you installed it), or via the `MLBPlayista/mlbplayista.py` file.
1. Choose a speed, if you didn't set a default speed in `config.txt`.
1. Choose a game.
1. Choose a team broadcast stream.
1. Wait for MLBPlayista to fetch the stream.
1. MLBPlayista will then open the stream in LivePlayer. (click *Open*, if prompted "Pythonista wants to open Live Player")
1. Enjoy the game!

#### Configuration

For MLBPlayista there are only a few config options that are useful (complete config options are explained in full [here](https://sourceforge.net/p/mlbviewer/wiki/Configuration%20File%20Options/)): _[Don't put quotes around any of the values]_
  - `user` - MLB.tv username
  - `pass` - MLB.tv password
  - `speed` - `450, 800, 1200, 1800, 2500` default video stream speed (Kbps)
  - `favorite` - teamcode, pins your favorite team(s) to the top of the list
  - `time_offset` - can be used to specify local time offset from US/Eastern (UTC-4) if default time conversion fails (e.g. _-03:00_ to indicate US/Eastern-3 or US/Pacific)
  - `international` - `True/False`, prune NAT from listings to allow international users to see the correct INT streams instead
  - `postseason` - `True/False`, for international users, this setting ignores US blackout statuses that appear during postseason
  - `debug` - `True/False`, display the media URL only; does not launch player; also produces crashes with stack traces for failures instead of handling errors gracefully
  

#### Credits:
-   [**mlbviewer**](https://sourceforge.net/projects/mlbviewer/) is an awesome project - check it out for an alternate viewing experience to the MLB.tv website. Full credit to Matthew Levine and Jesse Rosenthal for completely reverse engineering the MLB.tv media process. Paypal donations can be sent to them via _straycat000(at)yahoo(dot)com_. mlbviewer is in no way affiliated with MLBPlayista. 
- [**Pythonista**](https://itunes.apple.com/us/app/pythonista/id528579881?mt=8&uo=4&at=11l6hc) is a wonderful, indispensable app which runs Python applications on an iOS device.
- [**Live Player**](https://itunes.apple.com/us/app/live-player-professional-streaming/id1099439153?mt=8&uo=4&at=11l6hc) is the only app on the AppStore [which I could find](https://forum.videolan.org/viewtopic.php?t=126825) that can play rtmp streams _with parameters_.
- Half of the installation script was plagiarized from [StaSh](https://github.com/ywangd/stash) tool.
- The other half uses the html from the Pythonista's built in shortcut generator.
- The shortcut icon was made by [Vicent Pla](https://www.iconfinder.com/icons/204717/mlb_icon)

 
##### Notes:
  - Instead of installing Pythonista (which you should buy - it's a great app with so many use cases), you can use the [PythonistaAppTemplate](https://github.com/omz/PythonistaAppTemplate) to sideload MLBPlayista on to your device (See http://bouk.co/blog/sideload-iphone/ for more information on how to sideload.)
