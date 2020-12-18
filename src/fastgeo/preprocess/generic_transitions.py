"""
Handling transitions between generic modules.
"""

import datetime
from yaml import load as yload, FullLoader
from ujson import dump, load
from csv import reader as csvreader, writer as csvwriter
from file_conversion import segs_to_csv
from copy import deepcopy
from spatial_binning import sbin_main as spatial_binning
from psycopg2 import connect
from geo import str2time

config = yload(open("./config.yaml"), Loader=FullLoader)
start_time = str2time(config['streamStartTime'])

def remove_old(lst):
    """
    Removes old time bins from the recent period.
    """
    # start = datetime.datetime.now()
    addr_in, addr_out, addr_remove, table, cutoff = lst
    cutoff = str2time(cutoff, True)

    conn = connect("dbname=fastgeo user=postgres password=postgres host=localhost port=5432")
    conn.autocommit = True
    cur = conn.cursor()

    to_delete = []
    to_reinsert = []
    to_next = []
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
            reinsert_full = True
            for i in range(len(line['meta']['times'])):
                t = str2time(line['meta']['times'][i], True)
                if(t < cutoff):
                    if(i > 0):
                        to_reinsert.append(deepcopy(line))
                        to_reinsert[-1]['meta']['times'] = line['meta']['times'][:i]
                        to_reinsert[-1]['meta']['totals'] = line['meta']['totals'][:i]
                        sum_total = 0
                        for total in to_reinsert[-1]['meta']['totals']:
                            sum_total += total
                        to_reinsert[-1]['meta']['total'] = sum_total
                    to_delete.append(line['meta']['trkid'])
                    to_next.append(deepcopy(line))
                    to_next[-1]['meta']['times'] = line['meta']['times'][i:]
                    to_next[-1]['meta']['totals'] = line['meta']['totals'][i:]
                    sum_total = 0
                    for total in to_next[-1]['meta']['totals']:
                        sum_total += total
                    to_next[-1]['meta']['total'] = sum_total
                    reinsert_full = False
                    break
            if(reinsert_full):
                to_reinsert.append(line)
        cur.execute("truncate " + table + ";")
    
    dump({'values': to_delete}, open(addr_remove, 'w'))
    dump(to_next, open(addr_out, 'w'))
    csvwriter(open(addr_in, 'w', newline=''), delimiter='|').writerows(segs_to_csv(to_reinsert))
    # print("Removal time:\t", str((datetime.datetime.now() - start).total_seconds()))
    return

def update_new(lst):
    # start = datetime.datetime.now()
    addr, addr_added, bin_size, curr_time, table = lst
    bin_size = eval(bin_size)
    curr_time = str2time(curr_time, True)

    segs = load(open(addr, 'r'))

    adjusted_time = curr_time - datetime.timedelta(\
        seconds=(curr_time - start_time).total_seconds() % bin_size)
    for s in segs:
        ts = {}
        for t in s['meta']['times']:
            t = str2time(t, True)
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
        s['remove'] = False

    segs = spatial_binning(addr, list(segs), table)

    csvwriter(open(addr, 'w', newline=''), delimiter='|').writerows(segs_to_csv(segs))
    return
    
    
    