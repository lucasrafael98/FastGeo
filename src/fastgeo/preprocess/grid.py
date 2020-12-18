"""
Grid binning.
""" 
from ujson import dumps, loads
from geo import distance, interpolate_distance, in_bb
import datetime
import pickle
from os.path import isfile
from os import remove
from numpy import array, zeros, uint16, isclose
from math import ceil, cos, sqrt

grid_file = './data/temp/grid.pickle'
# the changes file is used to optimize grid display.
changes_file = './data/temp/grid_changes.pickle'

def grid_update(lst):

    def high_level_grid(prev_grid):
        """
        Creates a grid that is half the size as prev_grid.
        """
        len_x = len(prev_grid)
        len_y = len(prev_grid[0])
        new_grid = zeros((round(len_x / 2), round(len_y/ 2)),dtype=uint16)
        return new_grid

    addr, res, threshold, display = lst
    res = eval(res)
    display = eval(display)
    threshold = eval(threshold)
    segs = loads(open(addr, 'r').read())
    grid_changes = [{'delta': {}, 'new': {}, 'rebin': 0},\
                    {'delta': {}, 'new': {}, 'rebin': 0},\
                    {'delta': {}, 'new': {}, 'rebin': 0}]
    
    if(not len(segs)):
        if(isfile(changes_file)):
            remove(changes_file)
        return
    
    if(not isfile(grid_file)):
        minlo, minla, maxlo, maxla = [1e6, 1e6, -1e6, -1e6]
        for s in segs:
            if(s['geom'][0][0] < minlo):
                minlo = s['geom'][0][0]
            if(s['geom'][0][1] < minla):
                minla = s['geom'][0][1]
            if(s['geom'][-1][0] < minlo):
                minlo = s['geom'][-1][0]
            if(s['geom'][-1][1] < minla):
                minla = s['geom'][-1][1]
            if(s['geom'][0][0] > maxlo):
                maxlo = s['geom'][0][0]
            if(s['geom'][0][1] > maxla):
                maxla = s['geom'][0][1]
            if(s['geom'][-1][0] > maxlo):
                maxlo = s['geom'][-1][0]
            if(s['geom'][-1][1] > maxla):
                maxla = s['geom'][-1][1]

        start = [minlo, minla]
        end = [maxlo, maxla]
        d = distance(start,[end[0], start[1]])
        res_a = res * 4
        if(d % res_a != 0):
            adjust = ((res_a - (d % res_a)) / d) * abs(maxlo - minlo)
            end[0] += adjust
        d = distance(start,[start[0], end[1]])
        if(d % res_a != 0):
            adjust = ((res_a - (d % res_a)) / d) * abs(maxla - minla)
            end[1] += adjust
        len_x = round(distance(start, [end[0], minla]) / res)
        len_y = round(distance(start, [minlo, end[1]]) / res)
        
        grid = zeros((len_x, len_y),dtype=uint16)
        grid2, grid3 = [[],[]]

        if((len_x + 1) >= 2 and (len_x + 1) >= 2):
            grid2 = high_level_grid(grid)
        
        if((len_x + 1) >= 4 and (len_x + 1) >= 4):
            grid3 = high_level_grid(grid2)

        g2_exists = (grid2 != [])
        g3_exists = (grid3 != [])

        prevx, prevy = [-1,-1]
        grid_sum = 0
        subtr_x = len_x / (end[0] - start[0])
        subtr_y = len_y / (end[1] - start[1])
        for s in segs:
            grid_sum += s['meta']['total']
            points = interpolate_distance(s, res)
            for p in points:
                x = min(round((p[0] - start[0]) * subtr_x), len_x - 1)
                y = min(round((p[1] - start[1]) * subtr_y), len_y - 1)
                if(x != prevx or y != prevy):
                    flat = x * len_x + y
                    flat2 = (x//2) * round(len_x/2) + y//2
                    flat3 = (x//4) * round(len_x/4) + y//4
                    if(flat in grid_changes[0]['new']):
                        grid_changes[0]['new'][flat][0] += s['meta']['total']
                    else:
                        grid_changes[0]['new'][flat] = [s['meta']['total'], x,y]
                    grid[x][y] += s['meta']['total']
                    if(g2_exists):
                        if(flat2 in grid_changes[1]['new']):
                            grid_changes[1]['new'][flat2][0] += s['meta']['total']
                        else:
                            grid_changes[1]['new'][flat2] = [s['meta']['total'], x//2, y//2]
                        grid2[x//2][y//2] += s['meta']['total']
                    if(g3_exists):
                        if(flat3 in grid_changes[2]['new']):
                            grid_changes[2]['new'][flat3][0] += s['meta']['total']
                        else:
                            grid_changes[2]['new'][flat3] = [s['meta']['total'], x//4, y//4]
                        grid3[x//4][y//4] += s['meta']['total']
                prevx,prevy = [x,y]


        grid_dict = {
                'min': start,
                'max': end,
                'sum': grid_sum,
                'grid': grid.tolist(),
                'grid2': grid2 if(grid2 == []) else grid2.tolist(),
                'grid3': grid3 if(grid3 == []) else grid3.tolist(),
                'outliers': []
            }
        outfile = open(grid_file, 'wb')
        pickle.dump(grid_dict, outfile)
        outfile.close()
        outfile_ch = open(changes_file, 'wb')
        pickle.dump({'len': [[len(grid_dict['grid']), len(grid_dict['grid'][0])],\
                        [len(grid_dict['grid2']), len(grid_dict['grid2'][0])] if(grid_dict['grid2'] != []) else [],\
                        [len(grid_dict['grid3']), len(grid_dict['grid3'][0])] if(grid_dict['grid3'] != []) else []],\
                        'min': start, 'max': end, 'changes': grid_changes}, outfile_ch)
        outfile_ch.close()
    else:
        infile = open(grid_file, 'rb')
        grid_dict = pickle.load(infile)
        infile.close()

        start = grid_dict['min']
        end = grid_dict['max']
        grid = grid_dict['grid']
        grid_sum = grid_dict['sum']
        center = [end[0] - start[0], end[1] - start[1]]
        halfedge = distance(start, center)

        sum_out = 0
        sum_in = 0
        segs_out = []
        segs_in = []
        for s in segs:
            if(in_bb(s['geom'], start, end)):
                sum_in += s['meta']['total']
                segs_in.append(s)
            else:
                sum_out += s['meta']['total']
                segs_out.append(s)

        outliers_invalid = []
        for out in grid_dict['outliers']:
            if(distance(out['geom'][0], center) > halfedge * 2 or distance(out['geom'][0], center) > halfedge * 2):
                outliers_invalid.append(out)
            else:
                segs_out.append(out)
                sum_out += s['meta']['total']

        perc_out = sum_out / (grid_sum + sum_in + sum_out) * 100
        # print(grid_sum, sum_in, sum_out)
        if(perc_out > threshold):
            # Grid expansion
            # print("\tExpanding grid...")
            minlo, minla, maxlo, maxla = [start[0], start[1], end[0], end[1]]
            for s in segs_out:
                if(s['geom'][0][0] < minlo):
                    minlo = s['geom'][0][0]
                if(s['geom'][0][1] < minla):
                    minla = s['geom'][0][1]
                if(s['geom'][-1][0] < minlo):
                    minlo = s['geom'][-1][0]
                if(s['geom'][-1][1] < minla):
                    minla = s['geom'][-1][1]
                if(s['geom'][0][0] > maxlo):
                    maxlo = s['geom'][0][0]
                if(s['geom'][0][1] > maxla):
                    maxla = s['geom'][0][1]
                if(s['geom'][-1][0] > maxlo):
                    maxlo = s['geom'][-1][0]
                if(s['geom'][-1][1] > maxla):
                    maxla = s['geom'][-1][1]

            new_start = [minlo, minla]
            new_end = [maxlo, maxla]

            res_a = res * 4

            d = distance(new_start,[new_start[0], start[1]])
            if(not isclose(round(d / res_a), d / res_a,rtol=0)):
                adjust = ((res_a - (d % res_a)) / d) * abs(start[1] - new_start[1])
                new_start[1] -= adjust
            d = distance(new_start,[start[0], new_start[1]])
            if(not isclose(round(d / res_a), d / res_a,rtol=0)):
                adjust = ((res_a - (d % res_a)) / d) * abs(start[0] - new_start[0])
                new_start[0] -= adjust
            d = distance(end,[end[0], new_end[1]])
            if(not isclose(round(d / res_a), d / res_a,rtol=0)):
                adjust = ((res_a - (d % res_a)) / d) * abs(new_end[1] - end[1])
                new_end[1] += adjust
            d = distance(end,[new_end[0], end[1]])
            if(not isclose(round(d / res_a), d / res_a,rtol=0)):
                adjust = ((res_a - (d % res_a)) / d) * abs(new_end[0] - end[0])
                new_end[0] += adjust

            d = distance(new_start,[new_start[0], new_end[1]])
            if(not isclose(round(d / res_a), d / res_a,rtol=0)):
                adjust = ((res_a - (d % res_a)) / d) * abs(new_end[1] - new_start[1])
                new_end[1] += adjust
            d = distance(new_start,[new_end[0], new_start[1]])
            if(not isclose(round(d / res_a), d / res_a,rtol=0)):
                adjust = ((res_a - (d % res_a)) / d) * abs(new_end[0] - new_start[0])
                new_end[0] += adjust

            # print(distance(new_start,[start[0], new_start[1]]) / res, distance(new_start,[new_start[0], start[1]]) / res,\
                # distance(end,[new_end[0], end[1]]) / res, distance(end,[end[0], new_end[1]]) / res)
            len_x = round(distance(new_start, [new_end[0], new_start[1]]) / res)
            len_y = round(distance(new_start, [new_start[0], new_end[1]]) / res)
            # print(distance(new_start,[new_end[0], new_start[1]]))
            # print(distance(new_start,[new_start[0], new_end[1]]))
            new_grid = zeros((len_x, len_y),dtype=uint16)
            new_grid2, new_grid3 = [[],[]]

            if((len_x + 1) >= 2 and (len_x + 1) >= 2):
                new_grid2 = high_level_grid(new_grid)
            
            if((len_x + 1) >= 4 and (len_x + 1) >= 4):
                new_grid3 = high_level_grid(new_grid2)

            subtr_x = len_x / (new_end[0] - new_start[0]) 
            subtr_y = len_y / (new_end[1] - new_start[1]) 

            offset_min_x = round((start[0] - new_start[0]) * subtr_x)
            offset_min_y = round((start[1] - new_start[1]) * subtr_y)
            offset_max_x = offset_min_x + len(grid)
            offset_max_y = offset_min_y + len(grid[0])
            g2_exists = (new_grid2 != [])
            g3_exists = (new_grid3 != [])

            new_grid[offset_min_x: offset_max_x, offset_min_y:offset_max_y] = grid
            if(g2_exists):
                new_grid2[offset_min_x//2: offset_min_x//2 + len(grid_dict['grid2']),\
                            offset_min_y//2: offset_min_y//2 + len(grid_dict['grid2'][0])] = grid_dict['grid2']
            if(g3_exists):
                new_grid3[offset_min_x//4: offset_min_x//4 + len(grid_dict['grid3']),\
                            offset_min_y//4: offset_min_y//4 + len(grid_dict['grid3'][0])] = grid_dict['grid3']     

            len_x_old = len(grid)
            len_y_old = len(grid[0])
            for x in range(len_x_old):
                for y in range(len_y_old):
                    # grid_changes[0]['rebin'][(x * len_x_old + y)] = (x + offset_min_x) * len_x + y + offset_min_y
                    if(grid[x][y]):
                        # grid_changes[0]['rebin'][(x * len_x_old + y)] = [x,y, (x + offset_min_x) * len_x + y + offset_min_y]
                        grid_changes[0]['new'][((x + offset_min_x) * len_x + y + offset_min_y)] = [grid[x][y], x + offset_min_x, y + offset_min_y]

            len_x_old = len(grid_dict['grid2'])
            len_y_old = len(grid_dict['grid2'][0])
            for x in range(len_x_old):
                for y in range(len_y_old):
                    # grid_changes[1]['rebin'][(x * len_x_old + y)] = (x + offset_min_x//2) * len_x + y + offset_min_y//2
                    if(grid_dict['grid2'][x][y]):
                        # grid_changes[1]['rebin'][(x * len_x_old + y)] = [x,y, (x + offset_min_x//2) * len_x + y + offset_min_y//2]
                        grid_changes[1]['new'][((x + offset_min_x//2) * len_x + y + offset_min_y//2)] =\
                                [grid_dict['grid2'][x][y], x + offset_min_x//2, y + offset_min_y//2]

            len_x_old = len(grid_dict['grid3'])
            len_y_old = len(grid_dict['grid3'][0])
            for x in range(len_x_old):
                for y in range(len_y_old):
                    # grid_changes[2]['rebin'][(x * len_x_old + y)] = (x + offset_min_x//4) * len_x + y + offset_min_y//4
                    if(grid_dict['grid3'][x][y]):
                        # grid_changes[2]['rebin'][(x * len_x_old + y)] = [x,y,(x + offset_min_x//4) * len_x + y + offset_min_y//4]
                        grid_changes[2]['new'][((x + offset_min_x//4) * len_x + y + offset_min_y//4)] =\
                                [grid_dict['grid3'][x][y], x + offset_min_x//4, y + offset_min_y//4]

            grid_changes[0]['rebin'] = 1
            grid_changes[1]['rebin'] = 1
            grid_changes[2]['rebin'] = 1

            prevx, prevy = [-1,-1]
            new_sum = grid_sum
            for s in segs:
                new_sum += s['meta']['total']
                points = interpolate_distance(s, res)
                for p in points:
                    x = min(round((p[0] - new_start[0]) * subtr_x), len_x - 1)
                    y = min(round((p[1] - new_start[1]) * subtr_y), len_y - 1)
                    if(x != prevx or y != prevy):
                        flat = x * len_x + y
                        flat2 = (x//2) * round(len_x/2) + y//2
                        flat3 = (x//4) * round(len_x/4) + y//4
                        if(new_grid[x][y]):
                            if(flat in grid_changes[0]['delta']):
                                grid_changes[0]['delta'][flat] += s['meta']['total']
                            else:
                                grid_changes[0]['delta'][flat] = s['meta']['total']
                        else:
                            if(flat in grid_changes[0]['new']):
                                grid_changes[0]['new'][flat][0] += s['meta']['total']
                            else:
                                grid_changes[0]['new'][flat] = [s['meta']['total'], x, y]
                        new_grid[x][y] += s['meta']['total']
                        if(g2_exists):
                            if(new_grid2[x//2][y//2]):
                                if(flat2 in grid_changes[1]['delta']):
                                    grid_changes[1]['delta'][flat2] += s['meta']['total']
                                else:
                                    grid_changes[1]['delta'][flat2] = s['meta']['total']
                            else:
                                if(flat2 in grid_changes[1]['new']):
                                    grid_changes[1]['new'][flat2][0] += s['meta']['total']
                                else:
                                    grid_changes[1]['new'][flat2] = [s['meta']['total'], x//2, y//2]
                            new_grid2[x//2][y//2] += s['meta']['total']
                        if(g3_exists):
                            if(new_grid3[x//4][y//4]):
                                if(flat3 in grid_changes[2]['delta']):
                                    grid_changes[2]['delta'][flat3] += s['meta']['total']
                                else:
                                    grid_changes[2]['delta'][flat3] = s['meta']['total']
                            else:
                                if(flat3 in grid_changes[2]['new']):
                                    grid_changes[2]['new'][flat3][0] += s['meta']['total']
                                else:
                                    grid_changes[2]['new'][flat3] = [s['meta']['total'], x//4, y//4]
                            new_grid3[x//4][y//4] += s['meta']['total']
                    prevx,prevy = [x,y]

            grid_dict = {
                'min': new_start,
                'max': new_end,
                'sum': new_sum,
                'grid': new_grid.tolist(),
                'grid2': new_grid2 if(new_grid2 == []) else new_grid2.tolist(),
                'grid3': new_grid3 if(new_grid3 == []) else new_grid3.tolist(),
                'outliers': outliers_invalid,
            }
            outfile = open(grid_file, 'wb')
            pickle.dump(grid_dict, outfile)
            outfile.close()
            outfile_ch = open(changes_file, 'wb')
            pickle.dump({'len': [[len(grid_dict['grid']), len(grid_dict['grid'][0])],\
                        [len(grid_dict['grid2']), len(grid_dict['grid2'][0])],\
                        [len(grid_dict['grid3']), len(grid_dict['grid3'][0])]],\
                        'min': new_start, 'max': new_end, 'changes': grid_changes}, outfile_ch)
            outfile_ch.close()

        else:
            len_x = int(distance(start, [end[0], start[1]]) // res)
            len_y = int(distance(start, [start[0], end[1]]) // res)
            subtr_x = len_x / (end[0] - start[0])
            subtr_y = len_y / (end[1] - start[1])
            # print(len_x, len_y)

            grid2 = grid_dict['grid2']
            grid3 = grid_dict['grid3']
            g2_exists = (grid2 != [])
            g3_exists = (grid3 != [])

            prevx, prevy = [-1,-1]
            new_sum = grid_sum
            for s in segs_in:
                new_sum += s['meta']['total']
                points = interpolate_distance(s, res)
                for p in points:
                    x = min(round((p[0] - start[0]) * subtr_x), len_x - 1)
                    y = min(round((p[1] - start[1]) * subtr_y), len_y - 1)
                    if(x != prevx or y != prevy):
                        flat = x * len_x + y
                        flat2 = (x//2) * round(len_x/2) + y//2
                        flat3 = (x//4) * round(len_x/4) + y//4
                        if(grid[x][y]):
                            if(flat in grid_changes[0]['delta']):
                                grid_changes[0]['delta'][flat] += s['meta']['total']
                            else:
                                grid_changes[0]['delta'][flat] = s['meta']['total']
                        else:
                            if(flat in grid_changes[0]['new']):
                                grid_changes[0]['new'][flat][0] += s['meta']['total']
                            else:
                                grid_changes[0]['new'][flat] = [s['meta']['total'], x, y]
                        grid[x][y] += s['meta']['total']
                        if(g2_exists):
                            if(grid2[x//2][y//2]):
                                if(flat2 in grid_changes[1]['delta']):
                                    grid_changes[1]['delta'][flat2] += s['meta']['total']
                                else:
                                    grid_changes[1]['delta'][flat2] = s['meta']['total']
                            else:
                                if(flat2 in grid_changes[1]['new']):
                                    grid_changes[1]['new'][flat2][0] += s['meta']['total']
                                else:
                                    grid_changes[1]['new'][flat2] = [s['meta']['total'], x//2, y//2]
                            grid2[x//2][y//2] += s['meta']['total']
                        if(g3_exists):
                            if(grid3[x//4][y//4]):
                                if(flat3 in grid_changes[2]['delta']):
                                    grid_changes[2]['delta'][flat3] += s['meta']['total']
                                else:
                                    grid_changes[2]['delta'][flat3] = s['meta']['total']
                            else:
                                if(flat3 in grid_changes[2]['new']):
                                    grid_changes[2]['new'][flat3][0] += s['meta']['total']
                                else:
                                    grid_changes[2]['new'][flat3] = [s['meta']['total'], x//4, y//4]
                            grid3[x//4][y//4] += s['meta']['total']
                    prevx,prevy = [x,y]
            grid_dict = {
                'min': start,
                'max': end,
                'sum': new_sum,
                'grid': grid,
                'grid2': grid2,
                'grid3': grid3,
                'outliers': segs_out + outliers_invalid,
            }
            outfile = open(grid_file, 'wb')
            pickle.dump(grid_dict, outfile)
            outfile.close()
            outfile_ch = open(changes_file, 'wb')
            pickle.dump({'len': [[len(grid_dict['grid']), len(grid_dict['grid'][0])],\
                        [len(grid_dict['grid2']), len(grid_dict['grid2'][0])] if(grid_dict['grid2'] != []) else [],\
                        [len(grid_dict['grid3']), len(grid_dict['grid3'][0])] if(grid_dict['grid3'] != []) else []],\
                        'min': start, 'max': end, 'changes': grid_changes}, outfile_ch)
            outfile_ch.close()
    
    # print("\tGrid time:\t", str((datetime.datetime.now() - start_time).total_seconds()))
    return