#!/usr/bin/python3
#
# Program to create a ytdl-history file from the SQLite database.
# youtube-dl uses the ytdl-history to skip downloading files already
# downloaded.
#
import sqlite3
import sys
import os

# GLOBALS
HOME      = os.path.dirname(os.path.realpath(__file__)) + '/'
DLBASE    = '/home/ipfs/ytDL/'

def usage():
    cmd =  sys.argv[0]
    str =  "\nCreate a youtube history file from a SQLite database.\n"
    str += "Usage: " + cmd + " [-h] | <-d sqlite DB file> <-o history file pathname>\n\n"
    print(str)
    exit(0)


#############################################################################
#                                                                           #
# main                                                                      #
#                                                                           #
#############################################################################
argc = len(sys.argv)
conn = sql = row = None

try:
    # Parse command line
    if argc > 1:
        if sys.argv[1] == "-h":
            usage()

        # Required parameter: SQLite database file to check pins against
        if argc > 2 and sys.argv[1] == "-d":
            dbFile = sys.argv[2]
            conn = sqlite3.connect(dbFile)   # Failure to open is exception
            conn.row_factory = sqlite3.Row   # Result format to dictionary
            cursor = conn.cursor()
        else: usage()

        # Required parameter: output file - youtube history file pathname
        if argc > 4 and sys.argv[3] == "-o":
            oFile = sys.argv[4]
            outHandle = open(oFile, mode='w')      # Open the output file

        else: usage()
    else: usage()

    # Get the rows & columns we need for history file
    rowCount = 0
    sql =  "SELECT extractor, id FROM IPFS_HASH_INDEX"
    sql += " WHERE episode_number is not null and season_number is not null"
    for row in cursor.execute(sql):
        outHandle.write(row['extractor'] + " " + row['id'] + "\n")
        rowCount += 1

    outHandle.close()
    print("\nWrote %d lines to %s" % (rowCount, oFile))
    exit(0)

except Exception as e:
    print("Oh no, something went wrong!%s\n\n" % e)

exit(0)

