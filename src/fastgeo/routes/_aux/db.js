let { Client, Query } = require('pg');
let fs = require('fs');
let path = require("path");

let queries = require('./queries.js');
let connectionString = "";
/**
 * Queries the database synchronously multiple times.
 *
 * @param {array} queries queries that will be performed one by one.
 * @param {array} errorqueries queries that will be performed should there be an error
 * (admittedly, the array structure isn't the best for this argument, but oh well).
 */
function multiQueryDatabaseSync(queries, errorqueries=[]){
        return new Promise(async (resolve, reject)=>{
            let client = new Client(connectionString);
            client.connect();
            for(i = 0; i < queries.length; i++){
                await client.query(queries[i])
                    .catch(async (err)=>{
                        if(errorqueries[i].length == 0) return;
                        for(j = 0; j < errorqueries[i].length; j++){
                            await client.query(errorqueries[i][j]);
                        }
                    });              
            }
            client.end();
            resolve();
        });
    }

module.exports = {
    /**
     * Queries the database synchronously. For queries where a result isn't expected.
     *
     * @param {string} query query to be performed.
     */
    queryDatabaseSync:
        (query)=>{
            return new Promise(async (resolve, reject)=>{
                let client = new Client(connectionString);
                client.connect();
                await client.query(query)
                    .catch(err=>{
                        console.error(err.stack);
                        console.error(query);
                        reject();
                    });
                client.end();
                resolve();
            });
        },

    /**
     * Queries the database synchronously. For queries where a result is expected.
     *
     * @param {*} query query to be performed.
     * @returns promise resolution with query result.
     */
    queryDatabaseSyncResult:
        (query)=>{
            return new Promise(async (resolve, reject)=>{
                var client = new Client(connectionString);
                client.connect();
                var queryResult = client.query(new Query(query));
                queryResult.on("row", function (row, result) {
                    result.addRow(row);
                });
                queryResult.on("end", function(result){
                    client.end();
                    resolve(result.rows);
                });
                queryResult.on("error", err=>{
                    console.error(err.stack);
                    console.error(query);
                    reject();
                });
            });
        },
    
    /**
     * Creates the raw table, as well as inserting data in it. 
     * Also updates the connection string.
     *
     * @param {string} connection database coonnection string.
     */
    initializeRawTable:
        (connection)=>{
            return new Promise(async function (resolve, reject){
                connectionString = connection;
                await multiQueryDatabaseSync(
                    [
                        queries.createRawTable, 
                        queries.insertInRawTable(path.resolve("./data/temp/converted_tracks.csv"))
                    ],
                    [[queries.dropRawTable,queries.createRawTable, 
                    queries.insertInRawTable(path.resolve("./data/temp/converted_tracks.csv"))],[]]
                );
                resolve();
            });
        },
    /**
     * Initializes ongoing tables.
     */
    initializeOngoing:
        ()=>{
            return new Promise(async (resolve, reject)=>{
                await multiQueryDatabaseSync(
                    [queries.createOngoingLinesTable + queries.createOngoingLinesTable],
                    [[queries.dropOngoingPointsTable + queries.dropOngoingLinesTable,
                      queries.createOngoingPointsTable + queries.createOngoingLinesTable]]
                );
                resolve();
            });
        },

    /**
     * Initializes raw_fetched table.
     */
    initializeRawFetched:
        ()=>{
            return new Promise(async (resolve, reject)=>{
                await multiQueryDatabaseSync(
                    [queries.createRawFetchedTable],
                    [[queries.dropRawFetchedTable, queries.createRawFetchedTable]]
                );
                resolve();
            });
        },


    /** 
     * Initializes the given table
     * (if a table with the same name exists, it will be deleted).
     */
    initializeGenericTable:
        (table)=>{
            return new Promise(async (resolve, reject)=>{
                await multiQueryDatabaseSync(
                    [queries.createGenericTable(table)],
                    [[queries.dropTable(table), queries.createGenericTable(table)]]
                );
                resolve();
            });
        },

}