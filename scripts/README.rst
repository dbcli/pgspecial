Scripts
--------------------------

**docparser.py**

Parses SGML files containing Postgres command information and converts them
into a JSON data structure, this is the converted into a python dictionary
and saved to `pgspecial/help/commands.py`

This should me manually ran and the results committed after each new release
of the main Postgres project.

SGML files can be found: https://github.com/postgres/postgres/tree/master/doc/src/sgml/ref
Grab a copy of this directory on your local system.

**Usage**

::
    pip install beautifulsoup4
    # From root of project
    echo -n "helpcommands = " > pgspecial/help/commands.py; python scripts/docparser.py ref/ | python -mjson.tool | sed 's/"\: null/": None/g' >> pgspecial/help/commands.py
