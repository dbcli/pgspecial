-- name: version
SELECT version()
-- name: list_databases
SELECT d.datname AS "Name",
       pg_catalog.pg_get_userbyid(d.datdba) AS "Owner",
       pg_catalog.pg_encoding_to_char(d.encoding) AS "Encoding",
       d.datcollate AS "Collate",
       d.datctype AS "Ctype",
       pg_catalog.array_to_string(d.datacl, e'\n') AS "Access privileges"
FROM pg_catalog.pg_database d
WHERE d.datname ~ %s
ORDER BY 1
-- name: list_databases_verbose
SELECT d.datname AS "Name",
       pg_catalog.pg_get_userbyid(d.datdba) AS "Owner",
       pg_catalog.pg_encoding_to_char(d.encoding) AS "Encoding",
       d.datcollate AS "Collate",
       d.datctype AS "Ctype",
       pg_catalog.array_to_string(d.datacl, e'\n') AS "Access privileges",
       CASE
           WHEN pg_catalog.has_database_privilege(d.datname, 'CONNECT')
           THEN pg_catalog.pg_size_pretty(pg_catalog.pg_database_size(d.datname))
           ELSE 'No Access'
       END AS "Size",
       t.spcname AS "Tablespace",
       pg_catalog.shobj_description(d.oid, 'pg_database') AS "Description"
FROM pg_catalog.pg_database d
JOIN pg_catalog.pg_tablespace t ON d.dattablespace = t.oid
WHERE d.datname ~ %s
ORDER BY 1
-- name: list_roles_9_verbose
SELECT r.rolname,
       r.rolsuper,
       r.rolinherit,
       r.rolcreaterole,
       r.rolcreatedb,
       r.rolcanlogin,
       r.rolconnlimit,
       r.rolvaliduntil,
ARRAY(SELECT b.rolname FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles b ON (m.roleid = b.oid) WHERE m.member = r.oid) as memberof,
pg_catalog.shobj_description(r.oid, 'pg_authid') AS description,
r.rolreplication
FROM pg_catalog.pg_roles r
WHERE r.rolname ~ %s
ORDER BY 1
-- name: list_roles_9
SELECT r.rolname,
       r.rolsuper,
       r.rolinherit,
       r.rolcreaterole,
       r.rolcreatedb,
       r.rolcanlogin,
       r.rolconnlimit,
       r.rolvaliduntil,
ARRAY(SELECT b.rolname FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles b ON (m.roleid = b.oid) WHERE m.member = r.oid) as memberof,
r.rolreplication
FROM pg_catalog.pg_roles r
WHERE r.rolname ~ %s
ORDER BY 1
-- name: list_roles
SELECT u.usename AS rolname,
       u.usesuper AS rolsuper,
       TRUE AS rolinherit,
       FALSE AS rolcreaterole,
       u.usecreatedb AS rolcreatedb,
       TRUE AS rolcanlogin,
       -1 AS rolconnlimit,
       u.valuntil AS rolvaliduntil,
       array(SELECT g.groname FROM pg_catalog.pg_group g WHERE u.usesysid = any(g.grolist)) AS memberof
FROM pg_catalog.pg_user u
-- name:  list_schemas
-- docs: ("\\dn", "\\dn[+] [pattern]", "List schemas.")
SELECT
    n.nspname AS "name",
    pg_catalog.pg_get_userbyid(n.nspowner) AS "owner",
    pg_catalog.array_to_string(n.nspacl, E'\\n') AS "access_privileges",
    pg_catalog.obj_description(n.oid, 'pg_namespace') AS "description"
FROM
    pg_catalog.pg_namespace n
WHERE
    n.nspname ~ :pattern
ORDER BY 1

-- name:  list_privileges
-- docs: ("\\dp", "\\dp [pattern]", "List roles.", aliases=("\\z",))
SELECT n.nspname AS "Schema",
       c.relname AS "Name",
       CASE c.relkind
           WHEN 'r' THEN 'table'
           WHEN 'v' THEN 'view'
           WHEN 'p' THEN 'partitioned table'
           WHEN 'm' THEN 'materialized view'
           WHEN 'i' THEN 'index'
           WHEN 'I' THEN 'partitioned index'
           WHEN 'S' THEN 'sequence'
           WHEN 's' THEN 'special'
           WHEN 'f' THEN 'foreign table'
           WHEN 't' THEN 'toast table'
           WHEN 'c' THEN 'composite type'
       END AS "Type",
       pg_catalog.array_to_string(c.relacl, e'\n') AS "Access privileges",
       pg_catalog.array_to_string(ARRAY
         (SELECT attname || e':\n  ' || pg_catalog.array_to_string(attacl, e'\n  ')
          FROM pg_catalog.pg_attribute a
          WHERE attrelid = c.oid
            AND NOT attisdropped
            AND attacl IS NOT NULL), e'\n') AS "Column privileges",
       pg_catalog.array_to_string(ARRAY
         (SELECT polname ||
             CASE
                  WHEN NOT polpermissive THEN e' (RESTRICTIVE)'
                  ELSE ''
              END ||
             CASE
                 WHEN polcmd != '*' THEN e' (' || polcmd::pg_catalog.text || e'):'
                 ELSE e':'
             END ||
             CASE
                 WHEN polqual IS NOT NULL THEN e'\n  (u): ' || pg_catalog.pg_get_expr(polqual, polrelid)
                 ELSE e''
             END ||
             CASE
                 WHEN polwithcheck IS NOT NULL THEN e'\n  (c): ' || pg_catalog.pg_get_expr(polwithcheck, polrelid)
                 ELSE e''
             END ||
             CASE
                 WHEN polroles <> '{0}' THEN e'\n  to: ' || pg_catalog.array_to_string(ARRAY
                   (SELECT rolname FROM pg_catalog.pg_roles WHERE oid = ANY (polroles) ORDER BY 1), e', ')
                 ELSE e''
             END
          FROM pg_catalog.pg_policy pol
          WHERE polrelid = c.oid), e'\n') AS "Policies"
FROM pg_catalog.pg_class c
LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'v', 'm', 'S', 'f', 'p')
  AND n.nspname !~ '^pg_'
  AND CASE
          WHEN NOT %s::bool THEN pg_catalog.pg_table_is_visible(c.oid)
          ELSE (c.relname operator(pg_catalog.~) %s COLLATE pg_catalog.default
                AND n.nspname operator(pg_catalog. ~) %s COLLATE pg_catalog.default)
      END
ORDER BY 1, 2

-- name:  list_default_privileges
-- docs: ("\\ddp", "\\ddp [pattern]", "Lists default access privilege settings.")
SELECT pg_catalog.pg_get_userbyid(d.defaclrole) AS "Owner",
       n.nspname AS "Schema",
       CASE d.defaclobjtype
       WHEN 'r' THEN 'table'
       WHEN 'S' THEN 'sequence'
       WHEN 'f' THEN 'function'
       WHEN 'T' THEN 'type'
       WHEN 'n' THEN 'schema'
       END as "Type",
       pg_catalog.array_to_string(d.defaclacl, e'\n') AS "Access privileges"
FROM pg_catalog.pg_default_acl d
LEFT JOIN pg_catalog.pg_namespace n ON n.oid = d.defaclnamespace
WHERE (n.nspname OPERATOR(pg_catalog. ~) %s COLLATE pg_catalog.default
       OR pg_catalog.pg_get_userbyid(d.defaclrole) OPERATOR(pg_catalog. ~) %s COLLATE pg_catalog.default)
ORDER BY 1, 2, 3

-- name:  list_tablespaces
-- docs: ("\\db", "\\db[+] [pattern]", "List tablespaces.")
SELECT
    n.spcname AS "name",
    pg_catalog.pg_get_userbyid(n.spcowner) AS "owner",
    CASE
        WHEN (EXISTS ( SELECT * FROM pg_proc WHERE proname = 'pg_tablespace_location'))
        THEN pg_catalog.pg_tablespace_location(n.oid)
        ELSE 'Not supported'
    END AS "location"
FROM
    pg_catalog.pg_tablespace n
WHERE
    n.spcname ~ :pattern
ORDER BY 1

-- name:  list_extensions
SELECT
    e.extname AS "name",
    e.extversion AS "version",
    n.nspname AS "schema",
    c.description AS "description"
FROM
    pg_catalog.pg_extension e
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = e.extnamespace
    LEFT JOIN pg_catalog.pg_description c ON c.objoid = e.oid
        AND c.classoid = 'pg_catalog.pg_extension'::pg_catalog.regclass
WHERE
    e.extname ~ :pattern
ORDER BY 1, 2

-- name:  list_extensions_verbose
SELECT
    e.extname AS "name",
    pg_catalog.pg_describe_object(classid, objid, 0) AS "object_description"
FROM
    pg_catalog.pg_depend d
    LEFT OUTER JOIN pg_catalog.pg_extension e ON e.oid = refobjid
WHERE
    refclassid = 'pg_catalog.pg_extension'::pg_catalog.regclass
    AND deptype = 'e'
    AND e.extname ~ :pattern
ORDER BY 1

-- name:  list_objects
-- docs: This method is used by list_tables, list_views, list_materialized views and list_indexes
SELECT
    n.nspname AS "schema",
    c.relname AS "name",
    :relkind AS "type",
    pg_catalog.pg_get_userbyid(c.relowner) AS "owner",
    pg_catalog.pg_size_pretty(pg_catalog.pg_table_size(c.oid)) as "size",
    pg_catalog.obj_description(c.oid, 'pg_class') as "description"
FROM
    pg_catalog.pg_class c
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE
    c.relkind IN (:relkinds)
AND n.nspname ~ :schema_pattern
        AND n.nspname <> 'pg_catalog'
        AND n.nspname <> 'information_schema'
        AND n.nspname !~ '^pg_toast'
    AND c.relname ~ :pattern
ORDER BY 1, 2

-- name:  list_functions
-- docs: ("\\df", "\\df[+] [pattern]", "List functions.")
SELECT
    n.nspname AS "schema",
    p.proname AS "name",
    pg_catalog.pg_get_function_result(p.oid) AS "result_data_type",
    pg_catalog.pg_get_function_arguments(p.oid) AS "argument_data_types",
    CASE
    WHEN p.prokind = 'a' THEN 'agg'
    WHEN p.prokind = 'w' THEN 'window'
    WHEN p.prorettype = 'pg_catalog.trigger'::pg_catalog.regtype THEN 'trigger'
    ELSE 'normal'
    END AS "type",
    :provolatile AS "volatility",
    pg_catalog.pg_get_userbyid(p.proowner) AS "owner",
    l.lanname AS "language",
    p.prosrc AS "source_code",
    pg_catalog.obj_description(p.oid, 'pg_proc') AS "description"
FROM
    pg_catalog.pg_proc p
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
    LEFT JOIN pg_catalog.pg_language l ON l.oid = p.prolang
WHERE
    n.nspname ~ :schema_pattern
    AND p.proname ~ :pattern
ORDER BY 1, 2, 4

-- name:  list_datatypes
-- docs: ("\\dT", "\\dT[S+] [pattern]", "List data types")
SELECT
    n.nspname AS "schema",
    pg_catalog.format_type(t.oid, NULL) AS "name",
    t.typname AS "internal_name",
    CASE
    WHEN t.typrelid != 0 THEN CAST('tuple' AS pg_catalog.text)
    WHEN t.typlen < 0 THEN CAST('var' AS pg_catalog.text)
    ELSE CAST(t.typlen AS pg_catalog.text)
    END AS "size",
    pg_catalog.array_to_string(ARRAY (
            SELECT e.enumlabel FROM pg_catalog.pg_enum e WHERE
                e.enumtypid = t.oid ORDER BY e.enumsortorder), E'\n') AS "elements",
    pg_catalog.array_to_string(t.typacl, E'\n') AS "access_privileges",
    pg_catalog.obj_description(t.oid, 'pg_type') AS "description"
FROM
    pg_catalog.pg_type t
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
WHERE (t.typrelid = 0
    OR (
        SELECT
            c.relkind = 'c'
        FROM
            pg_catalog.pg_class c
        WHERE
            c.oid = t.typrelid))
    AND n.nspname ~ :schema_pattern
    AND (t.typname ~ :pattern OR pg_catalog.format_type(t.oid, NULL) ~ :pattern)
ORDER BY 1, 2

-- name:  list_domains
-- docs: ("\\dD", "\\dD[+] [pattern]", "List or describe domains.")
SELECT
    n.nspname AS "schema",
    t.typname AS "name",
    pg_catalog.format_type(t.typbasetype, t.typtypmod) AS "type",
    pg_catalog.ltrim((COALESCE((
            SELECT
                (' collate ' || c.collname)
            FROM pg_catalog.pg_collation AS c, pg_catalog.pg_type AS bt
            WHERE
                c.oid = t.typcollation
                AND bt.oid = t.typbasetype
                AND t.typcollation <> bt.typcollation), '') ||
        CASE WHEN t.typnotnull THEN ' not null' ELSE '' END) ||
    CASE WHEN t.typdefault IS NOT NULL THEN (' default ' || t.typdefault) ELSE '' END) AS "modifier",
    pg_catalog.array_to_string(ARRAY (
            SELECT
                pg_catalog.pg_get_constraintdef(r.oid, TRUE)
            FROM pg_catalog.pg_constraint AS r
            WHERE t.oid = r.contypid), ' ') AS "check",
        pg_catalog.array_to_string(t.typacl, E'\n') AS "access_privileges",
    d.description AS "description"
FROM
    pg_catalog.pg_type AS t
    LEFT JOIN pg_catalog.pg_namespace AS n ON n.oid = t.typnamespace
    LEFT JOIN pg_catalog.pg_description d ON d.classoid = t.tableoid
        AND d.objoid = t.oid
        AND d.objsubid = 0
WHERE
    t.typtype = 'd'
    AND n.nspname ~ :schema_pattern
    AND t.typname ~ :pattern
ORDER BY 1, 2
-- name:  describe_table_details
-- docs: ( "\\d", "\\d[+] [pattern]", "List or describe tables, views and sequences.")
SELECT
    c.oid,
    n.nspname,
    c.relname
FROM
    pg_catalog.pg_class c
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE
    n.nspname ~ :schema_pattern
--    AND pg_catalog.pg_table_is_visible(c.oid)
    AND c.relname OPERATOR (pg_catalog. ~) :pattern
ORDER BY 2, 3

-- name:  describe_one_table_details
SELECT
    c.relchecks,
    c.relhasindex,
    c.relhasrules,
    c.relhastriggers,
    pg_catalog.array_to_string(c.reloptions || ARRAY (
            SELECT 'toast.' || x FROM pg_catalog.unnest(tc.reloptions) x), ', ') as reloptions,
    c.reltablespace,
    :reloftype as reloftype,
    :relkind as relkind,
    :relpersistence as relpersistence,
    c.relispartition
FROM
    pg_catalog.pg_class c
    LEFT JOIN pg_catalog.pg_class tc ON (c.reltoastrelid = tc.oid)
WHERE
    c.oid = :oid

-- name: get_column_info
SELECT
    a.attname AS "name",
    a.attnotnull AS "not_null",
    a.attidentity AS "identity",
    a.attgenerated AS "generated",
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS "data_type",
    pg_catalog.col_description(a.attrelid, a.attnum) AS "description",
    pg_catalog.pg_get_indexdef(a.attrelid, a.attnum, TRUE) AS "index_definition",
    pg_catalog.pg_get_viewdef(:oid::pg_catalog.oid, TRUE) AS "view_definition",
    (
        SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid, TRUE) FOR 128)
        FROM
            pg_catalog.pg_attrdef d
        WHERE
            d.adrelid = a.attrelid
            AND d.adnum = a.attnum
            AND a.atthasdef) AS "default_value",
    (
        SELECT
            c.collname
        FROM
            pg_catalog.pg_collation c,
            pg_catalog.pg_type t
        WHERE
            c.oid = a.attcollation
            AND t.oid = a.atttypid
            AND a.attcollation <> t.typcollation) AS "collation",
    CASE
        WHEN a.attnum <= (SELECT i.indnkeyatts FROM pg_catalog.pg_index i WHERE i.indexrelid = :oid) THEN 'yes'
        ELSE 'no'
    END AS "is_key",
    CASE
        WHEN a.attstattarget = - 1 THEN NULL
        ELSE a.attstattarget
    END AS "stat_target",
    CASE
        WHEN attfdwoptions IS NULL THEN ''
        ELSE '(' || array_to_string(ARRAY
            (SELECT quote_ident(option_name) || ' ' || quote_literal(option_value) FROM pg_options_to_table(attfdwoptions)), ', ') || ')'
    END AS "fdw_options"
FROM
    pg_catalog.pg_attribute a
WHERE
    a.attrelid = :oid
    AND a.attnum > 0
    AND NOT a.attisdropped
ORDER BY a.attnum

-- name: get_view_info
SELECT pg_catalog.pg_get_viewdef(:oid::pg_catalog.oid, true) as viewdef

-- name: get_index_info
SELECT
    i.indisunique,
    i.indisprimary,
    i.indisclustered,
    i.indisvalid,
    (NOT i.indimmediate)
    AND EXISTS ( SELECT 1 FROM pg_catalog.pg_constraint
        WHERE
            conrelid = i.indrelid
            AND conindid = i.indexrelid
            AND contype IN ('p', 'u', 'x')
            AND condeferrable) AS condeferrable,
    (NOT i.indimmediate)
    AND EXISTS ( SELECT 1 FROM pg_catalog.pg_constraint
        WHERE
            conrelid = i.indrelid
            AND conindid = i.indexrelid
            AND contype IN ('p', 'u', 'x')
            AND condeferred) AS condeferred,
    a.amname,
    c2.relname,
    pg_catalog.pg_get_expr(i.indpred, i.indrelid, TRUE)
FROM
    pg_catalog.pg_index i,
    pg_catalog.pg_class c,
    pg_catalog.pg_class c2,
    pg_catalog.pg_am a
WHERE
    i.indexrelid = c.oid
    AND c.oid = :oid
    AND c.relam = a.oid
    AND i.indrelid = c2.oid

-- name: get_sequence_info
SELECT
    pg_catalog.quote_ident(nspname) || '.' ||
    pg_catalog.quote_ident(relname) || '.' ||
    pg_catalog.quote_ident(attname) AS "column"
FROM
    pg_catalog.pg_class c
    INNER JOIN pg_catalog.pg_depend d ON c.oid = d.refobjid
    INNER JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    INNER JOIN pg_catalog.pg_attribute a ON (a.attrelid = c.oid AND a.attnum = d.refobjsubid)
WHERE
    d.classid = 'pg_catalog.pg_class'::pg_catalog.regclass
    AND d.refclassid = 'pg_catalog.pg_class'::pg_catalog.regclass
    AND d.objid = :oid
    AND d.deptype = 'a'

-- name: get_table_index_info
SELECT
    c2.relname,
    i.indisprimary,
    i.indisunique,
    i.indisclustered,
    i.indisvalid,
    pg_catalog.pg_get_indexdef(i.indexrelid, 0, TRUE),
    pg_catalog.pg_get_constraintdef(con.oid, TRUE),
    :contype as contype,
    condeferrable,
    condeferred,
    c2.reltablespace
FROM
    pg_catalog.pg_class c,
    pg_catalog.pg_class c2,
    pg_catalog.pg_index i
    LEFT JOIN pg_catalog.pg_constraint con ON conrelid = i.indrelid
        AND conindid = i.indexrelid
        AND contype IN ('p', 'u', 'x')
WHERE
    c.oid = :oid
    AND c.oid = i.indrelid
    AND i.indexrelid = c2.oid
ORDER BY
    i.indisprimary DESC,
    i.indisunique DESC,
    c2.relname

-- name: get_table_constraints
SELECT
    conrelid::pg_catalog.regclass,
    con.conname,
    :contype as contype,
    pg_catalog.pg_get_constraintdef(con.oid, TRUE) AS condef
FROM
    pg_catalog.pg_constraint con
WHERE
    con.confrelid = :oid
ORDER BY 1

-- name: get_table_rules
SELECT
    r.rulename,
    :ev_enabled as ev_enabled,
    trim(TRAILING ';' FROM pg_catalog.pg_get_ruledef(r.oid, TRUE))
FROM
    pg_catalog.pg_rewrite r
WHERE
    r.ev_class = :oid
ORDER BY 1

-- name: get_is_partition
SELECT
    quote_ident(np.nspname) || '.' ||
    quote_ident(cp.relname) || ' ' ||
    pg_get_expr(cc.relpartbound, cc.oid, TRUE) AS partition_of,
    pg_get_partition_constraintdef (cc.oid) AS partition_constraint
FROM
    pg_inherits i
    INNER JOIN pg_class cp ON cp.oid = i.inhparent
    INNER JOIN pg_namespace np ON np.oid = cp.relnamespace
    INNER JOIN pg_class cc ON cc.oid = i.inhrelid
    INNER JOIN pg_namespace nc ON nc.oid = cc.relnamespace
WHERE
    cc.oid = :oid

-- name: get_table_triggers
SELECT
    t.tgname,
    pg_catalog.pg_get_triggerdef(t.oid, TRUE),
    t.tgenabled
FROM
    pg_catalog.pg_trigger t
WHERE
    t.tgrelid = :oid
    AND NOT t.tgisinternal
ORDER BY 1

-- name: get_foreign_table_info
SELECT
    s.srvname,
    array_to_string(ARRAY (
            SELECT
                quote_ident(option_name) || ' ' ||
                quote_literal(option_value)
            FROM pg_options_to_table(ftoptions)), ', ') AS ftoptions
FROM
    pg_catalog.pg_foreign_table f,
    pg_catalog.pg_foreign_server s
WHERE
    f.ftrelid = :oid
    AND s.oid = f.ftserver

-- name: get_inherited_tables
SELECT
    c.oid::pg_catalog.regclass
FROM
    pg_catalog.pg_class c,
    pg_catalog.pg_inherits i
WHERE
    c.oid = i.inhparent
    AND i.inhrelid = :oid
ORDER BY inhseqno

-- name: get_child_tables
SELECT
    c.oid::pg_catalog.regclass
FROM
    pg_catalog.pg_class c,
    pg_catalog.pg_inherits i
WHERE
    c.oid = i.inhrelid
    AND i.inhparent = :oid
ORDER BY c.oid::pg_catalog.regclass::pg_catalog.text

-- name:  show_function_definition
-- docs: ("\\sf", "\\sf[+] FUNCNAME", "Show a function's definition.")
SELECT
    pg_catalog.pg_get_functiondef(
        SELECT
            coalesce(
                get_coordinates::pg_catalog.regprocedure::pg_catalog.oid,
                get_coordinates::pg_catalog.regproc::pg_catalog.oid)
        ) AS source


-- name:  list_foreign_tables
-- docs: ("\\dE", "\\dE[+] [pattern]", "List foreign tables.", aliases=())
SELECT
    n.nspname AS "schema",
    c.relname AS "name",
    :relkind AS "type",
    pg_catalog.pg_get_userbyid(c.relowner) AS "owner",
    pg_catalog.pg_size_pretty(pg_catalog.pg_table_size(c.oid)) AS "size",
    pg_catalog.obj_description(c.oid, 'pg_class') AS "description"
FROM
    pg_catalog.pg_class c
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE
    c.relkind IN ('f', '')
    AND n.nspname <> 'pg_catalog'
    AND n.nspname <> 'information_schema'
    AND n.nspname !~ '^pg_toast'
    AND pg_catalog.pg_table_is_visible(c.oid)
    AND c.relname OPERATOR (pg_catalog. ~) :pattern
ORDER BY 1, 2

-- name: relkind
CASE c.relkind
WHEN 'r' THEN 'table'
WHEN 'v' THEN 'view'
WHEN 'p' THEN 'partitioned table'
WHEN 'm' THEN 'materialized view'
WHEN 'i' THEN 'index'
WHEN 'I' THEN 'partitioned index'
WHEN 'S' THEN 'sequence'
WHEN 's' THEN 'special'
WHEN 'f' THEN 'foreign table'
WHEN 't' THEN 'toast table'
WHEN 'c' THEN 'composite type'
END

-- name: relpersistence
CASE c.relpersistence
WHEN 'p' THEN 'permanent'
WHEN 'u' THEN 'unlogged'
WHEN 't' THEN 'temporary'
END

-- name: reloftype
CASE
WHEN c.reloftype = 0
THEN ''
ELSE c.reloftype::pg_catalog.regtype::pg_catalog.text
END

-- name: defaclobjtype
CASE d.defaclobjtype
WHEN 'r' THEN 'table'
WHEN 'S' THEN 'sequence'
WHEN 'f' THEN 'function'
WHEN 'T' THEN 'type'
WHEN 'n' THEN 'schema'
END

-- name: provolatile
CASE p.provolatile
WHEN 'i' THEN 'immutable'
WHEN 's' THEN 'stable'
WHEN 'v' THEN 'volatile'
WHEN 'c' THEN 'volatile'
END

-- name: contype
CASE con.contype
WHEN 'c' THEN 'check constraint'
WHEN 'f' THEN 'foreign key constraint'
WHEN 'p' THEN 'primary key constraint'
WHEN 'u' THEN 'unique constraint'
WHEN 't' THEN 'constraint trigger'
WHEN 'x' THEN 'exclusion constraint'
END

-- name: ev_enabled
CASE ev_enabled
WHEN 'A' THEN 'always'
WHEN 'O' THEN 'origin'
WHEN 'R' THEN 'replica'
WHEN 'D' THEN 'disabled'
END
