/**
 * "Abstract" class for a time period module.
 */
class StreamModule{
    constructor(displayFiles, inFiles, outFiles){
        this.fs = require('fs');
        this.db = require('../../_aux/db.js');
        this.queries = require('../../_aux/queries.js');
        this.spawner = require('../../_aux/spawner.js');
        this.dataDir = "./data/temp/";
        for(i = 0; i != displayFiles.length; i++)
            displayFiles[i] = this.dataDir + displayFiles[i]
        for(i = 0; i != inFiles.length; i++)
            inFiles[i] = this.dataDir + inFiles[i]
        for(i = 0; i != outFiles.length; i++)
            outFiles[i] = this.dataDir + outFiles[i]
        /**
         * Data that is meant to be displayed in the front end will be written here.
         */
        this.displayFiles = displayFiles;
        /**
         * Data that is meant to be given to the "next" period will be written here.
         */
        this.outFiles = outFiles;
        /**
         * Data that is meant to be inserted in this module will be written here.
         */
        this.inFiles = inFiles;
    }
    /**
     * Stringifies a JS date and clips milliseconds.
     * 
     * @param {Date} timestamp to be processed.
     * 
     * @returns stringified and clipped timestamp.
     */
    clipMsec(timestamp){
        return JSON.stringify(timestamp).substr(1,JSON.stringify(timestamp).length - 7);
    }
    /**
     * Writes data to be displayed in the class's display file.
     * 
     * @param {JSON} req 
     * Any data that the method may require (varies on implementation).
     */
    displayData(req={}){
        throw new Error("Unimplemented function!");
    }

    /**
     * Reads from the "in" file and inserts the contained data in the table.
     * 
     * @param {JSON} req 
     * Any data that the method may require (varies on implementation).
     */
    updateData(req={}){
        throw new Error("Unimplemented function!");
    }

    /**
     * Checks all data in order to see if something needs to be removed 
     * and transferred to the next period.
     * 
     * @param {JSON} req 
     * Any data that the method may require (varies on implementation).
     */
    removeData(req={}){
        throw new Error("Unimplemented function!");
    }
}

module.exports.StreamModule = StreamModule;