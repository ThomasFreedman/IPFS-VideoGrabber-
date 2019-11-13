#!/usr/bin/python3

#
# Program to scrape videos from youtube and add to IPFS
#
from __future__ import unicode_literals
from youtube_dl import utils
from math import floor
import youtube_dl
import time
import os
import re

downloadedList = [] # List of downloaded file names, used by dl callback
missingList = [] # List of folders without an .mp4 video file

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBNEW = HOME + '/ytDLn/'
LOG = DLBNEW + 'ytDL_IDs.log'

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
RedoList = {}

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
def mp4Inside(dir):
    fList = os.listdir(dir)
    found = False
    for file in fList:
        (fil_, ext) = os.path.splitext(file)  # Strip extension from file name
        if ext == '.part':
            os.remove(file)
        if ext == '.mp4' or ext == '.webm':
            found = True
#            break
    return found

#if partVideo("/home/ipfs/ytDLn/worldaltmedia/WO2vK6TtGv0_20190105/"):

# Walk ALL folders and find problems we need to revisit
for group in UrlList:
    i = 0
    for subdir, dirs, files in os.walk(DLBNEW + group):
        for dir in dirs:
            target = subdir + '/' + dir
            if not mp4Inside(target):
                missingList.append(target)

# Found these problems:
print("%d items in missingList\n" % len(missingList))

# Now construct a new dictionary to retry those problems:
for line in missingList:
    g = line.split('/')
    id = g[5].rsplit('_', 1)
    url = "https://www.youtube.com/watch?v=" + id[0]
    if g[4] not in RedoList: RedoList[ g[4] ] = [ url ]
    else: RedoList[ g[4] ].append(url)
#    print("Date=%s g=%s id=%s" % (id[1].strip('\n'), g[4], id[0]))

with youtube_dl.YoutubeDL(commonOpts) as ydl:
    for group in RedoList:
        ydl.params['outtmpl'] = DLBNEW + group + Dest
        ydl.download(RedoList[group])

exit(0)

