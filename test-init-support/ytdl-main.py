#!/usr/bin/python3

#
# Program to scrape videos from youtube and add to IPFS
#
from __future__ import unicode_literals
from youtube_dl import utils
import youtube_dl
import os

downloadedList = [] # List of downloaded file names, used by dl callback
Grp = ''            # Global var used by callback for root of group

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBASE = HOME + '/ytDL/'
FILZ = DLBASE + 'aaDList.log'
LOG = DLBASE + 'ytDL_IDs.log'

Dest = "/%(id)s_%(upload_date)s/%(duration)ss_%(resolution)s_%(id)s.%(ext)s"

Targets = {
    'lukewearechange': ['https://www.youtube.com/user/lukewearechange/videos'],
    'wearechange':     ['https://www.youtube.com/user/wearechange/videos'],
    'wearechange.org': ['https://wearechange.com'],
    'press4truth':     ['https://www.youtube.com/user/weavingspider/videos'],
    'worldaltmedia':   ['https://www.youtube.com/channel/UCLdZo0Mkh_z2IQZSmD8Iy0Q/videos'],
    'truthstream':     ['https://www.youtube.com/user/TRUTHstreammedia/videos']
}
TstList = ["https://www.youtube.com/playlist?list=PLNE1ZEvllnmjuUUH5AdmyXoYqCaqtNomN"]
TestTwo = {
    'test1': [ # Short items for testing
        'https://www.youtube.com/playlist?list=PLNE1ZEvllnmjuUUH5AdmyXoYqCaqtNomN'
    ],
    'test2': [
        'https://www.youtube.com/watch?v=wuc6MpHjp8w'
    ]
}

# Guaranteed to be called at least once per download.
def callback(d):
    global Grp
    if d['status'] == 'finished':
        downloadedList.append(d['filename'])
        print('>>>>> Download Complete!\n')

# Options common to all downloads
commonOpts = {
    'outtmpl': DLBASE + "/%(id)s_%(upload_date)s/%(duration)ss_%(resolution)s_%(id)s.%(ext)s",
    'progress_hooks': [callback],
    'merge-output-format': 'mkv',
    'restrictfilenames': True,
    'writedescription': True,
    'writeinfojson': True,
    'ignoreerrors': True,
#    'skip_download': True,
    'format': 'best',
    'download_archive': LOG
}

#UrlList = Targets
UrlList = TestTwo
#UrlList = {'truthstream': ['https://www.youtube.com/user/TRUTHstreammedia/videos']}
with youtube_dl.YoutubeDL(commonOpts) as ydl:
    for group in UrlList:
        if not os.path.isdir(DLBASE + group):
            os.mkdir(DLBASE + group)
        ydl.params['outtmpl'] = DLBASE + group + Dest
        print("BEGIN " + group)
        Grp = DLBASE + group
        ydl.download(UrlList[group])

#
# We could add the files to IPFS as a post-process step here:
#
with open(FILZ, mode='a+') as log:   # Write the log
    for item in downloadedList:
        log.write(item + '\n')

exit(0)

