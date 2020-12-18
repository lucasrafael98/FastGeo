// Code for the tooltips that appear 
// when hovering the mouse over an object.

function loadTooltips(){
    map.on('mousemove', 'ongoing-point', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This point represents the current location of an object with ID " 
                            + e.features[0].properties.f1 + ".";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    }); 
    map.on('mouseleave', 'ongoing-point', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });
    map.on('mousemove', 'ongoing-point-selected', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This point represents the current location of an object with ID " 
                            + e.features[0].properties.f1 + ".";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    }); 
    map.on('mouseleave', 'ongoing-point-selected', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });


    map.on('mousemove', 'ongoing-line', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This line represents the ongoing trajectory of an object with ID " 
                            + e.features[0].properties.f1 + ".";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    }); 
    map.on('mouseleave', 'ongoing-line', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });
    map.on('mousemove', 'ongoing-line-selected', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This line represents the ongoing trajectory of an object with ID " 
                            + e.features[0].properties.f1 + ".";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    }); 
    map.on('mouseleave', 'ongoing-line', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });
    map.on('mousemove', 'ongoing-line-old', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This line represents the ongoing trajectory of an object with ID " 
                            + e.features[0].properties.f1 + ".";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    }); 
    map.on('mouseleave', 'ongoing-line-old', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });

    map.on('mousemove', 'gen0', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This line represents " + e.features[0].properties.total 
                            + " objects that passed through here recently.";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    }); 
    map.on('mouseleave', 'gen0', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });

    map.on('mousemove', 'grid1', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This grid square represents " + e.features[0].properties.total 
                            + " objects that passed through here in the past.";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    });
    map.on('mouseleave', 'grid1', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });

    map.on('mousemove', 'grid2', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This grid square represents " + e.features[0].properties.total 
                            + " objects that passed through here in the past.";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    });
    map.on('mouseleave', 'grid2', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });

    map.on('mousemove', 'grid3', function(e) {
        map.getCanvas().style.cursor = 'pointer';
        var description = "This grid square represents " + e.features[0].properties.total 
                            + " objects that passed through here in the past.";
        popup.setLngLat(e.lngLat).setHTML(description).addTo(map);
    });
    map.on('mouseleave', 'grid3', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });
}