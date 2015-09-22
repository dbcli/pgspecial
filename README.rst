Meta-commands for Postgres
--------------------------

|BuildStatus|  |PyPI|

This package provides an API to execute meta-commands (AKA "special", or
"backslash commands") on PostgreSQL.

Quick Start
-----------

This is a python package. It can be installed with:

::

    $ pip install pgspecial


Usage
-----

Once this library is included into your project, you will most likely use the
following imports:

::

    from pgspecial.main import PGSpecial
    from pgspecial.namedqueries import NamedQueries

Then you will create and use an instance of PGSpecial:

::

        pgspecial = PGSpecial()
        for result in pgspecial.execute(cur, sql):
            # Do something

If you want to import named queries from an existing config file, it is
convenient to initialize and keep around the class variable in
``NamedQueries``:

::

    from configobj import ConfigObj

    NamedQueries.instance = NamedQueries.from_config(
        ConfigObj('~/.config_file_name'))

Contributions:
--------------

If you're interested in contributing to this project, first of all I would like
to extend my heartfelt gratitude. I've written a small doc to describe how to
get this running in a development setup.

https://github.com/dbcli/pgspecial/blob/master/DEVELOP.rst

Please feel free to reach out to me if you need help.
My email: amjith.r@gmail.com, Twitter: `@amjithr <http://twitter.com/amjithr>`_

.. |BuildStatus| image:: https://api.travis-ci.org/dbcli/pgspecial.svg?branch=master
    :target: https://travis-ci.org/dbcli/pgspecial

.. |PyPI| image:: https://pypip.in/version/pgspecial/badge.svg
    :target: https://pypi.python.org/pypi/pgspecial/
    :alt: Latest Version
