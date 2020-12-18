"""
Geographic and geometric functions.
Points are [longitude, latitude].
"""
import math
from datetime import datetime
from yaml import load as yload, FullLoader
config = yload(open("./config.yaml"), Loader=FullLoader)

threshold = config['edgeBundlingDistThreshold']
unrealistic_velocity = config['unrealisticVelocityThreshold']
error = 1e-6

# One degree in meters
ONE_DEGREE = 1000. * 10000.8 / 90.

def distance(p1, p2):
    """
    Simplified distance between two points, in meters. Doesn't consider elevation or distance for haversines.
    """
    coef = math.cos(p1[1] / 180. * math.pi)
    x = p1[1] - p2[1]
    y = (p1[0] - p2[0]) * coef

    distance_2d = math.sqrt(x * x + y * y) * ONE_DEGREE
    return distance_2d

def bearing(point1, point2):
    """
    Calculates the initial bearing between point1 and point2 relative to north
    (zero degrees).
    
    From: https://www.jonblack.me/how-to-distribute-gps-points-evenly/
    """

    lat1r = math.radians(point1[1])
    lat2r = math.radians(point2[1])
    dlon = math.radians(point2[0] - point1[0])

    y = math.sin(dlon) * math.cos(lat2r)
    x = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) \
                        * math.cos(lat2r) * math.cos(dlon)
    return math.degrees(math.atan2(y, x))
    
def weighted_avg_point(p1,p2,w1,w2,bias=False):
    """
    Creates a weighted average point
    between two points.
    """
    if(bias):
        if(w1 >= w2):
            w1 += 10
        else:
            w2 += 10
    return  [(p1[0] * w1 + p2[0] * w2) / (w1 + w2),\
                (p1[1] * w1 + p2[1] * w2) / (w1 + w2)]

def multi_weighted_avg_point(points, weights):
    """
    Creates a weighted average point
    between n points (both lists must have n length).
    """
    lat, lon, sum_w = 0, 0, 0
    for i in range(len(points)):
        lat += points[i][1] * weights[i]
        lon += points[i][0] * weights[i]
        sum_w += weights[i]
    return [lon / sum_w, lat / sum_w]

def weighted_avg_segment(s1,s2):
    """
    Creates a weighted average segment
    between two segments.
    """
    b1 = bearing(s1['geom'][-1], s1['geom'][0])
    b2 = bearing(s2['geom'][-1], s2['geom'][0])
    diff = abs(round(b2 - b1))
    if(diff > 90 and diff < 270):
        s2['geom'] = [s2['geom'][-1], s2['geom'][0]]
        s2['meta']['adj'] = list(reversed(s2['meta']['adj']))
    
    s = {}
    s['geom'] = [\
            weighted_avg_point(s1['geom'][0], s2['geom'][0], \
                s1['meta']['total'], s2['meta']['total']),
            weighted_avg_point(s1['geom'][-1], s2['geom'][-1], \
                s1['meta']['total'], s2['meta']['total'])
        ]
    s['meta'] = {'times': s1['meta']['times'].union(s2['meta']['times']),\
                    'ids': s1['meta']['ids'].union(s2['meta']['ids']),\
                    'bbox': s1['meta']['bbox'].union(s2['meta']['bbox'])}
    s['meta']['total'] = len(s['meta']['times'])
    return s

def find_angle(prev, curr, next):
    a = distance(prev, curr)
    b = distance(curr, next)
    c = distance(prev, next)

    cos = min(1, (a*a + b*b - c*c) / (2 * a * b)) if (2 * a * b) != 0 else 0
    cos = max(-1, cos)
    angle = math.acos(cos)
    angle = math.degrees(angle)
    
    return angle, a

def slope(p1,p2,normal=False):
    """
    Computes the slope (m) between two points.

    normal: whether to return the slope's normal (-1/m).
    """
    dx = p2[0] - p1[0]
    if(dx == 0):
        dx = error * error if p2[0] > p1[0] else -error * error
    dy = p2[1] - p1[1]
    if(dy == 0):
        dy = error * error if p2[1] > p1[1] else -error * error
    m = dy / dx
    return m if not normal else (-1 / m)
  
def y_intercept(m,p):
    """
    Computes the y-intercept of a line with slope m using point p.
    """
    return p[1] - m * p[0]

def intersection_point(m1,b1,m2,b2):
    """
    Computes the intersection point of two lines:

    y = m1 * x + b1

    y = m2 * x + b2
    """
    xi = (b1-b2) / (m2-m1)
    yi = m1 * xi + b1
    return (xi,yi)

def boundaries(seg):
    """
    Returns max, min (x,y) values of a segment.
    """
    if(seg['geom'][0][0] > seg['geom'][-1][0]):
        maxx = seg['geom'][0][0]
        minx = seg['geom'][-1][0]
    else:
        maxx = seg['geom'][-1][0]
        minx = seg['geom'][0][0]
    if(seg['geom'][0][1] > seg['geom'][-1][1]):
        maxy = seg['geom'][0][1]
        miny = seg['geom'][-1][1]
    else:
        maxy = seg['geom'][-1][1]
        miny = seg['geom'][0][1]
    return maxx + error, minx - error, maxy + error, miny - error

def distance_from_line(point, line_point_1, line_point_2):
    """ Distance of point from a line given with two points. (from gpxpy)"""
    assert point, point
    assert line_point_1, line_point_1
    assert line_point_2, line_point_2

    a = distance(line_point_1, line_point_2)

    if a == 0:
        return distance(line_point_1, point)

    b = distance(line_point_1, point)
    c = distance(line_point_2, point)

    s = (a + b + c) / 2.

    return 2. * math.sqrt(abs(s * (s - a) * (s - b) * (s - c))) / a

def get_line_equation_coefficients(location1, location2):
    """
    Get line equation coefficients for:
        latitude * a + longitude * b + c = 0
    This is a normal cartesian line (not spherical!) (from gpxpy)
    """
    if location1[0] == location2[0]:
        # Vertical line:
        return float(0), float(1), float(-location1[0])
    else:
        a = float(location1[1] - location2[1]) / (location1[0] - location2[0])
        b = location1[1] - location1[0] * a
        return float(1), float(-a), float(-b)

def rdp(points, max_distance): 
    """Does Ramer-Douglas-Peucker algorithm for simplification of polyline (from gpxpy)"""

    if len(points) < 3:
        return points

    begin, end = points[0], points[-1]

    # Use a "normal" line just to detect the most distant point (not its real distance)
    # this is because this is faster to compute than calling distance_from_line() for
    # every point.
    #
    # This is an approximation and may have some errors near the poles and if
    # the points are too distant, but it should be good enough for most use
    # cases...
    a, b, c = get_line_equation_coefficients(begin, end)

    tmp_max_distance = -1000000
    tmp_max_distance_position = None

    for point_no in range(len(points[1:-1])):
        point = points[point_no]
        d = abs(a * point[1] + b * point[0] + c)

        if d > tmp_max_distance:
            tmp_max_distance = d
            tmp_max_distance_position = point_no

    # Now that we have the most distant point, compute its real distance:

    real_max_distance = distance_from_line(points[tmp_max_distance_position], begin, end)

    if real_max_distance < max_distance:
        return [begin, end]

    return (rdp(points[:tmp_max_distance_position + 2], max_distance) +
            rdp(points[tmp_max_distance_position + 1:], max_distance)[1:])

def length(points):
    length = 0
    for i in range(len(points)):
        if i > 0:
            prev_point = points[i - 1]
            point = points[i]
            length += distance(point, prev_point)
    return length

def simplify3(points, times):
    avg_speed = length(points) / (times[-1] - times[0]).total_seconds()
    i = 1
    while i < len(points) - 1:
        prev = points[i-1]
        curr = points[i]
        next = points[i+1]
        angle, dist = find_angle(prev, curr, next)
        if not (165 <= angle <= 195):
            time_dif = (times[i] - times[i-1]).total_seconds()
            speed = distance(curr, prev) / float(time_dif)
            if speed is not None and (speed > 10 * avg_speed or speed < 0.5):
                points.remove(curr)
                del times[i]
            else:
                i += 1
        else:
            i += 1
    
    return points, times

def simplify(points, times):
    points, times = simplify3(points, times)
    # points = rdp(points, 30)
    segs = []
    i = 1
    while i < len(points) - 1:
        prev = points[i-1]
        curr = points[i]
        next = points[i+1]
        angle, dist = find_angle(prev, curr, next)
        if 165 <= angle <= 195 and dist <= threshold:
            points.remove(points[i])
            continue
        elif distance(prev,next) < distance(prev,curr) \
            and distance(prev,curr) / (times[i] - times[i-1]).total_seconds() > unrealistic_velocity * 0.7:
            points.remove(points[i])
            continue 
        segs.append({'geom': points[i-1:i+1], 'meta': {'times': set([times[i]])}})
        i += 1
    segs.append({'geom': points[i-1:i+1], 'meta': {'times': set([times[i]])}})
    return segs

def str2time(string, js=False):
    """
    Turns a string to a Python datetime object.

    js: whether the time string is from JS or PG, instead of Python.
    """
    conv = "%Y-%m-%dT%H:%M:%S" if js else "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(string, conv)

def interpolate_distance(seg, dist):
    even_points = []
    p1 = seg['geom'][0]
    p2 = seg['geom'][1]
    times = int(distance(seg['geom'][0], seg['geom'][1]) / dist)
    if(times == 0):
        return [p1,p2]
    values = []
    for i in range(times + 1):
        values.append(i / times)

    for v in values:
        even_points.append([(p1[0] * (1 - v) + p2[0] * v), (p1[1] * (1 - v) + p2[1] * v)])

    return even_points

def segs_to_points(segs):
    points = {'type': 'FeatureCollection', 'features': []}
    for s in segs:
        interp_points = interpolate_distance(s, 50)
        for p in interp_points:
            points['features'].append({
                'type':'Feature',
                'geometry':{
                    'type': 'Point',
                    'coordinates': p
                },
                'properties': {'total': s['total']}
            })
    return points

def in_bb(line, bound_min, bound_max):
    """
    Checks if a segment is contained (fully) in a bounding box.

    line: segment to evaluate;
    bound_min: minimum bounds of BB;
    bound_max: maximum bounds of BB;

    Returns whether the segment is or isn't contained.
    """
    return  line[0][0] >= bound_min[0] and line[0][0] <= bound_max[0]\
        and line[0][1] >= bound_min[1] and line[0][1] <= bound_max[1]\
        and line[1][0] >= bound_min[0] and line[1][0] <= bound_max[0]\
        and line[1][1] >= bound_min[1] and line[1][1] <= bound_max[1]