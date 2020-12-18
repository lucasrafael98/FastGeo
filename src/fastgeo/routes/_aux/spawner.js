let {spawn} = require('child_process');
let os =  require('os');

let isWindows = (os.platform() === 'win32');

/** 
 * Spawns non-Javascript processes.
*/
module.exports = {

    spawnPythonModuleManager:
        (period)=>{
            childProcess = isWindows ? spawn('python', ['-i', '-u', `./preprocess/manager_${period}.py`]) 
                                    : spawn('python3', ['-i', '-u', `./preprocess/manager_${period}.py`]);
            childProcess.stderr.on("data",(data)=>{console.error(data.toString())});
            childProcess.stdin.setEncoding('utf-8');
            childProcess.stdout.setEncoding('utf-8');
            return childProcess;
        },

    /**
    * Spawns a Python child process with the given argments in a synchronous manner.
    * 
    * @param {Array} args first argument is the .py file to run, subsequent arguments are given to the Python process.
    */
    spawnPythonProcessSync:
        (args)=>{
            return new Promise((resolve,reject)=>{
                childProcess = isWindows ? spawn('python',args) : spawn('python3',args);
                childProcess.on("exit", ()=>{resolve();});

                childProcess.stderr.on("data",(data)=>{console.error(data.toString())});
                childProcess.stdout.on("data",(data)=>{console.log(data.toString())});
            });
        },

    /**
    * Spawns a Python child process with the given argments.
    * 
    * @param {Array} args first argument is the .py file to run, subsequent arguments are given to the Python process.
    */
    spawnPythonProcessAsync:
        (args)=>{
            childProcess = isWindows ? spawn('python',args) : spawn('python3',args);

            childProcess.stderr.on("data",(data)=>{console.error(data.toString())});
            childProcess.stdout.on("data",(data)=>{console.log(data.toString())});
        }

}