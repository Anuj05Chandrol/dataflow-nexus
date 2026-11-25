
-- PostgreSQL database storage consumption

SELECT
    pg_size_pretty(
        pg_database_size('dataflow_nexus')
    ) AS database_size;
