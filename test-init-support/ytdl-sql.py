#!/usr/bin/python3

#
# Program to walk file system and create a SQLite database with
# info from metadata files. Requires previous processing of files
# by ytdl-ipfs to create the IPFS hash files or this will fail to
# add  those hashes to the created DB. ytdl-ipfs.py makes this
# program more or less obsolete.
#
from __future__ import unicode_literals
import sqlite3
import json
import os

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME = '/home/ipfs'
DLBASE = HOME + '/ytDL/'
SQLFI  = DLBASE + 'ipfsHashList.sqlite'
KEYS   = DLBASE + 'commonJsonKeys.txt'

Cols   = []
Conn   = None

UrlList = {
    'lukewearechange': ['https://www.youtube.com/user/lukewearechange/videos'],
    'wearechange':     ['https://www.youtube.com/user/wearechange/videos'],
    'truthstream':     ['https://www.youtube.com/user/TRUTHstreammedia/videos'],
    'press4truth':     ['https://www.youtube.com/user/weavingspider/videos'],
    'worldaltmedia':   ['https://www.youtube.com/channel/UCLdZo0Mkh_z2IQZSmD8Iy0Q/videos']
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

# Read the list of common keys from file into an array and return it.
def readKeys():
    fields = []
    with open(KEYS, 'r') as cKeys:
        for line in cKeys:
            fields.append(line.strip())
    return fields


# Create the SQLite database file if it doesn't exist, using the
# KEYS file for schema.  If it already exists, open a connection
# to it. Always returns a connection object to the db_file.
def create_or_open_db():
    global SQLFI, Cols
    db_is_new = not os.path.exists(SQLFI)
    conn = sqlite3.connect(SQLFI)
    if db_is_new:
        sql = '''create table if not exists IPFS_HASH_INDEX (
        "pky" INTEGER PRIMARY KEY AUTOINCREMENT,
        "g_idx" TEXT,
        "grupe" TEXT,
        "vhash" TEXT,
        "mhash" TEXT'''

        Cols = readKeys()
        for col in Cols:
            sql += ',\n\t"' + col + '" TEXT'
        sql += ')'
        conn.execute(sql)
    return conn


# Add one row (one for each video)
def addRow(group, g_idx, mhash, vhash, meta):
    values = [group, g_idx, mhash, vhash]
    sql = 'INSERT INTO IPFS_HASH_INDEX ("grupe", "g_idx", "mhash", "vhash"'
    for col in Cols:
        sql += ',\n\t"' + col + '"'

    sql += ") VALUES (?,?,?,?"

    for col in Cols:
        sql += ",?"
        values.append(meta[col])
    sql += "); "
    cursor = Conn.cursor()
    cursor.execute(sql, values)
    Conn.commit()
    return cursor.lastrowid

Conn = create_or_open_db()

# Walk ALL folders and examine the .json files. Create a SQLite DB with them.
for group in UrlList:
    # Read the group hash file saved in root of group folder
    with open(DLBASE + group + '/' + "indexHash.txt") as gh:
        g_idx = gh.read().split()[1]
    for subdir, dirs, files in os.walk(DLBASE + group):
        i = 0
        for dir in dirs:
            target = subdir + '/' + dir
            fList = os.listdir(target)
            # Process the json metadata file
            for file in fList:
                if file.endswith(".json"):
                    with open(target + '/' + file, 'r') as jsn:
                        jStr = jsn.read()
                    jDict = json.loads(jStr)
                    jFlat = flatten_json(jDict)
                # Read the IPFS hash for video and its' metadata
                elif file.endswith("Hash.txt"):
                    with open(target + '/' + file, 'r') as hash:
                        hStr = hash.read().split()[1]
                    if file.startswith("meta"): mHash = hStr
                    else: vHash = hStr
            if len(g_idx) > 0 and len(mHash) > 0 and len(vHash) > 0 and \
                len(jFlat) > 0:
                i += 1
                addRow(group, g_idx, mHash, vHash, jFlat)
                print("\rLast row for %s=%d out of %d for group"
                    % (group, i, len(dirs)), end='')
#    break
exit(0)



