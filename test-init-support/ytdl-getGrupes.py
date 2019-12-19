#!/usr/bin/python3

#
# Program to scrape videos and add them to IPFS.
#
# It also builds  a  SQLite3 database of IPFS hashes and detailed metadata for
# each  video.  This  lightweight  SQL engine is filesystem based (no server).
#
# This script requires a  JSON formated config file containing  schema  column
# names and other info.
#
# Youtube changes the metadata keys from time to time which makes it difficult
# to rely on youtube metadata for the schema, which is why an external file is
# used with a common set of fields.
#
# The -r command line parameter can be used to optionally specify a JSON retry
# file to attempt to download videos that fail.
#
# Currently processing youtube-dl exceptions is not working.
#
from __future__ import unicode_literals
from youtube_dl import utils
from datetime import *
import youtube_dl
import subprocess
import sqlite3
import time
import json
import sys
import os

#
# Global Variables
#
FinishedFiles = []    # Lists populated by download callback
GroupIdxVideo = []
GroupIdxMeta  = []
ErrorList     = []

CBArgs        = False # These 3 are required by youtube-dl callback code
Conn          = None
Grp           = None

# Loaded from config file specified on command line (JSON file format).
# This template must remain as is until the config file is read.
Config = {
    'DLbase': None,    # Folder with groups of downloaded files
    'DLeLog': None,    # Error list of download failures
    'DLfLog': None,    # Full pathname of Log for finished video downloads
    'DLgIdx': None,    # Grupe index file: DLbase + grupe + DLgIdx

    'DownloadOptions': {           # Name / value pairs for youtube-dl options
        'optName1': 'value1',      # NOT necessarily the same as cmd line opts
    },

    'Grupes': {        # Group name and array of URL(s), playlist(s) or single
        'gName': ['url1', 'url2' ] # Must be an array, even if only 1 url
    },

    'MetaColumns': [   # Contains the list of database fields for metadata.
    ]
}

def usage():
    cmd =  sys.argv[0]
    str =  "\nUses youtube-dl to download videos and add them to IPFS and track\n"
    str += "the results in a SQLite database.\n\n"
    str += "Usage:  " + cmd + " [-h] | <-c config> <-d sqlite> [-r]\n"
    str += "-h or no args print this help message.\n\n"
    str += "-c is a JSON formated config file that specifies the target groups,\n"
    str += "their URL(s),  the list of metadata columns, downloader options and\n"
    str += "the base or top level folder for the groups of files downloaded.\n\n"
    str += "-d is the SQLite filename (it is created if it doesn't exist).\n\n"
    str += "-r is used to process download failures, but is not yet implemented.\n"
    print(str)
    exit(0)


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


# TODO: Refactor rety code
# Process error list into a JSON retry file
def loadRetries(json):
    if os.path.isfile(json):
        with open(json, 'r') as jsn:
            return json.load(jsn)['Grupes']
    else: return None


# Create the SQLite database file if it doesn't  exist,  using the
# MetaColumns from Config. If it already exists, open a connection
# to it. Always returns a connection object to the dbFile.
def openSQLiteDB(columns, dbFile):
    newDatabase = not os.path.exists(dbFile)
    conn = sqlite3.connect(dbFile)
    if newDatabase:
        sql = '''create table if not exists IPFS_HASH_INDEX (
        "pky" INTEGER PRIMARY KEY AUTOINCREMENT,
        "g_idx" TEXT,
        "grupe" TEXT,
        "vhash" TEXT,
        "mhash" TEXT'''

        for c in columns:
            sql += ',\n\t"' + c + '" TEXT'
        sql += ')'
        conn.execute(sql)
    return conn


# Update all rows for this grupe with the hash for the groupIndex.txt file
def updateGrp(conn, Grp, hash):
    sql = "UPDATE IPFS_HASH_INDEX set g_idx=? WHERE grupe=?"
    cursor = conn.cursor()
    cursor.execute(sql, (hash, Grp))
    conn.commit()
    return cursor.rowcount


# Add one row (one for each video) to SQLite database. Most of the column data
# comes from the JSON metadata downloaded with the video.
def addRow(conn, cols, grupe, vhash, mhash, meta):
    errors = False
    cursor = conn.cursor()
    meta["episode_number"] = mhash # Mark row as pinned by adding the hashes
    meta["season_number"] = vhash  #  to these fields
    values = [grupe, vhash, mhash] # 1st 3 values: video group and IPFS hashes
    sql    = 'INSERT INTO IPFS_HASH_INDEX ("grupe", "vhash", "mhash"'

    for col in cols:
        sql += ',\n\t"' + col + '"'

    sql += ") VALUES (?,?,?"       # Now add metadata
    for col in cols:
        sql += ",?"
        values.append(meta[col])
    sql += "); "

    try:
        cursor.execute(sql, values)
        conn.commit()

    except sqlite3.Error as e:
        print("Exception in addRow: %s\n\n" % e)
        conn.close()
        exit(-1)

    else: return cursor.lastrowid


# Add a file to IPFS and return the hash for it
def add2IPFS(file):
    lst = []
    cmd = ["ipfs", "add", file]
    out = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode('utf-8')
    return(out.split("\n")[0][6:52])    # Take only the hash


# I can't see a way to change the arguments to the youtube callback,
# and so the need for global parameters.  Guaranteed to be called at
# least once per download.
def callback(d):
    global CBArgs, Grp, ErrorList, FinishedFiles, GroupIdxMeta, GroupIdxVideo
    vFile = mFile = jFlat = row = None
    cols = Config['MetaColumns']

    if d['status'] == 'finished':
        vFile = d['filename']             # Callback provides full pathname
        mFile = os.path.splitext(vFile)[0] + ".info.json"   # Switch extension
        if os.path.isfile(mFile):         # Verify we have the file to be added
            mHash = add2IPFS(mFile)       # Add the metadata file to IPFS
            with open(mFile, 'r') as jsn: # Read the entire JSON metadata file
                jDict = json.load(jsn)    # Create a python dictionary from it
            jFlat = flatten_json(jDict)   # Flatten the dictionary
        else: mHash = None                # File not downloaded!

        if os.path.isfile(vFile):         # Verify we have the file to be added
            vHash = add2IPFS(vFile)       # Add video file to IPFS
        else: vHash = None                # File not downloaded!

        # If all processed OK, add the info to SQLite DB and index lists
        if mHash != None and vHash != None and len(jFlat) > 0:
            row = addRow(Conn, cols, Grp, vHash, mHash, jFlat)
            FinishedFiles.append("%d %s" % (row, vFile)) # Add row and video
            GroupIdxVideo.append("%d %s" % (row, vHash)) # Add row and vHash
            GroupIdxMeta.append("%d %s" % (row, mHash))  # Add row and mHash
            now = datetime.now()
            mark = now.strftime("%a %H:%M:%S")
            args = (mark, row, vHash, mHash)
            print("%s Added row %d to DB,\n\tvideo=%s metadata=%s\n" % args)
        else:
            d['status'] = "Failed!"
            ErrorList.append("Grupe=%s vHash=%s mHash=%s vFile=%s" %
                             (Grp, vHash, mHash, os.path.basename(vFile)))
        CBArgs = d # This will signal download completion


##############################################################################
#                                                                            #
# Primary program loop. The  youtube-dl library  takes care of downloading.  #
# The callback function above processes each download, adding files to IPFS  #
# and info to the SQLite database.                                           #
#                                                                            #
##############################################################################
def ytdlProcess(conn, config):
    global CBArgs, Grp
    ytdlFileFormat  = "/%(duration)ss_%(resolution)s_%(id)s.%(ext)s"
    finishedLog     = config['DLfLog']
    errorsLog       = config['DLeLog']
    grupeIdex       = config['DLgIdx']
    grupeList       = config['Grupes']
    dlBase          = config['DLbase']
    dlOpts          = config['DownloadOptions']
    grupes =  urls  = 0

    # Add some crucial download options
    dlOpts['writeinfojson'] = True
    dlOpts['progress_hooks'] = [callback]
    dlOpts['restrictfilenames'] = True

    try:
        with youtube_dl.YoutubeDL(dlOpts) as ydl:
            for grupe in grupeList:
                Grp = grupe
                CBArgs = False
                print("\nBEGIN " + grupe)
                if not os.path.isdir(dlBase + grupe):
                    os.mkdir(dlBase + grupe)

                ydl.params['outtmpl'] = dlBase + grupe + ytdlFileFormat
                ydl.download(grupeList[grupe]) # Start downloading the grupe!

                while not CBArgs:              # Wait for downloads to finish
                    time.sleep(0.050)          # Difficult to set a limit here
    except:
        ErrorList.append("Download exception in youtube-dl: Grupe=%s" % Grp)

    try:
        # Grupe is finished, create group idx file,add 2 IPFS, update DB
        idxFile = dlBase + grupe + grupeIdex
        with open(idxFile, mode='a+') as idx:
            for info in GroupIdxVideo:
                idx.write(str(info) + '\n')
            idx.close()
            g_idx = add2IPFS(idxFile)
            rows = updateGrp(conn, grupe, g_idx)
            print("Updated %d rows for grupe %s with grupe index hash %s" %
                  (rows, grupe, g_idx))

        # Write a list of finished downloads with DB row ID and filenames
        with open(finishedLog, mode='a+') as ok:
            for fName in FinishedFiles:
                ok.write(fName + '\n')
            err.close()

        # Write a list of download failures as filenames that includes id
        with open(errorsLog, mode='a+') as err:
            for item in ErrorList:
                err.write(item + '\n')
            err.close()

    except:
        ErrorList.append("Exception occured after downloading %s" % grupe)


##############################################################################
#                                                                            #
# Program "main" entry point. I know, not pythonic - too bad, it's easy fix. #
#                                                                            #
# Usage: thisFile [-h] | <-c config> <-d sqlite> [-r]                        #
# Parse command line and report config info                                  #
#                                                                            #
##############################################################################
retryList = None
if len(sys.argv) >= 5:
    grupes = urls = 0

    # Required parameter: -c config file
    if sys.argv[1] == "-c" and os.path.isfile(sys.argv[2]):
        with open(sys.argv[2], 'r') as jsn:
            Config = json.load(jsn)
        metaSize = len(Config['MetaColumns'])
        if metaSize > 0:  # Config info loaded OK?
            for grupe in Config['Grupes']: # Count groups and urls in them
                grupes += 1
                urls += len( Config['Grupes'][grupe] )
            print("Database Metadata Columns=%d" % metaSize)
            print("All downloads will be saved in %s" % Config['DLbase'])
            print("%d groups, %d urls to process" % (grupes, urls))
        else: usage()
    else: usage()

    # Required parameter: -d SQLite database file
    if sys.argv[3] == "-d":
        Conn = openSQLiteDB(Config['MetaColumns'], sys.argv[4])
        Conn.row_factory = sqlite3.Row          # Results as python dictionary
    if Conn == None: usage()

    # Optional parameter: -r (process failed downloads in Config DLrTry file
    if sys.argv[-1] == "-r":
        pass
#        retryList = loadRetries(Config['DLrTry'])

    if not os.path.isdir(Config['DLbase']):
        os.mkdir(dlBase)
else: usage()

# Command line and config file processed, time to get down
if retryList == None:
    ytdlProcess(Conn, Config)
else:
    pass

exit(0)

