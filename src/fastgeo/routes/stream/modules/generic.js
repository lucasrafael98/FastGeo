let {StreamModule} = require('./stream_module.js');

class GenericStreamModule extends StreamModule{
    constructor(display, input, output, table, 
                binSize, cutoff, displayMethod, eb){
        super(display, input, output);
        this.table = table;
        this.binSize = binSize;
        this.cutoff = cutoff;
        this.displayMethod = displayMethod;
        this.eb = eb
        this.childProcess = this.spawner.spawnPythonModuleManager("recent");
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
        return new Promise(async (resolve,reject)=>{
            let res = await this.displayMethod({proc: this.childProcess, table: this.table, addr: this.displayFiles[0]});
            if(res){
                resolve(res);
            } else {
                let promise = new Promise((resolve, reject)=>{this.continue = resolve;})
                await promise;
                resolve(JSON.parse(this.fs.readFileSync(this.displayFiles[0]).toString()));
            }
        });
    }

    updateData(req={}){
        return new Promise(async (resolve,reject)=>{
            if(this.eb){
                this.childProcess.stdin.write(`['bundle', '${this.inFiles[0]}','${this.binSize}',\
                                                '${this.clipMsec(req.currTime)}', '${this.table}']\n`, "utf-8");
            } else {
                this.childProcess.stdin.write(`['update', '${this.inFiles[0]}', '${this.displayFiles[0]}','${this.binSize}',\
                                                '${this.clipMsec(req.currTime)}', '${this.table}']\n`, "utf-8");
            }
            let promise = new Promise((resolve, reject)=>{this.continue = resolve;})
            await promise;
            await this.db.queryDatabaseSync(
                this.queries.insertInGeneric(this.inFiles[0], this.table));
            resolve();
        });
    }

    removeData(req={}){
        return new Promise(async (resolve,reject)=>{
            if(this.outFiles.length != 0){
                this.childProcess.stdin.write(`['remove', '${this.outFiles[1]}', '${this.outFiles[0]}','${this.outFiles[2]}',\
                                                '${this.table}', '${this.clipMsec(req.historyTime)}']\n`, "utf-8");
                let promise = new Promise((resolve, reject)=>{this.continue = resolve;})
                await promise;
                await this.db.queryDatabaseSync(
                    this.queries.insertInGeneric(this.outFiles[1], this.table));
            }
            resolve();
        });
    }
}

module.exports.GenericStreamModule = GenericStreamModule;