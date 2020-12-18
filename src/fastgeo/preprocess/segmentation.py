"""
Track segmentation.
"""
import datetime
from geo import distance

def segment(track, curr_time, time_diff, dist_diff, cutoff_time):
    """
    Split a track into various segments based on spatiotemporal constraints.

    This was originally based in TrackToTrip's segmentation (using DBSCAN clustering).
    However, the low GPS update rate in the Beijing dataset used here doesn't work well 
    with that approach.

    Receives a track - list [id, long, lat, time, lineid], as well as:

    curr_time - current simulation time

    time_diff - time difference to consider a stop event

    dist_diff - distance difference to consider a stop event

    cutoff_time - time to consider segmenting older parts of a track.

    Returns a list of segments.
    """
    threshold_v = dist_diff / time_diff
    segments = []
    curr_segment = []
    prevlon, prevlat, prevtime = ("", "", "")
    curr_time = datetime.datetime.strptime(curr_time, "%Y-%m-%dT%H:%M:%S")

    for point in track:
        lon, lat = [eval(i) for i in point[1:3]]
        time = datetime.datetime.strptime(point[3], "%Y-%m-%d %H:%M:%S")

        if(prevtime != ""):
            prev_age = (curr_time - prevtime).total_seconds()
            curr_age = (curr_time - time).total_seconds()

            # If part of a track is older than the cutoff time, segment it
            if(prev_age > cutoff_time and curr_age < cutoff_time):
                curr_segment.append(point)
                segments.append(curr_segment)
                curr_segment = []

            dist = distance([lon, lat], [prevlon, prevlat])
            dt = (time - prevtime).total_seconds()
            v = dist / dt
            if(v < threshold_v):
                curr_segment.append(point)
                segments.append(curr_segment)
                curr_segment = []

        curr_segment.append(point)
        prevlon, prevlat, prevtime = (lon, lat, time)
    
    if(curr_segment != []):
        segments.append(curr_segment)
        
        # Final check: if a track hasn't been updated in a while, just boot it to recent
        prevtime = datetime.datetime.strptime(curr_segment[-1][3], "%Y-%m-%d %H:%M:%S")
        diff = (curr_time - prevtime).total_seconds()
        if(diff > time_diff):
            segments.append([])
    return segments