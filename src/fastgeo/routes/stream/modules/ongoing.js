let {StreamModule} = require('./stream_module.js');

class OngoingStreamModule extends StreamModule{
    constructor(){
        super(
            ["ongoing_points.json", "ongoing_lines.json"],
            ["raw_points.csv", "raw_points_latest.csv"],
            ["raw_lines.csv", "to_delete_ongoing.csv", "to_recent.csv", "ongoing_line_delete.json"]
        );
        this.childProcess = this.spawner.spawnPythonModuleManager("ongoing");
        this.continue;
        const rl = require('readline').createInterface({
            input: childProcess.stdout
        });
        rl.on('line', (line)=>{
            if(line[0] === '_' && this.continue) this.continue();
            else console.log(line);
        }); 
    }
    
    displayData(req={}){
        return new Promise(async(resolve,reject)=>{
            let display_time = new Date();
            let lines = await this.db.queryDatabaseSyncResult(this.queries.selectLinesBetweenTime_noFile(
                this.clipMsec(req.prevTime),
                this.clipMsec(req.currTime),
            ));
            let points = await this.db.queryDatabaseSyncResult(
                this.queries.selectPoints_noFile());
            if(lines[0]) lines = lines[0].jsonb_build_object;
            if(points[0]) points = points[0].jsonb_build_object;
            resolve({'lines': lines, 'points': points});
        });
    }

    updateData(req={}){
        // process raw lines in order to insert in ongoing_lines db
        return new Promise(async(resolve,reject)=>{
            await this.db.queryDatabaseSync(this.queries.selectRawPointsBetweenTime(
                this.inFiles[0], this.inFiles[1],
                this.clipMsec(req.prevTime), this.clipMsec(req.currTime)
            ));
            this.childProcess.stdin.write("['consec', '" + this.inFiles[0] + "']\n", "utf-8");
            let promise = new Promise((resolve, reject)=>{this.continue = resolve;})
            await promise;
            await this.db.queryDatabaseSync(this.queries.insertInOngoingTables(
                this.inFiles[0], this.inFiles[1]
            ));
            await this.db.queryDatabaseSync(this.queries.updateLatestPoints);
            resolve();
        });
    }

    removeData(req={}){
        // write all lines in a file and then check for stop events
        // afterwards, delete stopped tracks from ongoing table
        return new Promise(async(resolve,reject)=>{
            await this.db.queryDatabaseSync(this.queries.selectAllLines(
                this.outFiles[0]
            ));
            this.childProcess.stdin.write(`['stops', '${this.outFiles[0]}','${this.outFiles[1]}',\
                                            '${this.outFiles[2]}', '${this.clipMsec(req.currTime)}']\n`, "utf-8");
            let promise = new Promise((resolve, reject)=>{this.continue = resolve;});
            await promise;
            await this.db.queryDatabaseSync(this.queries.cleanOngoing(
                this.outFiles[1]
            ));
            let toDelete = [];
            this.fs.createReadStream(this.outFiles[1])
                .on('data', (row)=>{
                    toDelete = row.toString().split("\n");
                    toDelete.forEach((e,i, arr)=> {
                        arr[i] = parseInt(arr[i], 10);
                    });
                })
                .on('end', ()=>{
                    this.fs.writeFileSync(
                        this.outFiles[3],
                        '{ "values": ' + JSON.stringify(toDelete) + '}'
                    );
                    resolve();
                });
        });
    }
}

module.exports.OngoingStreamModule = OngoingStreamModule;