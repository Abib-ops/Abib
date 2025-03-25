************
ABIB README:
************

Description.
------------

Abib Bible Reader is a Bible reading tool which allows you to quickly move to different Bible references, 
useful when following an online sermon, the screen footprint is low and fully adjustable. 
There is a comprehensive 'Find' facility, and Spurgeon's Morning and Evening Readings is included.
Although further features are being planned, it is fully operational in its current state. 
(By Donna and me)

The Abib Bible Reader is a simple tool designed to make Bible reading easier and more convenient. 
It allows you to quickly move between different Bible references, 
which can be particularly helpful when following along with an online sermon. 
The interface is compact and adjustable, so it can fit neatly on your screen without taking up too much space.
It also includes a handy search feature to help you find specific passages quickly, 
as well as Spurgeon's _Morning and Evening_ readings for daily inspiration. 
While there are plans to add more features in the future, 
Abib Bible Reader is fully functional and ready to use as it is. 
(By GPT-4o)

**Discover the Abib Bible Reader** – a powerful, user-friendly tool designed to enhance your Bible reading experience. 
Effortlessly navigate to any Bible reference in seconds, 
making it a perfect companion for online sermons or personal study. 
Its compact, 
adjustable interface ensures it fits seamlessly into your workflow without taking up unnecessary screen space.
Enjoy the convenience of a comprehensive search feature to quickly locate specific verses or passages. 
Plus, deepen your spiritual journey with included readings from Spurgeon's uplifting _Morning and Evening_ devotionals.
Fully operational and ready for use, Abib Bible Reader is continually improving with exciting features on the horizon. 
Start using it today and transform the way you read, study, and engage with the Bible!
(Also GPT-4o in less humble mode)


Installing the Abib Bible App.
------------------------------

If you have Windows, the installer provided will simply install everything, just double-click on it, and follow the instructions.

There may be a Linux executable available soon, but for the present, please use the source code to run with Python. 

So, on Linux, if you have Windows, copy the whole 'C:\Program Files\Abib' folder to a USB key and then do the following:

Suppose your username is andrew, your USB key may be mounted under '/media/andrew/a_volume_name'. 
So first, you need to get this full path. 
You can store it in a shell variable to make it easy:

ls /media/andrew

The usb mount point is variable and '/media' is deprecated in many modern Linux distributions.

Run mount to find the mount point.

See or find the right entry in the output, and now save it in the source directory variable (s_dir):

s_dir=/media/andrew/my_usb_drive

Of course, replace my_usb_drive with the right name. Once you have this, enter this command:

cp -r "$s_dir"/Abib /home/andrew/.Abib

Possibly /home/username/.Abib where username is replaced with your linux username.

Now you can run it by navigating to that folder and doing:

$ python Abib.py

------------------
Cascadia Mono font
------------------

Please ensure that the Cascadia Mono font is installed on your device. 
This will provide the designed appearance. 
(You can do this before or after you install Abib.)

You will find it in the 'C:\Program Files\Abib\font' folder. It is called CascadiaMono and is a Truetype Microsoft Windows font.

How to install the Cascadia Mono font.
--------------------------------------

For Windows 10: Type 'fonts' into the search box.

Click on Font settings.

Under Add fonts, there is a Drag and Drop to install box.

So, using File Explorer, go to 'C:\Program Files\Abib\font' and there you will see the file CascadiaMono.ttf. 
Drag the CascadiaMono file, from inside the font folder, into the box, and it will install automatically.

If the font is installed already, you will do no harm, you will be warned with a message and can cancel.

For Windows 11: Do nothing, the CascadiaMono font is built in.

For arch-based linux distros.
-----------------------------

Do this:

$ sudo pacman -S ttf-cascadia-code

For other distributions, you can find the Cascadia Code font as a standard .ttf at:

https://github.com/microsoft/cascadia-code/releases

The file above can be installed on most modern operating systems, including Ubuntu. 
For the latter, just double-click on the .ttf file to open the font manager/preview tool. 
Hit ‘install’ to install on your Ubuntu system. 
Thanks to Hal.


God Bless you.


Photo Credit: Abibofgod.com for the splash screen.

Spurgeon's Morning and Evening Readings Obtained from www.spurgeon.org.
Reformatted by Eternal Life Ministries.
Additional Bible-based resources are available at www.spurgeongems.org.

Copyright 2025 Andrew Kingston

This file is part of Abib Bible Reader.

Abib is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

Abib is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with Abib.  If not, see <https://www.gnu.org/licenses/>.
