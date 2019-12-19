These python3 scripts use the youtube-dl module and sqlite along with IPFS to download videos and store them in IPFS. The metadata for each video is stored in the sqlite database, and can be used to search for any video based on over 60 criteria. It will provide 2 IPFS hashes for each video: 1) the video and 2) the metadata file in JSON format.

Youtube-dl is both a python module as well as a command line program that uses it. It is cross-platform, and capable of automating the download of videos from over 1000 sources including youtube, vimeo and bitchute.

Most of the scripts in this folder are originals and obsolete. They require the user to edit the python code to specify the list of URLs and qualifying criteria for videos to download and the IPFS repository to store them in. They also require an external file to specify metadata columns. 

Newer, renamed and refactored versions can be found in the init-test-support folder. ytdl-getGrupes.py no longer uses the shell to add files to IPFS, but instead uses the "subprocess" module to do so, which is more efficient and provides a tighter integration. A single JSON config file allows configuring all but 2 options (the sqlite database file and the JSON config file), inluding various log pathnames, youtube-dl download options, the list of grupes and their URLs to download, and the metadata columns for SQLite.

My plans to create a "Pirate Box" for Ernest Hancock as a repository for his family to share their photos etc privately (so they could stop putting all their info into facebook) are currently on hold, pending downloading videos related to my medical research. I will resume that effort after completing that and a GUI tool to query SQLite to locate videos of interest and launch a viewer. That work will be directly applicable to Ernie's pirate box.

I have determined the basic infrastructure for such a private IPFS network was possible, and files added on any node would be available from all other nodes that shared the same swarm key (a hash that all nodes in the private network must use). I was going to use Zenity to create a basic GUI to perform queries and insert individual files into IPFS. On Sept 19th I outlined the approach I was planning in a Telegram DM to Ernie:

1) No need to worry about an installer right now, just use the SD card as delivery mechanism. Prototype becomes product faster that way.

2) Only "installer" chores required are setting up brand new SSD for use as a local IPFS repository.

3) Create a simple GUI based on Zenity, write all code in Python3.

4) Use SQLite database as search index for all info added to private IPFS on SSD drive.

5) Ability to search, fetch files or folders of files based on hash or database search (which has related hash[s]).

6) Launch appropiate viewer (VLC for images and videos, file manager for folders, others based on file extention).

7) Create ability to save YT/vimeo/Bitchute videos via Zenity GUI. User enters the URL for a video or playlist, and possibly some very basic qualification criteria such as publish date.

However, I have since learned of a far more robust way to create a GUI 100% in python with the python-tk module. I have no experience using it but have reviewed its' API and looks (relatively) easy, and far more capable than Zenity. 

I also established that it is possible to create a public IPFS repo and grab videos, then convert it to a private one rather easily. This breaks the IPFS web interface, so that must be installed after the conversion, if you want it on the private network.

That was the last thing I accomplished before my putting the project aside to deal with health issues.
