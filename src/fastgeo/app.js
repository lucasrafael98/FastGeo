let createError = require('http-errors');
let express = require('express');
let path = require('path');
let cookieParser = require('cookie-parser');
let logger = require('morgan');
let fs = require('fs');

let indexRouter = require('./routes/index');
let usersRouter = require('./routes/users');

let db = require('./routes/_aux/db.js');
let queries = require('./routes/_aux/queries.js');
let stream = require("./routes/stream/manager.js");

let app = express();

// view engine setup
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'pug');

// Uncomment to see front end requests.
// app.use(logger('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

app.use('/', indexRouter);
app.use('/users', usersRouter);

// catch 404 and forward to error handler
app.use(function(req, res, next) {
  next(createError(404));
});

// error handler
app.use(function(err, req, res, next) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? err : {};

  // render the error page
  res.status(err.status || 500);
  res.render('error');
});

var rmdir = function(dir) {
    var list = fs.readdirSync(dir);
    for(var i = 0; i < list.length; i++) {
        var filename = path.join(dir, list[i]);
        var stat = fs.statSync(filename);
        if(stat.isDirectory()) {
            rmdir(filename);
        } else {
            fs.unlinkSync(filename);
        }
    }
    fs.rmdirSync(dir);
};

// Catching SIGINT (CTRL+C): deletes tables and all files in data/temp.
process.on('SIGINT', async ()=>{
    console.log("\nCaught interrupt signal (CTRL+C).\nStopping stream simulation loop.");
    await stream.stopLoop();
    console.log("Deleting tables.");
    // rmdir("./data/temp");
    if(!fs.existsSync('./data/last'))
        fs.mkdirSync('./data/last');
    if(fs.existsSync('./data/temp/grid.pickle'))
        fs.copyFileSync("./data/temp/grid.pickle", "./data/last/grid.pickle");
    fs.copyFileSync("./data/temp/converted_tracks.csv", "./data/last/converted_tracks.csv");
    let onp = await db.queryDatabaseSyncResult(queries.selectAllCSV("ongoing_points"));
    let stri = "";
    for(let i = 0; i != onp.length; i++){
        r = onp[i];
        r.data_time.setHours(r.data_time.getHours() + 2)
        stri += r.taxid + "," + r.long + "," + r.lat + "," 
                + JSON.stringify(r.data_time).substr(1,JSON.stringify(r.data_time).length - 7) 
                + "," + JSON.stringify(r.insert_date).substr(1,JSON.stringify(r.insert_date).length - 7)  + "\n";
    }
    fs.writeFileSync("./data/last/ongoing_points.csv", stri);
    let onl = await db.queryDatabaseSyncResult(queries.selectAllCSV("ongoing_lines"));
    stri = "";
    for(let i = 0; i != onl.length; i++){
        r = onl[i];
        r.data_time1.setHours(r.data_time1.getHours() + 2)
        r.data_time2.setHours(r.data_time2.getHours() + 2)
        stri += r.taxid + "," + r.lineid + "," + r.long1 + "," + r.lat1 + "," 
                + JSON.stringify(r.data_time1).substr(1,JSON.stringify(r.data_time1).length - 7) 
                + "," + r.long2 + "," + r.lat2 + "," 
                + JSON.stringify(r.data_time2).substr(1,JSON.stringify(r.data_time2).length - 7)  
                + "," + JSON.stringify(r.insert_date).substr(1,JSON.stringify(r.insert_date).length - 7)  + "\n";
    }
    fs.writeFileSync("./data/last/ongoing_lines.csv", stri);
    let rec = await db.queryDatabaseSyncResult(queries.selectAllCSV("recent"));
    stri = "";
    for(let i = 0; i != rec.length; i++){
        r = rec[i];
        let times = [];
        for(let j = 0; j != r.data_times.length; j++){
            r.data_times[j].setHours(r.data_times[j].getHours() + 2)
            times.push(JSON.stringify(r.data_times[j]).substr(1,JSON.stringify(r.data_times[j]).length - 7));
        }
        stri += "{" + r.taxids + "}|" + r.trkid + "|" + r.total + "|" + r.coords + "|{" + r.totals + "}|{" 
                + times + "}|{" + r.adj1 + "}|{" + r.adj2 + "}|" 
                + JSON.stringify(r.insert_date).substr(1,JSON.stringify(r.insert_date).length - 7)  + "\n";
    }
    fs.writeFileSync("./data/last/recent.csv", stri);
    await db.queryDatabaseSync(
        queries.dropRawTable 
        + queries.dropRawFetchedTable
        + queries.dropOngoingPointsTable
        + queries.dropOngoingLinesTable
        + queries.dropRecentTable
        + queries.dropGenTables());
    process.exit();
});

module.exports = app;
