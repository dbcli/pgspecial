1.6.0
=====

Features:
---------

* Add a function to extract the sql from `\watch` command. (Thanks: `stuartquin`_)

1.5.0
=====

Features:
---------

* Add support for `\db` command. (Thanks: `Irina Truong`_)

1.4.0
=====

Features:
---------

* Add support for `\copy` command. (Thanks: `Catherine Devlin`_)
* Add support for `\dx` command. (Thanks: `Darik Gamble`_)

1.3.0
=====

Features:
---------

* Add initial support for Postgres 8.4 and above.(Thanks: `Timothy Cleaver`_, darikg_). 
  This enables us to add support for Amazon Redshift. If things look broken please report.

* Add \pset pager command. (Thanks: `pik`_).

Bug fixes:
----------

* Fix 'ftoptions' not defined error with FDW. (Thanks: `François Pietka`_).


1.2.0
=====

Features:
---------

* Add support for ``\h``. (Thanks: `stuartquin`_)
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
.. _`stuartquin`: https://github.com/stuartquin
.. _`darikg`: https://github.com/darikg
.. _`Timothy Cleaver`: Timothy Cleaver
.. _`François Pietka`: https://github.com/fpietka
.. _`pik`: https://github.com/pik
.. _`Catherine Devlin`: https://github.com/catherinedevlin
.. _`Darik Gamble`: https://github.com/darikg
.. _`Irina Truong`: https://github.com/j-bennet
