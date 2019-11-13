#!/usr/bin/python3

#
# Program to scrape videos from youtube and add to IPFS
#
from __future__ import unicode_literals
import json
import os

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBASE = HOME + '/ytDL/'
COMMON = DLBASE + 'commonJsonKeys.txt'

UrlList = {
    'lukewearechange': ['https://www.youtube.com/user/lukewearechange/videos'],
    'wearechange':     ['https://www.youtube.com/user/wearechange/videos'],
    'press4truth':     ['https://www.youtube.com/user/weavingspider/videos'],
    'worldaltmedia':   ['https://www.youtube.com/channel/UCLdZo0Mkh_z2IQZSmD8Iy0Q/videos'],
    'truthstream':     ['https://www.youtube.com/user/TRUTHstreammedia/videos']
}

# Flattens a nested JSON object and returns a python dictionary
def flatten_json(nested_json):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(nested_json)
    return out

# Walk ALL folders and examine  the .json files. Do they use the same fields?
max = 0
common_keys = {}
for group in UrlList:
    i = 0
    for subdir, dirs, files in os.walk(DLBASE + group):
        for dir in dirs:
            target = subdir + '/' + dir
            fList = os.listdir(target)
            for file in fList:
                if file.endswith(".json"):
                    with open(target + '/' + file, 'r') as jsn:
                        jDict = json.load(jsn)
                    jFlat = flatten_json(jDict)
                    for key in jFlat.keys():
                        if key not in common_keys: common_keys[key] = 1
                        else: common_keys[key] += 1

print("Common keys=%d" % len(common_keys))

max = 0
with open(COMMON, mode='w') as com:
    for k in sorted(common_keys):
        if k.startswith("formats_"): continue
        if common_keys[k] > 2000:
            com.write(k + '\n')

#for k in sorted(common_keys):
#    if common_keys[k] > 5898:
#        max += 1
#        print("key=%s: %d" % (k, common_keys[k]))

print("%d keys were used by more than 5898 videos" % max)

exit(0)

