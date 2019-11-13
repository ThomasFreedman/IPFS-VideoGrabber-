#!/usr/bin/python3

#
# Program to scrape videos from youtube and add to IPFS
#
from __future__ import unicode_literals
from youtube_dl import utils
#from subprocess import PIPE
from math import floor
import youtube_dl
import subprocess
import time
import os
import re

downloadedList = [] # List of downloaded file names, used by dl callback
missingList = [] # List of folders without an .mp4 video file

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBASE = HOME + '/ytDL/'
DLBNEW = HOME + '/ytDLn/'
BADLST = DLBASE + 'aaBadList.log'
FILZ = DLBASE + 'aaDList.log'
LOG = DLBASE + 'ytDL_IDs.log'

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
    'outtmpl': DLBASE + "/%(id)s_%(upload_date)s/%(duration)ss_%(resolution)s_%(id)s.%(ext)s",
    'progress_hooks': [callback],
    'merge-output-format': 'mkv',
    'restrictfilenames': True,
    'writedescription': True,
#    'writeinfojson': True,
    'ignoreerrors': True,
    'skip_download': True,
    'format': 'best',
    'download_archive': LOG
#    'postprocessors': [{
#        'key': 'FFmpegExtractAudio',
#        'nopostoverwrites': True,
#        'preferredcodec': 'mp3'
#    }],
}

#for group in UrlList:
#    if not os.path.isdir(DLBASE + group):
#        os.mkdir(DLBASE + group)
#
#exit(0)

def mp4Inside(dir):
    fList = os.listdir(dir)
    found = False
    for file in fList:
        (fil_, ext) = os.path.splitext(file)  # Strip extension from file name
        if ext == '.mp4' or ext == '.webm':
            found = True
            break
    return found

for group in UrlList:
    i = 0
    for subdir, dirs, files in os.walk(DLBNEW + group):
        for dir in dirs:
            i += 1
            print("\r%-24s%d" % (group, i), end='')
            if i >= len(dirs): print("")
            os.system("rm -rf " + DLBASE + dir)

#            print("mv " + DLBASE + dir + '/* ' + subdir + '/' + dir + '/.')
#            i += 1
#            if i > 5: break

#        print("%s : %d" % (group, len(dirs)))
#        i -= 10
#        if i < 0: break

exit(0)

#for subdir, dirs, files in os.walk(DLBASE):
#    if not mp4Inside(subdir):
#        missingList.append(dir)

#print("%d errors (no mp4 file) found" % len(missingList))

#with open(BADLST, mode='a+') as bad:
#    for item in missingList:
#        bad.write(item + '\n')

#exit(0)

#    for dir in dirs:
#        print(dir)

#exit(0)

#with youtube_dl.YoutubeDL( {'progress_hooks': [callback]} ) as ydl:
with youtube_dl.YoutubeDL(commonOpts) as ydl:
    for group in UrlList:
        if not os.path.isdir(DLBASE + group):
            os.mkdir(DLBASE + group)
        ydl.params['outtmpl'] = DLBASE + group + Dest
        print(ydl.params['outtmpl'])
        ydl.download(UrlList[group])
#        ydl.download(TstList)

#with youtube_dl.main(OPTS) as ydl:
#        ydl.YoutubeDL( {'progress_hooks': [callback]} ).download()
#        ydl.download()

###print("Callback DL list size: %d" % len(downloadedList))

#
# We could add the files to IPFS as a post-process step here:
#
with open(FILZ, mode='a+') as log:   # Write the log
    for item in downloadedList:
        log.write(item + '\n')

exit(0)

