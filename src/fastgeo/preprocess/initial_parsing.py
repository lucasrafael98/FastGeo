from os import makedirs
from glob import glob
from xml.dom import minidom
from datetime import datetime, timedelta

"""
Initial folder parsing for insertion in the raw data table.

Gets data from data/raw/mods/ (.gpx) or data/raw/ (.txt in CSV format).

Writes a ".txt" (CSV) file with all data to upload to raw table.
"""
makedirs("data/temp", exist_ok=True)
makedirs("data/raw/mods", exist_ok=True)

gpxFiles = glob("data/raw/mods/*.gpx")
txtFiles = glob("data/raw/*.txt")
csvFiles = glob("data/raw/*.csv")
objectID = 0

with open("data/temp/converted_tracks.csv", "w", newline='') as outfile:
    for gpx in gpxFiles:
        with open(gpx, 'r') as infile:
            thisDoc = minidom.parse(gpx)

            points = thisDoc.getElementsByTagName('trkpt')
            if(len(points) == 0):
                continue

            i = 0
            for point in points:
                if(i % 2 == 0):
                    lon = point.attributes['lon'].value
                    lat = point.attributes['lat'].value
                    time = '\'' + point.getElementsByTagName('time')[0].firstChild.nodeValue.replace('T', ' ') + '\''
                    outfile.write(str(objectID) + "," + time.replace('Z', '') + "," + lon + "," + lat + ',' + "0" +  "\n")
                i += 1

        objectID += 1
    for txt in txtFiles:
        with open(txt, 'r') as infile:
            for line in infile:
                splitLine = [x.strip() for x in line.split(',')]
                if(len(splitLine) != 4):
                    print("Invalid TXT - a valid file would consist of (id,timestamp,lat,long). Skipping...")
                    continue
                outfile.write(str(objectID) + ',\'' + splitLine[1] + '\',' + splitLine[2] + ',' + splitLine[3] + ',' + "0" + '\n')

        objectID += 1

    for csv in csvFiles:
        with open(csv, 'r') as infile:
            for line in infile:
                # ignore header
                if(line[1] == 'T'):
                    continue
                splitLine = [x.strip() for x in line.replace('"', '').split(',', 8)]
                taxid = eval(splitLine[4])
                tripid = eval(splitLine[0])
                time = datetime.fromtimestamp(eval(splitLine[5]))
                polyline = eval(splitLine[8])
                for l in polyline:
                    outfile.write(f"{taxid},'{time}',{l[0]},{l[1]},'{tripid}'\n")
                    time += timedelta(seconds=15)

    # rmtree("data/raw/mods")