import numpy as np
from os.path import isfile
from geo import str2time, distance
from segmentation import segment
from yaml import load as yload, FullLoader
from csv import reader as csvreader, writer as csvwriter

config = yload(open("./config.yaml"), Loader=FullLoader)
# converting km/h to m/s (1000/3600 = 5/18)
velocityThreshold = config['unrealisticVelocityThreshold'] * 5 / 18

def check_fast_line(lst):
    """
    Checks if a line corresponds to unrealistically fast movement.

    Receives a "line" - list of format [long1, lat1, time1, long2, lat2, time2].

    Returns False if the line is acceptable, True if it's unrealistic.
    """
    long1,lat1,time1,long2,lat2,time2 = lst
    time1 = str2time(time1)
    time2 = str2time(time2)
    

    dist = distance([eval(long1), eval(lat1)], [eval(long2), eval(lat2)])
    dt = (time2 - time1).total_seconds()
    if(dt == 0):
        return True # avoiding points with the same timestamp.

    return (dist / dt) > velocityThreshold

def check_stop_events(lst):
    """
    Receives a csv (addr_in) and detects stop events.

    Returns lineids to remove to addr_delete
    and stopped tracks for addr_out (to send to recent).
    """
    addr_in, addr_delete, addr_out, curr_time = lst
    if(isfile("data/temp/trkids.txt")):
        trackIDCount = eval(open("data/temp/trkids.txt",'r').readline())
    else:
        trackIDCount = 0
    file = open(addr_in, 'r')
    rows = csvreader(file, delimiter=',')
    currTrack = []
    previd = -1
    prevtime = 0
    segments = []
    for row in rows:
        id, long1, lat1, time1, long2, lat2, time2, lineid = row
        if(previd != -1 and (previd != eval(id) or
            (previd != -1 and long1 != prevlo2 and lat1 != prevla2))):
            currTrack.append([previd, prevlo2, prevla2, prevtime2, prevlid])
            segments.append(segment(currTrack, curr_time, \
                config['stopEventTimeDiff'], config['stopEventDistDiff'],\
                config['ongoingTimeCutoff'])[:-1])
            prevtime = 0
            currTrack = []
        if(prevtime == 0):
            currTrack.append([id, long1, lat1, time1, lineid])
            prevtime = str2time(time1)
        else:
            time = str2time(time1)
            currTrack.append([id, long1, lat1, time1, lineid])
        previd = eval(id)
        prevlo2, prevla2, prevtime2, prevlid = long2, lat2, time2, lineid

    file_delete = open(addr_delete, 'w', newline='')
    writer_delete = csvwriter(file_delete, delimiter=',')
    file_out = open(addr_out, 'w', newline='')
    writer_out = csvwriter(file_out, delimiter=',')
    for seg_group in segments:
        for seg in seg_group:
            for i in range(len(seg)):
                line = seg[i]
                txid, lo, la, time, lid = line
                if(i != len(seg) - 1):
                    writer_delete.writerow([eval(lid)])
                writer_out.writerow([int(txid), trackIDCount, lo, la, time])
            trackIDCount += 1
    open("data/temp/trkids.txt",'w').write(str(trackIDCount))

def consecutive_lines(addr):
    """
    Changes the raw points in order to compute lines
    after importing the transformed csv into the lines table.

    Receives a csv with format:

    id1, time1, long1, lat1

    id1, time2, long2, lat2(...)

    Returns a csv with format:

    id1, long1, lat1, time1, long2, lat2, time2, velocity (...)

    (time/long/lat1 correspond to the older point, and *2 to the newer.)
    """
    file = open(addr, 'r')
    lines = csvreader(file, delimiter=',')
    allRows = np.empty((0,8))
    currentGroup = np.empty((0,4))
    lastPoint = []
    previd = -1
    prevtrip = -1
    for row in lines:
        id, time, lon, lat, trip = row
        if((previd != eval(id) and previd != -1) or\
            (prevtrip != eval(trip) and prevtrip != -1)):
            if(len(currentGroup) > 1): #avoiding first step
                exceptmax = np.array(currentGroup[:-1])
                exceptmin = np.array(currentGroup[1:])
                velocity = []
                for i in range(len(exceptmax[:,0])):
                    dt = (str2time(exceptmin[:,1][i]) - str2time(exceptmax[:,1][i])).total_seconds()
                    if(dt == 0):
                        velocity.append([0])
                        continue
                    dist = distance(\
                        [eval(exceptmax[:,2][i]), eval(exceptmax[:,3][i])],\
                        [eval(exceptmin[:,2][i]), eval(exceptmin[:,3][i])])
                    velocity.append([dist/dt])
                allRows = np.append(allRows, \
                    np.array([exceptmax[:,0], exceptmax[:,2], exceptmax[:,3], exceptmax[:,1],\
                                exceptmin[:,2], exceptmin[:,3], exceptmin[:,1], np.array(velocity)[:,0]]).T\
                    ,axis=0)
                currentGroup = np.empty((0,4))
            else:
                currentGroup = np.empty((0,4))
        # beijing taxi dataset has some duplicate points we want to remove with this condition.
        if([lon, lat] != lastPoint):
            currentGroup = np.append(currentGroup, np.array([row[:-1]]), axis=0)
        lastPoint = [lon, lat]
        previd = eval(id)
        prevtrip = eval(trip)
    if(len(currentGroup) > 1): #case for last ID on the iterator
        exceptmax = np.array(currentGroup[:-1])
        exceptmin = np.array(currentGroup[1:])
        velocity = []
        for i in range(len(exceptmax[:,0])):
            dist = distance(\
                    [eval(exceptmax[:,2][i]), eval(exceptmax[:,3][i])],\
                    [eval(exceptmin[:,2][i]), eval(exceptmin[:,3][i])])
            dt = (str2time(exceptmin[:,1][i]) - str2time(exceptmax[:,1][i])).total_seconds()
            dt = dt if dt > 0 else 1
            velocity.append([dist/dt])
        allRows = np.append(allRows, \
            np.array([exceptmax[:,0], exceptmax[:,2], exceptmax[:,3], exceptmax[:,1],\
                        exceptmin[:,2], exceptmin[:,3], exceptmin[:,1], np.array(velocity)[:,0]]).T\
            ,axis=0)
    file.close()
    transform = open(addr, 'w', newline='')
    writer = csvwriter(transform, delimiter=',')
    for i in range(len(allRows)):
        if(not check_fast_line(allRows[i][1:-1])):
            writer.writerow(allRows[i])