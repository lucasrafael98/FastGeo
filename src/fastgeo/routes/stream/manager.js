let db = require("../_aux/db.js");
let queries = require("../_aux/queries.js");
let fs = require('fs');
let yaml = require('js-yaml');
let sleep = require('sleep')
let {methods, gridMethods} = require('./display_methods.js');
let {OngoingStreamModule} = require('./modules/ongoing.js');
let {GenericStreamModule} = require('./modules/generic.js');
let {GridStreamModule} = require('./modules/grid.js');

let config = yaml.safeLoad(fs.readFileSync("./config.yaml"));
let currTime = new Date(Date.parse(config.streamStartTime + "Z"));
let genericCount = config.genericCount;
let binSizes = config.streamTimeBinSizes;
let timeDiffs = config.streamGenericTimeDiffs;
let genMethods = config.streamDisplayMethods;
let streamRatio = config.streamRatio;
let gridDisplayMethod = config.gridDisplayMethod;
let gridResolution = config.gridResolution;
let gridRebinThreshold = config.gridRebinThreshold;
let streamMinSimTime = config.streamMinSimTime;
var modules;
var keepLooping = true;
var prevFetchTime = (fs.existsSync(config.resumeFolder)) ? new Date(Date.parse(config.streamStartTime + "Z")) : new Date(0);
var prevSimTime = (fs.existsSync(config.resumeFolder)) ? new Date(Date.parse(config.streamStartTime + "Z")) : new Date(0);
var currSimTime;
var dataCap = config.streamDataCap;

var timeCSV = fs.createWriteStream('./data/time.csv',{flags: 'a'});
timeCSV.write("interval,remove,update,display,total\n");
var display_time;

/**
 * This is used so Python can properly understand the timestamps being sent.
 */
function clipMsec(timestamp){
    return JSON.stringify(timestamp).substr(1,JSON.stringify(timestamp).length - 7);
}

async function display(){
    return new Promise((resolve, reject)=>{
        display_time = new Date();
    
        promises = [];
        for(i = 0; i != modules.length; i++)
            promises.push(modules[i].displayData(updateReqs[i]));
        Promise.all(promises).then((values)=>{
            // console.log("\tProcessing display time: " + 
            //     ((new Date()).getTime() - display_time.getTime()) / 1000 + " seconds.")
            resolve();
            let updateReport = {
                'currentDate': currSimTime.toString(),
                'display': {},
                'remove' : {}
            };
            for(gen = 0; gen < genericCount; gen++){
                genDisplay = values[gen + 1];
                updateReport['display'][gen] = (genDisplay == {}) ? [] : genDisplay['features']
                if(gen < genericCount - 1)
                updateReport['remove'][gen] = fs.readFileSync("./data/temp/to_remove_" + gen + ".json").toString()
            }

            gridDisplay = values[values.length - 1];
            updateReport['display']['grid'] = (gridDisplay == {}) ? [] : gridDisplay;
                
            let ongoingLineUpdate = values[0]['lines'];
            let ongoingPointUpdate = values[0]['points'];
            let ongoingLineDelete = fs.readFileSync("./data/temp/ongoing_line_delete.json").toString();
            
            updateReport['display']['ongoing_lines'] = (ongoingLineUpdate == "") ? [] : ongoingLineUpdate['features']
            updateReport['display']['ongoing_points'] = (ongoingPointUpdate == "") ? [] : ongoingPointUpdate['features']
            updateReport['remove']['ongoing'] = (ongoingLineDelete == "") ? [] : JSON.parse(ongoingLineDelete)['values'];
            
            updateReport = JSON.stringify(updateReport);
            fs.writeFileSync("./data/temp/update.json", updateReport);
            console.log("Overall display time: " + 
                ((new Date()).getTime() - display_time.getTime()) / 1000 + " seconds.")
            display_time = ((new Date()).getTime() - display_time.getTime()) / 1000;
        });
    });
}

/**
 * Main simulation loop.
 * 
 * Retrieves data from the raw_fetched table, and performs the three substeps.
 */
async function simulationLoop(){
    while(keepLooping){
        let start_time = new Date();
        let csvRow = [];
        if(prevSimTime.getTime() != (new Date(0)).getTime() && (currTime.getTime() - prevSimTime.getTime()) / 1000 > dataCap)
            currSimTime = new Date(prevSimTime.getTime() + dataCap * 1000);
        else 
            currSimTime = new Date(currTime);

        console.log("Starting simulation step between " + prevSimTime + " and " + currSimTime + ".")
        csvRow.push((currSimTime - prevSimTime) / 1000);

        removalReqs = [
            {currTime: currSimTime},
            {historyTime: new Date(currSimTime - timeDiffs[0] * 60 * 1000)},
        ];
    
        updateReqs = [
            {currTime: currSimTime, prevTime: prevSimTime},
            {currTime: currSimTime},
        ]
        displayReqs = [
            {currTime: currSimTime, prevTime: prevSimTime},
            {currTime: currSimTime, prevTime: prevSimTime},
        ]

        for(c = 0; c < genericCount; c++){
            removalReqs.push({historyTime: new Date(currSimTime - timeDiffs[c+1] * 60 * 1000)});
            updateReqs.push({currTime: currSimTime});
            displayReqs.push({});
        }
        let remove_time = new Date();
        promises = [];
        for(i = 0; i != modules.length - 1; i++)
            promises.push(modules[i].removeData(removalReqs[i]));
        await Promise.all(promises);
        csvRow.push(((new Date()).getTime() - remove_time.getTime()) / 1000);
        console.log("Overall removal time: " + 
            ((new Date()).getTime() - remove_time.getTime()) / 1000 + " seconds.")
    
        let update_time = new Date();
        promises = [];
        for(i = 0; i != modules.length; i++)
            promises.push(modules[i].updateData(updateReqs[i]));
        await Promise.all(promises);
        csvRow.push(((new Date()).getTime() - update_time.getTime()) / 1000);
        console.log("Overall update time: " + 
            ((new Date()).getTime() - update_time.getTime()) / 1000 + " seconds.")

        await display();
        csvRow.push(display_time);

        let elapsed_time = ((new Date()).getTime() - start_time.getTime()) / 1000
        csvRow.push(elapsed_time);
        timeCSV.write(`${csvRow[0]},${csvRow[1]},${csvRow[2]},${csvRow[3]},${csvRow[4]}\n`);
        if(elapsed_time < streamMinSimTime / 1000){
            console.log("Simulation step complete. Elapsed time: " + 
                        elapsed_time + " seconds. " + 
                        "(Simulation will now wait due to excessive speed).");
            await sleep.msleep(streamMinSimTime - elapsed_time * 1000);
        } else{
            console.log("Simulation step complete. Elapsed time: " + 
                elapsed_time + " seconds.")
        }
        prevSimTime = new Date(currSimTime);
    }
}

/**
 * Accumulates data in a raw_fetched table for the main sim loop.
 */
async function rawFetchLoop(){
    while(keepLooping){
        var realStartTime = new Date();
        await db.queryDatabaseSync(queries.fetchRaw(clipMsec(prevFetchTime), clipMsec(currTime)));
        // console.log("Fetched raw data from " + prevFetchTime + " to " + currTime + ".");
        prevFetchTime = new Date(currTime);
        currTime.setMilliseconds(currTime.getMilliseconds() + 
            ((new Date()).getTime() - realStartTime.getTime()) * streamRatio);
    }
}

module.exports = {
    currTime: currTime,

    /**
     * Creates the time period modules and starts the simulation loops.
     */
    startMainLoop:
        async ()=>{
            await db.initializeRawFetched();
            await db.initializeOngoing();

            modules = [new OngoingStreamModule()]
            for(c = 0; c < genericCount; c++){
                let eb = (c == 0);
                let method = methods[genMethods[c]];
                let table = (c == 0) ? "recent" : ("gen" + c);
                let cutoff = (c == genericCount - 1) 
                    ? NaN : timeDiffs[c] * 60 * 1000
                let outFiles = (c == genericCount - 1) 
                    ? ["to_grid0.json", "to_keep_" + c + ".csv", "to_remove_" + c + ".json"] 
                    : ["to_" + (c + 1) + ".json", "to_keep_" + c + ".csv", "to_remove_" + c + ".json"]
                let inFiles = (c == 0) ? ["to_recent.csv", "added_recent.csv"] 
                                        : ["to_" + c + ".json", "added_" + c + + ".json"];
                
                await db.initializeGenericTable(table);
                modules.push(new GenericStreamModule(
                    [c + ".json"], inFiles, outFiles,
                    table, binSizes[c] * 60, cutoff, method, eb));
            }
            if(fs.existsSync(config.resumeFolder)){
                await db.queryDatabaseSync(queries.copyOngoingPoints(config.resumeFolder + "/ongoing_points.csv"));
                await db.queryDatabaseSync(queries.copyOngoingLines(config.resumeFolder + "/ongoing_lines.csv"));
                await db.queryDatabaseSync(queries.copyRecent(config.resumeFolder + "/recent.csv"));
            }

            modules.push(new GridStreamModule(["grid0.json"], ["to_grid0.json"],
                    [], gridResolution, gridRebinThreshold,
                    gridMethods[gridDisplayMethod], gridDisplayMethod));
            // await modules[0].updateData(
            //     {currTime: currTime, prevTime: new Date(currTime - timeDiff)}
            // );
            // currTime.setSeconds(currTime.getSeconds() + timeDiff/1000);

            rawFetchLoop();
            simulationLoop();
    },

    /**
     * Stops stream loop. (activated when the node process receives a SIGINT).
     */
    stopLoop:
        async ()=>{
            keepLooping = false;
        },
}