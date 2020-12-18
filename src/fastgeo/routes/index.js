let express = require('express');
let router = express.Router();
let fs = require('fs');
let yaml = require('js-yaml');
let path = require('path');

// aux files
let db = require("./_aux/db.js");
let stream = require("./stream/manager.js");
let spawner = require("./_aux/spawner.js")
let queries = require("./_aux/queries.js")

// Connection to PostgreSQL
let username = "postgres";
let password = "postgres";
let host = "localhost:5432";
let database = "fastgeo";
let connectionStr = "postgres://"+username+":"+password+"@"+host+"/"+database;

let config = yaml.safeLoad(fs.readFileSync("./config.yaml"))

function initComplete(){
    console.log("Preprocessing and database initialization complete.");
    console.log("Please go to https://localhost:3000 on your browser.");
    
    stream.startMainLoop();

    // GET map page
    router.get('/', async function(req, res) {
        result = res;
        result.render('index', { 
            title: "FastGeo",
        });
    });

    router.get('/config', (req,res)=>{
        res.send(config);
    });

    router.get('/update', async(req,res)=>{
        res.send(fs.readFileSync("./data/temp/update.json").toString());
    });
}

if(fs.existsSync("./data/temp")){
    var list = fs.readdirSync("./data/temp");
    for(var i = 0; i < list.length; i++) {
        var filename = path.join("./data/temp", list[i]);
        var stat = fs.statSync(filename);
        if(stat.isDirectory()) {
            rmdir(filename);
        } else {
            fs.unlinkSync(filename);
        }
    }
    fs.rmdirSync("./data/temp");
}
if(fs.existsSync(config.resumeFolder)){
    fs.mkdirSync('./data/temp')
    if(fs.existsSync(config.resumeFolder +'/grid.pickle'))
        fs.copyFileSync(config.resumeFolder + "/grid.pickle", "./data/temp/grid.pickle");
    fs.copyFileSync(config.resumeFolder + "/converted_tracks.csv", "./data/temp/converted_tracks.csv");
    db.initializeRawTable(connectionStr).then(()=>{
        initComplete();
    });
} else{
    // The server starts by parsing folders and inserting all data on the raw data table.
    spawner.spawnPythonProcessSync(["./preprocess/initial_parsing.py"])
        .then(()=>{
            db.initializeRawTable(connectionStr).then(()=>{
                initComplete();
            });
        }); 
}

module.exports = router;
