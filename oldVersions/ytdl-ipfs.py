#!/usr/bin/python3

#
# OBSOLETE!!! Use test-init-support/ipfs-getGrupes.py !!!
#
# Program to scrape videos and add to IPFS.
#
# It also builds a SQLite3 database of IPFS hashes and
# detailed metadata for each video. This lightweight
# SQL engine is filesystem based (no server daemon).
#
# This script requires a file containing the column
# names for the metadata, which was created by looking
# at the json metadata for a large sample of videos.
# It is stored in the KEYS file (commonJsonKeys.txt).
#
# This script will also read the retry.json file if it
# exists, and attempt to download those videos again.
#
from __future__ import unicode_literals
from youtube_dl import utils
import youtube_dl
import sqlite3
import json
import os

#HOME = os.path.dirname(os.path.realpath(__file__)) + '/'
#HOME   = '/media/rootfs/home/ipfs/u-tube'
HOME   = '/home/ipfs/u-tube'
IPFS   = HOME + '/scripts/add2IPFS'
DLBASE = HOME + '/ytDL/'
SQLFI  = DLBASE + 'ipfsHashList.sqlite'
PARTS  = DLBASE + 'parts.log'
JSON   = DLBASE + 'retry.json'
KEYS   = DLBASE + 'commonJsonKeys.txt'
LOG    = DLBASE + '__completed.log'

CompletedList = [] # List of downloaded file names, used by dl callback
Dest = "/%(id)s_%(upload_date)s/%(duration)ss_%(resolution)s_%(id)s.%(ext)s"
Cols = []
Redo = False
Conn = None
Grp  = None

Targets = {
    'londonReal': ['https://www.youtube.com/user/LondonRealTV/videos'],
#    'jordPeters': ['https://www.youtube.com/user/JordanPetersonVideos/videos'],
#    'lukewearechange': ['https://www.youtube.com/user/lukewearechange/videos'],
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
    global Cols, SQLFI
    db_is_new = not os.path.exists(SQLFI)
    conn = sqlite3.connect(SQLFI)
    if db_is_new:
        sql = '''create table if not exists IPFS_HASH_INDEX (
        "pky" INTEGER PRIMARY KEY AUTOINCREMENT,
        "g_idx" TEXT,
        "grupe" TEXT,
        "vhash" TEXT,
        "mhash" TEXT'''

        for col in Cols:
            sql += ',\n\t"' + col + '" TEXT'
        sql += ')'
        conn.execute(sql)
    return conn


# Add one row (one for each video) to SQLite database
def addRow(grupe, vhash, mhash, meta):
    global Conn, Cols
    values = [grupe, vhash, mhash]
    sql = 'INSERT INTO IPFS_HASH_INDEX ("grupe", "vhash", "mhash"'
    for col in Cols:
        sql += ',\n\t"' + col + '"'

    sql += ") VALUES (?,?,?"

    for col in Cols:
        sql += ",?"
        values.append(meta[col])
    sql += "); "
    cursor = Conn.cursor()
    cursor.execute(sql, values)
    Conn.commit()
    return cursor.lastrowid


# Update all rows for this grupe with the hash for the groupIndex.txt file
def updateGrp(Grp, hash):
    sql = "UPDATE IPFS_HASH_INDEX set g_idx=? WHERE grupe=?"
    cursor = Conn.cursor()
    cursor.execute(sql, (hash, Grp))
    Conn.commit()
    return cursor.rowcount


# The add2IPFS bash script is called to add the files to IPFS.
# add2IPFS args: $1 == path to grupe containing folders holding videos
#                $2 == base file name for all associated files
#                $3 == video file
# Guaranteed to be called at least once per download.
def callback(d):
    row = None
    jFlat = None
    global Grp, CompletedList
    if d['status'] == 'finished':
        CompletedList.append(d['filename'])
        (path, vid) = d['filename'].rsplit('/', 1)
        base = os.path.splitext(vid)[0]

        # Read the metadata JSON file into a flattened Python dictionary
        meta = path + '/' + base + ".info.json"
        if os.path.isfile(meta):
            with open(path + '/' + base + ".info.json", 'r') as jsn:
                jDict = json.load(jsn)
            jFlat = flatten_json(jDict)

        # Add the video and JSON metadata files to IPFS and save their hashes
        os.system(IPFS + " %s %s %s" % (path, base, vid))

        # Read the IPFS hash for the video's metadata file created above
        with open(path + '/' + "metaHash.txt", 'r') as mHndl:
            mHash = mHndl.read().split()[1]

        # Now read the IPFS hash for video file, also created above
        with open(path + '/' + "videoHash.txt", 'r') as vHndl:
            vHash = vHndl.read().split()[1]

        # If all processed OK, add the info to SQLite DB and report it
        if len(mHash) > 0 and len(vHash) > 0 and len(jFlat) > 0:
            row = addRow(Grp, vHash, mHash, jFlat)
            print('>>>>> Download Complete! Added row=%s to SQL DB' % str(row))


# Options common to all downloads
commonOpts = {
    'outtmpl': DLBASE + "/%(id)s_%(upload_date)s/%(duration)ss_%(resolution)s_%(id)s.%(ext)s",
    'progress_hooks': [callback],
    'merge-output-format': 'mkv',
    'restrictfilenames': True,
#    'writedescription': True,
    'writeinfojson': True,
    'ignoreerrors': True,
    'continuedl': True,
    'retries': 5,
#    'skip_download': True,
    'format': 'best',
    'download_archive': LOG
}


# Read the KEYS file with columns for metadata in SQLite DB
Cols = readKeys()
Conn = create_or_open_db()
print("DB Schema Columns=%d" % len(Cols))

# If the JSON file exists use that as List of URLs to process
if not os.path.isfile(JSON):
    UrlList = Targets        # No JSON file with retries
else:
    Redo = True
    with open(JSON, 'r') as jsn:
        UrlList = json.load(jsn)
#for k in UrlList:
#    print("%s=%s" % (k, UrlList[k]))


#############################################################################
#                                                                           #
# The main download loop. The youtube-dl library takes care of downloading. #
# The callback function above processes each download, adding files to IPFS #
# and the SQLite database.                                                  #
#                                                                           #
#############################################################################
with youtube_dl.YoutubeDL(commonOpts) as ydl:
    for grupe in UrlList:
        Grp = grupe
        print("\nBEGIN " + grupe)
        if not os.path.isdir(DLBASE + grupe):
            os.mkdir(DLBASE + grupe)
        ydl.params['outtmpl'] = DLBASE + grupe + Dest
        ydl.download(UrlList[grupe])

        # Downloads for all the URLs in grupe are done, add group hash to IPFS
        os.system("cd " + DLBASE + grupe + \
                  "; ipfs add groupHashes.txt > indexHash.txt 2> /dev/null")

        # Now read the indexHash.txt file created above and update the SQL DB
        with open(DLBASE + grupe + '/' + "indexHash.txt", 'r') as idx:
            g_idx = idx.read().split()[1]
        rows = updateGrp(grupe, g_idx)
        print("Updated %d rows for grupe %s" % (rows, grupe))

#
# These are the files we've downloaded and added to IPFS
#
FILZ = DLBASE + '_completedFullPath.log'
with open(FILZ, mode='a+') as log:   # Write the log
    for item in CompletedList:
        log.write(item + '\n')

exit(0)
