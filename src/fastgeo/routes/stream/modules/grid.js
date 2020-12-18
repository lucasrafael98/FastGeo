let {StreamModule} = require('./stream_module.js');

class GridStreamModule extends StreamModule{
    constructor(display, input, output, 
        resolution, rebinThreshold, displayMethod, displayNumber){
        super(display, input, output);
        this.resolution = resolution;
        this.rebinThreshold = rebinThreshold;
        this.displayMethod = displayMethod;
        this.displayNumber = displayNumber;
        // adjust this number if you're resuming the sim,
        // so that the grid shows up on the front end.
        this.fullGrid = 0;
        this.childProcess = this.spawner.spawnPythonModuleManager("history");
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
            this.displayMethod({proc: this.childProcess, addr: this.displayFiles[0],
                                             res: this.resolution, fullGrid: this.fullGrid});
            let promise = new Promise((resolve, reject)=>{this.continue = resolve;})
            await promise;
            if(this.fullGrid) this.fullGrid -= 1;
            resolve(JSON.parse(this.fs.readFileSync(this.displayFiles[0]).toString()));
        });
    }

    updateData(req={}){
        return new Promise(async (resolve,reject)=>{
            this.childProcess.stdin.write(`['update', '${this.inFiles[0]}','${this.resolution}',\
                                            '${this.rebinThreshold}', '${this.displayNumber}']\n`, "utf-8");
            let promise = new Promise((resolve, reject)=>{this.continue = resolve;})
            await promise;
            resolve();
        });
    }

    removeData(req={}){
        // not even called
        return new Promise((resolve,reject)=>{resolve();});
    }
}

module.exports.GridStreamModule = GridStreamModule;