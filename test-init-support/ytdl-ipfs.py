#!/usr/bin/python3

#
# Program to scrape videos from youtube and add to IPFS
#
from __future__ import unicode_literals
from youtube_dl import utils
import youtube_dl
import os

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = "/home/ipfs"
IPFS = HOME + "/scripts/add2IPFS"
DLBNEW = HOME + "/ytDLn/"

GrpList = [
    'lukewearechange', 'wearechange', 'wearechange.org', 'press4truth',
    'worldaltmedia', 'truthstream'
]

# Return the first video file found (.mp4 or .webm) otherwise None.
# Also remove any partially downloaded video files (.part extn).
def getVideo(dir):
    out = None
    fList = os.listdir(dir)
    for file in fList:
        (fil_, ext) = os.path.splitext(file)  # Strip extension from file name
        if ext == '.mp4' or ext == '.webm':
            out = dir + '/' + file
        elif ext == '.part':
            os.remove(dir + '/' + file)
    return out

# Walk ALL folders for each group and add the video and json metadata to ipfs
for group in GrpList:
    i = 0
    for subdir, dirs, files in os.walk(DLBNEW + group):
        for dir in dirs:
            target = subdir + '/' + dir
            video = getVideo(target)
            if video != None:
                parts = os.path.splitext(video.rsplit('/', 1)[1])
                args = target + ' ' + group + ' ' + parts[0] + ' ' + parts[1]
                os.system(IPFS + ' ' + args)
#                break
            else: print("No video: " + target)
        os.system("cd " + DLBNEW + group + "; ipfs add groupHashes.txt > indexHash.txt 2> /dev/null")
        break
    break

exit(0)


