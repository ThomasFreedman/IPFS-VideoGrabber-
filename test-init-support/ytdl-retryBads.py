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
badList = []        # List of problematic folders found by ytdl-scan.py

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBNEW = HOME + '/ytDLn/'
REDO = DLBNEW + 'retryURLs.log'
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
    'writedescription': True,
    'writeinfojson': True,
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

for line in list(open(BAD, 'r')):
    badList.append(line)

# Found these problems:
print("%d items in badList\n" % len(badList))
#for x in badList:
#    print(x.strip('\n'))
#exit(0)

# Now construct a new dictionary to retry those problems:
for line in badList:
    g = line.split('/')
    id = g[5].rsplit('_', 1)
    url = "https://www.youtube.com/watch?v=" + id[0]
    if g[4] not in RedoList: RedoList[ g[4] ] = [ url ]
    else: RedoList[ g[4] ].append(url)
#    print("Date=%s g=%s id=%s" % (id[1].strip('\n'), g[4], id[0]))

# Save the dictionary to disk. Should probably use JSON for this
#with open(REDO, mode='w') as red:   # Write the log
#    for group in RedoList:
#        red.write("'%s': [\n" % group)
#        for url in RedoList[group]:
#            red.write("    '%s',\n" % url)
#        red.write("],\n")
#exit(0)

with youtube_dl.YoutubeDL(commonOpts) as ydl:
    for group in RedoList:
        ydl.params['outtmpl'] = DLBNEW + group + Dest
        ydl.download(RedoList[group])

exit(0)

