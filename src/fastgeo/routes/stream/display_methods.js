let fs = require('fs')

function displayRaw(req){
    return new Promise(async (resolve,reject)=>{
        let data = 
            await this.db.queryDatabaseSyncResult(
                this.queries.selectGeneric(req.table));
        resolve(data[0].jsonb_build_object);
    });
}

function displayAdjCorrected(req){
    req.proc.stdin.write(`['adj', '${req.table}','${req.addr}']\n`, "utf-8");
}

function displayHeatmap(req){
    req.proc.stdin.write(`['hm', '${req.addr}','${req.table}']\n`, "utf-8");
}

function displayGridHeatmap(req){
    req.proc.stdin.write(`['shm', '${req.addr}','${req.fullGrid}']\n`, "utf-8");
}

function displayGrid(req){
    req.proc.stdin.write(`['chm', '${req.addr}','${req.res}','${req.fullGrid}']\n`, "utf-8");
}

module.exports = {
    methods: [displayRaw, displayAdjCorrected, displayHeatmap],
    gridMethods: [displayGridHeatmap, displayGrid]
}