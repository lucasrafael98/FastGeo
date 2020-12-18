"""
Handles file conversion for various formats.
"""

from csv import reader as csvreader, writer as csvwriter
from xml.dom import minidom
import os

def sqlLineString(lst):
    """
    Receives a list [lon,lat], returning a LineString in SQL text format.
    """
    arrayString = "LINESTRING("
    for el in lst:
        arrayString += str(el[0]) + " " + str(el[1]) + ","
    return arrayString[:-1] + ")"

def gpx2csv(folder, addr_out):
    """
    Receives a folder full of GPX files.
    
    Returns a single CSV file for insertion in the recent table.
    """
    files = os.listdir(folder)
    rows = []
    for f in files:
        
        if(".gpx" not in f):
            continue
        gpx = minidom.parse(os.path.join(folder,f))
        segs = gpx.getElementsByTagName('trkseg')
        if(segs==[]):
            continue
        points = []
        taxid,trkid = f[4:-4].split('-')
        for s in segs:
            row = s.getElementsByTagName('trkpt')[0]
            points.append([row.attributes["lon"].value, row.attributes["lat"].value])
        lastpoint = segs[-1].getElementsByTagName('trkpt')[1]
        points.append([lastpoint.attributes["lon"].value, lastpoint.attributes["lat"].value])
        rows.append([taxid,\
            lastpoint.getElementsByTagName('time')[0].firstChild.nodeValue[:-1],\
            sqlLineString(points)])
    
    out = open(addr_out, 'w', newline='')
    writer = csvwriter(out, delimiter='|')
    writer.writerows(rows)

def csv2gpx(addr_in):
    """
    Receives a CSV file (addr_in) with format:

    taxi_id, track_id, long, lat, time

    Returning a GPX file in addr_out.
    """
    folder = '/'.join(addr_in.split('/')[0:-1])
    os.makedirs(folder+"/gpx", exist_ok=True)
    file_in = open(addr_in, 'r')
    rows = list(csvreader(file_in, delimiter=','))
    if(rows == []):
        return -1
    prevtrkid, prevtaxid = -1,-1
    trk = ""
    for row in rows:
        taxid,trkid,lon,lat,time = row
        if(prevtrkid != eval(trkid)):
            if(prevtrkid != -1):
                trk+='</trkseg></trk></gpx>'
                open(folder+"/gpx/"+str(prevtaxid)+'-'+str(prevtrkid)+'.gpx', 'w').write(trk)
            trk = '<?xml version="1.0" encoding="UTF-8"?>\n'
            trk += '<gpx version="1.1" creator="FastGeo" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
            trk += '<metadata></metadata>'
            trk += '<trk><trkseg>'
            prevtrkid = eval(trkid)
            prevtaxid = eval(taxid)
        trk += f'<trkpt lat="{lat}" lon="{lon}">'
        trk += f'<time>{time}</time></trkpt>'
        trk += f'<extensions><id>{eval(taxid)}</id></extensions>'

    trk+='</trkseg></trk></gpx>'
    open(folder+"/gpx/"+taxid+'-'+trkid+'.gpx', 'w').write(trk)
    return 0

def segs_to_csv(segs):
    """
    Writes the given segment list into a CSV string with format:

    taxids, times, totals, total, line, trkid, adj1, adj2
    """
    to_csv = []

    for s in segs:
        points = []
        pts = s['geom']
        for p in pts:
            points.append([p[0], p[1]])
        taxid_str = '{'
        for taxid in s['meta']['ids']:
            taxid_str += str(taxid) + ','
        taxid_str = taxid_str[:-1] + '}'
        time_str = '{'
        for time in s['meta']['times']:
            time_str += str(time)  + ','
        time_str = time_str[:-1] + '}'
        tots_str = '{'
        for time in s['meta']['totals']:
            tots_str += str(time)  + ','
        tots_str = tots_str[:-1] + '}'
        adj1_str = '{'
        if(len(s['meta']['adj1']) != 0):
            for adj in s['meta']['adj1']:
                adj1_str += str(adj)  + ','
            adj1_str = adj1_str[:-1] + '}'
        else:
            adj1_str += '}'
        adj2_str = '{'
        if(len(s['meta']['adj2']) != 0):
            for adj in s['meta']['adj2']:
                adj2_str += str(adj)  + ','
            adj2_str = adj2_str[:-1] + '}'
        else:
            adj2_str += '}'
        to_csv.append([taxid_str, time_str, tots_str, s['meta']['total'],\
            sqlLineString(points), s['meta']['trkid'], adj1_str, adj2_str])
    
    return to_csv