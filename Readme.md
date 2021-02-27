# ytdl-videoGrabber.py
## NOTE (May 18th, 2020): 
Many changes have been done, including the use of threads to process each video and emailing results. 

These python3 scripts use the youtube-dl module and sqlite along with IPFS to download videos and store them in IPFS. The metadata for each video is stored in the sqlite database, and can be used to search for any video based on over 60 criteria. It will provide 2 IPFS hashes for each video: 1) the video and 2) the metadata file in JSON format.

Youtube-dl is both a python module as well as a command line program that uses it. It is cross-platform, and capable of automating the download of videos from over 1000 sources including youtube, vimeo and bitchute.

The scripts in this folder are the newest versions refactored and improved from those in the subfolders. The originals  required the user to edit the python code to specify the list of URLs and qualifying criteria for videos to download and the IPFS repository to store them in. They also require an external file to specify metadata columns. All editing for specifying the download operation is now done in a single JSON formated configuration file, found here in the config subfolder.

Newer, renamed and refactored versions can be found in this folder. ytdl-videoGrabber.py no longer uses the shell to add files to IPFS, but instead uses the "subprocess" module to do so, which is more efficient and provides a tighter integration. A single JSON config file allows configuring all but 2 options (the sqlite database file and the JSON config file), inluding various log pathnames, youtube-dl download options, the list of grupes and their URLs to download, and the metadata columns for SQLite.

As of December 2019 I have save over 11,000 videos in IPFS. I am turning my focus towards a search tool with a GUI front end. That will directly be applicable to Earnie's "Pirate Box". 

# Pirate Box
My plans to create a "Pirate Box" for Ernest Hancock as a repository for his family to share their photos etc privately (so they could stop putting all their info into facebook) are currently on hold, pending completion of the GUI search tool. 

I have determined the basic infrastructure for such a private IPFS network was possible, and files added on any node would be available from all other nodes that shared the same swarm key (a hash that all nodes in the private network must use). I was going to use Zenity to create a basic GUI to perform queries and insert individual files into IPFS. On Sept 19th I outlined the approach I was planning in a Telegram DM to Ernie:

1) No need to worry about an installer right now, just use the SD card as delivery mechanism. Prototype becomes product faster that way.

2) Only "installer" chores required are setting up brand new SSD for use as a local IPFS repository.

3) Create a simple GUI based on ~~Zenity~~, write all code in Python3 -- **UPDATED**, see below.

4) Use SQLite database as search index for all info added to private IPFS on SSD drive.

5) Ability to search, fetch files or folders of files based on hash or database search (which has related hash[s]).

6) Launch appropiate viewer (VLC for images and videos, file manager for folders, others based on file extention).

7) Create ability to save YT/vimeo/Bitchute videos via GUI. User enters the URL for a video or playlist, and possibly some very basic qualification criteria such as publish date.

However, I have since learned of a far more robust way to create a GUI 100% in python with the ~~python-tk~~ PySimpleGUI module. I have only played around with for a day but love it! It's far more capable than Zenity and will be fun creating a GUI search tool. 

I also established that it is possible to create a public IPFS repo and grab videos, then convert it to a private one rather easily. This breaks the IPFS web interface, so that must be installed after the conversion, if you want it on the private network.

That was the last thing I accomplished before my putting the project aside to deal with health issues. As of 12-31-2019 I must put coding aside again (just when it was getting fun too) to focus on my health. Be back at it when I can.

## UPDATE (Feb268th, 2021):
I have completed the preliminary search GUI app which is found in the pboxSearch folder. Rudimentary, proof of concept without IPFS integration.
I have also updated the ytdlVideoGrabber files with most recent tweaks & changes which are relatively minor functionally.
