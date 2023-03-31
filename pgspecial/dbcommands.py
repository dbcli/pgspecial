from __future__ import unicode_literals
import logging
import shlex
import subprocess
from collections import namedtuple

from psycopg.sql import SQL

from .main import special_command, RAW_QUERY

TableInfo = namedtuple(
    "TableInfo",
    [
        "checks",
        "relkind",
        "hasindex",
        "hasrules",
        "hastriggers",
        "hasoids",
        "tablespace",
        "reloptions",
        "reloftype",
        "relpersistence",
        "relispartition",
    ],
)

log = logging.getLogger(__name__)


@special_command("\\l", "\\l[+] [pattern]", "List databases.", aliases=("\\list",))
def list_databases(cur, pattern, verbose):
    params = {}
    query = SQL(
        """SELECT d.datname as "Name",
        pg_catalog.pg_get_userbyid(d.datdba) as "Owner",
        pg_catalog.pg_encoding_to_char(d.encoding) as "Encoding",
        d.datcollate as "Collate",
        d.datctype as "Ctype",
        pg_catalog.array_to_string(d.datacl, E'\n') AS "Access privileges"
        {verbose_fields}
        FROM pg_catalog.pg_database d
        {verbose_tables}
        {pattern_where}
        ORDER BY 1"""
    )
    if verbose:
        params["verbose_fields"] = SQL(
            ''',
            CASE WHEN pg_catalog.has_database_privilege(d.datname, 'CONNECT')
                    THEN pg_catalog.pg_size_pretty(pg_catalog.pg_database_size(d.datname))
                    ELSE 'No Access'
            END as "Size",
            t.spcname as "Tablespace",
            pg_catalog.shobj_description(d.oid, 'pg_database') as "Description"'''
        )
        params["verbose_tables"] = SQL(
            """JOIN pg_catalog.pg_tablespace t on d.dattablespace = t.oid"""
        )
    else:
        params["verbose_fields"] = SQL("")
        params["verbose_tables"] = SQL("")

    if pattern:
        _, schema = sql_name_pattern(pattern)
        params["pattern_where"] = SQL("""WHERE d.datname ~ {}""").format(schema)
    else:
        params["pattern_where"] = SQL("")
    formatted_query = query.format(**params)
    log.debug(formatted_query.as_string(cur))
    cur.execute(formatted_query)
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]
    else:
        return [(None, None, None, cur.statusmessage)]


@special_command("\\du", "\\du[+] [pattern]", "List roles.")
def list_roles(cur, pattern, verbose):
    """
    Returns (title, rows, headers, status)
    """

    params = {}

    if cur.connection.info.server_version > 90000:
        sql = SQL(
            """
            SELECT r.rolname,
                r.rolsuper,
                r.rolinherit,
                r.rolcreaterole,
                r.rolcreatedb,
                r.rolcanlogin,
                r.rolconnlimit,
                r.rolvaliduntil,
                ARRAY(SELECT b.rolname FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles b ON (m.roleid = b.oid) WHERE m.member = r.oid) as memberof,
                {verbose}
                r.rolreplication
            FROM pg_catalog.pg_roles r
                {pattern}
            ORDER BY 1
            """
        )
        if verbose:
            params["verbose"] = SQL(
                """pg_catalog.shobj_description(r.oid, 'pg_authid') AS description, """
            )
        else:
            params["verbose"] = SQL("")
    else:
        sql = SQL(
            """
            SELECT u.usename AS rolname,
                u.usesuper AS rolsuper,
                true AS rolinherit,
                false AS rolcreaterole,
                u.usecreatedb AS rolcreatedb,
                true AS rolcanlogin,
                -1 AS rolconnlimit,
                u.valuntil as rolvaliduntil,
                ARRAY(SELECT g.groname FROM pg_catalog.pg_group g WHERE u.usesysid = ANY(g.grolist)) as memberof
            FROM pg_catalog.pg_user u
            """
        )

    if pattern:
        _, schema = sql_name_pattern(pattern)
        params["pattern"] = SQL("WHERE r.rolname ~ {}").format(schema)
    else:
        params["pattern"] = SQL("")

    formatted_query = sql.format(**params)
    log.debug(formatted_query.as_string(cur))
    cur.execute(formatted_query)
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dp", "\\dp [pattern]", "List roles.", aliases=("\\z",))
def list_privileges(cur, pattern, verbose):
    """Returns (title, rows, headers, status)"""
    sql = SQL(
        """
        SELECT n.nspname as "Schema",
          c.relname as "Name",
          CASE c.relkind WHEN 'r' THEN 'table'
                         WHEN 'v' THEN 'view'
                         WHEN 'm' THEN 'materialized view'
                         WHEN 'S' THEN 'sequence'
                         WHEN 'f' THEN 'foreign table'
                         WHEN 'p' THEN 'partitioned table' END as "Type",
          pg_catalog.array_to_string(c.relacl, E'\n') AS "Access privileges",
          pg_catalog.array_to_string(ARRAY(
            SELECT attname || E':\n  ' || pg_catalog.array_to_string(attacl, E'\n  ')
            FROM pg_catalog.pg_attribute a
            WHERE attrelid = c.oid AND NOT attisdropped AND attacl IS NOT NULL
          ), E'\n') AS "Column privileges",
          pg_catalog.array_to_string(ARRAY(
            SELECT polname
            || CASE WHEN NOT polpermissive THEN
               E' (RESTRICTIVE)'
               ELSE '' END
            || CASE WHEN polcmd != '*' THEN
                   E' (' || polcmd::pg_catalog.text || E'):'
               ELSE E':'
               END
            || CASE WHEN polqual IS NOT NULL THEN
                   E'\n  (u): ' || pg_catalog.pg_get_expr(polqual, polrelid)
               ELSE E''
               END
            || CASE WHEN polwithcheck IS NOT NULL THEN
                   E'\n  (c): ' || pg_catalog.pg_get_expr(polwithcheck, polrelid)
               ELSE E''
               END    || CASE WHEN polroles <> '{0}' THEN
                   E'\n  to: ' || pg_catalog.array_to_string(
                       ARRAY(
                           SELECT rolname
                           FROM pg_catalog.pg_roles
                           WHERE oid = ANY (polroles)
                           ORDER BY 1
                       ), E', ')
               ELSE E''
               END
            FROM pg_catalog.pg_policy pol
            WHERE polrelid = c.oid), E'\n')
            AS "Policies"
        FROM pg_catalog.pg_class c
             LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    """
    )

    if pattern:
        schema, table = sql_name_pattern(pattern)
        if table:
            pattern = SQL(
                " AND c.relname OPERATOR(pg_catalog.~) {} COLLATE pg_catalog.default "
            ).format(table)
        if schema:
            pattern += SQL(
                " AND n.nspname OPERATOR(pg_catalog.~) {} COLLATE pg_catalog.default "
            ).format(schema)
    else:
        pattern = SQL(" AND pg_catalog.pg_table_is_visible(c.oid) ")

    where_clause = SQL(
        """
        WHERE c.relkind IN ('r','v','m','S','f','p')
          {pattern}
          AND n.nspname !~ '^pg_'
    """
    ).format(pattern=pattern)

    sql += where_clause + SQL(" ORDER BY 1, 2 ")

    log.debug(sql.as_string(cur))
    cur.execute(sql)
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\ddp", "\\ddp [pattern]", "Lists default access privilege settings.")
def list_default_privileges(cur, pattern, verbose):
    """Returns (title, rows, headers, status)"""
    sql = SQL(
        """
    SELECT pg_catalog.pg_get_userbyid(d.defaclrole) AS "Owner",
    n.nspname AS "Schema",
    CASE d.defaclobjtype WHEN 'r' THEN 'table'
                         WHEN 'S' THEN 'sequence'
                         WHEN 'f' THEN 'function'
                         WHEN 'T' THEN 'type'
                         WHEN 'n' THEN 'schema' END AS "Type",
    pg_catalog.array_to_string(d.defaclacl, E'\n') AS "Access privileges"
    FROM pg_catalog.pg_default_acl d
        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = d.defaclnamespace
        {where_clause}
    ORDER BY 1, 2, 3
    """
    )

    params = {}
    if pattern:
        params["where_clause"] = SQL(
            """
            WHERE (n.nspname OPERATOR(pg_catalog.~) {pattern} COLLATE pg_catalog.default
            OR pg_catalog.pg_get_userbyid(d.defaclrole) OPERATOR(pg_catalog.~) {pattern} COLLATE pg_catalog.default)
        """
        ).format(pattern=f"^({pattern})$")
    else:
        params["where_clause"] = SQL("")

    log.debug(sql.format(**params).as_string(cur))
    cur.execute(sql.format(**params))
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\db", "\\db[+] [pattern]", "List tablespaces.")
def list_tablespaces(cur, pattern, **_):
    """
    Returns (title, rows, headers, status)
    """

    params = {}
    cur.execute(
        "SELECT EXISTS(SELECT * FROM pg_proc WHERE proname = 'pg_tablespace_location')"
    )
    (is_location,) = cur.fetchone()

    sql = SQL(
        """SELECT n.spcname AS "Name", pg_catalog.pg_get_userbyid(n.spcowner) AS "Owner",
                {location} AS "Location" FROM pg_catalog.pg_tablespace n
                {pattern}
                ORDER BY 1
              """
    )

    if is_location:
        params["location"] = SQL(" pg_catalog.pg_tablespace_location(n.oid)")
    else:
        params["location"] = SQL(" 'Not supported'")

    if pattern:
        _, tbsp = sql_name_pattern(pattern)
        params["pattern"] = SQL(" WHERE n.spcname ~ {}").format(tbsp)
    else:
        params["pattern"] = SQL("")

    formatted_query = sql.format(**params)
    log.debug(formatted_query.as_string(cur))
    cur.execute(formatted_query)

    headers = [x.name for x in cur.description] if cur.description else None
    return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dn", "\\dn[+] [pattern]", "List schemas.")
def list_schemas(cur, pattern, verbose):
    """
    Returns (title, rows, headers, status)
    """

    params = {}
    sql = SQL(
        """SELECT n.nspname AS "Name", pg_catalog.pg_get_userbyid(n.nspowner) AS "Owner"
                {verbose}
              FROM pg_catalog.pg_namespace n WHERE n.nspname
                {pattern}
              ORDER BY 1
              """
    )

    if verbose:
        params["verbose"] = SQL(
            ''', pg_catalog.array_to_string(n.nspacl, E'\\n') AS "Access privileges", pg_catalog.obj_description(n.oid, 'pg_namespace') AS "Description"'''
        )
    else:
        params["verbose"] = SQL("")

    if pattern:
        _, schema = sql_name_pattern(pattern)
        params["pattern"] = SQL("~ {}").format(schema)
    else:
        params["pattern"] = SQL("!~ '^pg_' AND n.nspname <> 'information_schema'")

    formatted_query = sql.format(**params)
    log.debug(formatted_query.as_string(cur))
    cur.execute(formatted_query)
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


# https://github.com/postgres/postgres/blob/master/src/bin/psql/describe.c#L5471-L5638
@special_command("\\dx", "\\dx[+] [pattern]", "List extensions.")
def list_extensions(cur, pattern, verbose):
    def _find_extensions(cur, pattern):
        sql = SQL(
            """
            SELECT e.extname, e.oid FROM pg_catalog.pg_extension e
            {pattern}
            ORDER BY 1, 2;
        """
        )

        params = {}
        if pattern:
            _, schema = sql_name_pattern(pattern)
            params["pattern"] += SQL("WHERE e.extname ~ {}").format(schema)
        else:
            params["pattern"] = SQL("")

        formatted_query = sql.format(**params)
        log.debug(formatted_query.as_string(cur))
        cur.execute(formatted_query)
        return cur.fetchall()

    def _describe_extension(cur, oid):
        sql = SQL(
            """
            SELECT  pg_catalog.pg_describe_object(classid, objid, 0)
                    AS "Object Description"
            FROM    pg_catalog.pg_depend
            WHERE   refclassid = 'pg_catalog.pg_extension'::pg_catalog.regclass
                    AND refobjid = {}
                    AND deptype = 'e'
            ORDER BY 1"""
        ).format(oid)
        log.debug(sql.as_string(cur))
        cur.execute(sql)

        headers = [x.name for x in cur.description]
        return cur, headers, cur.statusmessage

    if cur.connection.info.server_version < 90100:
        not_supported = "Server versions below 9.1 do not support extensions."
        cur, headers = [], []
        yield None, cur, None, not_supported
        return

    if verbose:
        extensions = _find_extensions(cur, pattern)

        if extensions:
            for ext_name, oid in extensions:
                title = f'''\nObjects in extension "{ext_name}"'''
                cur, headers, status = _describe_extension(cur, oid)
                yield title, cur, headers, status
        else:
            yield None, None, None, f"""Did not find any extension named "{pattern}"."""
        return

    sql = SQL(
        """
      SELECT e.extname AS "Name",
             e.extversion AS "Version",
             n.nspname AS "Schema",
             c.description AS "Description"
      FROM pg_catalog.pg_extension e
           LEFT JOIN pg_catalog.pg_namespace n
             ON n.oid = e.extnamespace
           LEFT JOIN pg_catalog.pg_description c
             ON c.objoid = e.oid
                AND c.classoid = 'pg_catalog.pg_extension'::pg_catalog.regclass
        {where_clause}
       ORDER BY 1, 2
      """
    )

    params = {}
    if pattern:
        _, schema = sql_name_pattern(pattern)
        params["where_clause"] = SQL("WHERE e.extname ~ {}").format(schema)
    else:
        params["where_clause"] = SQL("")

    formatted_query = sql.format(**params)
    log.debug(formatted_query.as_string(cur))
    cur.execute(formatted_query)
    if cur.description:
        headers = [x.name for x in cur.description]
        yield None, cur, headers, cur.statusmessage


def list_objects(cur, pattern, verbose, relkinds):
    """
    Returns (title, rows, header, status)

    This method is used by list_tables, list_views, list_materialized views
    and list_indexes

    relkinds is a list of strings to filter pg_class.relkind

    """
    schema_pattern, table_pattern = sql_name_pattern(pattern)

    params = {"relkind": relkinds}
    if verbose:
        params["verbose_columns"] = SQL(
            """
            ,pg_catalog.pg_size_pretty(pg_catalog.pg_table_size(c.oid)) as "Size",
            pg_catalog.obj_description(c.oid, 'pg_class') as "Description" """
        )
    else:
        params["verbose_columns"] = SQL("")

    sql = SQL(
        """SELECT n.nspname as "Schema",
                    c.relname as "Name",
                    CASE c.relkind
                      WHEN 'r' THEN 'table' WHEN 'v' THEN 'view'
                      WHEN 'p' THEN 'partitioned table'
                      WHEN 'm' THEN 'materialized view' WHEN 'i' THEN 'index'
                      WHEN 'S' THEN 'sequence' WHEN 's' THEN 'special'
                      WHEN 'f' THEN 'foreign table' END
                    as "Type",
                    pg_catalog.pg_get_userbyid(c.relowner) as "Owner"
                    {verbose_columns}
            FROM    pg_catalog.pg_class c
                    LEFT JOIN pg_catalog.pg_namespace n
                      ON n.oid = c.relnamespace
            WHERE   c.relkind = ANY({relkind})
                {schema_pattern}
                {table_pattern}
            ORDER BY 1, 2
        """
    )

    if schema_pattern:
        params["schema_pattern"] = SQL(" AND n.nspname ~ {}").format(schema_pattern)
    else:
        params["schema_pattern"] = SQL(
            """
            AND n.nspname <> 'pg_catalog'
            AND n.nspname <> 'information_schema'
            AND n.nspname !~ '^pg_toast'
            AND pg_catalog.pg_table_is_visible(c.oid) """
        )

    if table_pattern:
        params["table_pattern"] = SQL(" AND c.relname ~ {}").format(table_pattern)
    else:
        params["table_pattern"] = SQL("")

    formatted_query = sql.format(**params)
    log.debug(formatted_query.as_string(cur))
    cur.execute(formatted_query)

    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dt", "\\dt[+] [pattern]", "List tables.")
def list_tables(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ["r", "p", ""])


@special_command("\\dv", "\\dv[+] [pattern]", "List views.")
def list_views(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ["v", "s", ""])


@special_command("\\dm", "\\dm[+] [pattern]", "List materialized views.")
def list_materialized_views(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ["m", "s", ""])


@special_command("\\ds", "\\ds[+] [pattern]", "List sequences.")
def list_sequences(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ["S", "s", ""])


@special_command("\\di", "\\di[+] [pattern]", "List indexes.")
def list_indexes(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ["i", "s", ""])


@special_command("\\df", "\\df[+] [pattern]", "List functions.")
def list_functions(cur, pattern, verbose):
    if verbose:
        verbose_columns = """
            ,CASE
                 WHEN p.provolatile = 'i' THEN 'immutable'
                 WHEN p.provolatile = 's' THEN 'stable'
                 WHEN p.provolatile = 'v' THEN 'volatile'
            END as "Volatility",
            pg_catalog.pg_get_userbyid(p.proowner) as "Owner",
          l.lanname as "Language",
          p.prosrc as "Source code",
          pg_catalog.obj_description(p.oid, 'pg_proc') as "Description" """

        verbose_table = """ LEFT JOIN pg_catalog.pg_language l
                                ON l.oid = p.prolang"""
    else:
        verbose_columns = verbose_table = ""

    if cur.connection.info.server_version >= 110000:
        sql = (
            """
            SELECT  n.nspname as "Schema",
                    p.proname as "Name",
                    pg_catalog.pg_get_function_result(p.oid)
                      as "Result data type",
                    pg_catalog.pg_get_function_arguments(p.oid)
                      as "Argument data types",
                     CASE
                        WHEN p.prokind = 'a' THEN 'agg'
                        WHEN p.prokind = 'w' THEN 'window'
                        WHEN p.prorettype = 'pg_catalog.trigger'::pg_catalog.regtype
                            THEN 'trigger'
                        ELSE 'normal'
                    END as "Type" """
            + verbose_columns
            + """
            FROM    pg_catalog.pg_proc p
                    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                            """
            + verbose_table
            + """
            WHERE  """
        )
    elif cur.connection.info.server_version > 90000:
        sql = (
            """
            SELECT  n.nspname as "Schema",
                    p.proname as "Name",
                    pg_catalog.pg_get_function_result(p.oid)
                      as "Result data type",
                    pg_catalog.pg_get_function_arguments(p.oid)
                      as "Argument data types",
                     CASE
                        WHEN p.proisagg THEN 'agg'
                        WHEN p.proiswindow THEN 'window'
                        WHEN p.prorettype = 'pg_catalog.trigger'::pg_catalog.regtype
                            THEN 'trigger'
                        ELSE 'normal'
                    END as "Type" """
            + verbose_columns
            + """
            FROM    pg_catalog.pg_proc p
                    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                            """
            + verbose_table
            + """
            WHERE  """
        )
    else:
        sql = (
            """
            SELECT  n.nspname as "Schema",
                    p.proname as "Name",
                    pg_catalog.format_type(p.prorettype, NULL) as "Result data type",
                    pg_catalog.oidvectortypes(p.proargtypes) as "Argument data types",
                     CASE
                        WHEN p.proisagg THEN 'agg'
                        WHEN p.prorettype = 'pg_catalog.trigger'::pg_catalog.regtype THEN 'trigger'
                        ELSE 'normal'
                    END as "Type" """
            + verbose_columns
            + """
            FROM    pg_catalog.pg_proc p
                    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                            """
            + verbose_table
            + """
            WHERE  """
        )

    schema_pattern, func_pattern = sql_name_pattern(pattern)
    params = {}

    if schema_pattern:
        sql += " n.nspname ~ %(nspname)s "
        params["nspname"] = schema_pattern
    else:
        sql += " pg_catalog.pg_function_is_visible(p.oid) "

    if func_pattern:
        sql += " AND p.proname ~ %(proname)s "
        params["proname"] = func_pattern

    if not (schema_pattern or func_pattern):
        sql += """ AND n.nspname <> 'pg_catalog'
                   AND n.nspname <> 'information_schema' """

    sql += " ORDER BY 1, 2, 4"

    log.debug("%s, %s", sql, params)
    cur.execute(sql, params)

    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dT", "\\dT[S+] [pattern]", "List data types")
def list_datatypes(cur, pattern, verbose):
    sql = """SELECT n.nspname as "Schema",
                    pg_catalog.format_type(t.oid, NULL) AS "Name", """

    if verbose:
        sql += r''' t.typname AS "Internal name",
                    CASE
                        WHEN t.typrelid != 0
                            THEN CAST('tuple' AS pg_catalog.text)
                        WHEN t.typlen < 0
                            THEN CAST('var' AS pg_catalog.text)
                        ELSE CAST(t.typlen AS pg_catalog.text)
                    END AS "Size",
                    pg_catalog.array_to_string(
                        ARRAY(
                              SELECT e.enumlabel
                              FROM pg_catalog.pg_enum e
                              WHERE e.enumtypid = t.oid
                              ORDER BY e.enumsortorder
                          ), E'\n') AS "Elements",
                    pg_catalog.array_to_string(t.typacl, E'\n')
                        AS "Access privileges",
                    pg_catalog.obj_description(t.oid, 'pg_type')
                        AS "Description"'''
    else:
        sql += """  pg_catalog.obj_description(t.oid, 'pg_type')
                        as "Description" """

    if cur.connection.info.server_version > 90000:
        sql += """  FROM    pg_catalog.pg_type t
                            LEFT JOIN pg_catalog.pg_namespace n
                              ON n.oid = t.typnamespace
                    WHERE   (t.typrelid = 0 OR
                              ( SELECT c.relkind = 'c'
                                FROM pg_catalog.pg_class c
                                WHERE c.oid = t.typrelid))
                            AND NOT EXISTS(
                                SELECT 1
                                FROM pg_catalog.pg_type el
                                WHERE el.oid = t.typelem
                                      AND el.typarray = t.oid) """
    else:
        sql += """  FROM    pg_catalog.pg_type t
                            LEFT JOIN pg_catalog.pg_namespace n
                              ON n.oid = t.typnamespace
                    WHERE   (t.typrelid = 0 OR
                              ( SELECT c.relkind = 'c'
                                FROM pg_catalog.pg_class c
                                WHERE c.oid = t.typrelid)) """

    schema_pattern, type_pattern = sql_name_pattern(pattern)
    params = {}

    if schema_pattern:
        sql += " AND n.nspname ~ %(nspname)s "
        params["nspname"] = schema_pattern
    else:
        sql += " AND pg_catalog.pg_type_is_visible(t.oid) "

    if type_pattern:
        sql += """ AND (t.typname ~ %(typname)s
                        OR pg_catalog.format_type(t.oid, NULL) ~ %(typname)s) """
        params["typname"] = type_pattern

    if not (schema_pattern or type_pattern):
        sql += """ AND n.nspname <> 'pg_catalog'
                   AND n.nspname <> 'information_schema' """

    sql += " ORDER BY 1, 2"
    log.debug("%s, %s", sql, params)
    cur.execute(sql, params)
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dD", "\\dD[+] [pattern]", "List or describe domains.")
def list_domains(cur, pattern, verbose):
    if verbose:
        extra_cols = r''',
               pg_catalog.array_to_string(t.typacl, E'\n') AS "Access privileges",
               d.description as "Description"'''
        extra_joins = """
           LEFT JOIN pg_catalog.pg_description d ON d.classoid = t.tableoid
                                                AND d.objoid = t.oid AND d.objsubid = 0"""
    else:
        extra_cols = extra_joins = ""

    sql = f"""\
        SELECT n.nspname AS "Schema",
               t.typname AS "Name",
               pg_catalog.format_type(t.typbasetype, t.typtypmod) AS "Type",
               pg_catalog.ltrim((COALESCE((SELECT (' collate ' || c.collname)
                                           FROM pg_catalog.pg_collation AS c,
                                                pg_catalog.pg_type AS bt
                                           WHERE c.oid = t.typcollation
                                             AND bt.oid = t.typbasetype
                                             AND t.typcollation <> bt.typcollation) , '')
                                || CASE
                                     WHEN t.typnotnull
                                       THEN ' not null'
                                     ELSE ''
                                   END) || CASE
                                             WHEN t.typdefault IS NOT NULL
                                               THEN(' default ' || t.typdefault)
                                             ELSE ''
                                           END) AS "Modifier",
               pg_catalog.array_to_string(ARRAY(
                 SELECT pg_catalog.pg_get_constraintdef(r.oid, TRUE)
                 FROM pg_catalog.pg_constraint AS r
                 WHERE t.oid = r.contypid), ' ') AS "Check"{extra_cols}
        FROM pg_catalog.pg_type AS t
           LEFT JOIN pg_catalog.pg_namespace AS n ON n.oid = t.typnamespace{extra_joins}
        WHERE t.typtype = 'd' """

    schema_pattern, name_pattern = sql_name_pattern(pattern)
    params = {}
    if schema_pattern or name_pattern:
        if schema_pattern:
            sql += " AND n.nspname ~ %(nspname)s"
            params["nspname"] = schema_pattern
        if name_pattern:
            sql += " AND t.typname ~ %(typname)s"
            params["typname"] = name_pattern
    else:
        sql += """
          AND (n.nspname <> 'pg_catalog')
          AND (n.nspname <> 'information_schema')
          AND pg_catalog.pg_type_is_visible(t.oid)"""

    sql += " ORDER BY 1, 2"
    log.debug("%s, %s", sql, params)
    cur.execute(sql, params)
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dF", "\\dF[+] [pattern]", "List text search configurations.")
def list_text_search_configurations(cur, pattern, verbose):
    def _find_text_search_configs(cur, pattern):
        sql = """
            SELECT c.oid,
                 c.cfgname,
                 n.nspname,
                 p.prsname,
                 np.nspname AS pnspname
            FROM pg_catalog.pg_ts_config c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.cfgnamespace,
                                                 pg_catalog.pg_ts_parser p
            LEFT JOIN pg_catalog.pg_namespace np ON np.oid = p.prsnamespace
            WHERE p.oid = c.cfgparser
        """

        params = {}
        if pattern:
            _, schema = sql_name_pattern(pattern)
            sql += "AND c.cfgname ~ %(cfgname)s"
            params["cfgname"] = schema

        sql += " ORDER BY 1, 2;"
        log.debug("%s, %s", sql, params)
        cur.execute(sql, params)
        return cur.fetchall()

    def _fetch_oid_details(cur, oid):
        params = {"oid": oid}
        sql = """
            SELECT
              (SELECT t.alias
               FROM pg_catalog.ts_token_type(c.cfgparser) AS t
               WHERE t.tokid = m.maptokentype ) AS "Token",
                   pg_catalog.btrim(ARRAY
                                      (SELECT mm.mapdict::pg_catalog.regdictionary
                                       FROM pg_catalog.pg_ts_config_map AS mm
                                       WHERE mm.mapcfg = m.mapcfg
                                         AND mm.maptokentype = m.maptokentype
                                       ORDER BY mapcfg, maptokentype, mapseqno) :: pg_catalog.text, '{}') AS "Dictionaries"
            FROM pg_catalog.pg_ts_config AS c,
                 pg_catalog.pg_ts_config_map AS m
            WHERE c.oid = %(oid)s
              AND m.mapcfg = c.oid
            GROUP BY m.mapcfg,
                     m.maptokentype,
                     c.cfgparser
            ORDER BY 1;
        """

        log.debug("%s, %s", sql, params)
        cur.execute(sql, params)

        headers = [x.name for x in cur.description]
        return cur, headers, cur.statusmessage

    if cur.connection.info.server_version < 80300:
        not_supported = "Server versions below 8.3 do not support full text search."
        cur, headers = [], []
        yield None, cur, None, not_supported
        return

    if verbose:
        configs = _find_text_search_configs(cur, pattern)

        if configs:
            for oid, cfgname, nspname, prsname, pnspname in configs:
                extension = f'''\nText search configuration "{nspname}.{cfgname}"'''
                parser = f'''\nParser: "{pnspname}.{prsname}"'''
                title = extension + parser
                cur, headers, status = _fetch_oid_details(cur, oid)
                yield title, cur, headers, status
        else:
            yield None, None, None, 'Did not find any results for pattern "{}".'.format(
                pattern
            )
        return

    sql = """
        SELECT n.nspname AS "Schema",
               c.cfgname AS "Name",
               pg_catalog.obj_description(c.oid, 'pg_ts_config') AS "Description"
        FROM pg_catalog.pg_ts_config c
        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.cfgnamespace
        """

    params = {}
    if pattern:
        _, schema = sql_name_pattern(pattern)
        sql += "WHERE c.cfgname ~ %(cfgname)s"
        params["cfgname"] = schema

    sql += " ORDER BY 1, 2"
    log.debug("%s, %s", sql, params)
    cur.execute(sql, params)
    if cur.description:
        headers = [x.name for x in cur.description]
        yield None, cur, headers, cur.statusmessage


@special_command(
    "describe", "DESCRIBE [pattern]", "", hidden=True, case_sensitive=False
)
@special_command(
    "\\d", "\\d[+] [pattern]", "List or describe tables, views and sequences."
)
def describe_table_details(cur, pattern, verbose):
    """
    Returns (title, rows, headers, status)
    """

    # This is a simple \d[+] command. No table name to follow.
    if not pattern:
        return list_objects(cur, pattern, verbose, ["r", "p", "v", "m", "S", "f", ""])

    # This is a \d <tablename> command. A royal pain in the ass.
    schema, relname = sql_name_pattern(pattern)
    where = []
    params = {}

    if schema:
        where.append("n.nspname ~ %(nspname)s")
        params["nspname"] = schema
    else:
        where.append("pg_catalog.pg_table_is_visible(c.oid)")

    if relname:
        where.append("c.relname OPERATOR(pg_catalog.~) %(relname)s")
        params["relname"] = relname

    sql = (
        """SELECT c.oid, n.nspname, c.relname
             FROM pg_catalog.pg_class c
             LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
             """
        + ("WHERE " + " AND ".join(where) if where else "")
        + """
             ORDER BY 2,3"""
    )
    # Execute the sql, get the results and call describe_one_table_details on each table.

    log.debug("%s, %s", sql, params)
    cur.execute(sql, params)
    if not (cur.rowcount > 0):
        return [(None, None, None, f"Did not find any relation named {pattern}.")]

    results = []
    for oid, nspname, relname in cur.fetchall():
        results.append(describe_one_table_details(cur, nspname, relname, oid, verbose))

    return results


def describe_one_table_details(cur, schema_name, relation_name, oid, verbose):
    if verbose and cur.connection.info.server_version >= 80200:
        suffix = """pg_catalog.array_to_string(c.reloptions || array(select
        'toast.' || x from pg_catalog.unnest(tc.reloptions) x), ', ')"""
    else:
        suffix = "''"

    if cur.connection.info.server_version >= 120000:
        relhasoids = "false as relhasoids"
    else:
        relhasoids = "c.relhasoids"

    if cur.connection.info.server_version >= 100000:
        sql = f"""SELECT c.relchecks, c.relkind, c.relhasindex,
                    c.relhasrules, c.relhastriggers, {relhasoids},
                    {suffix},
                    c.reltablespace,
                    CASE WHEN c.reloftype = 0 THEN ''
                        ELSE c.reloftype::pg_catalog.regtype::pg_catalog.text
                    END,
                    c.relpersistence,
                    c.relispartition
                 FROM pg_catalog.pg_class c
                 LEFT JOIN pg_catalog.pg_class tc ON (c.reltoastrelid = tc.oid)
                 WHERE c.oid = '{oid}'"""

    elif cur.connection.info.server_version > 90000:
        sql = f"""SELECT c.relchecks, c.relkind, c.relhasindex,
                    c.relhasrules, c.relhastriggers, c.relhasoids,
                    {suffix},
                    c.reltablespace,
                    CASE WHEN c.reloftype = 0 THEN ''
                        ELSE c.reloftype::pg_catalog.regtype::pg_catalog.text
                    END,
                    c.relpersistence,
                    false as relispartition
                 FROM pg_catalog.pg_class c
                 LEFT JOIN pg_catalog.pg_class tc ON (c.reltoastrelid = tc.oid)
                 WHERE c.oid = '{oid}'"""

    elif cur.connection.info.server_version >= 80400:
        sql = f"""SELECT c.relchecks,
                    c.relkind,
                    c.relhasindex,
                    c.relhasrules,
                    c.relhastriggers,
                    c.relhasoids,
                    {suffix},
                    c.reltablespace,
                    0 AS reloftype,
                    'p' AS relpersistence,
                    false as relispartition
                 FROM pg_catalog.pg_class c
                 LEFT JOIN pg_catalog.pg_class tc ON (c.reltoastrelid = tc.oid)
                 WHERE c.oid = '{oid}'"""

    else:
        sql = f"""SELECT c.relchecks,
                    c.relkind,
                    c.relhasindex,
                    c.relhasrules,
                    c.reltriggers > 0 AS relhastriggers,
                    c.relhasoids,
                    {suffix},
                    c.reltablespace,
                    0 AS reloftype,
                    'p' AS relpersistence,
                    false as relispartition
                 FROM pg_catalog.pg_class c
                 LEFT JOIN pg_catalog.pg_class tc ON (c.reltoastrelid = tc.oid)
                 WHERE c.oid = '{oid}'"""

    # Create a namedtuple called tableinfo and match what's in describe.c

    log.debug(sql)
    cur.execute(sql)
    if cur.rowcount > 0:
        tableinfo = TableInfo._make(cur.fetchone())
    else:
        return None, None, None, f"Did not find any relation with OID {oid}."

    # If it's a seq, fetch it's value and store it for later.
    if tableinfo.relkind == "S":
        # Do stuff here.
        sql = f'''SELECT * FROM "{schema_name}"."{relation_name}"'''
        log.debug(sql)
        cur.execute(sql)
        if not (cur.rowcount > 0):
            return None, None, None, "Something went wrong."

        seq_values = cur.fetchone()

    # Get column info
    cols = 0
    att_cols = {}
    sql = """SELECT a.attname,
    pg_catalog.format_type(a.atttypid, a.atttypmod)
    , (SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid, true) for 128)
                     FROM pg_catalog.pg_attrdef d
                     WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum AND a.atthasdef)
                    , a.attnotnull"""
    att_cols["attname"] = cols
    cols += 1
    att_cols["atttype"] = cols
    cols += 1
    att_cols["attrdef"] = cols
    cols += 1
    att_cols["attnotnull"] = cols
    cols += 1
    if cur.connection.info.server_version >= 90100:
        sql += """,\n(SELECT c.collname FROM pg_catalog.pg_collation c, pg_catalog.pg_type t
                    WHERE c.oid = a.attcollation
                    AND t.oid = a.atttypid AND a.attcollation <> t.typcollation) AS attcollation"""
    else:
        sql += ",\n  NULL AS attcollation"
    att_cols["attcollation"] = cols
    cols += 1
    if cur.connection.info.server_version >= 100000:
        sql += ",\n  a.attidentity"
    else:
        sql += ",\n  ''::pg_catalog.char AS attidentity"
    att_cols["attidentity"] = cols
    cols += 1
    if cur.connection.info.server_version >= 120000:
        sql += ",\n  a.attgenerated"
    else:
        sql += ",\n  ''::pg_catalog.char AS attgenerated"
    att_cols["attgenerated"] = cols
    cols += 1
    # index, or partitioned index
    if tableinfo.relkind == "i" or tableinfo.relkind == "I":
        if cur.connection.info.server_version >= 110000:
            sql += (
                f",\n CASE WHEN a.attnum <= (SELECT i.indnkeyatts FROM pg_catalog.pg_index i "
                "WHERE i.indexrelid = '{oid}') THEN 'yes' ELSE 'no' END AS is_key"
            )
            att_cols["indexkey"] = cols
            cols += 1
        sql += ",\n pg_catalog.pg_get_indexdef(a.attrelid, a.attnum, TRUE) AS indexdef"
    else:
        sql += """,\n NULL AS indexdef"""
    att_cols["indexdef"] = cols
    cols += 1
    if tableinfo.relkind == "f" and cur.connection.info.server_version >= 90200:
        sql += """, CASE WHEN attfdwoptions IS NULL THEN '' ELSE '(' ||
                array_to_string(ARRAY(SELECT quote_ident(option_name) ||  ' '
                || quote_literal(option_value)  FROM
                pg_options_to_table(attfdwoptions)), ', ') || ')' END AS attfdwoptions"""
    else:
        sql += """, NULL AS attfdwoptions"""
    att_cols["attfdwoptions"] = cols
    cols += 1
    if verbose:
        sql += """, a.attstorage"""
        att_cols["attstorage"] = cols
        cols += 1
        if (
            tableinfo.relkind == "r"
            or tableinfo.relkind == "i"
            or tableinfo.relkind == "I"
            or tableinfo.relkind == "m"
            or tableinfo.relkind == "f"
            or tableinfo.relkind == "p"
        ):
            sql += (
                ",\n  CASE WHEN a.attstattarget=-1 THEN "
                "NULL ELSE a.attstattarget END AS attstattarget"
            )
            att_cols["attstattarget"] = cols
            cols += 1
        if (
            tableinfo.relkind == "r"
            or tableinfo.relkind == "v"
            or tableinfo.relkind == "m"
            or tableinfo.relkind == "f"
            or tableinfo.relkind == "p"
            or tableinfo.relkind == "c"
        ):
            sql += ",\n  pg_catalog.col_description(a.attrelid, a.attnum)"
            att_cols["attdescr"] = cols
            cols += 1

    sql += f""" FROM pg_catalog.pg_attribute a WHERE a.attrelid = '{oid}' AND
    a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum; """

    log.debug(sql)
    cur.execute(sql)
    res = cur.fetchall()

    # Set the column names.
    headers = ["Column", "Type"]

    show_modifiers = False
    if (
        tableinfo.relkind == "r"
        or tableinfo.relkind == "p"
        or tableinfo.relkind == "v"
        or tableinfo.relkind == "m"
        or tableinfo.relkind == "f"
        or tableinfo.relkind == "c"
    ):
        headers.append("Modifiers")
        show_modifiers = True

    if tableinfo.relkind == "S":
        headers.append("Value")

    if tableinfo.relkind == "i":
        headers.append("Definition")

    if tableinfo.relkind == "f":
        headers.append("FDW Options")

    if verbose:
        headers.append("Storage")
        if (
            tableinfo.relkind == "r"
            or tableinfo.relkind == "m"
            or tableinfo.relkind == "f"
        ):
            headers.append("Stats target")
        #  Column comments, if the relkind supports this feature. */
        if (
            tableinfo.relkind == "r"
            or tableinfo.relkind == "v"
            or tableinfo.relkind == "m"
            or tableinfo.relkind == "c"
            or tableinfo.relkind == "f"
        ):
            headers.append("Description")

    view_def = ""
    # /* Check if table is a view or materialized view */
    if (tableinfo.relkind == "v" or tableinfo.relkind == "m") and verbose:
        sql = f"""SELECT pg_catalog.pg_get_viewdef('{oid}'::pg_catalog.oid, true)"""
        log.debug(sql)
        cur.execute(sql)
        if cur.rowcount > 0:
            (view_def,) = cur.fetchone()

    # Prepare the cells of the table to print.
    cells = []
    for i, row in enumerate(res):
        cell = []
        cell.append(row[att_cols["attname"]])  # Column
        cell.append(row[att_cols["atttype"]])  # Type

        if show_modifiers:
            modifier = ""
            if row[att_cols["attcollation"]]:
                modifier += f" collate {row[att_cols['attcollation']]}"
            if row[att_cols["attnotnull"]]:
                modifier += " not null"
            if row[att_cols["attrdef"]]:
                modifier += f" default {row[att_cols['attrdef']]}"
            if row[att_cols["attidentity"]] == "a":
                modifier += " generated always as identity"
            elif row[att_cols["attidentity"]] == "d":
                modifier += " generated by default as identity"
            elif row[att_cols["attgenerated"]] == "s":
                modifier += f" generated always as ({row[att_cols['attrdef']]}) stored"
            cell.append(modifier)

        # Sequence
        if tableinfo.relkind == "S":
            cell.append(seq_values[i])

        # Index column
        if tableinfo.relkind == "i":
            cell.append(row[att_cols["indexdef"]])

        # /* FDW options for foreign table column, only for 9.2 or later */
        if tableinfo.relkind == "f":
            cell.append(att_cols["attfdwoptions"])

        if verbose:
            storage = row[att_cols["attstorage"]]

            if storage[0] == "p":
                cell.append("plain")
            elif storage[0] == "m":
                cell.append("main")
            elif storage[0] == "x":
                cell.append("extended")
            elif storage[0] == "e":
                cell.append("external")
            else:
                cell.append("???")

            if (
                tableinfo.relkind == "r"
                or tableinfo.relkind == "m"
                or tableinfo.relkind == "f"
            ):
                cell.append(row[att_cols["attstattarget"]])

            #  /* Column comments, if the relkind supports this feature. */
            if (
                tableinfo.relkind == "r"
                or tableinfo.relkind == "v"
                or tableinfo.relkind == "m"
                or tableinfo.relkind == "c"
                or tableinfo.relkind == "f"
            ):
                cell.append(row[att_cols["attdescr"]])
        cells.append(cell)

    # Make Footers

    status = []
    if tableinfo.relkind == "i":
        # /* Footer information about an index */

        if cur.connection.info.server_version > 90000:
            sql = f"""SELECT i.indisunique,
                        i.indisprimary,
                        i.indisclustered,
                        i.indisvalid,
                        (NOT i.indimmediate) AND EXISTS (
                            SELECT 1
                            FROM pg_catalog.pg_constraint
                            WHERE conrelid = i.indrelid
                                AND conindid = i.indexrelid
                                AND contype IN ('p','u','x')
                                AND condeferrable
                        ) AS condeferrable,
                        (NOT i.indimmediate) AND EXISTS (
                            SELECT 1
                            FROM pg_catalog.pg_constraint
                            WHERE conrelid = i.indrelid
                                AND conindid = i.indexrelid
                                AND contype IN ('p','u','x')
                                AND condeferred
                        ) AS condeferred,
                        a.amname,
                        c2.relname,
                        pg_catalog.pg_get_expr(i.indpred, i.indrelid, true)
                        FROM pg_catalog.pg_index i,
                            pg_catalog.pg_class c,
                            pg_catalog.pg_class c2,
                            pg_catalog.pg_am a
                        WHERE i.indexrelid = c.oid
                            AND c.oid = '{oid}'
                            AND c.relam = a.oid
                            AND i.indrelid = c2.oid;
                """
        else:
            sql = f"""SELECT i.indisunique,
                        i.indisprimary,
                        i.indisclustered,
                        't' AS indisvalid,
                        'f' AS condeferrable,
                        'f' AS condeferred,
                        a.amname,
                        c2.relname,
                        pg_catalog.pg_get_expr(i.indpred, i.indrelid, true)
                        FROM pg_catalog.pg_index i,
                            pg_catalog.pg_class c,
                            pg_catalog.pg_class c2,
                            pg_catalog.pg_am a
                        WHERE i.indexrelid = c.oid
                            AND c.oid = '{oid}'
                            AND c.relam = a.oid
                            AND i.indrelid = c2.oid;
                """

        log.debug(sql)
        cur.execute(sql)

        (
            indisunique,
            indisprimary,
            indisclustered,
            indisvalid,
            deferrable,
            deferred,
            indamname,
            indtable,
            indpred,
        ) = cur.fetchone()

        if indisprimary:
            status.append("primary key, ")
        elif indisunique:
            status.append("unique, ")
        status.append(f"{indamname}, ")

        # /* we assume here that index and table are in same schema */
        status.append(f'''for table "{schema_name}.{indtable}"''')

        if indpred:
            status.append(f", predicate ({indpred})")

        if indisclustered:
            status.append(", clustered")

        if not indisvalid:
            status.append(", invalid")

        if deferrable:
            status.append(", deferrable")

        if deferred:
            status.append(", initially deferred")

        status.append("\n")
        # add_tablespace_footer(&cont, tableinfo.relkind,
        # tableinfo.tablespace, true);

    elif tableinfo.relkind == "S":
        # /* Footer information about a sequence */
        # /* Get the column that owns this sequence */
        sql = (
            "SELECT pg_catalog.quote_ident(nspname) || '.' ||"
            "\n   pg_catalog.quote_ident(relname) || '.' ||"
            "\n   pg_catalog.quote_ident(attname)"
            "\nFROM pg_catalog.pg_class c"
            "\nINNER JOIN pg_catalog.pg_depend d ON c.oid=d.refobjid"
            "\nINNER JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace"
            "\nINNER JOIN pg_catalog.pg_attribute a ON ("
            "\n a.attrelid=c.oid AND"
            "\n a.attnum=d.refobjsubid)"
            "\nWHERE d.classid='pg_catalog.pg_class'::pg_catalog.regclass"
            "\n AND d.refclassid='pg_catalog.pg_class'::pg_catalog.regclass"
            f"\n AND d.objid={oid} \n AND d.deptype='a'"
        )

        log.debug(sql)
        cur.execute(sql)
        result = cur.fetchone()
        if result:
            status.append(f"Owned by: {result[0]}")

        # /*
        # * If we get no rows back, don't show anything (obviously). We should
        # * never get more than one row back, but if we do, just ignore it and
        # * don't print anything.
        # */

    elif (
        tableinfo.relkind == "r"
        or tableinfo.relkind == "p"
        or tableinfo.relkind == "m"
        or tableinfo.relkind == "f"
    ):
        # /* Footer information about a table */

        if tableinfo.hasindex:
            if cur.connection.info.server_version > 90000:
                sql = f"""SELECT c2.relname,
                                i.indisprimary,
                                i.indisunique,
                                i.indisclustered,
                                i.indisvalid,
                                pg_catalog.pg_get_indexdef(i.indexrelid, 0, true),
                                pg_catalog.pg_get_constraintdef(con.oid, true),
                                contype,
                                condeferrable,
                                condeferred,
                                c2.reltablespace
                        FROM pg_catalog.pg_class c,
                            pg_catalog.pg_class c2,
                            pg_catalog.pg_index i
                        LEFT JOIN pg_catalog.pg_constraint con
                        ON conrelid = i.indrelid
                            AND conindid = i.indexrelid
                            AND contype IN ('p','u','x')
                        WHERE c.oid = '{oid}'
                            AND c.oid = i.indrelid
                            AND i.indexrelid = c2.oid
                        ORDER BY i.indisprimary DESC,
                            i.indisunique DESC,
                            c2.relname;
                    """
            else:
                sql = f"""SELECT c2.relname,
                                i.indisprimary,
                                i.indisunique,
                                i.indisclustered,
                                't' AS indisvalid,
                                pg_catalog.pg_get_indexdef(i.indexrelid, 0, true),
                                pg_catalog.pg_get_constraintdef(con.oid, true),
                                contype,
                                condeferrable,
                                condeferred,
                                c2.reltablespace
                        FROM pg_catalog.pg_class c,
                            pg_catalog.pg_class c2,
                            pg_catalog.pg_index i
                        LEFT JOIN pg_catalog.pg_constraint con
                        ON conrelid = i.indrelid
                            AND contype IN ('p','u','x')
                        WHERE c.oid = '{oid}'
                            AND c.oid = i.indrelid
                            AND i.indexrelid = c2.oid
                        ORDER BY i.indisprimary DESC,
                            i.indisunique DESC,
                            c2.relname;
                    """

            log.debug(sql)
            result = cur.execute(sql)

            if cur.rowcount > 0:
                status.append("Indexes:\n")
            for row in cur:
                # /* untranslated index name */
                status.append(f'''    "{row[0]}"''')

                # /* If exclusion constraint, print the constraintdef */
                if row[7] == "x":
                    status.append(" ")
                    status.append(row[6])
                else:
                    # /* Label as primary key or unique (but not both) */
                    if row[1]:
                        status.append(" PRIMARY KEY,")
                    elif row[2]:
                        if row[7] == "u":
                            status.append(" UNIQUE CONSTRAINT,")
                        else:
                            status.append(" UNIQUE,")

                    # /* Everything after "USING" is echoed verbatim */
                    indexdef = row[5]
                    usingpos = indexdef.find(" USING ")
                    if usingpos >= 0:
                        indexdef = indexdef[(usingpos + 7) :]
                    status.append(f" {indexdef}")

                    # /* Need these for deferrable PK/UNIQUE indexes */
                    if row[8]:
                        status.append(" DEFERRABLE")

                    if row[9]:
                        status.append(" INITIALLY DEFERRED")

                # /* Add these for all cases */
                if row[3]:
                    status.append(" CLUSTER")

                if not row[4]:
                    status.append(" INVALID")

                status.append("\n")
                # printTableAddFooter(&cont, buf.data);

                # /* Print tablespace of the index on the same line */
                # add_tablespace_footer(&cont, 'i',
                # atooid(PQgetvalue(result, i, 10)),
                # false);

        # /* print table (and column) check constraints */
        if tableinfo.checks:
            sql = (
                "SELECT r.conname, "
                "pg_catalog.pg_get_constraintdef(r.oid, true)\n"
                "FROM pg_catalog.pg_constraint r\n"
                f"WHERE r.conrelid = '{oid}' AND r.contype = 'c'\n"
                "ORDER BY 1;"
            )
            log.debug(sql)
            cur.execute(sql)
            if cur.rowcount > 0:
                status.append("Check constraints:\n")
            for row in cur:
                # /* untranslated contraint name and def */
                status.append(f"""    "{row[0]}" {row[1]}""")
                status.append("\n")

        # /* print foreign-key constraints (there are none if no triggers) */
        if tableinfo.hastriggers:
            sql = (
                "SELECT conname,\n"
                " pg_catalog.pg_get_constraintdef(r.oid, true) as condef\n"
                "FROM pg_catalog.pg_constraint r\n"
                f"WHERE r.conrelid = '{oid}' AND r.contype = 'f' ORDER BY 1;"
            )
            log.debug(sql)
            cur.execute(sql)
            if cur.rowcount > 0:
                status.append("Foreign-key constraints:\n")
            for row in cur:
                # /* untranslated constraint name and def */
                status.append(f"""    "{row[0]}" {row[1]}\n""")

        # /* print incoming foreign-key references (none if no triggers) */
        if tableinfo.hastriggers:
            sql = (
                "SELECT conrelid::pg_catalog.regclass, conname,\n"
                "  pg_catalog.pg_get_constraintdef(c.oid, true) as condef\n"
                "FROM pg_catalog.pg_constraint c\n"
                f"WHERE c.confrelid = '{oid}' AND c.contype = 'f' ORDER BY 1;"
            )
            log.debug(sql)
            cur.execute(sql)
            if cur.rowcount > 0:
                status.append("Referenced by:\n")
            for row in cur:
                status.append(
                    f"""    TABLE "{row[0]}" CONSTRAINT "{row[1]}" {row[2]}\n"""
                )

        # /* print rules */
        if tableinfo.hasrules and tableinfo.relkind != "m":
            sql = (
                "SELECT r.rulename, trim(trailing ';' from pg_catalog.pg_get_ruledef(r.oid, true)), "
                "ev_enabled\n"
                "FROM pg_catalog.pg_rewrite r\n"
                f"WHERE r.ev_class = '{oid}' ORDER BY 1;"
            )
            log.debug(sql)
            cur.execute(sql)
            if cur.rowcount > 0:
                for category in range(4):
                    have_heading = False
                    for row in cur:
                        if category == 0 and row[2] == "O":
                            list_rule = True
                        elif category == 1 and row[2] == "D":
                            list_rule = True
                        elif category == 2 and row[2] == "A":
                            list_rule = True
                        elif category == 3 and row[2] == "R":
                            list_rule = True

                        if not list_rule:
                            continue

                        if not have_heading:
                            if category == 0:
                                status.append("Rules:")
                            if category == 1:
                                status.append("Disabled rules:")
                            if category == 2:
                                status.append("Rules firing always:")
                            if category == 3:
                                status.append("Rules firing on replica only:")
                            have_heading = True

                        # /* Everything after "CREATE RULE" is echoed verbatim */
                        ruledef = row[1]
                        status.append(f"    {ruledef}")

        # /* print partition info */
        if tableinfo.relispartition:
            sql = (
                "select quote_ident(np.nspname) || '.' ||\n"
                "       quote_ident(cp.relname) || ' ' ||\n"
                "       pg_get_expr(cc.relpartbound, cc.oid, true) as partition_of,\n"
                "       pg_get_partition_constraintdef(cc.oid) as partition_constraint\n"
                "from pg_inherits i\n"
                "inner join pg_class cp\n"
                "on cp.oid = i.inhparent\n"
                "inner join pg_namespace np\n"
                "on np.oid = cp.relnamespace\n"
                "inner join pg_class cc\n"
                "on cc.oid = i.inhrelid\n"
                "inner join pg_namespace nc\n"
                "on nc.oid = cc.relnamespace\n"
                f"where cc.oid = {oid}"
            )
            log.debug(sql)
            cur.execute(sql)
            for row in cur:
                status.append(f"Partition of: {row[0]}\n")
                status.append(f"Partition constraint: {row[1]}\n")

        if tableinfo.relkind == "p":
            # /* print partition key */
            sql = f"select pg_get_partkeydef({oid})"
            log.debug(sql)
            cur.execute(sql)
            for row in cur:
                status.append(f"Partition key: {row[0]}\n")
            # /* print list of partitions */
            sql = (
                "select quote_ident(n.nspname) || '.' ||\n"
                "       quote_ident(c.relname) || ' ' ||\n"
                "       pg_get_expr(c.relpartbound, c.oid, true)\n"
                "from pg_inherits i\n"
                "inner join pg_class c\n"
                "on c.oid = i.inhrelid\n"
                "inner join pg_namespace n\n"
                "on n.oid = c.relnamespace\n"
                f"where i.inhparent = {oid} order by 1"
            )
            log.debug(sql)
            cur.execute(sql)
            if cur.rowcount > 0:
                if verbose:
                    first = True
                    for row in cur:
                        if first:
                            status.append(f"Partitions: {row[0]}\n")
                            first = False
                        else:
                            status.append(f"            {row[0]}\n")
                else:
                    status.append(
                        "Number of partitions %i: (Use \\d+ to list them.)\n"
                        % cur.rowcount
                    )

    if view_def:
        # /* Footer information about a view */
        status.append("View definition:\n")
        status.append(f"{view_def} \n")

        # /* print rules */
        if tableinfo.hasrules:
            sql = (
                "SELECT r.rulename, trim(trailing ';' from pg_catalog.pg_get_ruledef(r.oid, true))\n"
                "FROM pg_catalog.pg_rewrite r\n"
                f"WHERE r.ev_class = '{oid}' AND r.rulename != '_RETURN' ORDER BY 1;"
            )

            log.debug(sql)
            cur.execute(sql)
            if cur.rowcount > 0:
                status.append("Rules:\n")
                for row in cur:
                    # /* Everything after "CREATE RULE" is echoed verbatim */
                    ruledef = row[1]
                    status.append(f" {ruledef}\n")

    # /*
    # * Print triggers next, if any (but only user-defined triggers).  This
    # * could apply to either a table or a view.
    # */
    if tableinfo.hastriggers:
        if cur.connection.info.server_version > 90000:
            sql = f"""SELECT t.tgname,
                        pg_catalog.pg_get_triggerdef(t.oid, true),
                        t.tgenabled
                   FROM pg_catalog.pg_trigger t
                   WHERE t.tgrelid = '{oid}' AND NOT t.tgisinternal
                   ORDER BY 1
                """
        else:
            sql = f"""SELECT t.tgname,
                        pg_catalog.pg_get_triggerdef(t.oid),
                        t.tgenabled
                   FROM pg_catalog.pg_trigger t
                   WHERE t.tgrelid = '{oid}'
                   ORDER BY 1
                """

        log.debug(sql)
        cur.execute(sql)
        if cur.rowcount > 0:
            # /*
            # * split the output into 4 different categories. Enabled triggers,
            # * disabled triggers and the two special ALWAYS and REPLICA
            # * configurations.
            # */
            for category in range(4):
                have_heading = False
                list_trigger = False
                for row in cur:
                    # /*
                    # * Check if this trigger falls into the current category
                    # */
                    tgenabled = row[2]
                    if category == 0:
                        if tgenabled == "O" or tgenabled == True:
                            list_trigger = True
                    elif category == 1:
                        if tgenabled == "D" or tgenabled == False:
                            list_trigger = True
                    elif category == 2:
                        if tgenabled == "A":
                            list_trigger = True
                    elif category == 3:
                        if tgenabled == "R":
                            list_trigger = True
                    if list_trigger == False:
                        continue

                    # /* Print the category heading once */
                    if not have_heading:
                        if category == 0:
                            status.append("Triggers:")
                        elif category == 1:
                            status.append("Disabled triggers:")
                        elif category == 2:
                            status.append("Triggers firing always:")
                        elif category == 3:
                            status.append("Triggers firing on replica only:")
                        status.append("\n")
                        have_heading = True

                    # /* Everything after "TRIGGER" is echoed verbatim */
                    tgdef = row[1]
                    triggerpos = tgdef.find(" TRIGGER ")
                    if triggerpos >= 0:
                        tgdef = triggerpos + 9

                    status.append(f"    {row[1][tgdef:]}\n")

    # /*
    # * Finish printing the footer information about a table.
    # */
    if tableinfo.relkind == "r" or tableinfo.relkind == "m" or tableinfo.relkind == "f":
        # /* print foreign server name */
        if tableinfo.relkind == "f":
            # /* Footer information about foreign table */
            sql = f"""SELECT s.srvname,\n
                          array_to_string(ARRAY(SELECT
                          quote_ident(option_name) ||  ' ' ||
                          quote_literal(option_value)  FROM
                          pg_options_to_table(ftoptions)),  ', ')
                   FROM pg_catalog.pg_foreign_table f,\n
                        pg_catalog.pg_foreign_server s\n
                   WHERE f.ftrelid = {oid} AND s.oid = f.ftserver;"""
            log.debug(sql)
            cur.execute(sql)
            row = cur.fetchone()

            # /* Print server name */
            status.append(f"Server: {row[0]}\n")

            # /* Print per-table FDW options, if any */
            if row[1]:
                status.append(f"FDW Options: ({row[1]})\n")

        # /* print inherited tables */
        if not tableinfo.relispartition:
            sql = (
                "SELECT c.oid::pg_catalog.regclass\n"
                "FROM pg_catalog.pg_class c, pg_catalog.pg_inherits i\n"
                "WHERE c.oid = i.inhparent\n"
                f"  AND i.inhrelid = '{oid}'\n"
                "ORDER BY inhseqno"
            )
            log.debug(sql)
            cur.execute(sql)
            spacer = ""
            if cur.rowcount > 0:
                status.append("Inherits")
                spacer = ":"
                trailer = ",\n"
                for idx, row in enumerate(cur, 1):
                    if idx == 2:
                        spacer = " " * (len("Inherits") + 1)
                    if idx == cur.rowcount:
                        trailer = "\n"
                    status.append(f"{spacer} {row[0]}{trailer}")

        # /* print child tables */
        if cur.connection.info.server_version > 90000:
            sql = f"""SELECT c.oid::pg_catalog.regclass
                        FROM pg_catalog.pg_class c,
                            pg_catalog.pg_inherits i
                        WHERE c.oid = i.inhrelid
                            AND i.inhparent = '{oid}'
                        ORDER BY c.oid::pg_catalog.regclass::pg_catalog.text;
                    """
        else:
            sql = f"""SELECT c.oid::pg_catalog.regclass
                        FROM pg_catalog.pg_class c,
                            pg_catalog.pg_inherits i
                        WHERE c.oid = i.inhrelid
                            AND i.inhparent = '{oid}'
                        ORDER BY c.oid;
                    """

        log.debug(sql)
        cur.execute(sql)

        if not verbose:
            # /* print the number of child tables, if any */
            if cur.rowcount > 0:
                status.append(
                    "Number of child tables: %d (Use \\d+ to list"
                    " them.)\n" % cur.rowcount
                )
        else:
            if cur.rowcount > 0:
                status.append("Child tables")

                spacer = ":"
                trailer = ",\n"
                # /* display the list of child tables */
                for idx, row in enumerate(cur, 1):
                    if idx == 2:
                        spacer = " " * (len("Child tables") + 1)
                    if idx == cur.rowcount:
                        trailer = "\n"
                    status.append(f"{spacer} {row[0]}{trailer}")

        # /* Table type */
        if tableinfo.reloftype:
            status.append(f"Typed table of type: {tableinfo.reloftype}\n")

        # /* OIDs, if verbose and not a materialized view */
        if verbose and tableinfo.relkind != "m":
            status.append(f"Has OIDs: {'yes' if tableinfo.hasoids else 'no'}\n")

        # /* Tablespace info */
        # add_tablespace_footer(&cont, tableinfo.relkind, tableinfo.tablespace,
        # true);

    # /* reloptions, if verbose */
    if verbose and tableinfo.reloptions:
        status.append(f"Options: {tableinfo.reloptions}\n")

    return (None, cells, headers, "".join(status))


def sql_name_pattern(pattern):
    """
    Takes a wildcard-pattern and converts to an appropriate SQL pattern to be
    used in a WHERE clause.

    Returns: schema_pattern, table_pattern

    >>> sql_name_pattern('foo*."b""$ar*"')
    ('^(foo.*)$', '^(b"\\\\$ar\\\\*)$')
    """

    inquotes = False
    relname = ""
    schema = None
    pattern_len = len(pattern)
    i = 0

    while i < pattern_len:
        c = pattern[i]
        if c == '"':
            if inquotes and i + 1 < pattern_len and pattern[i + 1] == '"':
                relname += '"'
                i += 1
            else:
                inquotes = not inquotes
        elif not inquotes and c.isupper():
            relname += c.lower()
        elif not inquotes and c == "*":
            relname += ".*"
        elif not inquotes and c == "?":
            relname += "."
        elif not inquotes and c == ".":
            # Found schema/name separator, move current pattern to schema
            schema = relname
            relname = ""
        else:
            # Dollar is always quoted, whether inside quotes or not.
            if c == "$" or inquotes and c in "|*+?()[]{}.^\\":
                relname += "\\"
            relname += c
        i += 1

    if relname:
        relname = "^(" + relname + ")$"

    if schema:
        schema = "^(" + schema + ")$"

    return schema, relname


class _FakeCursor(list):
    "Minimalistic wrapper simulating a real cursor, as far as pgcli is concerned."

    def rowcount(self):
        return len(self)


@special_command("\\sf", "\\sf[+] FUNCNAME", "Show a function's definition.")
def show_function_definition(cur, pattern, verbose):
    params = {"pattern": pattern}
    if "(" in pattern:
        sql = "SELECT %(pattern)s::pg_catalog.regprocedure::pg_catalog.oid"
    else:
        sql = "SELECT %(pattern)s::pg_catalog.regproc::pg_catalog.oid"
    log.debug("%s, %s", sql, params)
    cur.execute(sql, params)
    (foid,) = cur.fetchone()

    params = {"foid": foid}
    sql = "SELECT pg_catalog.pg_get_functiondef(%(foid)s) as source"
    log.debug("%s, %s", sql, params)
    cur.execute(sql, params)
    if cur.description:
        headers = [x.name for x in cur.description]
        if verbose:
            (source,) = cur.fetchone()
            rows = _FakeCursor()
            rown = None
            for row in source.splitlines():
                if rown is None:
                    if row.startswith("AS "):
                        rown = 1
                else:
                    rown += 1
                rown_v = "" if rown is None else rown
                rows.append(f"{rown_v:<7} {row}")
            cur = [("\n".join(rows) + "\n",)]
    else:
        headers = None
    return [(None, cur, headers, None)]


@special_command("\\!", "\\! [command]", "Pass commands to shell.")
def shell_command(cur, pattern, verbose):
    cur, headers = [], []
    params = shlex.split(pattern)
    return [(None, cur, headers, subprocess.call(params))]


@special_command("\\dE", "\\dE[+] [pattern]", "List foreign tables.", aliases=())
def list_foreign_tables(cur, pattern, verbose):
    params = {}
    query = SQL(
        """
        SELECT n.nspname as "Schema",
        c.relname as "Name",
        CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized view' WHEN 'i' THEN 'index' WHEN 'S' THEN 'sequence' WHEN 's' THEN 'special' WHEN 'f' THEN 'foreign table' WHEN 'p' THEN 'table' WHEN 'I' THEN 'index' END as "Type",
        pg_catalog.pg_get_userbyid(c.relowner) as "Owner"
        {verbose_cols}
        FROM pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('f','')
            AND n.nspname <> 'pg_catalog'
            AND n.nspname <> 'information_schema'
            AND n.nspname !~ '^pg_toast'
        AND pg_catalog.pg_table_is_visible(c.oid)
        {filter}
        ORDER BY 1,2;
        """
    )

    if verbose:
        params["verbose_cols"] = SQL(
            """
            , pg_catalog.pg_size_pretty(pg_catalog.pg_table_size(c.oid)) as "Size",
            pg_catalog.obj_description(c.oid, 'pg_class') as "Description" """
        )
    else:
        params["verbose_cols"] = SQL("")

    if pattern:
        _, tbl_name = sql_name_pattern(pattern)
        params["filter"] = SQL(" AND c.relname OPERATOR(pg_catalog.~) {} ").format(
            f"^({tbl_name})$"
        )
    else:
        params["filter"] = SQL("")

    formatted_query = query.format(**params)
    log.debug(formatted_query.as_string(cur))
    cur.execute(formatted_query)
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]
    else:
        return [(None, None, None, cur.statusmessage)]
