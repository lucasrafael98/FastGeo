// Code for ongoing line animation.

let speedFactor = 1;
let animation;
let animationStartTime = 0;
let progress = 0;
let toAnimate;

function lineInterpolation(line, factor){
    geom = line['geometry']['coordinates'];
    x1 = geom[0][0];
    y1 = geom[0][1];
    x2 = geom[1][0];
    y2 = geom[1][1];

    len = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    dir = Math.atan2(y2 - y1, x2 - x1);

    xi = x1 + len * factor * Math.cos(dir);
    yi = y1 + len * factor * Math.sin(dir);

    return {
        "type": "Feature",
        "geometry": {
            "type":"LineString",
            "coordinates": [[x1,y1],[xi,yi]]
        },
        "properties": line['properties']
    };
}

/**
 * Interpolates a polyline. For example, a polyline with
 * three segments being interpolated with factor 0.5 will
 * return the first segment and half of the second.
 *
 * @param {feature[]} line line to interpolate
 * @param {float} factor interpolation factor
 */
function polyLineInterpolation(line, factor){
    factor = line.length * factor;
    idx = Math.trunc(factor);
    subfactor = factor % 1;
    // avoid interpolation if the subfactor seems irrelevant.
    if(subfactor < 0.05){
        return line.slice(0, idx);
    } else if (subfactor > 0.95){
        return line.slice(0, idx+1);
    } else {
        return line.slice(0, idx)
            .concat(lineInterpolation(line[idx], subfactor));
    }
}

/**
 * Called every frame until it's done.
 * For each line in newly updated ongoing, 
 * interpolates it for a factor that depends on 
 * animation progress, and creates a point that
 * follows the interpolation
 */
function animateOngoing(){
    let timestamp = performance.now();
    let progress = timestamp - animationStartTime;
    let interpolatedFeatures = [];
    let points = [];
    let interpolationFactor = progress * speedFactor / 1000;

    // stop animating when done
    if(interpolationFactor >= 1){
        map.getSource('ongoing-line').setData({
            type: 'FeatureCollection',
            features: ongoingLineData
        });
        map.getSource('ongoing-line-selected').setData({
            type: 'FeatureCollection',
            features: ongoingLineData.filter(f=>{ return filterIds[f.properties.f1]; })
        });
        updatePoints();
        return;
    }

    toAnimate.forEach(pl=>{
        interpolatedPL = polyLineInterpolation(pl, interpolationFactor);
        interpolatedFeatures = interpolatedFeatures.concat(interpolatedPL);
        if(interpolatedPL.length > 0){
            lastPoint = interpolatedPL.slice(-1)[0];
            interpolatedPoint = {
                "type": "Feature",
                "geometry": {
                    "type":"Point",
                    "coordinates": lastPoint['geometry']['coordinates'][1]
                },
                "properties": lastPoint['properties']
            };
            points.push(interpolatedPoint);
        }
    });

    map.getSource('ongoing-line').setData({
        type: 'FeatureCollection',
        features: interpolatedFeatures
    });
    map.getSource('ongoing-line-selected').setData({
        type: 'FeatureCollection',
        features: interpolatedFeatures.filter(f=>{ return filterIds[f.properties.f1]; })
    });

    map.getSource('ongoing-point').setData({
        type: 'FeatureCollection',
        features: 
            ongoingPointData.concat(points)
    });

    animation = requestAnimationFrame(animateOngoing);
}

function prepareOngoingAnimation(){
    animationStartTime = performance.now();
    toAnimate = [];
    let currID = ongoingLineData[0]['properties']['f1'];
    let animatedIDs = [ongoingLineData[0]['properties']['f1']];
    let currPolyLine = [];

    ongoingLineData.forEach(f=>{
        if(currID !== f['properties']['f1']){
            toAnimate.push(currPolyLine);
            currPolyLine = [];
            currID = f['properties']['f1'];
            animatedIDs.push(f['properties']['f1']);
        }
        currPolyLine.push(f);
    });
    toAnimate.push(currPolyLine);

    animatedIDs.push(currPolyLine.slice(-1)[0]['properties']['f1']);

    ongoingPointData = 
        ongoingPointData.filter(f=>{
            return $.inArray(f["properties"]["f1"], animatedIDs) == -1;
        });

    map.getSource('ongoing-point').setData({
        type: 'FeatureCollection',
        features: ongoingPointData
    });
    updateFilterList();
    animateOngoing();
}