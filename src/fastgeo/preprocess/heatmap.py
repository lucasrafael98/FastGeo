from ujson import dump
from os.path import exists
from geo import segs_to_points
import pickle
from math import cos

def prepare_heatmap(lst):
    """
    Prepares a heatmap for a generic period (unused).
    """
    from psycopg2 import connect
    addr, table = lst
    if not exists(addr):
        open(addr, 'w').write('{"type": "FeatureCollection", "features": []}')
        return
    conn = connect("dbname=fastgeo user=postgres password=postgres host=localhost port=5432")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT jsonb_build_object( \
            'type',     'FeatureCollection',\
            'features', jsonb_agg(features.feature)\
            )FROM (SELECT jsonb_build_object(\
                'type',       'Feature',\
                'geom',   ST_AsGeoJSON(line)::jsonb,\
                'total', total \
            ) AS feature FROM\
            " + table +") features")
    res = cur.fetchall()
    if(len(res[0]) > 0 and res[0][0]['features'] != None):
        for line in res[0][0]['features']:
            line['geom'] = line['geom']['coordinates']
        segs = res[0][0]['features']
        points = segs_to_points(segs)
    
        dump(points, open(addr, 'w'))

def prepare_heatmap_grid(lst):
    """
    Prepares a spatial heatmap for the history period.
    """
    addr, fullgrid = lst
    fullgrid = eval(fullgrid)
    if(fullgrid):
        grid_file = './data/temp/grid.pickle'
        if not exists(grid_file):
            open(addr, 'w').write('[{"type": "FeatureCollection", "features": []}]')
            return
        infile = open(grid_file, 'rb')
        grid_dict = pickle.load(infile)
        infile.close()
        points = [[],[],[],[]]
        start = grid_dict['min']
        end = grid_dict['max']
        grids = [grid_dict['grid'], grid_dict['grid2'], grid_dict['grid3']]#, grid_dict['grid4']]
        for g in range(len(grids)):
            grid = grids[g]
            len_x = len(grid)
            len_y = len(grid[0])
            for i in range(len(grid)):
                for j in range(len(grid[i])):
                    if(not grid[i][j]):
                        continue
                    points[g].append({
                        'type':'Feature',
                        'geometry':{
                            'type': 'Point',
                            'coordinates': [
                                (start[0] * (1 - (i / len_x)) + end[0] * i / len_x),
                                (start[1] * (1 - (j / len_y)) + end[1] * j / len_y)
                            ]
                        },
                        'properties': {'total': grid[i][j]}
                    })

        hmap = [{'new':{"type": "FeatureCollection", "features": points[0]}},
                {'new':{"type": "FeatureCollection", "features": points[1]}},
                {'new':{"type": "FeatureCollection", "features": points[2]}},
                {'new':{"type": "FeatureCollection", "features": points[3]}},]
        dump(hmap, open(addr, 'w'))
    else:
        changes_file = './data/temp/grid_changes.pickle'
        if not exists(changes_file):
            open(addr, 'w').write('[{"type": "FeatureCollection", "features": []}]')
            return
        infile = open(changes_file, 'rb')
        grid_dict = pickle.load(infile)
        infile.close()
        squares = [[],[],[],[]]
        start = grid_dict['min']
        end = grid_dict['max']
        changes = grid_dict['changes']
        for g in range(len(changes)):
            change = changes[g]
            if(change['new'] == {}):
                continue
            len_x, len_y = grid_dict['len'][g]
            for k in change['new']:
                c = change['new'][k]
                i = c[1]
                j = c[2]
                x = (start[0] * (1 - (i / len_x)) + end[0] * i / len_x)
                y = (start[1] * (1 - (j / len_y)) + end[1] * j / len_y)
                squares[g].append({
                    'type':'Feature',
                    'geometry':{
                        'type': 'Point',
                        'coordinates': [x, y]
                    },
                    'properties': {'total': c[0], 'pos': k}
                })
            change['new'] = {"type": "FeatureCollection", "features": squares[g]}

        dump(changes, open(addr, 'w'))

def prepare_heatmap_square_grid(lst):
    """
    Prepares a cluster heatmap for the history period.
    """
    addr, res, fullgrid = lst
    res = eval(res) / 2 / 111111
    fullgrid = eval(fullgrid)
    rs = [res, res * 2, res * 4]
    if(fullgrid):
        grid_file = './data/temp/grid.pickle'
        if not exists(grid_file):
            open(addr, 'w').write('[{"type": "FeatureCollection", "features": []}]')
            return
        infile = open(grid_file, 'rb')
        grid_dict = pickle.load(infile)
        infile.close()
        squares = [[],[],[],[]]
        start = grid_dict['min']
        end = grid_dict['max']
        grids = [grid_dict['grid'], grid_dict['grid2'], grid_dict['grid3']]#, grid_dict['grid4']]
        for g in range(len(grids)):
            grid = grids[g]
            len_x = len(grid)
            len_y = len(grid[0])
            for i in range(len(grid)):
                for j in range(len(grid[i])):
                    if(not grid[i][j]):
                        continue
                    x = (start[0] * (1 - (i / len_x)) + end[0] * i / len_x)
                    y = (start[1] * (1 - (j / len_y)) + end[1] * j / len_y)
                    rc = rs[g] / cos(y) * 1.25
                    squares[g].append({
                        'type':'Feature',
                        'geometry':{
                            'type': 'Polygon',
                            'coordinates': [[
                                [x - rc, y - rs[g]], [x - rc, y + rs[g]], 
                                [x + rc, y + rs[g]], [x + rc, y - rs[g]]]]
                        },
                        'properties': {'total': grid[i][j]}
                    })

        hmap = [{'new':{"type": "FeatureCollection", "features": squares[0]}},
                {'new':{"type": "FeatureCollection", "features": squares[1]}},
                {'new':{"type": "FeatureCollection", "features": squares[2]}},
                {'new':{"type": "FeatureCollection", "features": squares[3]}},]
        dump(hmap, open(addr, 'w'))
    else:
        changes_file = './data/temp/grid_changes.pickle'
        if not exists(changes_file):
            open(addr, 'w').write('[{"type": "FeatureCollection", "features": []}]')
            return
        infile = open(changes_file, 'rb')
        grid_dict = pickle.load(infile)
        infile.close()
        squares = [[],[],[],[]]
        start = grid_dict['min']
        end = grid_dict['max']
        changes = grid_dict['changes']
        for g in range(len(changes)):
            change = changes[g]
            if(change['new'] == {}):
                continue
            len_x, len_y = grid_dict['len'][g]
            for k in change['new']:
                c = change['new'][k]
                i = c[1]
                j = c[2]
                x = (start[0] * (1 - (i / len_x)) + end[0] * i / len_x)
                y = (start[1] * (1 - (j / len_y)) + end[1] * j / len_y)
                rc = rs[g] / cos(y) * 1.25
                squares[g].append({
                    'type':'Feature',
                    'geometry':{
                        'type': 'Polygon',
                        'coordinates': [[
                            [x - rc, y - rs[g]], [x - rc, y + rs[g]], 
                            [x + rc, y + rs[g]], [x + rc, y - rs[g]]]]
                    },
                    'properties': {'total': c[0], 'pos': k, 'grid':[i,j]}
                })
            change['new'] = {"type": "FeatureCollection", "features": squares[g]}

        dump(changes, open(addr, 'w'))