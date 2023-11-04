-- name: list_databases
SELECT d.datname as "Name",
pg_catalog.pg_get_userbyid(d.datdba) as "Owner",
pg_catalog.pg_encoding_to_char(d.encoding) as "Encoding",
d.datcollate as "Collate",
d.datctype as "Ctype",
pg_catalog.array_to_string(d.datacl, E'\n') AS "Access privileges"
FROM pg_catalog.pg_database d
WHERE d.datname ~ %s
ORDER BY 1

-- name: list_databases_verbose
SELECT d.datname as "Name",
pg_catalog.pg_get_userbyid(d.datdba) as "Owner",
pg_catalog.pg_encoding_to_char(d.encoding) as "Encoding",
d.datcollate as "Collate",
d.datctype as "Ctype",
pg_catalog.array_to_string(d.datacl, E'\n') AS "Access privileges",
CASE WHEN pg_catalog.has_database_privilege(d.datname, 'CONNECT')
  THEN pg_catalog.pg_size_pretty(pg_catalog.pg_database_size(d.datname))
ELSE 'No Access'
END as "Size",
t.spcname as "Tablespace",
pg_catalog.shobj_description(d.oid, 'pg_database') as "Description"
FROM pg_catalog.pg_database d
JOIN pg_catalog.pg_tablespace t on d.dattablespace = t.oid
WHERE d.datname ~ %s
ORDER BY 1
