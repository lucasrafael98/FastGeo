"""
Adjancency treatment.
"""

import datetime
from geo import distance, multi_weighted_avg_point
from yaml import load as yload, FullLoader
from ujson import dump
from psycopg2 import connect

config = yload(open("./config.yaml"), Loader=FullLoader)
min_dist = config['edgeBundlingMinDist']

def correct_adjacencies(segs):
    """
    Used after trajectory bundling.
    """
    smap = {}
    for s in segs:
        if(distance(s['geom'][0], s['geom'][1]) > min_dist):
            s['meta']['adjusted'] = [False,False]
            smap[s['meta']['trkid']] = s

    for k in reversed(sorted(smap)):
        for i in [0,-1]:
            for kk in reversed(sorted(smap[k]['meta']['adj'][i])):
                if(kk in smap and \
                    (k not in smap[kk]['meta']['adj'][0] \
                    and k not in smap[kk]['meta']['adj'][-1])):
                    if(distance(smap[k]['geom'][i], smap[kk]['geom'][0]) <\
                        distance(smap[k]['geom'][i], smap[kk]['geom'][-1])):
                        smap[kk]['meta']['adj'][0].add(k)
                    else:
                        smap[kk]['meta']['adj'][-1].add(k)
                    for ka in smap[k]['meta']['abs']:
                        if ka in smap[kk]['meta']['adj'][0]:
                            smap[kk]['meta']['adj'][0].remove(ka)
                        if ka in smap[kk]['meta']['adj'][-1]:
                            smap[kk]['meta']['adj'][-1].remove(ka)
                    for ka in smap[kk]['meta']['abs']:
                        if ka in smap[k]['meta']['adj'][0]:
                            smap[k]['meta']['adj'][0].remove(ka)
                        if ka in smap[k]['meta']['adj'][-1]:
                            smap[k]['meta']['adj'][-1].remove(ka)
                elif(kk not in smap):
                    min_key = -1
                    min_point = -1
                    min_d = 1e24
                    for l in reversed(sorted(smap)):
                        if(l <= kk): 
                            break
                        if(kk in smap[l]['meta']['abs']):
                            for j in [0,-1]:
                                d = distance(smap[k]['geom'][i], smap[l]['geom'][j])
                                if(d < min_d):
                                    min_key = l
                                    min_point = j
                                    min_d = d
                    if(min_key != -1):
                        smap[min_key]['meta']['adj'][min_point].add(k)
                        if(kk in smap[k]['meta']['adj'][i]):
                            smap[k]['meta']['adj'][i].remove(kk)
                        smap[k]['meta']['adj'][i].add(min_key)
                        for ka in smap[k]['meta']['abs']:
                            if ka in smap[min_key]['meta']['adj'][0]:
                                smap[min_key]['meta']['adj'][0].remove(ka)
                            if ka in smap[min_key]['meta']['adj'][-1]:
                                smap[min_key]['meta']['adj'][-1].remove(ka)
                        for ka in smap[min_key]['meta']['abs']:
                            if ka in smap[k]['meta']['adj'][0]:
                                smap[k]['meta']['adj'][0].remove(ka)
                            if ka in smap[k]['meta']['adj'][-1]:
                                smap[k]['meta']['adj'][-1].remove(ka)
                    else:
                        smap[k]['meta']['adj'][i].remove(kk)

    segs = list(smap.values())
    return segs

def adjust_adjacencies(segs):
    smap = {}
    for s in segs:
        s['meta']['adjusted'] = [False,False]
        smap[s['meta']['trkid']] = s

    for k in reversed(sorted(smap)):
        for i in [0,-1]:
            if(not smap[k]['meta']['adjusted'][i]):
                points = [smap[k]['geom'][i]]
                weights = [smap[k]['meta']['total']]
                keys_cl = []
                points_cl = []
                weights_cl = []
                for kk in smap[k]['meta']['adj'][i]:
                    if(kk not in smap):
                        continue
                    if(k in smap[kk]['meta']['adj'][0] and not smap[kk]['meta']['adjusted'][0]):
                        if(distance(smap[k]['geom'][i], smap[kk]['geom'][0])
                             > distance(smap[k]['geom'][i], smap[kk]['geom'][1])):
                            points.append(smap[kk]['geom'][1])
                            weights.append(smap[kk]['meta']['total'])
                        else:
                            points.append(smap[kk]['geom'][0])
                            weights.append(smap[kk]['meta']['total'])
                        for kj in smap[kk]['meta']['adj'][0]:
                            if(kj != k and kj in smap):
                                if(kk in smap[kj]['meta']['adj'][0] and not smap[kj]['meta']['adjusted'][0]
                                    and distance(smap[kk]['geom'][0], smap[kj]['geom'][0])
                                     < distance(smap[kk]['geom'][0], smap[kj]['geom'][1])):
                                    keys_cl.append([kj, 0])
                                    points_cl.append(smap[kj]['geom'][0])
                                    weights_cl.append(smap[kj]['meta']['total'])
                                elif(kk in smap[kj]['meta']['adj'][-1] and not smap[kj]['meta']['adjusted'][1]
                                    and distance(smap[kk]['geom'][0], smap[kj]['geom'][0])
                                     > distance(smap[kk]['geom'][0], smap[kj]['geom'][1])):
                                    keys_cl.append([kj, 1])
                                    points_cl.append(smap[kj]['geom'][1])
                                    weights_cl.append(smap[kj]['meta']['total'])
                    elif(k in smap[kk]['meta']['adj'][-1] and not smap[kk]['meta']['adjusted'][1]):
                        if(distance(smap[k]['geom'][i], smap[kk]['geom'][0])
                             < distance(smap[k]['geom'][i], smap[kk]['geom'][1])):
                            points.append(smap[kk]['geom'][1])
                            weights.append(smap[kk]['meta']['total'])
                        else:
                            points.append(smap[kk]['geom'][-1])
                            weights.append(smap[kk]['meta']['total'])
                        for kj in smap[kk]['meta']['adj'][-1]:
                            if(kj != k and kj in smap):
                                if(kk in smap[kj]['meta']['adj'][0] and not smap[kj]['meta']['adjusted'][0]
                                    and distance(smap[kk]['geom'][-1], smap[kj]['geom'][0])
                                     < distance(smap[kk]['geom'][-1], smap[kj]['geom'][1])):
                                    keys_cl.append([kj, 0])
                                    points_cl.append(smap[kj]['geom'][0])
                                    weights_cl.append(smap[kj]['meta']['total'])
                                elif(kk in smap[kj]['meta']['adj'][-1] and not smap[kk]['meta']['adjusted'][1]
                                    and distance(smap[kk]['geom'][-1], smap[kj]['geom'][0])
                                     > distance(smap[kk]['geom'][-1], smap[kj]['geom'][1])):
                                    keys_cl.append([kj, 1])
                                    points_cl.append(smap[kj]['geom'][1])
                                    weights_cl.append(smap[kj]['meta']['total'])
                    else:
                        continue
                point = multi_weighted_avg_point(points + points_cl, weights + weights_cl)
                smap[k]['geom'][i] = point
                for l in keys_cl:
                    smap[l[0]]['geom'][l[1]] = point
                    smap[l[0]]['meta']['adjusted'][l[1]] = True
                for kk in smap[k]['meta']['adj'][i]:
                    if(kk not in smap):
                        continue
                    if(k in smap[kk]['meta']['adj'][0]):
                        smap[kk]['geom'][0] = point
                        smap[kk]['meta']['adjusted'][0] = True
                    elif(k in smap[kk]['meta']['adj'][-1]):
                        smap[kk]['geom'][-1] = point
                        smap[kk]['meta']['adjusted'][-1] = True
                
                
    segs = list(smap.values())
    return segs

def display_adjacencies(lst):
    """
    Displays the bundled lines with adjacencies corrected.

    This does not overwrite data because that might create problems (check the thesis).
    """
    # start = datetime.datetime.now()
    table, addr = lst
    conn = connect("dbname=fastgeo user=postgres password=postgres host=localhost port=5432")
    conn.autocommit = True
    cur = conn.cursor()

    segs = []

    cur.execute("select jsonb_agg(features.feature)\
                from (select jsonb_build_object(\
                    'geom',   ST_AsGeoJSON(line)::jsonb,\
                    'meta', json_build_object(\
                        'total', total,\
                        'totals', totals,\
                        'times', data_times,\
                        'trkid', trkid,\
                        'ids', taxids,\
                        'adj1', adj1,\
                        'adj2', adj2\
                )) AS feature from " + table + ") features;")
    res = cur.fetchall()
    if(len(res[0]) > 0 and res[0][0] != None):
        for line in res[0][0]:
            line['geom'] = line['geom']['coordinates']
            line['meta']['adj'] = [set(line['meta']['adj1']), set(line['meta']['adj2'])]
            line['meta']['abs'] = []
            line['meta']['f1'] = line['meta']['total']
            segs.append(line)

    segs = adjust_adjacencies(segs)

    segs_json = {'type': 'FeatureCollection', 'features': []}

    for line in segs:
        del line['meta']['adj']
        segs_json['features'].append({
            'type' : 'Feature',
            'geometry':{
                'type' : 'LineString',
                'coordinates': line['geom']
            },
            'properties': line['meta']
        })  
    dump(segs_json, open(addr, 'w'))
    # print("\t\tAdjacency display:\t", str((datetime.datetime.now() - start).total_seconds()))
