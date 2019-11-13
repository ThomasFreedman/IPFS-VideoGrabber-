These python3 scripts use the youtube-dl module and sqlite along with IPFS to download videos and store them in IPFS. The metadata for each video is stored in the sqlite database, and can be used to search for any video based on over 60 criteria. It will provide 2 IPFS hashes for each video: 1) the video and 2) the metadata file in JSON format.

Youtube-dl is both a python module as well as a command line program that uses it. It os cross-platform, and capable of automating the download of videos from several sources including youtube, vimeo and even bitchute. Probably others as well.

These scripts are rather crude, and require the user to edit the python code to specify the list of URLs and qualifying criteria for videos to download and the IPFS repository to store them in. The basic script can be found in the VideoGrabber repo where this file is found.

My most recent plans were to create a "Pirate Box" for Ernest Hancock as a repository for his family to share their photos etc privately (so they could stop putting all their info into facebook). I have determined the basic infrastructure for such a private IPFS network was possible, and files added on any node would be available from all other nodes that shared the same swarm key (a hash that all nodes in the private network must use). I was going to use Zenity to create a basic GUI to perform queries and insert individual files into IPFS. On Sept 19th I outlined the approach I was planning in a Telegram DM to Ernie:

1) No need to worry about an installer right now, just use the SD card as delivery mechanism. Prototype becomes product faster that way.

2) Only "installer" chores required are setting up brand new SSD for use as a local IPFS repository.

3) Create a simple GUI based on Zenity, write all code in Python3.

4) Use SQLite database as search index for all info added to private IPFS on SSD drive.

5) Ability to search, fetch files or folders of files based on hash or database search (which has related hash[s]).

6) Launch appropiate viewer (VLC for images and videos, file manager for folders, others based on file extention).

7) Create ability to save YT/vimeo/Bitchute videos via Zenity GUI. User enters the URL for a video or playlist, and possibly some very basic qualification criteria such as publish date.

I also established that it is possible to create a public IPFS repo and grab videos, then convert it to a private one rather easily. This breaks the IPFS web interface, so that must be installed after the conversion, if you want it on the private network.

That was the last thing I accomplished before my putting the project aside to deal with health issues.
