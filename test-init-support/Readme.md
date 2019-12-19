Newest additions are checkPins.py, ytdl-getGrupes.py and ytdl-config.json. 

checkPins.py

Is used to verify and fetch video and metadata files in the SQLite database. It obtains a list of pins from IPFS using the subprocess module, pipeing STDOUT from "ipfs pin ls --type=recursive" command to run as subprocess. This is runs very fast. For evey pin in that list found in the SQLite database, the episode_number and season_number fields are updated with the metadata and video hashes, respectively. 

When the verify phase is complete the user is asked whether to obtain the missing files. If 'y' is entered an attempt is made to fetch the files with youtube-dl for the url found in SQLite's "webpage_url" column. Upon success that row is updated the newer hashes and marked verified as described above.

Errors encountered for the fetch phase are logged to a file.

ytdl-getGrupes.py

This is a refactored version of the video grabber. It no longer uses the add2IPFS bash script and os.system to add files to IPFS. Instead it uses the python3 "subprocess" module to accmplish adding files to IPFS, which is faster and provides a 100% python3 integration.

In addition, the separate commonKeys.json file is no longer used to define the list of metadata fields for SQLite's schema. Instead, this list of metadata columns is provided in the new ytdl-config.json file, along with other settings such as the list of grupes and their URL(s) to download, where in the filesystem to put them, log files and youtube-dl options.

ytdl-config.json

This is an example configuration file for the ytdl-getGrupes.py program. You no longer need to edit python code to use the downloader. At some point a GUI tool will create such a config file from user input to eliminate editing files completely.  
