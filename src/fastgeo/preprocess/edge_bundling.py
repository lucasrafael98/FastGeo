"""
Modified version of UnderstandMySteps: https://github.com/DSil/UnderstandMySteps.
Uses code from gpxpy.
Points are [longitude, latitude].
"""
import datetime, geo
from yaml import load as yload, FullLoader
from psycopg2 import connect
from csv import reader as csvreader, writer as csvwriter
from adjacencies import correct_adjacencies
from file_conversion import segs_to_csv

config = yload(open("./config.yaml"), Loader=FullLoader)

start_time = geo.str2time(config['streamStartTime'])
threshold = config['edgeBundlingDistThreshold']
diff_1 = config['edgeBundlingAngleDiff']
opposite_1 = 180 - diff_1
opposite_2 = 180 + diff_1
diff_2 = 360 - diff_1
error = 1e-6
min_dist = config['edgeBundlingMinDist']
trkid = 0
bb_size = str(threshold / 111111)

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

def new_seg(lst,pair,s1,s2=None,adj=None):
    """
    Creates a new seg with <pair> points using 
    the metadata from s1 (and s2), and puts it on lst.
    """
    # FIXME: two segments with diff ids but equal times
    if(geo.distance(pair[0], pair[1]) < min_dist):
        return
    nseg = {}
    nseg['geom'] = pair
    if(s2 is None):
        nseg['meta'] = {'total': len(s1['meta']['times']),\
            'times': s1['meta']['times'], 'ids': s1['meta']['ids'],\
            'bbox': s1['meta']['bbox']}
    else:
        nseg['meta'] = {'times': s1['meta']['times'].union(s2['meta']['times']),\
            'ids': s1['meta']['ids'].union(s2['meta']['ids']),\
            'bbox': s1['meta']['bbox'].union(s2['meta']['bbox'])}
        nseg['meta']['total'] = len(nseg['meta']['times'])
    global trkid
    nseg['meta']['trkid'] = trkid
    nseg['meta']['abs'] = []
    trkid += 1
    if(adj is not None):
        nseg['meta']['adj'] = adj
    lst.append(nseg)

def intersection_test(l1,l2,s1,s2,i,j, adjust=False):
    pi_s, pi_e, pi_s_adj, pi_e_adj, ext_s, ext_e, ss, se = unify_segments(s1, s2)
    ls = [l1,l2]
    segs = [s1,s2]
    adjs = [s1['meta']['adj'], s2['meta']['adj']]
    abss = [s1['meta']['abs'] + [s1['meta']['trkid']],\
            s2['meta']['abs'] + [s2['meta']['trkid']]]
    global trkid

    if(pi_s == pi_e):
        return i,j,l1,l2,False
    elif(pi_s is not None and pi_e is not None):
        if(geo.distance(pi_s_adj, pi_e_adj) < min_dist):
            return i,j,l1,l2,False
        
        if(not ext_s):
            ti1 = trkid
            if(adjust):
                ns = geo.slope(segs[ss]['geom'][0], pi_s, True)
                b_ns = geo.y_intercept(ns, segs[ss]['geom'][0])
                m_pi = geo.slope(pi_s_adj, pi_e_adj)
                b_m_pi = geo.y_intercept(m_pi, pi_s_adj)
                xi_s, yi_s = geo.intersection_point(ns, b_ns, m_pi, b_m_pi)
                new_seg(ls[ss],[[xi_s, yi_s], pi_s_adj],\
                        segs[ss], adj=[adjs[ss][0], set()])
            else:
                new_seg(ls[ss],[segs[ss]['geom'][0], pi_s], \
                    segs[ss], adj=[adjs[ss][0], set()])
            if(trkid != ti1):
                adjs[ss][0] = set([trkid])
                ls[ss][-1]['meta']['abs'] += abss[ss]
        if(not ext_e):
            ti1 = trkid
            if(adjust):
                ne = geo.slope(segs[se]['geom'][-1], pi_e, True)
                b_ne = geo.y_intercept(ne, segs[se]['geom'][-1])
                m_pi = geo.slope(pi_s_adj, pi_e_adj)
                b_m_pi = geo.y_intercept(m_pi, pi_e_adj)
                xi_e, yi_e = geo.intersection_point(ne, b_ne, m_pi, b_m_pi)
                new_seg(ls[se],[pi_e_adj, [xi_e, yi_e]],\
                        segs[se], adj=[set(), adjs[se][-1]])
            else:
                new_seg(ls[se],[pi_e, segs[se]['geom'][-1]], \
                    segs[se], adj=[set(), adjs[se][-1]])
            if(trkid != ti1):
                adjs[se][-1] = set([trkid])
                ls[se][-1]['meta']['abs'] += abss[se]

        adjs = [adjs[0][0].union(adjs[-1][0]), adjs[0][-1].union(adjs[-1][-1])]
        new_seg(ls[0],[pi_s_adj, pi_e_adj], s1, s2, adjs)
        if(ss != 0 and se != 0):
            ls[0][-1]['meta']['abs'] += abss[0]
        if(ss != -1 and se != -1):
            ls[0][-1]['meta']['abs'] += abss[-1]
        del l2[j]
        del l1[i]
        i -= 1
        j -= 1
        return i,j,ls[0],ls[1],True
    return i,j,l1,l2,False
    

def merge(segs, prev_segs=None):
    for i in range(len(segs)):
        si = 0
        while si < len(segs[i]):
            segment_deleted = False
            for j in range(len(segs)):
                if(i == j):
                    continue
                if(segment_deleted):
                    break
                sj = 0
                while sj < len(segs[j]):
                    s1 = segs[i][si]
                    s2 = segs[j][sj]

                    b1 = geo.bearing(s1['geom'][0], s1['geom'][-1])
                    b2 = geo.bearing(s2['geom'][0], s2['geom'][-1])
                    diff = abs(b2 - b1)
                    if(diff > opposite_1 and diff < opposite_2):
                        s2['geom'] = [s2['geom'][-1], s2['geom'][0]]
                        s2['meta']['adj'] = list(reversed(s2['meta']['adj']))
                    elif not (diff < diff_1 or diff > diff_2):
                        sj += 1
                        continue

                    if(s1['geom'][-1] == s2['geom'][0]):
                        s1['meta']['adj'][-1].add(s2['meta']['trkid'])
                        s2['meta']['adj'][0].add(s1['meta']['trkid'])
                        sj += 1
                        continue
                    if(s1['geom'][0] == s2['geom'][-1]):
                        s1['meta']['adj'][0].add(s2['meta']['trkid'])
                        s2['meta']['adj'][-1].add(s1['meta']['trkid'])
                        sj += 1
                        continue
                    si, sj, segs[i],segs[j],segment_deleted =\
                        intersection_test(\
                            segs[i], segs[j], s1, s2, si, sj)
                    if(segment_deleted):
                        break
                    sj += 1
            si += 1

    new_segs = []
    for group in segs:
        new_segs += group
    segs = new_segs

    if(prev_segs):
        i = 0
        while i < len(new_segs):
            s1 = new_segs[i]
            j = 0
            while j < len(prev_segs):
                s2 = prev_segs[j]
                can_compare = False
                for bb in s1['meta']['bbox']:
                    if(bb in s2['meta']['bbox']):
                        can_compare = True
                        break
                if not can_compare:
                    j += 1
                    continue

                b1 = geo.bearing(s1['geom'][0], s1['geom'][-1])
                b2 = geo.bearing(s2['geom'][0], s2['geom'][-1])
                diff = abs(b2 - b1)
                if(diff > opposite_1 and diff < opposite_2):
                    s2['geom'] = [s2['geom'][-1], s2['geom'][0]]
                    s2['meta']['adj'] = list(reversed(s2['meta']['adj']))
                elif not (diff < diff_1 or diff > diff_2):
                    j += 1
                    continue

                if(s1['geom'][-1] == s2['geom'][0]):
                    s1['meta']['adj'][-1].add(s2['meta']['trkid'])
                    s2['meta']['adj'][0].add(s1['meta']['trkid'])
                    j += 1
                    continue
                if(s1['geom'][0] == s2['geom'][-1]):
                    s1['meta']['adj'][0].add(s2['meta']['trkid'])
                    s2['meta']['adj'][-1].add(s1['meta']['trkid'])
                    j += 1
                    continue

                i, j, new_segs, prev_segs, segment_deleted =\
                    intersection_test(\
                        new_segs, prev_segs, s1, s2, i, j)

                if(segment_deleted):
                    break
                j += 1
            i += 1
        
        segs = prev_segs + new_segs
    return segs

def query_bb(rows, table):
    conn = connect("dbname=fastgeo user=postgres password=postgres host=localhost port=5432")
    conn.autocommit = True
    cur = conn.cursor()

    segs = []
    prevs = {}
    prev_segs = []

    cur.execute(f"select max(trkid) from {table};")
    res = cur.fetchall()[0][0]
    if(res is not None):
        global trkid
        trkid = res + 1
    start_q = datetime.datetime.now()
    for i in range(1, len(rows)):
        poly = rows[i]
        poly_prev = rows[i-1]
        if(poly[1] == poly_prev[1]):
            segs.append([poly[0], poly_prev[2], poly_prev[3], poly[2], poly[3], poly_prev[4], poly[4], poly[1]])
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
                        st_geomfromtext('LINESTRING({poly[2]} {poly[3]},\
                            {poly_prev[2]} {poly_prev[3]})', 4326),\
                        {bb_size},'endcap=flat join=round'))\
                order by st_length(line) desc) features;")
            res = cur.fetchall()
            if(len(res[0]) > 0 and res[0][0] != None):
                for line in res[0][0]:
                    line['meta']['bbox'] = set([eval(poly[1])])
                    prevs[line['meta']['trkid']] = line
    # print("\t\t\tSelection:\t", str((datetime.datetime.now() - start_q).total_seconds()))
    start_q = datetime.datetime.now()
    if(prevs):
        for k in prevs:
            line = prevs[k]
            ts = set()
            for i in range(len(line['meta']['times'])):
                t = line['meta']['times'][i]
                tot = line['meta']['totals'][i]
                for j in range(tot):
                    ts.add(geo.str2time(t, True) + datetime.timedelta(seconds=j))
            line['meta']['times'] = ts
            line['geom'] = line['geom']['coordinates']
            line['meta']['adj'] = [set(line['meta']['adj1']), set(line['meta']['adj2'])]
            line['meta']['abs'] = []
            prev_segs.append(line)
        # print("\t\t\tOrganization:\t", str((datetime.datetime.now() - start_q).total_seconds()))
        start_q = datetime.datetime.now()

    prevs_nobbox = []
    cur.execute(\
                f"select jsonb_agg(features.feature)\
                from (select jsonb_build_object(\
                    'geom',   ST_AsGeoJSON(line)::jsonb,\
                    'meta', json_build_object(\
                        'total', total,\
                        'totals', totals,\
                        'times', data_times,\
                        'trkid', trkid,\
                        'ids', taxids,\
                        'adj1', adj1,\
                        'adj2', adj2,\
                        'bbox', array[]::integer[],\
                        'abs', array[]::integer[]\
                )) AS feature from {table}) features;")
    res = cur.fetchall()
    # print("\t\t\tNo BBQuery:\t", str((datetime.datetime.now() - start_q).total_seconds()))
    start_q = datetime.datetime.now()
    if(len(res[0]) > 0 and res[0][0] != None):
        cur.execute(f"truncate {table};")
        for line in res[0][0]:
            if(line['meta']['trkid'] in prevs):
                continue
            line['geom'] = line['geom']['coordinates']
            line['meta']['adj'] = [set(line['meta']['adj1']), set(line['meta']['adj2'])]
            prevs_nobbox.append(line)
    # print("\t\t\tRemainder:\t", str((datetime.datetime.now() - start_q).total_seconds()))
    
    prevs = prev_segs
    return segs, prevs, prevs_nobbox

def parse(segs):
    global trkid
    segs_split = []
    segs_json = []
    points = []
    previd = -1
    prevtrkid = -1

    for s in segs:
        if(eval(s[7]) != prevtrkid):
            if(prevtrkid != -1):
                if(len(points) > 2):
                    segs_track_temp = geo.simplify(points, times)
                    segs_track = []
                    for st in segs_track_temp:
                        # datasets are weird like that sometimes.
                        if(st['geom'][0] == st['geom'][1]):
                            continue
                        segs_track.append(st)
                    for i in range(len(segs_track)):
                        seg = segs_track[i]
                        seg['meta'] = dict(seg['meta'], **{
                            'abs': [],
                            'adj': [set(), set()],
                            'bbox': set([prevtrkid]),
                            'ids': set([previd]),
                            'total': 1
                        })
                        seg['meta']['trkid'] = trkid
                        if(i > 0):
                            seg['meta']['adj'][0] = set([trkid - 1])
                        if(i < len(segs_track) - 1):
                            seg['meta']['adj'][1] = set([trkid + 1])
                        trkid += 1
                    segs_json += segs_track
                else:
                    seg = {'geom': points, 'meta': {
                            'abs': [],
                            'adj': [set(), set()],
                            'bbox': set([prevtrkid]),
                            'ids': set([previd]),
                            'total': 1
                        }}
                    seg['meta']['trkid'] = trkid
                    seg['meta']['times'] = set([times[-1]])
                    trkid += 1
                    segs_json.append(seg)
            points = [[eval(s[1]), eval(s[2])]]
            times = [datetime.datetime.strptime(s[5], "%Y-%m-%d %H:%M:%S")]
        if(eval(s[0]) != previd and previd != -1):
            segs_split.append(segs_json)
            segs_json = []
        
        points.append([eval(s[3]), eval(s[4])])
        times.append(datetime.datetime.strptime(s[6], "%Y-%m-%d %H:%M:%S"))
        previd = eval(s[0])
        prevtrkid = eval(s[7])

    if(len(points)):
        if(len(points) > 2):
            segs_track_temp = geo.simplify(points, times)
            segs_track = []
            for st in segs_track_temp:
                # datasets are weird like that sometimes.
                if(st['geom'][0] == st['geom'][1]):
                    continue
                segs_track.append(st)
            for i in range(len(segs_track)):
                seg = segs_track[i]
                seg['meta'] = dict(seg['meta'], **{
                    'abs': [],
                    'adj': [set(), set()],
                    'bbox': set([prevtrkid]),
                    'ids': set([previd]),
                    'total': 1
                })
                seg['meta']['trkid'] = trkid
                if(i > 0):
                    seg['meta']['adj'][0] = set([trkid - 1])
                if(i < len(segs_track) - 1):
                    seg['meta']['adj'][1] = set([trkid + 1])
                trkid += 1
            segs_json += segs_track
        else:
            seg = {'geom': points, 'meta': {
                    'abs': [],
                    'adj': [set(), set()],
                    'bbox': set([prevtrkid]),
                    'ids': set([previd]),
                    'total': 1
                }}
            seg['meta']['trkid'] = trkid
            seg['meta']['times'] = set([times[-1]])
            trkid += 1
            segs_json.append(seg)
        if(eval(s[0]) != previd and previd != -1):
            segs_split.append(segs_json)
            segs_json = []
    
    if(segs_json != []):
        segs_split.append(segs_json)
        
    return segs_split

def binning(segs, bin_size, curr_time):
    bin_size = eval(bin_size)
    curr_time = geo.str2time(curr_time, True)

    adjusted_time = curr_time - datetime.timedelta(\
        seconds=(curr_time - start_time).total_seconds() % bin_size)

    for s in segs:
        ts = {}
        for t in s['meta']['times']:
            if(t >= adjusted_time):
                bin_time = adjusted_time
            else:
                bin_time = adjusted_time - datetime.timedelta(\
                    seconds=(adjusted_time - t).total_seconds() // \
                    bin_size * bin_size)
            if(bin_time in ts):
                ts[bin_time] += 1
            else:
                ts[bin_time] = 1
        s['meta']['times'] = list(ts.keys())
        s['meta']['totals'] = list(ts.values())

    return segs

def main(lst):
    addr, bin_size, curr_time, table = lst
    start_ = datetime.datetime.now()
    start = datetime.datetime.now()
    file_in = open(addr, 'r')
    rows = list(csvreader(file_in, delimiter=','))
    segs, prevs, prevs_nobbox = query_bb(rows, table)
    # print("\t\tQuerying:\t", str((datetime.datetime.now() - start).total_seconds()))
    start = datetime.datetime.now()
    segs = parse(segs)
    # print("\t\tParsing:\t", str((datetime.datetime.now() - start).total_seconds()))
    start = datetime.datetime.now()
    segs = merge(segs, prevs)
    # print("\t\tMerging:\t", str((datetime.datetime.now() - start).total_seconds()))
    segs = binning(segs, bin_size, curr_time)
    if(prevs_nobbox):
        segs += prevs_nobbox
    start = datetime.datetime.now()
    segs = correct_adjacencies(segs)
    # print("\t\tCorrecting:\t", str((datetime.datetime.now() - start).total_seconds()))
    for s in segs:
        s['meta']['times'] = list(s['meta']['times'])
        s['meta']['ids'] = list(s['meta']['ids'])
        s['meta']['adj1'] = list(s['meta']['adj'][0])
        s['meta']['adj2'] = list(s['meta']['adj'][1])
        del s['meta']['bbox']
        del s['meta']['adj']
        del s['meta']['abs']
    segs = segs_to_csv(segs)
    out = open(addr, 'w', newline='')
    writer = csvwriter(out, delimiter='|')
    writer.writerows(segs)
    # print("\tBundling time:\t", str((datetime.datetime.now() - start_).total_seconds()))