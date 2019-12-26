#!/usr/bin/python3
#
# ytdl-videoGrabber.py - Program to scrape videos and add them to IPFS.
#
# It also builds  a  SQLite3 database of IPFS hashes and detailed metadata for
# each  video.  This  lightweight  SQL engine is filesystem based (no server).
#
# This script requires a  JSON formated config file containing  schema  column
# names and other info, like filter settings for video length and upload date.
#
# Youtube is known to change the metadata keys, making it difficult to rely on
# youtube metadata for the schema. After sampling 1000s of videos a common set
# of metadata columns was arrived at and is now found in the JSON config file.
#
# The -r command line parameter can be used to optionally specify a JSON retry
# file to attempt to download videos that fail. Not yet functional.
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
ErrorList     = []

Conn          = None  # These are required by youtube-dl callback code
Grp           = None

# Loaded from config file specified on command line (JSON file format).
# This variable will remain empty until the config file is read.
Config = {}

"""  Config file template, JSON format. Use single quotes only, null not None:
Config {
    "DLbase":    "dir",  # Base folder for downloaded files organized by grupe
    "DLeLog":    "file", # File for exceptions / errors during downloads
    "DLfLog":    "file", # File for Log of finished video downloads
    "DLarch":    "file", # This tracks downloads to skip those already done

    "DLOpts": {          # Name / value pairs for youtube-dl options
        "optName1": "value1",      # NOT always the same as cmd line opts
        ...
    },

    "Grupes": {    # Dictnnry of grupes to download, each with is own criteria
        "gName1": { # Group name containig video selection criteria
            "Duration": 0, # Min size of video in seconds; for no limits use 0
            "Start": null, # Earliest upload date string or (YYYYMMDD) or null
            "End": null    # Latest upload date or null. 1, 2 or neither OK
            "urls": [      # Must be a list (array), even if only 1 url
                "url1",
                "url2",
                ...
            ]
        },
        ...
    },

    "MetaColumns": [   # Contains the list of database fields for metadata.
        ...
    ]
}
"""

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
        "sqlts" TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
        "pky"   INTEGER PRIMARY KEY AUTOINCREMENT,
        "g_idx" TEXT,
        "grupe" TEXT,
        "vhash" TEXT,
        "mhash" TEXT'''

        for c in columns:
            sql += ',\n\t"' + c + '" TEXT'
        sql += ')'
        conn.execute(sql)
    return conn


# Add a file to IPFS and return the hash for it
def add2IPFS(file):
    lst = []
    cmd = ["ipfs", "add", file]
    out = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode('utf-8')
    return(out.split("\n")[0][6:52])    # Only take the 46 character hash


# Create a grupe index file containg a list of all video and metadata IPFS
# hashes for the group. Add it to IPFS & return the hash and count of rows
# updated.
def updateGrupeIndex(conn, grupe):
    cursor    = conn.cursor()

    idxFile = "/tmp/%s_idx.txt" % grupe
    idx = open(idxFile, "w")
    sql =  'SELECT "v=" || vhash || " " || "m=" || mhash'
    sql += '  FROM IPFS_HASH_INDEX'
    sql += ' WHERE grupe = "%s"' % grupe
    for row in cursor.execute(sql): # Loop through all rows this grupe
        idx.write(row[0] + "\n")
    idx.close()
    hash = add2IPFS(idxFile)
    if len(hash) > 0:
        sql = "UPDATE IPFS_HASH_INDEX set g_idx=? WHERE grupe=?"
        cursor.execute(sql, (hash, grupe))
        conn.commit()
        os.remove(idxFile)
    return (cursor.rowcount, hash)


#    This block of code will create group index files for every group in DB,
#    then add that file to IPFS. Update every row in the group with that hash,
#    and do that for every grupe, so every row in IPFS_HASH_INDEX table gets
#    updated. See "updateGrupeIndex" above for details. This just wraps that.
def regenerateAllGrupeIndexes(conn):
    cursor = conn.cursor()
    sql = "sSELECT DISTINCT grupe FROM IPFS_HASH_INDEX"
    for row in cursor.execute(sql):
        (count, hash) = updateGrupeIndex(conn, row[0])
        print("Updated %d rows for grupe %s with grupe index hash %s" %
               (count, row[0], hash))


# Add one row (one for each video) to SQLite database. Most of the column data
# comes from the JSON metadata downloaded with the video (meta argumemt).
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


# I can't see a way to change the arguments to the youtube callback,
# and so the need for global parameters.  Guaranteed to be called at
# least once per download.
def callback(d):
    global  ErrorList, FinishedFiles, Grp
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

        # If all processed OK, add the info to SQLite DB
        if mHash != None and vHash != None and len(jFlat) > 0:
            row = addRow(Conn, cols, Grp, vHash, mHash, jFlat)
            FinishedFiles.append("%d %s" % (row, vFile)) # Add row and video
            now = datetime.now()
            mark = now.strftime("%a %H:%M:%S")
            args = (mark, row, vHash, mHash)
            print("%s Added row %d to DB,\n\tvideo=%s metadata=%s" % args)
        else:
            print("Failure in youtube-dl callback!")
            ErrorList.append("Grupe=%s vHash=%s mHash=%s vFile=%s" %
                             (Grp, vHash, mHash, os.path.basename(vFile)))


##############################################################################
#                                                                            #
# Primary program loop. The  youtube-dl library  takes care of downloading.  #
# The callback function above processes each download, adding files to IPFS  #
# and info to the SQLite database.                                           #
#                                                                            #
##############################################################################
def ytdlProcess(conn, config):
    global          ErrorList, FinishedFiles, Grp
    dlBase          = config['DLbase']
    dlArch          = dlBase + config['DLarch']
    dlElog          = dlBase + config['DLeLog']
    dlFlog          = dlBase + config['DLfLog']
    dlOpts          = config['DLOpts']
    grupeList       = config['Grupes']
    ytdlFileFormat  = "/%(duration)ss_%(resolution)s_%(id)s.%(ext)s"
    grupes =  urls  = 0

    # Add crucial download options. Some options must be added in the DL loop
    dlOpts['writeinfojson'] = True
    dlOpts['progress_hooks'] = [callback]      # Called at least once / video
    dlOpts['download_archive'] = dlArch        # Facilitates updates w/o dupes
    dlOpts['restrictfilenames'] = True         # Required format for DLd files
#    dlOpts['force-ipv6'] = True                  # May not be enabled on host
#    dlOpts['source-address'] = "104.206.255.244" # Doesn't seem to work
    try:
        with youtube_dl.YoutubeDL(dlOpts) as ydl:
            for grupe in grupeList:
                Grp = grupe                     # Set global var for callback
                print("\nBEGIN " + grupe)       # Marks start of group in log

                if not os.path.isdir(dlBase + grupe):  # Create DL folder for
                    os.mkdir(dlBase + grupe)           # if it doesn't exist

                # Add qualifiers for minimum video duration (in seconds)
                dur = "duration > %d" % grupeList[grupe]['Duration']
                ydl.params['match_filter'] = utils.match_filter_func(dur)

                # Add release date range qualifier; either one or both OK
                sd = grupeList[grupe]['Start']  # Use null or YYYYMMDD format
                ed = grupeList[grupe]['End']    # in JSON
                dr = utils.DateRange(sd, ed)    # Dates are inclusive
                ydl.params['daterange'] = dr    # Always set a date range

                # This will change download file destination folder
                ydl.params['outtmpl'] = dlBase + grupe + ytdlFileFormat
                ydl.download(grupeList[grupe]['urls']) # BEGIN DOWNLOADING!!!

                # Complete. Create group idx file, add it to IPFS, update DB
                results = updateGrupeIndex(conn, grupe)
                print("Updated %d rows with grupe index hash %s" % results)
                print("PROCESSING COMPLETE for %s\n" % grupe)

                # Write a list of downloaded files with row ID and pathnames
                with open(dlFlog, mode='a+') as log:
                    log.write("END OF FILES FOR %s\n" % grupe)
                    for fName in FinishedFiles:
                        log.write(fName + '\n')
                    log.write('\n')
                    log.close()

                # Write a list of download failures as filenames that include id
                with open(dlElog, mode='a+') as err:
                    err.write("END OF ERRORS FOR %s\n" % grupe)
                    for item in ErrorList:
                        err.write(item + '\n')
                    err.write('\n\n')
                err.close()

    except Exception as e:
        ErrorList.append("Exception in youtube-dl: Grupe=%s:\n%s\n" % (Grp,e))


##############################################################################
#                                                                            #
# Program "main" entry point. I know, not pythonic - too bad, it's easy fix. #
#                                                                            #
# Usage: thisFile [-h] | <-c config> <-d sqlite> [-r]                        #
# Parse command line and report config info                                  #
#                                                                            #
##############################################################################
retryList = sqlDBfile = None
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
                urls += len( Config['Grupes'][grupe]['urls'] )
            print("Database Metadata Columns=%d" % metaSize)
            print("All downloads will be saved in %s" % Config['DLbase'])
            print("%d groups, %d urls to process" % (grupes, urls))
        else: usage()
    else: usage()

    # Required parameter: -d SQLite database file
    if sys.argv[3] == "-d":
        sqlDBfile = sys.argv[4]
        Conn = openSQLiteDB(Config['MetaColumns'], sqlDBfile)
        Conn.row_factory = sqlite3.Row          # Results as python dictionary
    if Conn == None: usage()

    # Optional parameter: -r (process failed downloads in Config DLrTry file
    if sys.argv[-1] == "-r":
        pass
#        retryList = loadRetries(Config['DLrTry'])

    if not os.path.isdir(Config['DLbase']):
        os.mkdir(dlBase)
else: usage()

#regenerateAllGrupeIndexes(Conn)  # Fix all grupe indexes
# exit(0)

# Command line and config file processed, time to get down
if retryList == None:
    ytdlProcess(Conn, Config)

    # Report all of the group indexes
    print("\nGrupe index file hashes, Videos, Grupes:")
    sql = "SELECT DISTINCT g_idx, count(*) as videos, grupe"
    sql += " FROM IPFS_HASH_INDEX GROUP BY grupe ORDER BY grupe;"
    for cols in Conn.execute(sql):
        print("%48s | %5d  |  %s" %
              (cols['g_idx'], cols['videos'], cols['grupe']))
    Conn.close()

    # Add the SQLite database file to IPFS and report it's hash
    hash = add2IPFS(sqlDBfile)
    print("\nHash of the updated SQLite database: %s" % hash)

else:
    pass

exit(0)
