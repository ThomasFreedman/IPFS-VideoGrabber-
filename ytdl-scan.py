#!/usr/bin/python3

#
# Program to delete video files from those already added to IPFS
#
from __future__ import unicode_literals
import time
import os

TheList = []        # List of folders with a .part (partial) video file

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBASE = HOME + '/ytDL/'
BYEBYE = DLBASE + 'vidsDeleted.log'

DELETE = ['.mp4', '.webm']  # Delete files with these extentions

UrlList = {
    'lukewearechange': ['https://www.youtube.com/user/lukewearechange/videos'],
    'wearechange':     ['https://www.youtube.com/user/wearechange/videos'],
    'truthstream':     ['https://www.youtube.com/user/TRUTHstreammedia/videos'],
#    'wearechange.org': ['https://wearechange.com'],
    'press4truth':     ['https://www.youtube.com/user/weavingspider/videos'],
    'worldaltmedia':   ['https://www.youtube.com/channel/UCLdZo0Mkh_z2IQZSmD8Iy0Q/videos'],
}


# Look for .mp4 and .webm files and return True if either is found.
def findVideo(dir):
    fList = os.listdir(dir)
    found = False
    os.system("cd " + dir + "; rm -rf " + "*.txt")
    for file in fList:
        (fil_, ext) = os.path.splitext(file)  # Strip extension from file name
        if ext in DELETE:
            found = True
            os.remove(dir + '/' + file)
    return found

# Walk ALL folders and find problems we need to revisit
for group in UrlList:
    for subdir, dirs, files in os.walk(DLBASE + group):
        for dir in dirs:
            target = subdir + '/' + dir
            if findVideo(target):
                TheList.append(target)

# Found these:
print("%d files deleted\n" % len(TheList))

with open(BYEBYE, mode='a+') as log:   # Write the log
    for item in TheList:
        log.write(item + '\n')
#        log.write("rm -rf " + item + "/*.mp4\n")

#for i in TheList:
#    print(i)

exit(0)
