from __future__ import unicode_literals
import logging
import shlex
import subprocess
from collections import namedtuple

from psycopg.sql import SQL
import aiosql
from .main import special_command

queries = aiosql.from_path("dbcommands.sql", "psycopg2")

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
    pattern = pattern or ".*"
    if verbose:
        cur.execute(queries.list_databases_verbose.sql, (pattern,))
    else:
        cur.execute(queries.list_databases.sql, (pattern,))

    headers = [x.name for x in cur.description] if cur.description else None
    return [(None, cur, headers, cur.statusmessage)]


@special_command("\\du", "\\du[+] [pattern]", "List roles.")
def list_roles(cur, pattern, verbose):
    """Returns (title, rows, headers, status)"""

    pattern = pattern or ".*"
    if cur.connection.info.server_version > 90000:
        if verbose:
            cur.execute(queries.list_roles_9_verbose.sql, (pattern,))
        else:
            cur.execute(queries.list_roles_9.sql, (pattern,))
    else:
        cur.execute(queries.list_roles.sql)

    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dp", "\\dp [pattern]", "List privileges.", aliases=("\\z",))
def list_privileges(cur, pattern, verbose):
    """Returns (title, rows, headers, status)"""
    param = bool(pattern)
    schema, table = sql_name_pattern(pattern)
    schema = schema or ".*"
    table = table or ".*"
    cur.execute(
        queries.list_privileges.sql,
        (param, table, schema),
    )
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\ddp", "\\ddp [pattern]", "Lists default access privilege settings.")
def list_default_privileges(cur, pattern, verbose):
    """Returns (title, rows, headers, status)"""

    pattern = f"^({pattern})$" if pattern else ".*"
    cur.execute(queries.list_default_privileges.sql, (pattern, pattern))
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\db", "\\db[+] [pattern]", "List tablespaces.")
def list_tablespaces(cur, pattern, **_):
    """Returns (title, rows, headers, status)"""

    pattern = pattern or ".*"
    cur.execute(queries.list_tablespaces.sql, {"pattern": pattern})

    headers = [x.name for x in cur.description] if cur.description else None
    return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dn", "\\dn[+] [pattern]", "List schemas.")
def list_schemas(cur, pattern, verbose):
    """Returns (title, rows, headers, status)"""
    pattern = pattern or ".*"
    if verbose:
        cur.execute(queries.list_schemas_verbose.sql, {"pattern": pattern})
    else:
        cur.execute(queries.list_schemas.sql, {"pattern": pattern})

    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


# https://github.com/postgres/postgres/blob/master/src/bin/psql/describe.c#L5471-L5638
@special_command("\\dx", "\\dx[+] [pattern]", "List extensions.")
def list_extensions(cur, pattern, verbose):
    def _find_extensions(cur, pattern):
        _, schema = sql_name_pattern(pattern)

        cur.execute(queries.find_extensions.sql, {"schema": schema or ".*"})
        return cur.fetchall()

    def _describe_extension(cur, oid):
        cur.execute(queries.describe_extension.sql, {"oid": oid})

        headers = [x.name for x in cur.description]
        return cur, headers, cur.statusmessage

    if cur.connection.info.server_version < 90100:
        not_supported = "Server versions below 9.1 do not support extensions."
        cur, headers = [], []
        yield None, cur, None, not_supported
        return

    if verbose:
        # TODO - use the join query instead of looping.
        # May need refactoring some more code.
        # cur.execute(queries.list_extensions_verbose.sql, {"pattern": pattern})
        extensions = _find_extensions(cur, pattern)

        if extensions:
            for ext_name, oid in extensions:
                title = f'''\nObjects in extension "{ext_name}"'''
                cur, headers, status = _describe_extension(cur, oid)
                yield title, cur, headers, status
        else:
            yield None, None, None, f"""Did not find any extension named "{pattern}"."""
        return

    if pattern:
        _, pattern = sql_name_pattern(pattern)
    else:
        pattern = ".*"

    cur.execute(queries.list_extensions.sql, {"pattern": pattern})

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
    if pattern:
        schema_pattern, table_pattern = sql_name_pattern(pattern)
    else:
        schema_pattern, table_pattern = ".*", ".*"
    params = {
        "schema_pattern": schema_pattern,
        "table_pattern": table_pattern,
        "relkinds": relkinds,
    }
    if verbose:
        cur.execute(queries.list_objects_verbose.sql, params)
    else:
        cur.execute(queries.list_objects.sql, params)

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
    schema_pattern, function_pattern = sql_name_pattern(pattern)
    params = {
        "schema_pattern": schema_pattern or ".*",
        "function_pattern": function_pattern or ".*",
    }

    if cur.connection.info.server_version >= 110000:
        if verbose:
            cur.execute(queries.list_functions_verbose_11.sql, params)
        else:
            cur.execute(queries.list_functions_11.sql, params)
    elif cur.connection.info.server_version > 90000:
        if verbose:
            cur.execute(queries.list_functions_verbose_9.sql, params)
        else:
            cur.execute(queries.list_functions_9.sql, params)
    else:
        if verbose:
            cur.execute(queries.list_functions_verbose.sql, params)
        else:
            cur.execute(queries.list_functions.sql, params)

    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dT", "\\dT[S+] [pattern]", "List data types")
def list_datatypes(cur, pattern, verbose):
    schema_pattern, type_pattern = sql_name_pattern(pattern)

    params = {
        "schema_pattern": schema_pattern or ".*",
        "type_pattern": type_pattern or ".*",
    }
    if cur.connection.info.server_version > 90000:
        if verbose:
            cur.execute(queries.list_datatypes_verbose_9.sql, params)
        else:
            cur.execute(queries.list_datatypes_9.sql, params)
    else:
        if verbose:
            cur.execute(queries.list_datatypes_verbose.sql, params)
        else:
            cur.execute(queries.list_datatypes.sql, params)

    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dD", "\\dD[+] [pattern]", "List or describe domains.")
def list_domains(cur, pattern, verbose):
    schema_pattern, name_pattern = sql_name_pattern(pattern)
    params = {"schema_pattern": schema_pattern or ".*", "pattern": name_pattern or ".*"}
    if verbose:
        cur.execute(queries.list_domains_verbose.sql, params)
    else:
        cur.execute(queries.list_domains.sql, params)
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]


@special_command("\\dF", "\\dF[+] [pattern]", "List text search configurations.")
def list_text_search_configurations(cur, pattern, verbose):
    def _find_text_search_configs(cur, pattern):
        _, schema = sql_name_pattern(pattern)
        cur.execute(queries.find_text_search_configs.sql, {"schema": schema})

        return cur.fetchall()

    def _fetch_oid_details(cur, oid):
        cur.execute(queries.fetch_oid_details.sql, {"oid": oid})
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
            yield (
                None,
                None,
                None,
                'Did not find any results for pattern "{}".'.format(pattern),
            )
        return

    _, schema = sql_name_pattern(pattern)
    cur.execute(queries.list_text_search_configurations.sql, {"schema": schema})

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
    schema = ".*" if not schema else schema
    relname = ".*" if not relname else relname

    # Execute the sql, get the results and call describe_one_table_details on each table.

    cur.execute(
        queries.describe_table_details.sql, {"nspname": schema, "relname": relname}
    )
    if not (cur.rowcount > 0):
        return [(None, None, None, f"Did not find any relation named {pattern}.")]

    results = []
    for oid, nspname, relname in cur.fetchall():
        results.append(describe_one_table_details(cur, nspname, relname, oid, verbose))

    return results


def describe_one_table_details(cur, schema_name, relation_name, oid, verbose):
    params = {"oid": oid}
    if cur.connection.info.server_version >= 120000:
        cur.execute(queries.describe_one_table_details_12.sql, params)
    elif cur.connection.info.server_version >= 100000:
        cur.execute(queries.describe_one_table_details_10.sql, params)
    elif cur.connection.info.server_version > 90000:
        cur.execute(queries.describe_one_table_details_9.sql, params)
    elif cur.connection.info.server_version >= 80400:
        cur.execute(queries.describe_one_table_details_804.sql, params)
    elif cur.connection.info.server_version >= 80200:
        cur.execute(queries.describe_one_table_details_802.sql, params)
    else:
        cur.execute(queries.describe_one_table_details.sql, params)

    if cur.rowcount > 0:
        # TODO if not verbose - drop suffix
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

    if cur.connection.info.server_version >= 120000:
        cur.execute(queries.get_footer_info_12.sql, params)
    elif cur.connection.info.server_version >= 110000:
        cur.execute(queries.get_footer_info_11.sql, params)
    elif cur.connection.info.server_version >= 100000:
        cur.execute(queries.get_footer_info_10.sql, params)
    elif cur.connection.info.server_version >= 90200:
        cur.execute(queries.get_footer_info_902.sql, params)
    elif cur.connection.info.server_version >= 90100:
        cur.execute(queries.get_footer_info_901.sql, params)
    else:
        cur.execute(queries.get_footer_info.sql, params)

    res = cur.fetchall()
    att_cols = {x.name: i for i, x in enumerate(cur.description)}

    # Set the column names.
    headers = ["Column", "Type"]

    show_modifiers = False
    if tableinfo.relkind in ["r", "p", "v", "m", "f", "c"]:
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
        if tableinfo.relkind in ["r", "m", "f"]:
            headers.append("Stats target")
        #  Column comments, if the relkind supports this feature. */
        if tableinfo.relkind in ["r", "v", "m", "c", "f"]:
            # do something
            headers.append("Description")

    view_def = ""
    # /* Check if table is a view or materialized view */
    if (tableinfo.relkind == "v" or tableinfo.relkind == "m") and verbose:
        cur.execute(queries.get_view_definition.sql, params)
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

            # the logic had additional types when adding to the query
            # but it was only used with the ones here.
            if tableinfo.relkind in ["r", "m", "f"]:  #  ["i", "I", "p"]
                cell.append(row[att_cols["attstattarget"]])

            #  /* Column comments, if the relkind supports this feature. */
            if tableinfo.relkind in ["r", "v", "m", "c", "f"]:  # ["p"]
                cell.append(row[att_cols["attdescr"]])
        cells.append(cell)
    # Make Footers

    status = []
    if tableinfo.relkind == "i":
        # /* Footer information about an index */

        if cur.connection.info.server_version > 90000:
            cur.execute(queries.footer_index_information_9.sql, params)
        else:
            cur.execute(queries.footer_index_information.sql, params)

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
        cur.execute(queries.get_sequence_column_name.sql, params)
        result = cur.fetchone()
        if result:
            status.append(f"Owned by: {result[0]}")

        # /*
        # * If we get no rows back, don't show anything (obviously). We should
        # * never get more than one row back, but if we do, just ignore it and
        # * don't print anything.
        # */

    elif tableinfo.relkind in ["r", "p", "m", "f"]:
        # do something
        # /* Footer information about a table */

        if tableinfo.hasindex:
            if cur.connection.info.server_version > 90000:
                cur.execute(queries.get_footer_table_index_information_9.sql, params)
            else:
                cur.execute(queries.get_footer_table_index_information.sql, params)

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

        # /* print table (and column) check constraints */
        if tableinfo.checks:
            cur.execute(queries.get_check_constraints.sql, params)
            if cur.rowcount > 0:
                status.append("Check constraints:\n")
            for row in cur:
                # /* untranslated contraint name and def */
                status.append(f"""    "{row[0]}" {row[1]}""")
                status.append("\n")

        # /* print foreign-key constraints (there are none if no triggers) */
        if tableinfo.hastriggers:
            cur.execute(queries.get_foreign_key_constraints.sql, params)
            if cur.rowcount > 0:
                status.append("Foreign-key constraints:\n")
            for row in cur:
                # /* untranslated constraint name and def */
                status.append(f"""    "{row[0]}" {row[1]}\n""")

        # /* print incoming foreign-key references (none if no triggers) */
        if tableinfo.hastriggers:
            cur.execute(queries.get_foreign_key_references.sql, params)
            if cur.rowcount > 0:
                status.append("Referenced by:\n")
            for row in cur:
                status.append(
                    f"""    TABLE "{row[0]}" CONSTRAINT "{row[1]}" {row[2]}\n"""
                )

        # /* print rules */
        if tableinfo.hasrules and tableinfo.relkind != "m":
            cur.execute(queries.get_foreign_key_references.sql, params)
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
            cur.execute(queries.get_partintion_info.sql, params)
            for row in cur:
                status.append(f"Partition of: {row[0]}\n")
                status.append(f"Partition constraint: {row[1]}\n")

        if tableinfo.relkind == "p":
            # /* print partition key */
            cur.execute(queries.get_partintion_key.sql, params)
            for row in cur:
                status.append(f"Partition key: {row[0]}\n")
            # /* print list of partitions */
            cur.execute(queries.get_partintions_list.sql, params)
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
            cur.execute(queries.get_view_rules.sql, params)
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
            cur.execute(queries.get_triggers_info_9.sql, params)
        else:
            cur.execute(queries.get_triggers_info.sql, params)
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
                        if tgenabled == "O" or tgenabled is True:
                            list_trigger = True
                    elif category == 1:
                        if tgenabled == "D" or tgenabled is False:
                            list_trigger = True
                    elif category == 2:
                        if tgenabled == "A":
                            list_trigger = True
                    elif category == 3:
                        if tgenabled == "R":
                            list_trigger = True
                    if list_trigger is False:
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
            cur.execute(queries.get_foreign_table_name.sql, params)
            row = cur.fetchone()

            # /* Print server name */
            status.append(f"Server: {row[0]}\n")

            # /* Print per-table FDW options, if any */
            if row[1]:
                status.append(f"FDW Options: ({row[1]})\n")

        # /* print inherited tables */
        if not tableinfo.relispartition:
            cur.execute(queries.get_foreign_inherited_tables.sql, params)
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
            cur.execute(queries.get_foreign_child_tables_9.sql, params)
        else:
            cur.execute(queries.get_foreign_child_tables.sql, params)
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
    cur.execute(
        queries.show_function_definition.sql,
        {"pattern": pattern},
    )
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
    _, tbl_name = sql_name_pattern(pattern)
    pattern = f"^({tbl_name})$" if tbl_name else ".*"
    if verbose:
        cur.execute(queries.list_foreign_tables_verbose.sql, {"pattern": pattern})
    else:
        cur.execute(queries.list_foreign_tables.sql, {"pattern": pattern})
    if cur.description:
        headers = [x.name for x in cur.description]
        return [(None, cur, headers, cur.statusmessage)]
    else:
        return [(None, None, None, cur.statusmessage)]
