#!/usr/bin/python3

#
# Program to scrape videos from youtube and add to IPFS
#
from __future__ import unicode_literals
from youtube_dl import utils
import youtube_dl
import time
import os
import re

downloadedList = [] # List of downloaded file names, used by dl callback
badList = []        # List of folders with a .part (partial) video file

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBNEW = HOME + '/ytDLn/'
LOG = DLBNEW + 'ytDL_IDs.log'
BAD = DLBNEW + 'parts.log'

Dest = "/%(id)s_%(upload_date)s/%(duration)ss_%(resolution)s_%(id)s.%(ext)s"

UrlList = {
    'lukewearechange': ['https://www.youtube.com/user/lukewearechange/videos'],
    'wearechange':     ['https://www.youtube.com/user/wearechange/videos'],
    'wearechange.org': ['https://wearechange.com'],
    'press4truth':     ['https://www.youtube.com/user/weavingspider/videos'],
    'worldaltmedia':   ['https://www.youtube.com/channel/UCLdZo0Mkh_z2IQZSmD8Iy0Q/videos'],
    'truthstream':     ['https://www.youtube.com/user/TRUTHstreammedia/videos']
}
TstList = ["https://www.youtube.com/playlist?list=PLNE1ZEvllnmjuUUH5AdmyXoYqCaqtNomN"]
UrlLisT = {
    'test1': [ # Short items for testing
        'https://www.youtube.com/playlist?list=PLNE1ZEvllnmjuUUH5AdmyXoYqCaqtNomN'
    ],
    'test2': [
        'https://www.youtube.com/watch?v=wuc6MpHjp8w'
    ]
}

# Guaranteed to be called at least once per download.
def callback(d):
    if d['status'] == 'finished':
        downloadedList.append(d['filename'])
        print('>>>>> Download Complete!\n')

# Options common to all downloads
commonOpts = {
    'outtmpl': DLBNEW + "/%(id)s_%(upload_date)s/%(duration)ss_%(resolution)s_%(id)s.%(ext)s",
    'progress_hooks': [callback],
    'merge-output-format': 'mkv',
    'restrictfilenames': True,
#    'writedescription': True,
#    'writeinfojson': True,
    'ignoreerrors': True,
    'continuedl': False,
#    'skip_download': True,
    'format': 'best',
    'download_archive': LOG
#    'postprocessors': [{
#        'key': 'FFmpegExtractAudio',
#        'nopostoverwrites': True,
#        'preferredcodec': 'mp3'
#    }],
}

# Look for .mp4 and .webm files and return True if either is found.
# Also remove any partially downloaded video files (.part extn).
def partVideo(dir):
    fList = os.listdir(dir)
    found = False
    for file in fList:
        (fil_, ext) = os.path.splitext(file)  # Strip extension from file name
        if ext == '.part':
            found = True
    return found

#if partVideo("/home/ipfs/ytDLn/worldaltmedia/WO2vK6TtGv0_20190105/"):

# Walk ALL folders and find problems we need to revisit
for group in UrlList:
    i = 0
    for subdir, dirs, files in os.walk(DLBNEW + group):
        for dir in dirs:
            target = subdir + '/' + dir
            if partVideo(target):
                badList.append(target)

# Found these problems:
print("%d items in badList:\n" % len(badList))

#with open(BAD, mode='w') as log:   # Write the log
#    for item in badList:
#        log.write(item + '\n')

for bad in badList:
    print(bad)

exit(0)

