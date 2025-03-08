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
