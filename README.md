# Copyright 2025 Andrew Kingston
#
# This file is part of Abib Bible Reader.
#
# Abib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# Abib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Abib.  If not, see <https://www.gnu.org/licenses/>.
#

Photo Credit: Abibofgod.com for the splash screen.

************
ABIB README:
************

Please note I am not planning any major revisions or new platforms.
Just trying to keep it going; improve it, and find bugs and glitches.

Abib v410
----------

Changelog.
Abib v410
Commentary removed because not ready yet.
First version on GitHub.


Abib409
Two extra arguments allowed for window width and window height.
Possible two more for window origin, which could be calculated depending on screen size.
Re-write of the F2 display reference section, because the code was hard to understand,
now it is easier to follow and more intuitive to use.
Introduced a sound for errors using the pygame library.
Allowed use of roman numerals in text input references.
Bound single integer entries to apply to the same chapter only.
Changed the ABOUT.txt window to have THE HOLY BIBLE title page.
Much, much more debugging and testing, e.g. miv.ii resolves to Micah 4:2 not 1004.2

Abib408
Devotional, Commentary and a blank button added.
The Commentary button is for future use.
Buttons rearranged to accommodate new ones.
Spurgeon's Morning and Evening Readings added.
Some improvements to the F2 reference entry section
(allows "--Eph. 5.12....... ").

Abib407
Text highlighting colour bug fixed.
'OK' button for Display verse text entry added.

Abib406
Minor background improvements.
Slightly improved startup time.

Abib405
Settings feature implemented.
Dark mode option introduced.
Splash screen made optional.
Find dialog text entry box retains focus now.
F2 Display text entry box retains focus now.
Linux and Windows versions identical code.

Abib404
F2 passage entry invalid text before and after valid entry now ignored.

Abib403
Splash screen added.
Ensured focus is in F2 display verse text entry box.

Abib402
Some refactoring and bugfixes.

Abib401
Removed acoustic guitar intro.
Removed all error sounds.
Error messages remain in the status bar a little longer.
Adjustment to Copyright, README and HELP windows size.

Abib400
Much refactoring of the code.
Possible improvement to the startup time.
Changes to the error sounds.
Short acoustic guitar intro. (To be removed).

Abib399
There is no 399.

Abib398
Corrected many bugs concerning search keys with words that are
not in the text.
Rationalised some of the book abbreviations.
Assured centering of the Abib window on startup.
Also, of the other windows except Find.

Abib397
Changes to About, Help, Readme and Copyright windows.

Abib396
Python 3.13.1 updated version
No real changes

Abib395
Changes to 'About' window.
Corrected problems with 'Any of the words' search.

Abib394
Is a test version of 393 to check that installation is correct.

Abib393
Blank lines placed at the end of Revelation to prevent a glitch.

Abib392 (Numbering changed to conform with the Python standards).
Built with Python3.13.0 and PySide6.
Extensively refactored.  Nothing major to the logic.
Except:
Bugfix correcting Back and especially Forward not working properly.

Another bug fixed regarding the following verses; Joshua 15:1,Job 7:1, Psalm 70:1,
Psalm 92:1, Hosea 8:1 and Romans 8:1.
These are all first verses of chapters that start with italicised first words.
These were displayed incorrectly when viewed using Back and Forward.

Some changes to the way that the Find process works and to the highlighting of
the search key.

Abib3.9.1b
Built with Python11.1 and Pyside6 to make the operation faster.
Some changes to the Help Menu.

Abib3.8.5b
Found and corrected a bug preventing, whole word, searches containing
the single letter words "A", "I" and "O".
Fixed bug preventing, whole word, searches for words containing a
hyphen, e.g., Beth-lehem.  Will now work with or without the hyphen.
However, Raw searches still require the hyphen.
Some adjustments made to improve search highlighting.

Abib3.8.4b
Change of sound for 'Not found'
Bug removed around AE and Æ in searches.
Program altered to allow a single command line argument, which will be
interpreted as the default font size for the Bible. 

This is how to use it (The default font size is 14):

    1) Right-click on the Abib desktop shortcut icon and click on
       Properties.
    2) In the Target text box, leave what is there unchanged, except
       after it put a space then the default font size that want.
       Like this "C:\Program Files\Abib410\Abib410.exe" 11 width height
       Here width and height can be adjusted from default values.
    3) Click on Apply, then Continue for Administrative permission and
       then OK.
    4) If you have another shortcut in the taskbar, you will need to
       unpin it and drag another one there, or Abib will not start up
       with the new default font size.

Abib3.8.3b
Changed the default font to a smaller size, can be adjusted with Ctrl &
mouse wheel.
Removed bug affecting highlighting after Find and using passage
dropdown boxes.

Abib3.8.2b
Rearranged push-buttons, some changes to the Book abbreviations to
agree with the abibsoft.com website.  The website is still under
development.

Abib3.8.1b
Adjustments made to ensure Abib takes up less screen real estate.

Abib3.7.4b
Bugfix affecting verses that start with italics, not showing, e.g. Romans 8:1.

Abib3.7.3b
Minor mods - change of name of organisation - from ARK to Abibsoft.

Abib3.7.2b
New method of entering the passage reference provided whilst retaining
the older text entry box.  Highlighting bug removed.

Abib3.7.1b
Some changes made towards a target of getting Digital Signing.
Startup time improved.
The Size of the overall package decreased.

Abib Beta 3.6
Some bugs removed and minor improvements made to regex searching.

Abib Beta 3.5
More reworking of the code and more improvements made to the
highlighting of the 'All' and 'Any' word searches.  These are now
highlighted from the first to the last search keyword in the verse.

The Find Options dialog window has been redesigned.  It is now more
intuitive and easier to understand.

Abib Beta 3.4: Some bad bugs removed, code reworked in the Find
section, some improvements made to the highlighting of the 'All' and
'Any' word searches, but more work is necessary to reach the desired
output.

------------------
Cascadia Mono font
------------------
Please ensure that the Cascadia Mono font is installed on your device.
This will provide for the designed output to occur. (You can do this
before or after you install Abib.)

You will find it here in the 'C:\Program Files\Abib410\font' folder.
It is called CascadiaMono and is a Truetype font which works with
Microsoft Windows.

How to install the Cascadia Mono font.
--------------------------------------

For Windows 10: Type 'fonts' into the search box.

Click on Font settings.

Under Add fonts, there is a Drag and Drop to install box.

So, using File Explorer navigate to C:\Program Files\Abib410\font and
there you will see the file CascadiaMono.ttf. Drag the CascadiaMono
file, from inside the font folder, into the box, and it will install
automatically.

If the font is installed already, you will do no harm, you will be
warned with a message and can cancel.

For Windows 11: Do nothing, the CascadiaMono font is built in.

For arch-based linux distros.
-----------------------------
Do:

$ sudo pacman -S ttf-cascadia-code

For other distributions, you can find the Cascadia Code font as a
standard .ttf at:

https://github.com/microsoft/cascadia-code/releases

The file above can be installed on almost every modern operating
system, including Ubuntu. For the latter, just double-click on the .ttf
file to open the font manager/preview tool. Hit ‘install’ to install it
on your system.  Thanks to Hal.

Installing the Abib Bible App.
------------------------------

If you have Windows, the installer provided will simply install
everything, just double-click on it, and follow the instructions.

For Linux, copy the whole C:\Program Files\Abib410 folder to a
USB key and then do the following:

Suppose your username is Andrew or rather andrew, your USB key will most
likely be mounted under /media/andrew/a_volume_name. So first, you need
to get this full path. You can store it in a shell variable to make it easy:

ls /media/andrew

The usb mount point is variable. /media is deprecated in many modern OS. 
Run mount to find the mount point.

See or find the right entry in the output, and now save it in the source
directory variable (s_dir):

s_dir=/media/andrew/my_usb_drive

Of course, replace my_usb_drive with the right name. Once you have this,
enter this command:

cp -r "$s_dir"/Abib410 /home/andrew/.Abib410

Possibly /home/username/.Abib410 where username is replaced with your
linux username.

Now you can run it by navigating to that folder and doing:

$ python Abib410.py


God Bless you.
