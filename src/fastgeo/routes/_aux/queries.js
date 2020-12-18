let path = require("path");

module.exports = {
    dropTable:
        (table)=>{
            return "drop table if exists " + table + ";";
        },

    dropRawTable:
        "DROP TABLE IF EXISTS raw;",
    
    dropRawFetchedTable:
        "DROP TABLE IF EXISTS raw_fetched;",

    dropOngoingPointsTable:
        "DROP TABLE IF EXISTS ongoing_points;",
    
    dropOngoingLinesTable:
        "DROP TABLE IF EXISTS ongoing_lines;",

    dropRecentTable:
        "DROP TABLE IF EXISTS recent;",

    dropGenTables:
        ()=>{
            let stri = "";
            let gens = 
                require('js-yaml').safeLoad(require('fs').readFileSync("./config.yaml")).genericCount;
            for(i = 0; i != gens; i++){
                stri += "DROP TABLE IF EXISTS gen" + i + ";"
            }
            return stri;
        },

    createRawTable:
        "CREATE TABLE\
            public.raw(\
                long double precision,\
                lat double precision,\
                data_time timestamp without time zone,\
                taxid integer,\
                tripid text)\
            TABLESPACE pg_default;",

    createRawFetchedTable:
        "CREATE TABLE\
            public.raw_fetched(\
                long double precision,\
                lat double precision,\
                data_time timestamp without time zone,\
                taxid integer,\
                tripid text)\
            TABLESPACE pg_default;",
    
    createOngoingPointsTable:
        "CREATE TABLE\
            public.ongoing_points(\
                insert_date timestamp default now(),\
                data_time timestamp without time zone,\
                long double precision,\
                lat double precision,\
                point geometry(Point,4326),\
                taxid integer)\
            TABLESPACE pg_default;",
    
    createOngoingLinesTable:
        "CREATE TABLE\
            public.ongoing_lines(\
                insert_date timestamp default now(),\
                data_time1 timestamp without time zone,\
                data_time2 timestamp without time zone,\
                line geometry(LineString,4326),\
                long1 double precision,\
                lat1 double precision,\
                long2 double precision,\
                lat2 double precision,\
                taxid integer,\
                lineid serial,\
                velocity double precision)\
            TABLESPACE pg_default;",

    createGenericTable:
        (table)=>{
            return "create table\
                    public." + table + "(\
                        insert_date timestamp default now(),\
                        data_times timestamp without time zone[],\
                        totals integer[],\
                        line geometry(LineString,4326),\
                        coords text,\
                        taxids integer[],\
                        trkid serial,\
                        total integer default 1,\
                        adj1 integer[],\
                        adj2 integer[])\
                    TABLESPACE pg_default;"
        },

    insertInRawTable:
        (file)=>{
            file = path.resolve(file);
            return "COPY raw(taxid, data_time, long, lat, tripid)\
                    FROM '" + file + "'\
                        DELIMITERS ',';";
        },

    insertInOngoingTables:
        (file, fileLatest)=>{
            file = path.resolve(file);
            fileLatest = path.resolve(fileLatest);
            return "COPY ongoing_points(taxid, data_time, long, lat)\
                        FROM '"+ fileLatest +"'\
                            DELIMITERS ',';\
                    COPY ongoing_lines(taxid, long1, lat1, data_time1, long2, lat2, data_time2, velocity)\
                        FROM '"+ file +"'\
                            DELIMITERS ',';\
                    UPDATE ongoing_lines\
                        SET line =\
                            ST_MakeLine(\
                                ST_SetSRID(ST_MakePoint(long1,lat1),4326),\
                                ST_SetSRID(ST_MakePoint(long2,lat2),4326));\
                    UPDATE ongoing_points\
                        SET point =\
                            ST_SetSRID(ST_MakePoint(long,lat),4326);";
            },

    insertInGeneric:
        (file, table)=>{
            file = path.resolve(file);
            return "COPY " + table + "(taxids, data_times, totals, total, coords, trkid, adj1, adj2)\
                    FROM '"+ file +"'\
                        DELIMITERS '|';\
                    UPDATE " + table + "\
                    SET line =\
                        ST_GeomFromText(coords, 4326);";
        },

    selectPoints_noFile:
        ()=>{
            return "SELECT jsonb_build_object(\
                'type',     'FeatureCollection',\
                'features', jsonb_agg(features.feature)\
                )FROM (SELECT jsonb_build_object(\
                    'type',       'Feature',\
                    'geometry',   ST_AsGeoJSON(point)::jsonb,\
                    'properties', json_build_object(\
                        'f1', taxid,\
                        'f2', data_time\
                )) AS feature\
                FROM (SELECT * FROM ongoing_points) inputs) features;";
        },

    selectLinesBetweenTime_noFile:
        (min, max)=>{
            return "SELECT jsonb_build_object(\
                'type',     'FeatureCollection',\
                'features', jsonb_agg(features.feature)\
                )FROM (SELECT jsonb_build_object(\
                    'type',       'Feature',\
                    'geometry',   ST_AsGeoJSON(line)::jsonb,\
                    'properties', json_build_object(\
                        'f1', taxid,\
                        'f2', data_time2,\
                        'f3', lineid,\
                        'f4', velocity\
                )) AS feature FROM\
                (select * from ongoing_lines\
                where data_time2 >= '"+ min +"'\
                and data_time2 < '"+ max +"') inputs) features;";
        },

    selectAllLines:
        (file)=>{
            file = path.resolve(file);
            return "copy(\
                select taxid, long1, lat1, data_time1, long2, lat2, data_time2, lineid\
                from ongoing_lines\
                order by taxid, data_time2\
            )to '" + file + "' csv delimiter ',';";
        },

    selectRawPointsBetweenTime:
        (file, fileLatest, min, max)=>{
            file = path.resolve(file);
            fileLatest = path.resolve(fileLatest);
            return "COPY(\
                        select taxid, data_time, long, lat, tripid\
                        from raw_fetched\
                        where data_time >= '"+ min +"'\
                        and data_time < '"+ max +"'\
                        union all\
                        select * from (\
                            select distinct on (taxid) taxid, data_time, long, lat, tripid\
                            from raw_fetched\
                            where data_time < '"+ min +"'\
                            order by taxid, data_time desc\
                        ) as prev\
                        order by taxid, data_time\
                    )\
                    TO '"+ file +"'\
                    WITH CSV DELIMITER ',';\
                    COPY(\
                        select distinct on (taxid) taxid, data_time, long, lat\
                        from raw_fetched\
                        where data_time >= '"+ min +"'\
                        and data_time < '"+ max +"'\
                        order by taxid, data_time desc\
                    )\
                    TO '"+ fileLatest +"'\
                    WITH CSV DELIMITER ',';";
        },

    updateLatestPoints:
        "DELETE FROM ongoing_points\
            WHERE ongoing_points.point NOT IN\
                (select distinct on (taxid) point\
                from ongoing_points\
                order by taxid, data_time desc);",

    cleanOngoing:
        (file)=>{
            file = path.resolve(file);
            return "create table temp_lines(lineid integer);\
                copy temp_lines(lineid) from '" + file + "';\
                delete from ongoing_lines\
                where lineid in (\
                    select lineid\
                    from temp_lines\
                );\
                drop table temp_lines;"
        },

    selectGeneric:
        (table)=>{
            return "SELECT jsonb_build_object(\
                'type',     'FeatureCollection',\
                'features', jsonb_agg(features.feature)\
                )FROM (SELECT jsonb_build_object(\
                    'type',       'Feature',\
                    'geometry',   ST_AsGeoJSON(line)::jsonb,\
                    'properties', json_build_object(\
                        'f1', total,\
                        'totals', totals,\
                        'times', data_times,\
                        'trkid', trkid,\
                        'ids', taxids,\
                        'adj1', adj1,\
                        'adj2', adj2\
                )) AS feature FROM\
                " + table +") features";
        },

    fetchRaw:
        (min, max)=>{
            return "insert into raw_fetched (\
                        select *\
                        from raw\
                        where data_time >= '"+ min +"'\
                        and data_time < '"+ max + "'\
                    );"
        },

    selectAllCSV:
        (table)=>{
            return "select * from " + table + ";"
        },

    copyOngoingPoints:
        (file)=>{
            file = path.resolve(file);
            return "copy ongoing_points(taxid,long,lat,data_time,insert_date)\
                        from '" + file + "'\
                        delimiters ',';\
                    UPDATE ongoing_points\
                        SET point =\
                            ST_SetSRID(ST_MakePoint(long,lat),4326);";
        },

    copyOngoingLines:
        (file)=>{
            file = path.resolve(file);
            return "copy ongoing_lines(taxid,lineid,long1,lat1,data_time1,long2,lat2,data_time2,insert_date)\
                        from '" + file + "'\
                        delimiters ',';\
                    UPDATE ongoing_lines\
                        SET line =\
                            ST_MakeLine(\
                                ST_SetSRID(ST_MakePoint(long1,lat1),4326),\
                                ST_SetSRID(ST_MakePoint(long2,lat2),4326));";
        }, 

    copyRecent:
        (file)=>{
            file = path.resolve(file);
            return "copy recent(taxids,trkid,total,coords,totals,data_times,adj1,adj2,insert_date)\
                        from '" + file + "'\
                        delimiters '|';\
                    UPDATE recent\
                        SET line =\
                            ST_GeomFromText(coords, 4326);";
        },
};