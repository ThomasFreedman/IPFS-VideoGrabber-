#!/usr/bin/python3
#
# Program to compare list of pinned IPFS objects to
# the sqlite database. Download and process the missing
# files into IPFS and update SQLite.
#
from __future__ import unicode_literals
from youtube_dl import utils
from datetime import *
import youtube_dl
import subprocess
import sqlite3
import time
import sys
import os

# GLOBALS
HOME      = os.path.dirname(os.path.realpath(__file__)) + '/'
DLBASE    = '/home/ipfs/ytDL/'
DLSTATUS  = False

def usage():
    cmd =  sys.argv[0]
    str =  "\nCheck pinned files on IPFS server to those in SQLite.\n"
    str += "Download the missing files and add to IPFS, then Update\n"
    str += "the SQLite database. -s skips the verification step and\n"
    str += "retieves files not verified in SQLite\n"
    str += "Usage: " + cmd + " [-h] | <-d sqlite DB file> [-s]\n\n"
    print(str)
    exit(0)


# Update the video file, hashes and flag as verified
def updateRowHashes(conn, pky, vhash, vPathname, mhash):
    cursor = conn.cursor()
    vfile = os.path.basename(vPathname)  # Strip the path from file

    print("Updating row=%d with newly downloaded files and hashes..." % pky)
    sql = "UPDATE IPFS_HASH_INDEX SET vhash='" + vhash + "', _filename='"
    sql += vfile + "', mhash='" + mhash + "', season_number='" + vhash + "',"
    sql += "episode_number='" + mhash + "'"
    sql += " WHERE pky = %d" % pky
    conn.execute(sql)
    conn.commit()


# Update this row's episode_number and season_number columns with the hash
# that matched.   episode_number for mhash, season_number for vhash.  Also
# update the _filename column by stripping the path leaving only the file.
def updateVerified(conn, row, hash):
    sql = "UPDATE IPFS_HASH_INDEX SET "
    whr = " WHERE pky = " + str(row[0])

    file = os.path.basename(row[3])  # Strip the original path from file
    if row[1] == hash:
        sql += "season_number = '" + hash + "', _filename = '" + file + "'"
    else:
        sql += "episode_number = '" + hash + "', _filename = '" + file + "'"

    conn.execute(sql + whr)
    conn.commit()


# Add the file to IPFS and return the hash
def add2IPFS(file):
    lst = []
    cmd = ["ipfs", "add", file]
    out = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode('utf-8')
    return(out.split("\n")[0][6:52])    # Take only the hash


# Print the 3 character day of week and time of day
def printMarker():
    now = datetime.now()
    mark = now.strftime("%a %H:%M:%S")
    print(mark, flush=True)


# Guaranteed to be called at least once per download.
def callback(d):
    global DLSTATUS
    if d['status'] == 'finished': DLSTATUS = d


# Download the missing video, add it to IPFS and update the SQLite DB
def getMissingVideoFiles(conn, row):
    global DLSTATUS
    url      = [ row["webpage_url"] ]  # Must be of type list even for 1 url
    pky      = row["pky"]
    grupe    = row["grupe"]
    dlFolder = DLBASE + grupe

    opts = {
        'outtmpl': dlFolder + "/%(duration)ss_%(resolution)s_%(id)s.%(ext)s",
        'progress_hooks': [callback],  # The callback is how we get filename
        'merge-output-format': 'mp4',
        'restrictfilenames': True,
        'writeinfojson': True,
        'no-playlist': True,
        'geo-bypass': True,
        'retries': 5,
        'format': 'best'
    }

    try:
        # Download the video and metadata files
        with youtube_dl.YoutubeDL(opts) as ydl:
            print("\nDownloading %s for %s" % (url, grupe))
            if not os.path.isdir(DLBASE + grupe):
                os.mkdir(DLBASE + grupe)
            DLSTATUS = False

            # Options for downloading
            ydl.download(url)
    except:
        return  # Catch the youtube-dl exception but continue

    # Wait for download to finish
    while not DLSTATUS: time.sleep(0.050)
    vfile = DLSTATUS['filename']         # Callback provides full pathname
    mfile = os.path.splitext(vfile)[0] + ".info.json"   # Switch extension

    # The metadata should be the same so no need to update all of the columns.
    if os.path.isfile(mfile):            # Verify we have the file to be added
        mhash = add2IPFS(mfile)          # Add the metadata file to IPFS
    else: mhash = None                   # File not downloaded!

    if os.path.isfile(vfile):            # Verify we have the file to be added
        vhash = add2IPFS(vfile)          # Add video file to IPFS
    else: vhash = None                   # File not downloaded!

    # Update SQLite with the new hashes for the files we just added to IPFS
    updateRowHashes(conn, pky, vhash, vfile, mhash)


# Create a python list of pinned hashes obtained from the local IPFS server.
def createIpfsPinList():
    lst = []
    cmd = ["ipfs", "pin", "ls", "--type=recursive"]
    out = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode('utf-8')
    for line in out.split("\n"):
        lst.append(line.split(" ")[0])  # Take only the hash
    return lst


#############################################################################
#                                                                           #
# main                                                                      #
#                                                                           #
#############################################################################
verify = True
argc = len(sys.argv)
conn = sql = row = url = None

try:
    # Parse command line
    if argc > 1:
        if sys.argv[1] == "-h":
            usage()

        # Optional parameter - skip verification and proceed to retrieval
        if sys.argv[-1] == "-s": verify = False

        # Required parameter: SQLite database file to check pins against
        if argc > 2 and sys.argv[1] == "-d":
            dbFile = sys.argv[2]
            conn = sqlite3.connect(dbFile)   # Failure to open is exception
            conn.row_factory = sqlite3.Row   # Result format to dictionary
            cursor = conn.cursor()
        else: usage()
    else: usage()

    if verify:
        # Verify loop: for all pinned hashes in IPFS verify both vhash & mhash
        # exist in SQLite. If found, update the row to flag the hash found,  &
        # strip the path "prefix" from  _filename leaving just the filename.
        sel = "SELECT pky,vhash,mhash,_filename FROM IPFS_HASH_INDEX "
        lines = createIpfsPinList()
        lCount = 0
        for line in lines:                        # For each hash pinned...
            lCount += 1
            hash = line.split(" ")[0]             # Get hash from pinned list
            args =  (lCount, len(lines), hash)
            print(" %5d of %5d Checking %s..." % args, end='\r')
            sql = sel + "WHERE vhash='%s' or mhash='%s'" % (hash, hash)
            r = cursor.execute(sql).fetchone()    # Fetch the row from database
            if r: updateVerified(conn, r, hash)   # Update the row if it exists

    # Report how many hashes failed to validate and ask to correct them
    sql =  "SELECT count(*) FROM IPFS_HASH_INDEX"
    sql += " WHERE episode_number is null or season_number is null"
    count = int(cursor.execute(sql).fetchone()[0])
    msg = "\nFound %d unpinned rows, do you want to fix them? (y/n) " % count
    if input(msg) != "y":
        print("Ok then, goodbye")
        exit(0)

    # Unverified videos loop - Get missing videos and add to IPFS & fix SQLite
    sql =  "SELECT pky,grupe,webpage_url FROM IPFS_HASH_INDEX"
    sql += " WHERE season_number is null or episode_number is null"
    for r in cursor.execute(sql):
        getMissingVideoFiles(conn, r)

except Exception as e:
    print("Exception: %s\n\n" % e)

except sqlite3.Error as e:
    print("Database error during query: %s\nSQL=%s\n\n" % (e, sql))

except sqlite3.OperationalError:
    print("ERROR!: Query Failure")

exit(0)

