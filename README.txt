************
ABIB README:
************

Abib is on GitHub, https://github.com/Abib-ops/Abib/releases

Abib v414.22
------------

Changelog.
-----------
Abib v414.22
Urgent bugfix of upgrade error.

Abib v414.21
Bug fix for text search.
Bug fix for the uninstallation process.

Abib v414.20
Search facility added for the "Other Works" text window.
(But it did not work).

Abib v414.19
Another bugfix attempt for Windows 10 dark-mode push-buttons.

Abib v414.18
Attempted bugfix for Windows 10 dark-mode push-buttons.

Abib v414.17
Did something can't remember what

Abib v414.16
README (on GitHub) has links for downloading the individual PDF files.

Abib v414.15
Finished work on "Works of Jonathan Edwards Vol II.txt"
"Last" push-button reduced in size.
Improved the detection of references in the reader texts.

Select the texts you want on your Reader window combo box list,
in the new Help --> Settings > Tick the ones you want.

Moved PDF files to the release section of GitHub.

Abib v414.14
PDF folder included properly.
Work done on Works of Jonathan Edwards Vol II.txt
Added The Works of Thomas Brook to the "pdf" folder.

Abib v414.13
Improved the detection of references that span two lines.
Completed work on Institutes - John Calvin. Also, Arminianism.
Added a new button to the reader window combobox 'Last' to return to the last viewed file.


Abib v414.12
Many changes, added new books to the reader window.
Work on books and texts ensuring highlighting of the scripture references.

Abib v414.11
Each reader file/book has its own stored screen position and size, plus the scroll position.
So, the settings.json file is now much larger.
The scripture references in the reader window when clicked appear in the main Bible window.
Hover response time slightly improved.

Abib v414.10
Many improvements made to the code.

The way that the "last_read_positions" values are updated and looked up before and
after loading a new text was not robust (In settings.json).
The problem was fixed now works; the last read positions are now stored in a dictionary
keyed by the book name.
The "Reset to defaults" button now resets all settings to canonical defaults immediately.
The in-memory settings object identity is preserved to update all open components without
recreation. Tooltip text was updated to clarify immediate reset effects and restart
requirements for some settings.

Fixes an issue where a saved per-file reading position contained a typo. The reader now
recognises and migrates the legacy key and correctly restores the saved position. Also,
slightly increases the robustness of the restore timing for huge files.

Abib v414.09
Intermediate version.

Abib v414.08
Fixed the problem with "last_read_position", code now defaults to "0" if not found.
The current code uses "last_read_positions" per file and defaults to 0 when no entry exists.
Safe to ignore or remove the old single-value key from the "settings.json" file.

Found and removed a few spurious '|' characters in the bible_data.json file.
This was showing up in the reader window while hovering over certain references.
Lots of work was done on the book texts, making references work better.

Abib v414.07
Changed README.md to be more concise and less technical.
Improved Dark mode functionality.
Changed the "Calvin" button's name to "Commentaries".
Changed the "The Pilgrim's Progress" combo box to default to the last item viewed.
Fixed the splashscreen bug.
Removed some unnecessary files.

Abib v414.06
Bugfix

Abib v414.05
Uses the spare button for Calvin Commentaries Access.

Abib v414.04
Added 'Commentary on Galatians' and 'Small Catechism' by Martin Luther.
Conceived an addition of a number of PDF format books that I have downloaded.
These will not be part of the standard distribution but will only be on the USB key,
because of the size of the files.

Abib v414.03
Added Charles Hodge's 'Systematic Theology Vol I-III'.

Abib v414.02
Modified the convert_roman_to_integer function to fix a CodeQL issue.
Refactored the code to remove duplicate code.
Modularised the code. Many new modules. Linted the code.

Abib v414.01
New books included.

Abib v413.06
The display font size can no longer be zoomed up and down by holding down
Ctrl and using the mouse wheel. From now on, use Ctrl+- and Ctrl++.
Adjustments made to prevent windows being located outside the screen area over a restart.

Abib v413.05
Same as v413.04 but now really gpg signed.
Which it turned out to be, and is now 'Verified' on GitHub.

Abib v413.04
Same as v413.03 but correctly gpg signed.

Abib v413.03
Release version, bugs fixed, Main Devotional and Pilgrim's Progress windows now preserve their position and size.
The font size is adjustable and persists for the Main and Devotional windows.
Package                   Version
------------------------- ---------
python                    3.13.9
pip                       25.2
altgraph                  0.17.4
certifi                   2025.10.5
charset-normalizer        3.4.4
idna                      3.11
packaging                 25.0
pefile                    2023.2.7
pip                       25.2
pygame                    2.6.1
pyinstaller               6.16.0
pyinstaller-hooks-contrib 2025.9
PySide6                   6.10.0
PySide6_Addons            6.10.0
PySide6_Essentials        6.10.0
pywin32-ctypes            0.2.3
requests                  2.32.5
roman                     5.1
setuptools                80.9.0  <81  # Pin to avoid pygame warning
shiboken6                 6.10.0
urllib3                   2.5.0

Abib v413.02
Changes made to fix settings.json.

Abib v413.01
Changes to the Devotional, Main and Pilgrim's Progress windows made by the user should now persist.
But it did not work.

Abib 412.9
Corrected error messages occurring when no internet connection is available at startup.
So, in this case, the update-available check is ignored.

Abib 412.8
Minor refactoring.

Abib v412.7
Upgraded various packages associated with requirements.txt.
These are needed for the pyinstaller build process.
GitHub gave a warning about a security vulnerability:
"setuptools has a path traversal vulnerability in PackageIndex.download that leads to Arbitrary File Write".
This is now fixed.

Abib v412.6
Adjustment to the position of the scripture popup windows to suit 
smaller screens in the Pilgrim's Progress window.

Abib v412.5
Bugfix, fixed non-responsive hovered over references in hypertext used in The Pilgrim's Progress.

Abib v412.4
Pilgrim's Progress improved with highlighted scripture references,
when hovered over with the mouse, the scripture pops up next to the 
text. The Pilgrim's Progress window remembers the user's last position.

Abib v412.3
Refactored PySide6 imports.
The Pilgrim's Progress by John Bunyan window included.
The issue has been addressed that when an invalid 'chapter.verse' input
(specified as a decimal) is entered, the system no longer defaults to
Genesis 1:1. Instead, it now remains on the current line.

Abib v412.2
New module fcs.py created to reduce the size of Abib.py.
Module shared.py created to prevent circular references.

Abib v412.1
Further test to ensure stability.

Abib v411.4
Same as v411.3 for testing purposes.

Abib v411.3
Possibly working upgrade, checks on start-up.

Abib v411.2
Rudimentary command history on passage entry text box introduced.

Abib v411.1
First "Check for updates" version

Abib v410.3
Bug fixed regarding installation.
About.txt changed for cross-platform compatibility.

The current implementation requires that you either provide no arguments or exactly three arguments, in the
following order: font-size, width, and height. By default, these values are set to "14 480 810" respectively.
Consequently, if you only wish to modify the font size, you must supply all three parameters, e.g. "11 480 810"
or "12 480 810." This approach ensures that a wide range of window sizes can be accommodated to suit different screens.

The place to put the arguments:
Right-click on the Windows Abib icon;
click on Properties;
in the Target text box you will see "C:\Program Files\Abib\Abib.exe".
It is after this that you can put your three arguments e.g.
"C:\Program Files\Abib\Abib.exe" 12 400 600

Apply Changes:
- Click Apply and OK to save the changes.

Abib v410.2
Bug fixed concerning incorrect behaviour when entering integer values for verses, that is just the verse number is
entered, and you should go to that verse in the chapter you are in. This was broken because of the addition of the
possibility of using negative numbers, which are interpreted as going back that number of verses, e.g. if you are at
verse 20, and you enter -5, you will go to verse 15.

Abib v410.1
Commentary removed because not ready yet.
First version on GitHub.

Abib409
Two extra arguments allowed for window width and window height.
Possibly two more for window origin, which could be calculated depending on screen size.
Re-write of the F2 display reference section, because the code was hard to understand,
now it is easier to follow and more intuitive to use.
Introduced a sound for errors using the pygame library.
Allowed use of roman numerals in text input references.
Bound single integer entries to apply to the same chapter only.
Changed the ABOUT.txt window to have THE HOLY BIBLE title page.
Much, much more debugging and testing, e.g. miv.ii resolves to Micah 4:2 not 1004.2

Abib408
Devotional, Commentary, and a blank button are added.
The Commentary button is for future use.
Buttons rearranged to accommodate new ones.
Spurgeon's Morning and Evening Readings added.
Some improvements to the F2 reference entry section
(allows "--Eph. 5.12....... ").

Abib407
Text highlighting colour bug fixed.
'OK' button for Display verse text entry is added.

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
F2 passage entry invalid text before and after valid entry is now ignored.

Abib403
Splash screen added.
Ensured focus is in the F2 display verse text entry box.

Abib402
Some refactoring and bugfixes.

Abib401
Removed acoustic guitar intro.
Removed all error sounds.
Error messages remain in the status bar a little longer.
Adjustment to Copyright, README, and HELP windows size.

Abib400
Much refactoring of the code.
Possible improvement to the startup time.
Changes to the error sounds.
Short acoustic guitar intro. (To be removed).

Abib399
There is no 399.

Abib398
Corrected many bugs concerning search keys with words that are not in the text.
Rationalised some of the book abbreviations.
Assured centering of the Abib window on startup.
Also, of some of the other windows except.

Abib397
Changes to About, Help, Readme, and Copyright windows.

Abib396
Python 3.13.1 updated version
No real changes

Abib395
Changes to the 'About' window.
Corrected problems with 'Any of the words' search.

Abib394
Is a test version of 393 to check that the installation is correct.

Abib393
Blank lines placed at the end of Revelation to prevent a glitch.

Abib392 (Numbering changed to conform with the Python standards).
Built with Python3.13.0 and PySide6.
Extensively refactored.  Nothing major to the logic.
Except:
Bugfix correcting Back and especially Forward not working properly.

Another bug fixed regarding the following verses; Joshua 15:1,Job 7:1, Psalm 70:1, Psalm 92:1, Hosea 8:1, and
Romans 8:1.  These are all first verses of chapters that start with italicised first words and were displayed
incorrectly when viewed using Back and Forward.

Some changes to the way that the Find process works and to the highlighting of the search key.

Abib3.9.1b
Built with Python11.1 and Pyside6 to make the operation faster.
Some changes to the Help Menu.

Abib3.8.5b
Found and corrected a bug preventing, whole word, searches containing
the single letter words "A", "I" and "O".
Fixed the bug preventing a "Whole word" search for words containing a
hyphen, e.g. Beth-lehem.  Will now work with or without the hyphen.
However, Raw searches still require the hyphen.
Some adjustments were made to improve search highlighting.

Abib3.8.4b
Change of sound for 'Not found'
Bug removed around AE and Æ in searches.

Program altered to allow the first or only command line argument,
which will be interpreted as the default font size for the Bible.

This is how to use it (The default font size is 14):

    1) Right-click on the Abib desktop shortcut icon and click on
       Properties.

    2) In the Target text box, leave what is there unchanged, except
       after it put a space then the default font size that you want.
       Like this:

        "C:\Program Files\Abib\Abib.exe" 11 width height

       Here width and height can be adjusted from default values.

    3) Click on Apply, then Continue for Administrative permission, and
       then OK.

    4) If you have another shortcut in the taskbar, you will need to
       unpin it and drag another one there, or Abib will not start up
       with the new default font size.

Abib3.8.3b
Changed the default font to a smaller size, can be adjusted with Ctrl &
mouse wheel.
Fixed the bug affecting highlighting after 'Find' and using passage
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

You will find it here in the 'C:\Program Files\Abib\font' folder.
It is called CascadiaMono and is a Truetype font which works with
Microsoft Windows.

How to install the Cascadia Mono font.
--------------------------------------

For Windows 10: Type 'fonts' into the search box.

Click on Font settings.

Under Add fonts, there is a Drag and Drop to install box.

In 'File Explorer' navigate to 'C:\Program Files\Abib\font' and
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
system, including Ubuntu. For the latter, double-click on the .ttf
file to open the font manager/preview tool. Hit ‘install’ to install it
on your system.  Thanks to Hal.

Installing the Abib Bible App.
------------------------------

If you have Windows, the installer provided will simply install
everything, just double-click on it, and follow the instructions.

For Linux, copy the whole C:\Program Files\Abib folder to a
USB key and then do the following:

Suppose your username is Andrew or rather andrew, your USB key will most
likely be mounted under /media/andrew/a_volume_name. So first, you need
to get this full path. You can store it in a shell variable to make it easy:

ls /media/andrew

The usb mount point is variable. /media is deprecated in many modern OS. 
Run mount to find the mount point.

See or find the right entry in the output and now save it in the source
directory variable (s_dir):

s_dir=/media/andrew/my_usb_drive

Of course, replace my_usb_drive with the right name. Once you have this,
enter this command:

cp -r "$s_dir"/Abib /home/andrew/.Abib

Possibly /home/username/.Abib where 'username' is replaced with your
linux username.

Now you can run it by navigating to that folder and doing:

$ python Abib.py

God Bless you.

Photo Credit: Abibofgod.com for the splash screen.

Spurgeon's Morning and Evening Readings obtained from www.spurgeon.org.
Reformatted by Eternal Life Ministries.
Additional Bible-based resources are available at www.spurgeongems.org.

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

Developer notes: Scripture reference indexing
-------------------------------------------
Abib’s scripture utilities use a 1-based contract for all public inputs and outputs:
- resolve_reference(...) returns (book, chapter, verse) as 1-based integers when available.
- calculate_book_line(book, chapter, verse, ...) expects 1-based integers.
Internally, these are converted to 0-based indices only for lookup into shared.Info, which
stores triples as [book_id, chapter_idx, verse_idx] with 0-based indexing.

Examples
- resolve_reference(["Genesis", "1", "1"]) -> (1, 1, 1)
- calculate_book_line(1, 1, 1, _) -> index of [0, 0, 0] in shared.Info
