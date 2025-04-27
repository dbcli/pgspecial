
2.2.0 (2025-04-27)
==================

* Moderize the repository
  * Use uv instead of pip
  * Use github trusted publisher for pypi release

2.1.3 (2024-11-25)
==================

* Made `\copy` case-insensitive, as it is in `psql`.

2.1.2 (2024-05-15)
==================

Bug fixes:
----------
* Fix `\d` when used with a pattern

2.1.1 (2023-10-29)
==================

* Added `build-system` section to `pyproject.toml` to use the modern setuptools backend.
* Fix SyntaxWarning with Python 3.12.
* Fix test_slash_l* to support non-en_US locales (https://github.com/dbcli/pgspecial/issues/140).
* Release script uses `build` module.

2.1.0 (2023-03-31)
=========

* Fixed displaying verbose view definitions when running `\d+`.
* Use psycopg.sql for constructing queries.

2.0.1 (2022-06-17):
===================

Internal:
---------
* Added argument to open_external_editor to specifiy desired editor.

2.0.0 (2022-06-03):
===================

Bug fixes:
----------

* Add `pytest` mark `dbtest` to `test_slash_dp_pattern_schema` so it can be skipped when necessary. (Thanks: `Benjamin Beasley`_)

Internal:
---------

* Switch to psycopg3 - breaking change.

1.13.1
======

Bug fixes:
----------

* Throw an exception if the TO/FROM keyword is missing in the `\copy` command. (Thanks: `Amjith`_)
* Allow multiline SQL and use default of 2s timing for the `\watch` command. (Thanks: `Saif Hakim`_)
* Fix for the `\dp` metacommand to properly work with the schema name as pattern (Thanks: `Roberto Dedoro`_)

Internal:
---------

* Drop unused dev/test dependency on mock (Thanks: `Benjamin Beasley`_).

1.13.0
======

Features:
---------

* Add support for the `\ddp` metacommand that lists the default privileges of Postgres objects (Thanks: `Roberto Dedoro`_)
* Add support for named query positional parameters aggregation (Thanks: `Guilhem Charles`_)

1.12.1
======

* Fix for broken `MANIFEST.in` that prevented source installation (#101. Thanks: `Dave Hirschfeld`_).

Bug fixes:
----------

* Fix deprecation warnings with stricter backslash escaping in strings. (Thanks: `Benjamin Beasley`_)

1.12.0
======

Features:
---------

* Add support for the `\dp` metacommand that lists the privileges of Postgres objects (Thanks: `Guru Devanla`_)
* Add support for the `\np <named_query_pattern>` metacommand that returns named queries matching the pattern (Thanks: `Guru Devanla`_)

Internal:
---------

* Use Black to format the code and run CI style checks.

1.11.10
======

Bug fixes:
----------

* Allows `\d foo` to display information about `IDENTITY` columns. (Thanks: `Denis Gantsev`_)


1.11.9
======

Bug fixes:
----------

* Fix for `\d foo` command crash in PostgreSQL 12. (Thanks: `Irina Truong`_)

1.11.8
======

Bug fixes:
----------

* ``\d some_schema.some_table`` will now work when ``some_schema`` is not in your ``search_path``.

1.11.7
======

Internal:
----------

* Allow usage of newer versions of psycopg2. (Thanks: `Aluísio Augusto Silva Gonçalves`_).

1.11.6
======

Bug fixes:
----------

* Scope the results of `\d foo` command to the current schema. (Thanks: `Amjith Ramanujam`_)

Internal:
---------

* Add missing psycopg2 dependency. (Thanks: `Dick Marinus`_).
* Fix issues when using the ``\dx+`` command. (Thanks: `Ignacio Campabadal`_).

1.11.5
=======

Features:
---------

* Add support for the ``\!`` command. (Thanks: `Ignacio Campabadal`_).
* Add support for describing text search configurations `\dF``. (Thanks: `Ignacio Campabadal`_).
* Add support for the ``\dE`` command. (Thanks: `Catherine Devlin`_).

1.11.4
=======

Bug fixes:
----------

* Fixed broken completion for special commands with prompt-toolkit 2.0. (Thanks: `Amjith Ramanujam`_)

1.11.3
=======

Bug fixes:
----------

* Fixed the IndexError caused by ``\ef`` without a function name. (Thanks: `Amjith Ramanujam`_)

1.11.2
======

Bug fixes:
----------

* Support for PG 10 partitioning and fix for https://github.com/OmniDB/OmniDB/issues/424. (Thanks: `William Ivanski`_).

1.11.1
======

Bug fixes:
----------

* Remove pycache files from release (Thanks: `Dick Marinus`_).
* Fix ``\df`` under PG11. (Thanks: `Lele Gaifax`_).

1.11.0
======

Features:
---------

* Add support for ``\ev``, ``\ef`` commands. (Thanks: `Catherine Devlin`_).

Bug fixes:
----------

* Avoid the need to escape "%" in named queries (dbcli/pgcli#865). (Thanks: `Jason Ribeiro`_).

1.10.0
======

Features:
---------

* Add support for ``\dD`` command. (Thanks: `Lele Gaifax`_).
* Add support parameter $1...$n in query (Thanks: `Frederic Aoustin`_).

Bug fixes:
----------

* Fix listing of table inheritance in ``\d`` command. (Thanks: `Lele Gaifax`_).

1.9.0
=====

Features:
---------

* Change ``\l`` command behavior, and add ``\list`` alias. (Thanks: `François Pietka`_).

Bug fixes:
----------

* Be less strict when searching for the ``\watch`` command. (Thanks: `Irina Truong`_).
* Fix glitch in ``EXCLUDE`` index description emitted by ``\d`` command. (Thanks: `Lele Gaifax`_).
* Fix ``\e`` command handling. (Thanks: `François Pietka`_).
* Fix UnicodeEncodeError when opening sql statement in editor (Thanks: `Klaus Wünschel`_).
* Fix listing of child tables in ``\d`` command. (Thanks: `Lele Gaifax`_).

1.8.0
=====

Features:
---------

* Implement ``\sf+`` function_name. (Thanks: `Lele Gaifax`_).
* Separate check constraints with newlines. (Thanks: `Joakim Koljonen`_).
* Enabled ``\dm`` command, corrections to ``\d+``, extended tests. (Thanks: `rsc`_).
* Opening an external editor will edit default text. (Thanks: `Thomas Roten`_).


1.7.0
=====

Features:
---------

* Handling saved queries with parameters. (Thanks: `Marcin Sztolcman`_).

Bug fixes:
----------

* Fix bug where ``\d`` called valid indices invalid & vice versa. (Thanks: `Joakim Koljonen`_).
* Fix typo in ``pset`` description. (Thanks: `Lele Gaifax`_).

1.6.0
=====

Features:
---------

* Add a function to extract the sql from ``\watch`` command. (Thanks: `stuartquin`_).

1.5.0
=====

Features:
---------

* Add support for ``\db`` command. (Thanks: `Irina Truong`_).

1.4.0
=====

Features:
---------

* Add support for ``\copy`` command. (Thanks: `Catherine Devlin`_).
* Add support for ``\dx`` command. (Thanks: `Darik Gamble`_).

1.3.0
=====

Features:
---------

* Add initial support for Postgres 8.4 and above.(Thanks: `Timothy Cleaver`_, darikg_).
  This enables us to add support for Amazon Redshift. If things look broken please report.

* Add ``\pset`` pager command. (Thanks: `pik`_).

Bug fixes:
----------

* Fix 'ftoptions' not defined error with FDW. (Thanks: `François Pietka`_).


1.2.0
=====

Features:
---------

* Add support for ``\h``. (Thanks: `stuartquin`_).
  Users can now run ``\h [keyword]`` to checkout the help for a keyboard.

1.1.0
=====

Features:
---------

* Support for ``\x auto`` by `stuartquin`_ with `darikg`_ (ported over from `pgcli`_).

1.0.0
=====

Features:
---------

* First release as an independent package.

.. _`pgcli`: https://github.com/dbcli/pgcli
.. _`Amjith Ramanujam`: https://github.com/amjith
.. _`stuartquin`: https://github.com/stuartquin
.. _`darikg`: https://github.com/darikg
.. _`Timothy Cleaver`: Timothy Cleaver
.. _`François Pietka`: https://github.com/fpietka
.. _`pik`: https://github.com/pik
.. _`Darik Gamble`: https://github.com/darikg
.. _`Irina Truong`: https://github.com/j-bennet
.. _`Joakim Koljonen`: https://github.com/koljonen
.. _`Marcin Sztolcman`: https://github.com/msztolcman
.. _`Thomas Roten`: https://github.com/tsroten
.. _`Lele Gaifax`: https://github.com/lelit
.. _`rsc`: https://github.com/rafalcieslinski
.. _`Klaus Wünschel`: https://github.com/kwuenschel
.. _`Frederic Aoustin`: https://github.com/fraoustin
.. _`Catherine Devlin`: https://github.com/catherinedevlin
.. _`Jason Ribeiro`: https://github.com/jrib
.. _`Dick Marinus`: https://github.com/meeuw
.. _`William Ivanski`: https://github.com/wind39
.. _`Aluísio Augusto Silva Gonçalves`: https://github.com/AluisioASG
.. _`Ignacio Campabadal`: https://github.com/igncampa
.. _`Dave Hirschfeld`: https://github.com/dhirschfeld
.. _`Roberto Dedoro`: https://github.com/mirobertod
.. _`Guilhem Charles`: https://github.com/chagui
.. _`Benjamin Beasley`: https://github.com/musicinmybrain
