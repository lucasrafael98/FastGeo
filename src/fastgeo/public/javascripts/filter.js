// Code for the filter function in the sidebar.

var filterIds = {}
var filterOpacityChange = 0.5;

function updateFilterList(){
    var filterIds_temp = {};
    map.getSource('ongoing-point')._data.features.forEach(f => {
        if(!filterIds[f.properties.f1])
            filterIds_temp[f.properties.f1] = false;
        else
            filterIds_temp[f.properties.f1] = true;
    });
    map.getSource('ongoing-point-selected')._data.features.forEach(f => {
        if(!filterIds[f.properties.f1])
            filterIds_temp[f.properties.f1] = false;
        else
            filterIds_temp[f.properties.f1] = true;
    });
    document.getElementById("filter-boxes").innerHTML = ""
    for(var id in filterIds_temp){
        document.getElementById("filter-boxes").innerHTML += 
            '<input type="checkbox" id="' + id + '" onclick="toggleId(' + id + ');">\
            <label for="' + id + '">' + id + '<br></label>'
        $("#" + id).attr("checked", filterIds_temp[id]);
    }
    filterIds = filterIds_temp;
    filterId();
    checkSelected();
}

function toggleId(id){
    filterIds[id] = !filterIds[id];
    updateSelected(id);
}

function filterId() {
    var input, filter, checkboxes, labels, inputs, i, txtValue;
    input = document.getElementById("filter-search");
    filter = input.value.toUpperCase();
    checkboxes = document.getElementById("filter-boxes");
    labels = checkboxes.getElementsByTagName("label");
    inputs = checkboxes.getElementsByTagName("input");
    for (i = 0; i < labels.length; i++) {
        txtValue = labels[i].textContent || labels[i].innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
            labels[i].style.display = "";
            inputs[i].style.display = "";
        } else {
            labels[i].style.display = "none";
            inputs[i].style.display = "none";
        }
    }
}

function updatePoints(){
    map.getSource('ongoing-point-selected').setData({
        type: 'FeatureCollection',
        features: 
            map.getSource('ongoing-point')._data.features
                .filter(f=>{ return filterIds[f.properties.f1]; })
    });
}

function updateSelected(selectedId){
    if(filterIds[selectedId]){
        let selectedPoint = map.getSource('ongoing-point')._data.features
                                .filter(f=>{ return f.properties.f1 == selectedId; });
        let selectedLines = map.getSource('ongoing-line-old')._data.features
                                .filter(f=>{ return f.properties.f1 == selectedId; });
        if(selectedLines === "")
            selectedLines = []
        map.getSource('ongoing-point-selected').setData({
            type: 'FeatureCollection',
            features: 
                map.getSource('ongoing-point-selected')._data.features.concat(selectedPoint)
        });
        map.getSource('ongoing-line-old-selected').setData({
            type: 'FeatureCollection',
            features: 
                map.getSource('ongoing-line-old-selected')._data.features.concat(selectedLines)
        });
        map.setPaintProperty('ongoing-point', 'circle-opacity', filterOpacityChange);
        map.setPaintProperty('ongoing-line', 'line-opacity', filterOpacityChange);
        map.setPaintProperty('ongoing-line-old', 'line-opacity', filterOpacityChange);
    } else {
        map.getSource('ongoing-point-selected').setData({
            type: 'FeatureCollection',
            features: 
                map.getSource('ongoing-point-selected')._data.features
                    .filter(f=>{ return f.properties.f1 != selectedId; })
        });
        map.getSource('ongoing-line-selected').setData({
            type: 'FeatureCollection',
            features: 
                map.getSource('ongoing-line-selected')._data.features
                    .filter(f=>{ return f.properties.f1 != selectedId; })
        });
        map.getSource('ongoing-line-old-selected').setData({
            type: 'FeatureCollection',
            features: 
                map.getSource('ongoing-line-old-selected')._data.features
                    .filter(f=>{ return f.properties.f1 != selectedId; })
        });
        checkSelected();
    }
}

function checkSelected(){
    let noneSelected = true;
    for(var id in filterIds){
        if(filterIds[id]){
            noneSelected = false;
            break;
        }
    }
    if(noneSelected){
        map.setPaintProperty('ongoing-point', 'circle-opacity', 1);
        map.setPaintProperty('ongoing-line', 'line-opacity', 1);
        map.setPaintProperty('ongoing-line-old', 'line-opacity', 1);
    }
    else{
        map.setPaintProperty('ongoing-point', 'circle-opacity', filterOpacityChange);
        map.setPaintProperty('ongoing-line', 'line-opacity', filterOpacityChange);
        map.setPaintProperty('ongoing-line-old', 'line-opacity', filterOpacityChange);
    }
}