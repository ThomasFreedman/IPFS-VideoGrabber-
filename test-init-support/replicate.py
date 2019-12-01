#!/usr/bin/python3
#
# Program to replicate an IPFS server populated with
# the Video Grabber progran (ytdl-ipfs????.py) which
# creates a SQLite database with hashes for each  of
# the files added to IPFS.
#
# This requires the SQLite3 database from the servers
# being replicated. It uses "ipfs cp <hash> /<grupe>/file"
# for every hash in the database to transfer the file,
# then an "ipfs pin add <hash>" to insure it will not
# be garbage collected on the local IPFS server
#
from __future__ import unicode_literals
from datetime import *
import sqlite3
import sys
import os

HOME = os.path.dirname(os.path.realpath(__file__)) + '/'

# GLOBALS
OpCounter = 0      # Count of IPFS operations done


def usage():
    str = "\nReplicate files on a remote IPFS server on local IPFS server."
    str += "Requires Sqlite3 database file that specifies the files.\n"
    str += "Usage: %s <-db file> | <--database file> [-p | --progress]\n" % sys.argv[0]
    str += "The ipfs command must be in the $PATH. To create a log file of "
    str += "the replication process (DON'T use the --progress flag) use:"
    str += "%s <args> | tee <log file name>" % sys.argv[0]
    print(str)
    exit(0)


# Prints IPFS operations done and day / time marker on console
def printMarker(newLine=False):
    global OpCounter
    now = datetime.now()
    str = "Ops: %5d %s"
    if newLine: str += "\n"
    mark = str % (OpCounter, now.strftime("%a %H:%M:%S"))
    print(mark, flush=True)
    OpCounter = OpCounter + 1


# Copy video & meta files from remote node into local virtual folder & pin them.
# Print progress as IPFS operations counter with day and time. The prog variable
# determines whether the  pinning operation reports incremental progress,  which 
# makes for very long log files if tee is used on the output to create the log.
def copyPinFiles(row, prog):
    grupe = row[0]
    vhash = row[1]
    mhash = row[2]
    video = os.path.basename(str(row[3]))
    meta  = video.split(".")[0] + ".info.json"
    if prog: progress = "--progress"
    else: progress = ''

    printMarker(True)
    copyCmd = "ipfs files cp /ipfs/" + vhash + " /" + grupe + "/" + video
#    os.system("echo " + copyCmd)
    os.system(copyCmd)

    printMarker()
    pinCmd = "ipfs pin add --recursive=true %s /ipfs/%s" % (progress, vhash)
#    os.system("echo " + pinCmd + "\n")
    os.system(pinCmd + "\n")

    printMarker(True)
    copyCmd = "ipfs files cp /ipfs/" + mhash + " /" + grupe + "/" + meta
#    os.system("echo " + copyCmd)
    os.system(copyCmd)

    printMarker()
    pinCmd = "ipfs pin add --recursive=true %s /ipfs/%s" % (progress, mhash)
#    os.system("echo " + pinCmd + "\n")
    os.system(pinCmd + "\n")




#############################################################################
#                                                                           #
# The main loop                                                             #
#                                                                           #
#############################################################################
argc = len(sys.argv)
conn = errors = grupe = sql = progress = False

try:
    # Parse command line
    if argc > 1:
        if sys.argv[1] == "-h" or sys.argv[1] == "--help":
            usage()
        if argc > 2 and (sys.argv[1] == "-db" or sys.argv[1] == "--database"):
            dbFile = sys.argv[2]
            conn = sqlite3.connect(dbFile)
        if argc > 3 and (sys.argv[3] == "-p" or sys.argv[3] == "--progress"): 
            progress = True
    else: usage()

    conn.row_factory = sqlite3.Row   # Set query results to dictionary format
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM IPFS_HASH_INDEX")
    rowCount = int(cursor.fetchone()[0])
    print("Database currently has %d rows\n" % rowCount)

    # Primary loop to obtain the files we'll replicate locally
    sql = "SELECT grupe,mhash,vhash,_filename FROM IPFS_HASH_INDEX order by grupe"
    for row in cursor.execute(sql):
        if row[0] != grupe:
            grupe = row[0]
#            os.system("echo 'ipfs files mkdir /" + grupe + "'")
            os.system("ipfs files mkdir /" + grupe)

        # Process this row into IPFS
        copyPinFiles(row, progress)


except sqlite3.Error as e:
    print("Database error during query: %s\nSQL=%s\n\n" % (e, sql))

except Exception as e:
    print("Exception in query: %s\nSQL=%s\n\n" % (e, sql))

except sqlite3.OperationalError:
    print("ERROR!: Query Failure")

exit(0)
