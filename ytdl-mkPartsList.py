#!/usr/bin/python3

#
# Program to scrape videos from youtube and add to IPFS
#
from __future__ import unicode_literals
import time
import json
import os

PartsList = []        # List of folders with a .part (partial) video file

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBASE = HOME + '/ytDL/'
PARTS  = DLBASE + 'parts.log'
JSON   = DLBASE + 'retry.json'

Targets = {
    'lukewearechange': ['https://www.youtube.com/user/lukewearechange/videos'],
    'wearechange':     ['https://www.youtube.com/user/wearechange/videos'],
#    'wearechange.org': ['https://wearechange.com'],
    'press4truth':     ['https://www.youtube.com/user/weavingspider/videos'],
    'worldaltmedia':   ['https://www.youtube.com/channel/UCLdZo0Mkh_z2IQZSmD8Iy0Q/videos'],
    'truthstream':     ['https://www.youtube.com/user/TRUTHstreammedia/videos']
}
RedoList = {}

# Remove any partially downloaded video files (.part extention) and
# return True or False, depending on presence of such files.
def partVideo(dir):
    fList = os.listdir(dir)
    found = False
    for file in fList:
        (fil_, ext) = os.path.splitext(file)  # Strip extension from file name
        if ext == '.part':
            found = True
    return found

# Walk ALL folders and find problems we need to revisit
GrpList = Targets
for group in GrpList:
    for subdir, dirs, files in os.walk(DLBASE + group):
        for dir in dirs:
            target = subdir + '/' + dir
            if partVideo(target):
                PartsList.append(target)

# Found these problems:
print("%d items in PartsList:\n" % len(PartsList))

# Now construct a new dictionary to retry those problems:
for line in PartsList:
    g = line.split('/')
    id = g[5].rsplit('_', 1)
    url = "https://www.youtube.com/watch?v=" + id[0]
    if g[4] not in RedoList: RedoList[ g[4] ] = [ url ]
    else: RedoList[ g[4] ].append(url)
#    print("Date=%s g=%s id=%s" % (id[1].strip('\n'), g[4], id[0]))

with open(JSON, 'w') as fp:
    json.dump(RedoList, fp)

#with open(PARTS, mode='w+') as log:   # Write the log
#    for item in PartsList:
#        log.write(item + '\n')

exit(0)

