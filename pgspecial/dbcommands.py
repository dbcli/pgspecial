import logging
from collections import namedtuple
from .main import special_command, RAW_QUERY

TableInfo = namedtuple("TableInfo", ['checks', 'relkind', 'hasindex',
'hasrules', 'hastriggers', 'hasoids', 'tablespace', 'reloptions', 'reloftype',
'relpersistence'])

log = logging.getLogger(__name__)


@special_command('\\l', '\\l', 'List databases.', arg_type=RAW_QUERY)
def list_databases(cur, **_):
    query = 'SELECT datname FROM pg_database;'
    cur.execute(query)
    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]
    else:
        return [(None, None, None, cur.statusmessage)]


@special_command('\\du', '\\du[+] [pattern]', 'List roles.')
def list_roles(cur, pattern, verbose):
    """
    Returns (title, rows, headers, status)
    """

    if cur.connection.server_version > 90000:
        sql = '''
            SELECT r.rolname,
                r.rolsuper,
                r.rolinherit,
                r.rolcreaterole,
                r.rolcreatedb,
                r.rolcanlogin,
                r.rolconnlimit,
                r.rolvaliduntil,
                ARRAY(SELECT b.rolname FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles b ON (m.roleid = b.oid) WHERE m.member = r.oid) as memberof,
            '''
        if verbose:
            sql += '''
                pg_catalog.shobj_description(r.oid, 'pg_authid') AS description,
            '''
        sql += '''
            r.rolreplication
        FROM pg_catalog.pg_roles r
        '''
    else:
        sql = '''
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
            '''

    params = []
    if pattern:
        _, schema = sql_name_pattern(pattern)
        sql += 'WHERE r.rolname ~ %s'
        params.append(schema)
    sql = cur.mogrify(sql + " ORDER BY 1", params)

    log.debug(sql)
    cur.execute(sql)
    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command('\\dn', '\\dn[+] [pattern]', 'List schemas.')
def list_schemas(cur, pattern, verbose):
    """
    Returns (title, rows, headers, status)
    """

    sql = '''SELECT n.nspname AS "Name",
    pg_catalog.pg_get_userbyid(n.nspowner) AS "Owner"''' + (''',
    pg_catalog.array_to_string(n.nspacl, E'\\n') AS "Access privileges",
    pg_catalog.obj_description(n.oid, 'pg_namespace') AS "Description"''' if verbose else '') + """
    FROM pg_catalog.pg_namespace n WHERE n.nspname """

    params = []
    if pattern:
        _, schema = sql_name_pattern(pattern)
        sql += '~ %s'
        params.append(schema)
    else:
        sql += "!~ '^pg_' AND n.nspname <> 'information_schema'"
    sql = cur.mogrify(sql + " ORDER BY 1", params)

    log.debug(sql)
    cur.execute(sql)
    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


def list_objects(cur, pattern, verbose, relkinds):
    """
        Returns (title, rows, header, status)

        This method is used by list_tables, list_views, and list_indexes

        relkinds is a list of strings to filter pg_class.relkind

    """
    schema_pattern, table_pattern = sql_name_pattern(pattern)

    if verbose:
        verbose_columns = '''
            ,pg_catalog.pg_size_pretty(pg_catalog.pg_table_size(c.oid)) as "Size",
            pg_catalog.obj_description(c.oid, 'pg_class') as "Description" '''
    else:
        verbose_columns = ''

    sql = '''SELECT n.nspname as "Schema",
                    c.relname as "Name",
                    CASE c.relkind
                      WHEN 'r' THEN 'table' WHEN 'v' THEN 'view'
                      WHEN 'm' THEN 'materialized view' WHEN 'i' THEN 'index'
                      WHEN 'S' THEN 'sequence' WHEN 's' THEN 'special'
                      WHEN 'f' THEN 'foreign table' END
                    as "Type",
                    pg_catalog.pg_get_userbyid(c.relowner) as "Owner"
          ''' + verbose_columns + '''
            FROM    pg_catalog.pg_class c
                    LEFT JOIN pg_catalog.pg_namespace n
                      ON n.oid = c.relnamespace
            WHERE   c.relkind = ANY(%s) '''

    params = [relkinds]

    if schema_pattern:
        sql += ' AND n.nspname ~ %s'
        params.append(schema_pattern)
    else:
        sql += '''
            AND n.nspname <> 'pg_catalog'
            AND n.nspname <> 'information_schema'
            AND n.nspname !~ '^pg_toast'
            AND pg_catalog.pg_table_is_visible(c.oid) '''

    if table_pattern:
        sql += ' AND c.relname ~ %s'
        params.append(table_pattern)

    sql = cur.mogrify(sql + ' ORDER BY 1, 2', params)

    log.debug(sql)
    cur.execute(sql)

    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command('\\dt', '\\dt[+] [pattern]', 'List tables.')
def list_tables(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ['r', ''])


@special_command('\\dv', '\\dv[+] [pattern]', 'List views.')
def list_views(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ['v', 's', ''])


@special_command('\\ds', '\\ds[+] [pattern]', 'List sequences.')
def list_sequences(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ['S', 's', ''])


@special_command('\\di', '\\di[+] [pattern]', 'List indexes.')
def list_indexes(cur, pattern, verbose):
    return list_objects(cur, pattern, verbose, ['i', 's', ''])


@special_command('\\df', '\\df[+] [pattern]', 'List functions.')
def list_functions(cur, pattern, verbose):

    if verbose:
        verbose_columns = '''
            ,CASE
                 WHEN p.provolatile = 'i' THEN 'immutable'
                 WHEN p.provolatile = 's' THEN 'stable'
                 WHEN p.provolatile = 'v' THEN 'volatile'
            END as "Volatility",
            pg_catalog.pg_get_userbyid(p.proowner) as "Owner",
          l.lanname as "Language",
          p.prosrc as "Source code",
          pg_catalog.obj_description(p.oid, 'pg_proc') as "Description" '''

        verbose_table = ''' LEFT JOIN pg_catalog.pg_language l
                                ON l.oid = p.prolang'''
    else:
        verbose_columns = verbose_table = ''

    if cur.connection.server_version > 90000:
        sql = '''
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
                    END as "Type" ''' + verbose_columns + '''
            FROM    pg_catalog.pg_proc p
                    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                            ''' + verbose_table + '''
            WHERE  '''
    else:
        sql = '''
            SELECT  n.nspname as "Schema",
                    p.proname as "Name",
                    pg_catalog.format_type(p.prorettype, NULL) as "Result data type",
                    pg_catalog.oidvectortypes(p.proargtypes) as "Argument data types",
                     CASE
                        WHEN p.proisagg THEN 'agg'
                        WHEN p.prorettype = 'pg_catalog.trigger'::pg_catalog.regtype THEN 'trigger'
                        ELSE 'normal'
                    END as "Type" ''' + verbose_columns + '''
            FROM    pg_catalog.pg_proc p
                    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                            ''' + verbose_table + '''
            WHERE  '''


    schema_pattern, func_pattern = sql_name_pattern(pattern)
    params = []

    if schema_pattern:
        sql += ' n.nspname ~ %s '
        params.append(schema_pattern)
    else:
        sql += ' pg_catalog.pg_function_is_visible(p.oid) '

    if func_pattern:
        sql += ' AND p.proname ~ %s '
        params.append(func_pattern)

    if not (schema_pattern or func_pattern):
        sql += ''' AND n.nspname <> 'pg_catalog'
                   AND n.nspname <> 'information_schema' '''

    sql = cur.mogrify(sql + ' ORDER BY 1, 2, 4', params)

    log.debug(sql)
    cur.execute(sql)

    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command('\\dT', '\\dT[S+] [pattern]', 'List data types')
def list_datatypes(cur, pattern, verbose):
    assert True
    sql = '''SELECT n.nspname as "Schema",
                    pg_catalog.format_type(t.oid, NULL) AS "Name", '''

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
        sql += '''  pg_catalog.obj_description(t.oid, 'pg_type')
                        as "Description" '''

    if cur.connection.server_version > 90000:
        sql += '''  FROM    pg_catalog.pg_type t
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
                                      AND el.typarray = t.oid) '''
    else:
        sql += '''  FROM    pg_catalog.pg_type t
                            LEFT JOIN pg_catalog.pg_namespace n
                              ON n.oid = t.typnamespace
                    WHERE   (t.typrelid = 0 OR
                              ( SELECT c.relkind = 'c'
                                FROM pg_catalog.pg_class c
                                WHERE c.oid = t.typrelid)) '''

    schema_pattern, type_pattern = sql_name_pattern(pattern)
    params = []

    if schema_pattern:
        sql += ' AND n.nspname ~ %s '
        params.append(schema_pattern)
    else:
        sql += ' AND pg_catalog.pg_type_is_visible(t.oid) '

    if type_pattern:
        sql += ''' AND (t.typname ~ %s
                        OR pg_catalog.format_type(t.oid, NULL) ~ %s) '''
        params.extend(2 * [type_pattern])

    if not (schema_pattern or type_pattern):
        sql += ''' AND n.nspname <> 'pg_catalog'
                   AND n.nspname <> 'information_schema' '''

    sql = cur.mogrify(sql + ' ORDER BY 1, 2', params)
    log.debug(sql)
    cur.execute(sql)
    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command('describe', 'DESCRIBE [pattern]', '', hidden=True, case_sensitive=False)
@special_command('\\d', '\\d [pattern]', 'List or describe tables, views and sequences.')
def describe_table_details(cur, pattern, verbose):
    """
    Returns (title, rows, headers, status)
    """

    # This is a simple \d command. No table name to follow.
    if not pattern:
        sql = """SELECT n.nspname as "Schema", c.relname as "Name",
                    CASE c.relkind WHEN 'r' THEN 'table'
                        WHEN 'v' THEN 'view'
                        WHEN 'm' THEN 'materialized view'
                        WHEN 'i' THEN 'index'
                        WHEN 'S' THEN 'sequence'
                        WHEN 's' THEN 'special'
                        WHEN 'f' THEN 'foreign table'
                    END as "Type",
                    pg_catalog.pg_get_userbyid(c.relowner) as "Owner"
                FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r','v','m','S','f','')
                AND n.nspname <> 'pg_catalog'
                AND n.nspname <> 'information_schema'
                AND n.nspname !~ '^pg_toast'
                AND pg_catalog.pg_table_is_visible(c.oid)
                ORDER BY 1,2 """

        log.debug(sql)
        cur.execute(sql)
        if cur.description:
            headers = [x[0] for x in cur.description]
            return [(None, cur, headers, cur.statusmessage)]

    # This is a \d <tablename> command. A royal pain in the ass.
    schema, relname = sql_name_pattern(pattern)
    where = []
    params = []

    if not pattern:
        where.append('pg_catalog.pg_table_is_visible(c.oid)')

    if schema:
        where.append('n.nspname ~ %s')
        params.append(schema)

    if relname:
        where.append('c.relname ~ %s')
        params.append(relname)

    sql = """SELECT c.oid, n.nspname, c.relname
             FROM pg_catalog.pg_class c
             LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
             """ + ('WHERE ' + ' AND '.join(where) if where else '') + """
             ORDER BY 2,3"""
    sql = cur.mogrify(sql, params)

    # Execute the sql, get the results and call describe_one_table_details on each table.

    log.debug(sql)
    cur.execute(sql)
    if not (cur.rowcount > 0):
        return [(None, None, None, 'Did not find any relation named %s.' % pattern)]

    results = []
    for oid, nspname, relname in cur.fetchall():
        results.append(describe_one_table_details(cur, nspname, relname, oid, verbose))

    return results


def describe_one_table_details(cur, schema_name, relation_name, oid, verbose):
    if verbose:
        suffix = """pg_catalog.array_to_string(c.reloptions || array(select
        'toast.' || x from pg_catalog.unnest(tc.reloptions) x), ', ')"""
    else:
        suffix = "''"

    if cur.connection.server_version > 90000:
        sql = """SELECT c.relchecks, c.relkind, c.relhasindex,
                    c.relhasrules, c.relhastriggers, c.relhasoids,
                    %s,
                    c.reltablespace,
                    CASE WHEN c.reloftype = 0 THEN ''
                        ELSE c.reloftype::pg_catalog.regtype::pg_catalog.text
                    END,
                    c.relpersistence
                 FROM pg_catalog.pg_class c
                 LEFT JOIN pg_catalog.pg_class tc ON (c.reltoastrelid = tc.oid)
                 WHERE c.oid = '%s'""" % (suffix, oid)
    elif cur.connection.server_version >= 80400:
        sql = """SELECT c.relchecks,
                    c.relkind,
                    c.relhasindex,
                    c.relhasrules,
                    c.relhastriggers,
                    c.relhasoids,
                    %s,
                    c.reltablespace,
                    0 AS reloftype,
                    'p' AS relpersistence
                 FROM pg_catalog.pg_class c
                 LEFT JOIN pg_catalog.pg_class tc ON (c.reltoastrelid = tc.oid)
                 WHERE c.oid = '%s'""" % (suffix, oid)
    else:
        sql = """SELECT c.relchecks,
                    c.relkind,
                    c.relhasindex,
                    c.relhasrules,
                    c.reltriggers > 0 AS relhastriggers,
                    c.relhasoids,
                    %s,
                    c.reltablespace,
                    0 AS reloftype,
                    'p' AS relpersistence
                 FROM pg_catalog.pg_class c
                 LEFT JOIN pg_catalog.pg_class tc ON (c.reltoastrelid = tc.oid)
                 WHERE c.oid = '%s'""" % (suffix, oid)

    # Create a namedtuple called tableinfo and match what's in describe.c

    log.debug(sql)
    cur.execute(sql)
    if (cur.rowcount > 0):
        tableinfo = TableInfo._make(cur.fetchone())
    else:
        return (None, None, None, 'Did not find any relation with OID %s.' % oid)

    # If it's a seq, fetch it's value and store it for later.
    if tableinfo.relkind == 'S':
        # Do stuff here.
        sql = '''SELECT * FROM "%s"."%s"''' % (schema_name, relation_name)
        log.debug(sql)
        cur.execute(sql)
        if not (cur.rowcount > 0):
            return (None, None, None, 'Something went wrong.')

        seq_values = cur.fetchone()

    # Get column info
    if cur.connection.server_version > 90000:
        sql = """SELECT a.attname,
                    pg_catalog.format_type(a.atttypid, a.atttypmod),
                    (
                        SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid) for 128)
                        FROM pg_catalog.pg_attrdef d
                        WHERE d.adrelid = a.attrelid
                            AND d.adnum = a.attnum
                            AND a.atthasdef
                    ),
                    a.attnotnull,
                    a.attnum,
                    (
                        SELECT c.collname
                        FROM pg_catalog.pg_collation c,
                            pg_catalog.pg_type t
                        WHERE c.oid = a.attcollation
                            AND t.oid = a.atttypid
                            AND a.attcollation <> t.typcollation
                    ) AS attcollation
                """
    else:
        sql = """SELECT a.attname,
                    pg_catalog.format_type(a.atttypid, a.atttypmod),
                    (
                        SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid) for 128)
                        FROM pg_catalog.pg_attrdef d
                        WHERE d.adrelid = a.attrelid
                            AND d.adnum = a.attnum
                            AND a.atthasdef
                    ),
                    a.attnotnull,
                    a.attnum,
                    NULL AS attcollation
                """


    if tableinfo.relkind == 'i':
        sql += """, pg_catalog.pg_get_indexdef(a.attrelid, a.attnum, TRUE)
                AS indexdef"""
    else:
        sql += """, NULL AS indexdef"""

    if tableinfo.relkind == 'f':
        sql += """, CASE WHEN attfdwoptions IS NULL THEN '' ELSE '(' ||
                array_to_string(ARRAY(SELECT quote_ident(option_name) ||  ' '
                || quote_literal(option_value)  FROM
                pg_options_to_table(attfdwoptions)), ', ') || ')' END AS
        attfdwoptions"""
    else:
        sql += """, NULL AS attfdwoptions"""

    if verbose:
        sql += """, a.attstorage"""
        sql += """, CASE WHEN a.attstattarget=-1 THEN NULL ELSE
                a.attstattarget END AS attstattarget"""
        if (tableinfo.relkind == 'r' or tableinfo.relkind == 'v' or
                tableinfo.relkind == 'm' or tableinfo.relkind == 'f' or
                tableinfo.relkind == 'c'):
            sql += """, pg_catalog.col_description(a.attrelid,
                    a.attnum)"""

    sql += """ FROM pg_catalog.pg_attribute a WHERE a.attrelid = '%s' AND
    a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum; """ % oid

    log.debug(sql)
    cur.execute(sql)
    res = cur.fetchall()

    title = (tableinfo.relkind, schema_name, relation_name)

    # Set the column names.
    headers = ['Column', 'Type']

    show_modifiers = False
    if (tableinfo.relkind == 'r' or tableinfo.relkind == 'v' or
            tableinfo.relkind == 'm' or tableinfo.relkind == 'f' or
            tableinfo.relkind == 'c'):
        headers.append('Modifiers')
        show_modifiers = True

    if (tableinfo.relkind == 'S'):
            headers.append("Value")

    if (tableinfo.relkind == 'i'):
            headers.append("Definition")

    if (tableinfo.relkind == 'f'):
            headers.append("FDW Options")

    if (verbose):
        headers.append("Storage")
        if (tableinfo.relkind == 'r' or tableinfo.relkind == 'm' or
                tableinfo.relkind == 'f'):
            headers.append("Stats target")
        #  Column comments, if the relkind supports this feature. */
        if (tableinfo.relkind == 'r' or tableinfo.relkind == 'v' or
                tableinfo.relkind == 'm' or
                tableinfo.relkind == 'c' or tableinfo.relkind == 'f'):
            headers.append("Description")

    view_def = ''
    # /* Check if table is a view or materialized view */
    if ((tableinfo.relkind == 'v' or tableinfo.relkind == 'm') and verbose):
        sql = """SELECT pg_catalog.pg_get_viewdef('%s'::pg_catalog.oid, true)""" % oid
        log.debug(sql)
        cur.execute(sql)
        if cur.rowcount > 0:
            view_def = cur.fetchone()

    # Prepare the cells of the table to print.
    cells = []
    for i, row in enumerate(res):
        cell = []
        cell.append(row[0])   # Column
        cell.append(row[1])   # Type

        if show_modifiers:
            modifier = ''
            if row[5]:
                modifier += ' collate %s' % row[5]
            if row[3]:
                modifier += ' not null'
            if row[2]:
                modifier += ' default %s' % row[2]

            cell.append(modifier)

        # Sequence
        if tableinfo.relkind == 'S':
            cell.append(seq_values[i])

        # Index column
        if TableInfo.relkind == 'i':
            cell.append(row[6])

        # /* FDW options for foreign table column, only for 9.2 or later */
        if tableinfo.relkind == 'f':
            cell.append(row[7])

        if verbose:
            storage = row[8]

            if storage[0] == 'p':
                cell.append('plain')
            elif storage[0] == 'm':
                cell.append('main')
            elif storage[0] == 'x':
                cell.append('extended')
            elif storage[0] == 'e':
                cell.append('external')
            else:
                cell.append('???')

            if (tableinfo.relkind == 'r' or tableinfo.relkind == 'm' or
                    tableinfo.relkind == 'f'):
                cell.append(row[9])

            #  /* Column comments, if the relkind supports this feature. */
            if (tableinfo.relkind == 'r' or tableinfo.relkind == 'v' or
                    tableinfo.relkind == 'm' or
                    tableinfo.relkind == 'c' or tableinfo.relkind == 'f'):
                cell.append(row[10])
        cells.append(cell)

    # Make Footers

    status = []
    if (tableinfo.relkind == 'i'):
        # /* Footer information about an index */

        if cur.connection.server_version > 90000:
            sql = """SELECT i.indisunique,
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
                            AND c.oid = '%s'
                            AND c.relam = a.oid
                            AND i.indrelid = c2.oid;
                """ % oid
        else:
            sql = """SELECT i.indisunique,
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
                            AND c.oid = '%s'
                            AND c.relam = a.oid
                            AND i.indrelid = c2.oid;
                """ % oid

        log.debug(sql)
        cur.execute(sql)

        (indisunique, indisprimary, indisclustered, indisvalid,
        deferrable, deferred, indamname, indtable, indpred) = cur.fetchone()

        if indisprimary:
            status.append("primary key, ")
        elif indisunique:
            status.append("unique, ")
        status.append("%s, " % indamname)

        #/* we assume here that index and table are in same schema */
        status.append('for table "%s.%s"' % (schema_name, indtable))

        if indpred:
            status.append(", predicate (%s)" % indpred)

        if indisclustered:
            status.append(", clustered")

        if indisvalid:
            status.append(", invalid")

        if deferrable:
            status.append(", deferrable")

        if deferred:
            status.append(", initially deferred")

        status.append('\n')
        #add_tablespace_footer(&cont, tableinfo.relkind,
                              #tableinfo.tablespace, true);

    elif tableinfo.relkind == 'S':
        # /* Footer information about a sequence */
        # /* Get the column that owns this sequence */
        sql = ("SELECT pg_catalog.quote_ident(nspname) || '.' ||"
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
                          "\n AND d.objid=%s \n AND d.deptype='a'" % oid)

        log.debug(sql)
        cur.execute(sql)
        result = cur.fetchone()
        if result:
            status.append("Owned by: %s" % result[0])

        #/*
         #* If we get no rows back, don't show anything (obviously). We should
         #* never get more than one row back, but if we do, just ignore it and
         #* don't print anything.
         #*/

    elif (tableinfo.relkind == 'r' or tableinfo.relkind == 'm' or
            tableinfo.relkind == 'f'):
        #/* Footer information about a table */

        if (tableinfo.hasindex):
            if cur.connection.server_version > 90000:
                sql = """SELECT c2.relname,
                                i.indisprimary,
                                i.indisunique,
                                i.indisclustered,
                                i.indisvalid,
                                pg_catalog.pg_get_indexdef(i.indexrelid, 0, true),
                                pg_catalog.pg_get_constraintdef(con.oid, true),
                                contype,
                                condeferrable,
                                condeferred,
                                c2.reltablespace,
                        FROM pg_catalog.pg_class c,
                            pg_catalog.pg_class c2,
                            pg_catalog.pg_index i
                        LEFT JOIN pg_catalog.pg_constraint con
                        ON conrelid = i.indrelid
                            AND conindid = i.indexrelid
                            AND contype IN ('p','u','x')
                        WHERE c.oid = '%s'
                            AND c.oid = i.indrelid
                            AND i.indexrelid = c2.oid
                        ORDER BY i.indisprimary DESC,
                            i.indisunique DESC,
                            c2.relname;
                    """ % oid
            else:
                sql = """SELECT c2.relname,
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
                        WHERE c.oid = '%s'
                            AND c.oid = i.indrelid
                            AND i.indexrelid = c2.oid
                        ORDER BY i.indisprimary DESC,
                            i.indisunique DESC,
                            c2.relname;
                    """ % oid

            log.debug(sql)
            result = cur.execute(sql)

            if (cur.rowcount > 0):
                status.append("Indexes:\n")
            for row in cur:

                #/* untranslated index name */
                status.append('    "%s"' % row[0])

                #/* If exclusion constraint, print the constraintdef */
                if row[7] == "x":
                    status.append(row[6])
                else:
                    #/* Label as primary key or unique (but not both) */
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
                    if (usingpos >= 0):
                        indexdef = indexdef[(usingpos + 7):]
                    status.append(" %s" % indexdef)

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

                status.append('\n')
                # printTableAddFooter(&cont, buf.data);

                # /* Print tablespace of the index on the same line */
                # add_tablespace_footer(&cont, 'i',
                # atooid(PQgetvalue(result, i, 10)),
                # false);

        # /* print table (and column) check constraints */
        if (tableinfo.checks):
            sql = ("SELECT r.conname, "
                    "pg_catalog.pg_get_constraintdef(r.oid, true)\n"
                    "FROM pg_catalog.pg_constraint r\n"
                    "WHERE r.conrelid = '%s' AND r.contype = 'c'\n"
                    "ORDER BY 1;" % oid)
            log.debug(sql)
            cur.execute(sql)
            if (cur.rowcount > 0):
                status.append("Check constraints:\n")
            for row in cur:
                #/* untranslated contraint name and def */
                status.append("    \"%s\" %s" % row)
            status.append('\n')

        #/* print foreign-key constraints (there are none if no triggers) */
        if (tableinfo.hastriggers):
            sql = ("SELECT conname,\n"
                    " pg_catalog.pg_get_constraintdef(r.oid, true) as condef\n"
                              "FROM pg_catalog.pg_constraint r\n"
                   "WHERE r.conrelid = '%s' AND r.contype = 'f' ORDER BY 1;" %
                   oid)
            log.debug(sql)
            cur.execute(sql)
            if (cur.rowcount > 0):
                status.append("Foreign-key constraints:\n")
            for row in cur:
                #/* untranslated constraint name and def */
                status.append("    \"%s\" %s\n" % row)

        #/* print incoming foreign-key references (none if no triggers) */
        if (tableinfo.hastriggers):
            sql = ("SELECT conrelid::pg_catalog.regclass, conname,\n"
                    "  pg_catalog.pg_get_constraintdef(c.oid, true) as condef\n"
                    "FROM pg_catalog.pg_constraint c\n"
                    "WHERE c.confrelid = '%s' AND c.contype = 'f' ORDER BY 1;" %
                    oid)
            log.debug(sql)
            cur.execute(sql)
            if (cur.rowcount > 0):
                status.append("Referenced by:\n")
            for row in cur:
                status.append("    TABLE \"%s\" CONSTRAINT \"%s\" %s\n" % row)

        # /* print rules */
        if (tableinfo.hasrules and tableinfo.relkind != 'm'):
            sql = ("SELECT r.rulename, trim(trailing ';' from pg_catalog.pg_get_ruledef(r.oid, true)), "
                              "ev_enabled\n"
                              "FROM pg_catalog.pg_rewrite r\n"
                              "WHERE r.ev_class = '%s' ORDER BY 1;" %
                              oid)
            log.debug(sql)
            cur.execute(sql)
            if (cur.rowcount > 0):
                for category in range(4):
                    have_heading = False
                    for row in cur:
                        if category == 0 and row[2] == 'O':
                            list_rule = True
                        elif category == 1 and row[2] == 'D':
                            list_rule = True
                        elif category == 2 and row[2] == 'A':
                            list_rule = True
                        elif category == 3 and row[2] == 'R':
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
                        status.append("    %s" % ruledef)

    if (view_def):
        #/* Footer information about a view */
        status.append("View definition:\n")
        status.append("%s \n" % view_def)

        #/* print rules */
        if tableinfo.hasrules:
            sql = ("SELECT r.rulename, trim(trailing ';' from pg_catalog.pg_get_ruledef(r.oid, true))\n"
                    "FROM pg_catalog.pg_rewrite r\n"
                    "WHERE r.ev_class = '%s' AND r.rulename != '_RETURN' ORDER BY 1;" % oid)

            log.debug(sql)
            cur.execute(sql)
            if (cur.rowcount > 0):
                status.append("Rules:\n")
                for row in cur:
                    #/* Everything after "CREATE RULE" is echoed verbatim */
                    ruledef = row[1]
                    status.append(" %s\n" % ruledef)


    #/*
    # * Print triggers next, if any (but only user-defined triggers).  This
    # * could apply to either a table or a view.
    # */
    if tableinfo.hastriggers:
        if cur.connection.server_version > 90000:
            sql = """SELECT t.tgname,
                        pg_catalog.pg_get_triggerdef(t.oid, true),
                        t.tgenabled
                   FROM pg_catalog.pg_trigger t
                   WHERE t.tgrelid = '%s' AND NOT t.tgisinternal
                   ORDER BY 1
                """ % oid
        else:
            sql = """SELECT t.tgname,
                        pg_catalog.pg_get_triggerdef(t.oid),
                        t.tgenabled
                   FROM pg_catalog.pg_trigger t
                   WHERE t.tgrelid = '%s'
                   ORDER BY 1
                """ % oid

        log.debug(sql)
        cur.execute(sql)
        if cur.rowcount > 0:
            #/*
            #* split the output into 4 different categories. Enabled triggers,
            #* disabled triggers and the two special ALWAYS and REPLICA
            #* configurations.
            #*/
            for category in range(4):
                have_heading = False;
                list_trigger = False;
                for row in cur:
                    #/*
                    # * Check if this trigger falls into the current category
                    # */
                    tgenabled = row[2]
                    if category ==0:
                        if (tgenabled == 'O' or tgenabled == True):
                            list_trigger = True
                    elif category ==1:
                        if (tgenabled == 'D' or tgenabled == False):
                            list_trigger = True
                    elif category ==2:
                        if (tgenabled == 'A'):
                            list_trigger = True
                    elif category ==3:
                        if (tgenabled == 'R'):
                            list_trigger = True
                    if list_trigger == False:
                        continue;

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
                        status.append('\n')
                        have_heading = True

                    #/* Everything after "TRIGGER" is echoed verbatim */
                    tgdef = row[1]
                    triggerpos = tgdef.find(" TRIGGER ")
                    if triggerpos >= 0:
                        tgdef = triggerpos + 9;

                    status.append("    %s\n" % row[1][tgdef:])

    #/*
    #* Finish printing the footer information about a table.
    #*/
    if (tableinfo.relkind == 'r' or tableinfo.relkind == 'm' or
            tableinfo.relkind == 'f'):
        # /* print foreign server name */
        if tableinfo.relkind == 'f':
            #/* Footer information about foreign table */
            sql = ("SELECT s.srvname,\n"
                   "       array_to_string(ARRAY(SELECT "
                   "       quote_ident(option_name) ||  ' ' || "
                   "       quote_literal(option_value)  FROM "
                   "       pg_options_to_table(ftoptions)),  ', ') "
                   "FROM pg_catalog.pg_foreign_table f,\n"
                   "     pg_catalog.pg_foreign_server s\n"
                   "WHERE f.ftrelid = %s AND s.oid = f.ftserver;" % oid)
            log.debug(sql)
            cur.execute(sql)
            row = cur.fetchone()

            # /* Print server name */
            status.append("Server: %s\n" % row[0])

            # /* Print per-table FDW options, if any */
            if (row[1]):
                status.append("FDW Options: (%s)\n" % row[1])

        #/* print inherited tables */
        sql = ("SELECT c.oid::pg_catalog.regclass FROM pg_catalog.pg_class c, "
                "pg_catalog.pg_inherits i WHERE c.oid=i.inhparent AND "
                "i.inhrelid = '%s' ORDER BY inhseqno;" % oid)

        log.debug(sql)
        cur.execute(sql)

        spacer = ''
        if cur.rowcount > 0:
            status.append("Inherits")
        for row in cur:
            status.append("%s: %s,\n" % (spacer, row))
            spacer = ' ' * len('Inherits')

        #/* print child tables */
        if cur.connection.server_version > 90000:
            sql =  """SELECT c.oid::pg_catalog.regclass
                        FROM pg_catalog.pg_class c,
                            pg_catalog.pg_inherits i
                        WHERE c.oid = i.inhrelid
                            AND i.inhparent = '%s'
                        ORDER BY c.oid::pg_catalog.regclass::pg_catalog.text;
                    """ % oid
        else:
            sql =  """SELECT c.oid::pg_catalog.regclass
                        FROM pg_catalog.pg_class c,
                            pg_catalog.pg_inherits i
                        WHERE c.oid = i.inhrelid
                            AND i.inhparent = '%s'
                        ORDER BY c.oid;
                    """ % oid

        log.debug(sql)
        cur.execute(sql)

        if not verbose:
            #/* print the number of child tables, if any */
            if (cur.rowcount > 0):
                status.append("Number of child tables: %d (Use \d+ to list"
                    "them.)\n" % cur.rowcount)
        else:
            spacer = ''
            if (cur.rowcount >0):
                status.append('Child tables')

            #/* display the list of child tables */
            for row in cur:
                status.append("%s: %s,\n" % (spacer, row))
                spacer = ' ' * len('Child tables')

        #/* Table type */
        if (tableinfo.reloftype):
            status.append("Typed table of type: %s\n" % tableinfo.reloftype)

        #/* OIDs, if verbose and not a materialized view */
        if (verbose and tableinfo.relkind != 'm'):
            status.append("Has OIDs: %s\n" %
                    ("yes" if tableinfo.hasoids else "no"))


        #/* Tablespace info */
        #add_tablespace_footer(&cont, tableinfo.relkind, tableinfo.tablespace,
                              #true);

    # /* reloptions, if verbose */
    if (verbose and tableinfo.reloptions):
        status.append("Options: %s\n" % tableinfo.reloptions)

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
    relname = ''
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
        elif not inquotes and c == '*':
            relname += '.*'
        elif not inquotes and c == '?':
            relname += '.'
        elif not inquotes and c == '.':
            # Found schema/name separator, move current pattern to schema
            schema = relname
            relname = ''
        else:
            # Dollar is always quoted, whether inside quotes or not.
            if c == '$' or inquotes and c in '|*+?()[]{}.^\\':
                relname += '\\'
            relname += c
        i += 1

    if relname:
        relname = '^(' + relname + ')$'

    if schema:
        schema = '^(' + schema + ')$'

    return schema, relname
