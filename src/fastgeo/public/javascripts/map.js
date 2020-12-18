/** 
 * The main visualization code.
 * 
 * If you don't understand why there's a bunch of 
 *      ['interpolate', ['linear'], <tons of random numbers>]
 * check https://docs.mapbox.com/mapbox-gl-js/style-spec/expressions/.
*/

var map;
var generics;
var displayModes;
var toDelete = [];
var rainbowGens = true;
var gridDisplay;

var popup = new mapboxgl.Popup({
    closeButton: false,
    closeOnClick: false
});

function addLineLayer(name, color, width){
    map.addSource(name, {
        'type': 'geojson',
        'data': { type: "FeatureCollection", features: [] }
    });
    map.addLayer({
        'id': name,
        'type': 'line',
        'source': name,
        'paint': {
            'line-color': color,
            'line-width': width,
            'line-opacity': 1,
        },
        'layout':{
            'line-cap': 'round',
            'line-join': 'miter'
        }
    });
}

function addHeatmapLayer(name, minzoom = 0, maxzoom = 22){
    map.addSource(name, {
        'type': 'geojson',
        'data': { type: "FeatureCollection", features: [] }
    });
    map.addLayer({
        'id': name,
        'type': 'heatmap',
        'source': name,
        'minzoom': minzoom,
        'maxzoom': maxzoom,
        'paint': {
            'heatmap-weight': ['interpolate', ['linear'], ['get', 'total'], 0, 0, 1, 0.05, 20, 0.5],
            'heatmap-intensity': ['interpolate',['linear'],['zoom'],4,0.01,6,0.2,10,0.8,13,2,20,15],
            'heatmap-color': [
                'interpolate',['linear'],['heatmap-density'],
                0,'rgba(255,255,255,0)',0.5,'rgba(40,40,40, 0.6)',0.9,'rgba(130,110,160,0.5)',1,'rgba(40,1,65,0.5)'],
            'heatmap-radius': ['interpolate',['linear'],['zoom'],11,2,13,20,13.5,25,14,30,14.99,35,15.01,30,16.99,110,17.01,70,20,250],
        }
    });
}

function addSquareLayer(name, minzoom = 0, maxzoom = 22){
    map.addSource(name, {
        'type': 'geojson',
        'data': { type: "FeatureCollection", features: [] }
    });
    map.addLayer({
        'id': name,
        'type': 'fill',
        'source': name,
        'minzoom': minzoom,
        'maxzoom': maxzoom,
        'paint': {
            'fill-color': ['interpolate', ['linear'], ['get', 'total'], 
                            0,'rgba(255,255,255,0)',10,'rgba(40,1,65,0.5)']
        }
    });
}

/**
 * Data update request to back end.
 */
function requestJSONRecurrent(url, freq, func){
    return window.setInterval(()=>{
        let timeRequest = $.ajax({
            url: url, type: 'GET', dataType:'json',
            error: function (xhr) {
                console.log(xhr);
                alert(xhr.statusText);
            },
            // ignores 304 (update.json not modified) responses.
            ifModified: true,
        })
        $.when(timeRequest).done(func);
    }, freq);
}

function initializeMap(){
    // Carto Basemaps have many styles. 
    // The thesis explains why light_all is used.
    // The other styles are viewable here: https://basemaps.cartocdn.com/
    let mapMode = 'light_all';
    map = new mapboxgl.Map({
        container: 'map', // container id
        style: {
            'version': 8,
            'sources': {
                'raster-tiles': {
                    'type': 'raster',
                    'tiles': [
                        'https://basemaps.cartocdn.com/'+ mapMode +'/{z}/{x}/{y}{r}.png'
                    ],
                    'tileSize': 256,
                }
            },
            'layers': [
                {
                    'id': 'simple-tiles',
                    'type': 'raster',
                    'source': 'raster-tiles',
                }
            ]
        },
        center: [-8.6,41.16],
        // center: [116.4578,39.8760], // starting position
        zoom: 12, // starting zoom
    });
    
    map.on('load', ()=>{
        if(gridDisplay == 0){
            addHeatmapLayer('grid1',minzoom=17);
            addHeatmapLayer('grid2',minzoom=15, maxzoom=17);
            addHeatmapLayer('grid3',minzoom=0, maxzoom=15);
            // addHeatmapLayer('grid4',minzoom=0, maxzoom=13);
        } else if (gridDisplay == 1){
            addSquareLayer('grid1',minzoom=17);
            addSquareLayer('grid2',minzoom=15, maxzoom=17);
            addSquareLayer('grid3',minzoom=0, maxzoom=15);
            // addSquareLayer('grid4',minzoom=0, maxzoom=13);
        }

        let lastDisplayMode = displayModes[0];
        for(i = generics - 1; i > -1; i--){
            if(displayModes[i] != lastDisplayMode || generics == 1)
                rainbowGens = false;
            if(displayModes[i] != 2){
                addLineLayer('gen' + i, ['get', 'color'], 
                    ['interpolate', ['linear'], ['zoom'],
                        9, ['*', 0.5, ['get', 'width']],
                        13, ['*', 1, ['get', 'width']], 
                        20, ['*', 3, ['get', 'width']]]
                );
                map.setLayoutProperty('gen' + i, 'line-sort-key', ['get', 'total']);
            }
            else
                addHeatmapLayer('gen' + i);
        }

        addLineLayer('ongoing-line-old', 'rgba(230,130,60, 0.6)', ['interpolate', ['linear'], ['zoom'], 10, 0.5, 20, 3]);
        addLineLayer('ongoing-line', 'rgba(230,130,60, 0.6)', ['interpolate', ['linear'], ['zoom'], 10, 0.5, 20, 3]);
        addLineLayer('ongoing-line-selected', 'rgba(230,130,60,1)', ['interpolate', ['linear'], ['zoom'], 10, 3, 20, 7]);
        addLineLayer('ongoing-line-old-selected', 'rgba(230,130,60,1)', ['interpolate', ['linear'], ['zoom'], 10, 3, 20, 7]);
        document.getElementById("ongoing-span").style.backgroundColor = 'rgb(230,130,60,0.8)';
        if(gridDisplay == 0)
            document.getElementById("history-span").style.background = historyHMGradient;

        map.addSource('ongoing-point', {
            'type': 'geojson',
            'data': { type: "FeatureCollection", features: [] }
        });
        map.addLayer({
            'id': 'ongoing-point',
            'type': 'circle',
            'source': 'ongoing-point',
            'paint': {
                'circle-color': 'rgb(220,85,50)',
                'circle-opacity': 1,
                'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 1, 10, 2.5, 24, 6]
            }
        });

        map.addSource('ongoing-point-selected', {
            'type': 'geojson',
            'data': { type: "FeatureCollection", features: [] }
        });
        map.addLayer({
            'id': 'ongoing-point-selected',
            'type': 'circle',
            'source': 'ongoing-point-selected',
            'paint': {
                'circle-color': 'rgb(220,110,50)',
                'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 4, 10, 5, 24, 8]
            }
        });

        loadTooltips();

        // Update request. The data=>{} function decides
        // what is done when the request returns.
        requestJSONRecurrent('/update', 1000, data=>{
            if(!data) return;
            currentDate = Date.parse(data["currentDate"])
            ongoingPointData = data['display']['ongoing_points']
            ongoingLineData = data['display']['ongoing_lines']
            ongoingLineDelete = data['remove']['ongoing']

            oldOngoingLineData = 
                map.getSource('ongoing-line-old')._data.features.concat(
                    map.getSource('ongoing-line')._data.features
            );
            
            map.getSource('ongoing-line-old').setData({
                type: 'FeatureCollection',
                features: oldOngoingLineData
            });

            oldOngoingLineSelData = 
                map.getSource('ongoing-line-old-selected')._data.features.concat(
                    map.getSource('ongoing-line-selected')._data.features
            );
            
            map.getSource('ongoing-line-old-selected').setData({
                type: 'FeatureCollection',
                features: oldOngoingLineSelData
            });
            if(map.getSource('ongoing-line')._data.features != [] || map.getSource('ongoing-line')._data.features != undefined){
                map.getSource('ongoing-line').setData({
                    type: 'FeatureCollection',
                    features: 
                        map.getSource('ongoing-line')._data.features
                            .filter(f=>{
                                return $.inArray(f["properties"]["f3"], toDelete) == -1;
                            })
                });
            }
            if(map.getSource('ongoing-line-old')._data.features != [] || map.getSource('ongoing-line-old')._data.features != undefined){
                map.getSource('ongoing-line-old').setData({
                    type: 'FeatureCollection',
                    features: 
                        map.getSource('ongoing-line-old')._data.features
                            .filter(f=>{
                                return $.inArray(f["properties"]["f3"], toDelete) == -1;
                            })
                });
            }

            if(ongoingLineDelete){
                map.getSource('ongoing-line-old').setData({
                    type: 'FeatureCollection',
                    features: 
                        map.getSource('ongoing-line-old')._data.features
                            .filter(f=>{
                                return $.inArray(f["properties"]["f3"], ongoingLineDelete) == -1;
                            })
                });
                map.getSource('ongoing-line-selected').setData({
                    type: 'FeatureCollection',
                    features: 
                        map.getSource('ongoing-line-selected')._data.features
                            .filter(f=>{
                                return $.inArray(f["properties"]["f3"], ongoingLineDelete) == -1;
                            })
                });
                map.getSource('ongoing-line-old-selected').setData({
                    type: 'FeatureCollection',
                    features: 
                        map.getSource('ongoing-line-old-selected')._data.features
                            .filter(f=>{
                                return $.inArray(f["properties"]["f3"], ongoingLineDelete) == -1;
                            })
                });
                map.getSource('ongoing-line').setData({
                    type: 'FeatureCollection',
                    features: 
                        map.getSource('ongoing-line')._data.features
                            .filter(f=>{
                                return $.inArray(f["properties"]["f3"], ongoingLineDelete) == -1;
                            })
                });
    
                toDelete = ongoingLineDelete;
            }

            if(ongoingLineData){
                prepareOngoingAnimation();
            }

            for(gen = generics - 1; gen > -1; gen--){
                let genData = data['display'][gen];
                if(!genData) continue;
                if(rainbowGens){
                    let max = genData.reduce((prev, current) => {
                        if(prev['properties']['total'] > current['properties']['total'])
                            return prev
                        else
                            return current
                    });
                    genData.forEach(f=>{
                        f['properties']['color'] = 'hsla(' + 360 * gen / generics + ',100%,50%, 0.5)';
                        f['properties']['width'] = recentEBWidthScale(max['properties']['total'],f['properties']['f1']);
                    });
                } else {
                    if(displayModes[gen] != 2 && genData.length != 0){
                        let max = genData.reduce((prev, current) => {
                            if(prev['properties']['total'] > current['properties']['total'])
                                return prev
                            else
                                return current
                        });
                        genData.forEach(f=>{
                            if(gen == 0)
                                f['properties']['color'] = recentEBScale(max['properties']['total'],f['properties']['f1']);
                            else
                                f['properties']['color'] = ['rgba(0,0,255, 0.5)', 'rgba(0, 255, 0, 0.5)', 'rgba(255, 0, 0, 0.3)'][gen+1];
                            f['properties']['width'] = recentEBWidthScale(max['properties']['total'],f['properties']['f1']);
                        });
                        document.getElementById("recent-span").style.background = recentEBGradient(max);
                        document.getElementById("max-recent").textContent = max['properties']['total'];
                    }
                }
                if(gen == 0 || displayModes[gen] != 2){
                    map.getSource('gen' + gen).setData({
                        type: 'FeatureCollection', features: genData
                    });
                } else {
                    map.getSource('gen' + gen).setData({
                        type: 'FeatureCollection', features: 
                            // map.getSource('gen' + gen)._data.features.concat(genData)
                            genData
                    });
                    if(genData.length != 0){
                        // this code changes the color scale by checking what the max total is.
                        let max = genData.reduce((prev, current) => {
                            if(prev['properties']['total'] > current['properties']['total'])
                                return prev
                            else
                                return current
                        });
                        if(max['properties']['total'] > 4){
                            map.setPaintProperty('gen' + gen, 'heatmap-weight', 
                                ['interpolate', ['linear'], ['get', 'total'], 0, 0, 1, 0.01, 2, 0.1, 
                                    max['properties']['total'] / 2, 0.5, max['properties']['total'], 1])
                        } else {
                            map.setPaintProperty('gen' + gen, 'heatmap-weight', 
                                ['interpolate', ['linear'], ['get', 'total'], 0, 0, 1, 0.05, 2, 0.1])
                        }
                    }
                }
            }
            
            let gridData = data['display']['grid'];
            if(gridData.length > 1){
                for(i = 0; i != gridData.length; i++){
                    gridFeatures = map.getSource('grid' + (i + 1))._data.features
                    if(gridFeatures.length != 0){
                        for(f = 0; f != gridFeatures.length; f++){
                            id = gridFeatures[f].properties.pos;
                            if(gridData[i].delta[id])
                                gridFeatures[f].properties.total += gridData[i].delta[id];
                        }
                        if(!_.isEmpty(gridData[i].new)){
                            map.getSource('grid' + (i + 1)).setData({
                                type: 'FeatureCollection', features: 
                                    gridData[i].rebin 
                                        ? gridData[i].new.features
                                        : gridFeatures.concat(gridData[i].new.features) 
                            });
                        } else {
                            map.getSource('grid' + (i + 1)).setData({
                                type: 'FeatureCollection', features: gridFeatures
                            });
                        }
                    } else if (!_.isEmpty(gridData[i].new)) {
                            map.getSource('grid' + (i + 1)).setData({
                            type: 'FeatureCollection', features: gridData[i].new.features
                        });
                    }
                    if(map.getSource('grid' + (i + 1))._data.features.length > 1){
                        // this code changes the color scale by checking what the max total is.
                        let max = map.getSource('grid' + (i + 1))._data.features.reduce((prev, current) => {
                            if(prev['properties']['total'] > current['properties']['total'])
                                return prev
                            else
                                return current
                        });
                        if(gridDisplay == 0){
                            if(max['properties']['total'] > 2000){
                                map.setPaintProperty('grid' + (i + 1), 'heatmap-weight', 
                                    ['interpolate', ['linear'], ['get', 'total'], 0, 0, 1, 0.01, 2, 0.05, 10, 0.15, 100, 0.25, 500, 0.3,
                                        1000, 0.5, max['properties']['total'] / 2, 0.8, max['properties']['total'], 1])
                            }
                            else if(max['properties']['total'] > 12){
                                map.setPaintProperty('grid' + (i + 1), 'heatmap-weight', 
                                    ['interpolate', ['linear'], ['get', 'total'], 0, 0, 1, 0.01, 2, 0.1, max['properties']['total'] / 4, 0.15,
                                        max['properties']['total'] / 3, 0.25, max['properties']['total'] / 2, 0.4, max['properties']['total'], 1])
                            } else {
                                map.setPaintProperty('grid' + (i + 1), 'heatmap-weight', 
                                    ['interpolate', ['linear'], ['get', 'total'], 0, 0, 1, 0.05, 2, 0.1])
                            }
                            document.getElementById("max-history").textContent = "";
                            document.getElementById("min-history").textContent = "";
                        }
                        if(gridDisplay == 1){
                            if(max['properties']['total'] > 2000){
                                map.setPaintProperty('grid' + (i + 1), 'fill-color', 
                                    ['interpolate', ['linear'], ['get', 'total'], 0, 'rgba(255,255,255,0)', 10, 'rgba(40,1,65,0.1)', 100, 'rgba(40,1,65,0.2)',
                                        500, 'rgba(40,1,65,0.25)', 1000, 'rgba(40,1,65,0.3)', 
                                        max['properties']['total'] / 2, 'rgba(40,1,65,0.375)', max['properties']['total'], 'rgba(40,1,65,0.5)'])
                            }
                            else if(max['properties']['total'] > 10){
                                map.setPaintProperty('grid' + (i + 1), 'fill-color', 
                                    ['interpolate', ['linear'], ['get', 'total'], 0,'rgba(255,255,255,0)',max['properties']['total'] / 4, 'rgba(40,1,65,0.3)',
                                    max['properties']['total'] / 3, 'rgba(40,1,65,0.35)', max['properties']['total'] / 2, 'rgba(40,1,65,0.375)',
                                    max['properties']['total'],'rgba(40,1,65,0.5)'])
                            }
                            document.getElementById("history-span").style.background = historyGridGradient(max);
                            document.getElementById("max-history").textContent = max['properties']['total'];
                        }
                    }
                }
            }
        });
    });
    
    map.addControl(new mapboxgl.FrameRateControl());
}

// The visualization starts by 
// requesting the contents of config.yaml
function requestConfig(){
    let timeRequest = 
        $.ajax({
            url: '/config', type: 'GET', dataType:'json',
            error: function (xhr) {alert(xhr.statusText)},
            ifModified: true,})
    $.when(timeRequest).done(data=>{
        generics = data.genericCount;
        displayModes = data.streamDisplayMethods;
        gridDisplay = data.gridDisplayMethod;
        let diffs = data.streamGenericTimeDiffs
        document.getElementById("history-span").title =
            "Tracks which stopped " + diffs[diffs.length - 1] + " minutes ago.";
        initializeMap();
    });
}

$(document).ready(()=>{
    requestConfig();
});