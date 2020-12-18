"""
Spatial binning (that is, keeping binned lines with regular length).
Points are [longitude, latitude].

Unused.
"""
import datetime, geo
from yaml import load as yload, FullLoader
from psycopg2 import connect

config = yload(open("./config.yaml"), Loader=FullLoader)

start_time = geo.str2time(config['streamStartTime'])
threshold = config['edgeBundlingDistThreshold']
diff_1 = config['edgeBundlingAngleDiff']
opposite_1 = 180 - diff_1
opposite_2 = 180 + diff_1
diff_2 = 360 - diff_1
error = 1e-6
min_dist = config['edgeBundlingMinDist']
bb_size = str(threshold / 111111)
bin_dist = 200

def intersect_segs(s1,s2,i):
    """
    Checks if there is a suitable point to unify s1 and s2. 

    i: index representing the point to use when intersecting the normal of s1 to s2.

    Return values:
    pi: intersection point between s1 and s2.
    ext: boolean stating whether the point is an extremity of s2.
    pi_adj: adjusted pi (weighted-average between s1 and s2)
    """
    n1 = geo.slope(s1['geom'][0], s1['geom'][-1],True)
    b_n1 = geo.y_intercept(n1,s1['geom'][i])
    m2 = geo.slope(s2['geom'][0], s2['geom'][-1])
    b_m2 = geo.y_intercept(m2,s2['geom'][-1])

    maxx, minx, maxy, miny = geo.boundaries(s2)

    xi,yi = geo.intersection_point(n1,b_n1,m2,b_m2)
    if not (xi > maxx or xi < minx or yi > maxy or yi < miny or \
        geo.distance([xi, yi], s1['geom'][i]) > threshold):

        pi = [xi, yi]
        ext = (pi == s2['geom'][i])
        pi_adj = geo.weighted_avg_point(pi, s1['geom'][i],\
                        s2['meta']['total'], s1['meta']['total'])
        return pi, ext, pi_adj
    else:
        return None, False, None

def unify_segments(s1,s2):
    """
    Checks several intersections to find points that unify s1 and s2.

    Return values:
    pi_s, pi_e: intersection points for the start and end of the segment.
    pi_s_adj, pi_e_adj: above points, but adjusted with a weighted average.
    ext_s, ext_e: booleans stating whether each point is an extremity.
    s_s, s_e: control variables to use in intersection_test.
    """
    pi_s,pi_e,pi_e_adj,pi_s_adj,s_s,s_e = None,None,None,None,None,None
    ext_s, ext_e = False,False

    pi_s, ext_s, pi_s_adj = intersect_segs(s1, s2, 0)
    if(pi_s is None):
        pi_s, ext_s, pi_s_adj = intersect_segs(s2, s1, 0)
        if(pi_s is not None):
            s_s = 0
    else:
        s_s = 1

    pi_e, ext_e, pi_e_adj = intersect_segs(s1, s2, -1)
    if(pi_e is None):
        pi_e, ext_e, pi_e_adj = intersect_segs(s2, s1, -1)
        if(pi_e is not None):
            s_e = 0
    else:
        s_e = 1

    return pi_s, pi_e, pi_s_adj, pi_e_adj, ext_s, ext_e, s_s, s_e

def filter_bins(rows, table):
    conn = connect("dbname=fastgeo user=postgres password=postgres host=localhost port=5432")
    # conn.autocommit = True
    cur = conn.cursor()

    prevs = {}
    to_del = []

    cur.execute(f"select max(trkid) from {table};")
    res = cur.fetchall()[0][0]
    if(res):
        global trkid
        trkid = res + 1
    start = datetime.datetime.now()
    # print("\t\t\t\t", len(rows), "segs.")
    for i in range(len(rows)):
        poly = rows[i]['geom'][-1]
        poly_prev = rows[i]['geom'][0]
        cur.execute(\
            f"select jsonb_agg(features.feature)\
            from (select jsonb_build_object(\
                'geom',   ST_AsGeoJSON(line)::jsonb,\
                'meta', json_build_object(\
                    'total', total,\
                    'times', data_times,\
                    'totals', totals,\
                    'trkid', trkid,\
                    'ids', taxids,\
                    'adj1', adj1,\
                    'adj2', adj2\
            )) AS feature from {table} \
            where st_intersects(line,\
                st_buffer(\
                    st_geomfromtext('LINESTRING({poly[0]} {poly[-1]},\
                        {poly_prev[0]} {poly_prev[-1]})', 4326),\
                    {bb_size},'endcap=flat join=round'))\
            order by st_length(line) desc) features;")
        res = cur.fetchall()
        if(len(res[0]) > 0 and res[0][0] != None):
            for line in res[0][0]:
                line['meta']['bbox'] = set([rows[i]['meta']['trkid']])
                if(line['meta']['trkid'] in prevs):
                    found = False
                    for j in range(len(prevs[line['meta']['trkid']])):
                        if(prevs[line['meta']['trkid']][j]['geom'] == line['geom']):
                            prevs[line['meta']['trkid']][j]['meta']['bbox'].add(rows[i]['meta']['trkid'])
                            found = True
                    if not found:
                        prevs[line['meta']['trkid']].append(line)
                else:
                    prevs[line['meta']['trkid']] = [line]
            to_del.append(i)
    # print("\t\t\t\tQueries:\t", str((datetime.datetime.now() - start).total_seconds()))
    if(prevs):
        start = datetime.datetime.now()
        prev_segs = []
        for i in to_del:
            cur.execute(\
                f"delete from {table} \
                where st_intersects(line,\
                    st_buffer(\
                        st_geomfromtext('LINESTRING({rows[i]['geom'][-1][0]} {rows[i]['geom'][-1][-1]},\
                            {rows[i]['geom'][-1][0]} {rows[i]['geom'][-1][-1]})', 4326),\
                        {bb_size},'endcap=flat join=round'));")
        conn.commit()
        # print("\t\t\t\tDeletions:\t", str((datetime.datetime.now() - start).total_seconds()))
        start = datetime.datetime.now()
        for k in prevs:
            for line in prevs[k]:
                ts = set()
                for i in range(len(line['meta']['times'])):
                    t = line['meta']['times'][i]
                    ts.add(t)
                line['meta']['times'] = ts
                line['geom'] = line['geom']['coordinates']
                line['meta']['adj'] = [set(line['meta']['adj1']), set(line['meta']['adj2'])]
                line['meta']['abs'] = []
                prev_segs.append(line)
        # print("\t\t\t\tAdjusts:\t", str((datetime.datetime.now() - start).total_seconds()))
        return prev_segs
    
    return []

def sbin_match(s1, s2, matches, i):
    # MATCH TYPES
    # 0: full
    # 1: partial, new is rightmost
    # 2: partial, old is rightmost
    # (the difference between 1 and 2 is for computing distances if deciding where to split the segment)
    pi_s, pi_e, pi_s_adj, pi_e_adj, ext_s, ext_e, ss, se = unify_segments(s1, s2)

    if(pi_s == pi_e): # No match, ignore
        return s1, s2, matches

    elif(pi_s is not None and pi_e is not None):
        if(geo.distance(pi_s_adj, pi_e_adj) < error):
            if(geo.distance(pi_s_adj, s1['geom'][0]) <\
            geo.distance(pi_s_adj, s1['geom'][-1])):
                s1['meta']['adj'][0].add(s2['meta']['trkid'])
            else:
                s1['meta']['adj'][-1].add(s2['meta']['trkid'])
            return s1, s2, matches
        if(ext_s and ext_e or ss == se): # full match OR contained
            return s1, s2, matches + [[i, 0]]
        else: 
            return s1, s2, matches + [[i, 1 + ss]]
    
    else:
        return s1, s2, matches
        

def match_bins(segs, nsegs):
    for s in segs:
        s['meta']['matches'] = []

    for s1 in nsegs:
        matches = []
        for i in range(len(segs)):
            s2 = segs[i]
            if(s1['meta']['trkid'] not in s2['meta']['bbox']):
                continue
            b1 = geo.bearing(s1['geom'][0], s1['geom'][-1])
            b2 = geo.bearing(s2['geom'][0], s2['geom'][-1])
            diff = abs(b2 - b1)
            if(diff > opposite_1 and diff < opposite_2):
                s2['geom'] = [s2['geom'][-1], s2['geom'][0]]
                s2['meta']['adj'] = list(reversed(s2['meta']['adj']))
            elif not (diff < diff_1 or diff > diff_2):
                continue

            s1, s2, matches = sbin_match(s1,s2,matches,i)

        max_dist = 0
        true_match = -1
        # FIXME: partial matches should also add the remaining segment
        for m in matches:
            if(m[1] == 0):
                true_match = -2
                max_dist = 1e20
                segs[m[0]]['meta']['matches'].append(s1)
            elif(m[1] == 1):
                dist = geo.distance(s1['geom'][0], segs[m[0]]['geom'][-1])
                if(dist > max_dist):
                    true_match = m[0]
            elif(m[1] == 2):
                dist = geo.distance(segs[m[0]]['geom'][0], s1['geom'][-1])
                if(dist > max_dist):
                    true_match = m[0]

        if(true_match > 0):
            segs[true_match]['meta']['matches'].append(s1)
        elif(true_match == -1):
          s1['meta']['matches'] = []
          s1['meta']['bbox'] = set()
          segs.append(s1)

    return segs

def insert_in_bins(segs):
    for s in segs:
        matches = s['meta']['matches']
        for m in matches:
            m['meta']['clustered'] = False

        def adj_cluster(i):
            start = matches[i]
            start['meta']['clustered'] = True

            for a in start['meta']['adj'][0]:
                for i in range(len(matches)):
                    m = matches[i]
                    if(m['meta']['trkid'] == a and not m['meta']['clustered']):
                        adj_cluster(i)

            for a in start['meta']['adj'][-1]:
                for i in range(len(matches)):
                    m = matches[i]
                    if(m['meta']['trkid'] == a and not m['meta']['clustered']):
                        adj_cluster(i)

            return
        
        for i in range(len(matches)):
            m = matches[i]
            if(m['meta']['clustered']):
                continue
            else:
                s['meta']['total'] += 1
                adj_cluster(i)

    return segs

def split_bins(bins):
    bins_split = []
    for b in bins:
        points = geo.interpolate_distance(b, bin_dist)
        for i in range(1, len(points)):
            bins_split.append({
                'geom': [points[i-1], points[i]],
                'meta': b['meta']
            })
    return bins_split

def sbin_main(addr, segs, table):
    for s in segs:
        s['meta']['adj'] = [set(s['meta']['adj1']), set(s['meta']['adj2'])]
    start_ = datetime.datetime.now()
    start = datetime.datetime.now()
    old_segs = filter_bins(segs, table)
    # print("\t\t\tQuerying:\t", str((datetime.datetime.now() - start).total_seconds()))
    for s in segs:
        s['geom'][0][0] = float(s['geom'][0][0])
        s['geom'][0][1] = float(s['geom'][0][1])
        s['geom'][-1][0] = float(s['geom'][-1][0])
        s['geom'][-1][1] = float(s['geom'][-1][1])
    start = datetime.datetime.now()
    segs = split_bins(segs)
    # print("\t\t\tSplitting:\t", str((datetime.datetime.now() - start).total_seconds()))
    start = datetime.datetime.now()
    bins = match_bins(old_segs, segs)
    # print("\t\t\tMatching:\t", str((datetime.datetime.now() - start).total_seconds()))
    start = datetime.datetime.now()
    bins = insert_in_bins(bins)
    # print("\t\t\tInserting:\t", str((datetime.datetime.now() - start).total_seconds()))
    # print("\t\tTotal time:\t", str((datetime.datetime.now() - start_).total_seconds()))

    return bins