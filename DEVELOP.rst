Development Guide
-----------------
This is a guide for developers who would like to contribute to this project.

GitHub Workflow
---------------

If you're interested in contributing to pgcli, first of all my heart felt
thanks. `Fork the project <https://github.com/dbcli/pgspecial>`_ in github.
Then clone your fork into your computer (``git clone <url-for-your-fork>``).
Make the changes and create the commits in your local machine. Then push those
changes to your fork. Then click on the pull request icon on github and create
a new pull request. Add a description about the change and send it along. I
promise to review the pull request in a reasonable window of time and get back
to you. 

In order to keep your fork up to date with any changes from mainline, add a new
git remote to your local copy called 'upstream' and point it to the main
``pgspecial`` repo.

:: 

   $ git remote add upstream git@github.com:dbcli/pgspecial.git

Once the 'upstream' end point is added you can then periodically do a ``git
pull upstream master`` to update your local copy and then do a ``git push
origin master`` to keep your own fork up to date. 

Local Setup
-----------

The installation instructions in the README file are intended for users of
``pgspecial``. If you're developing ``pgspecial``, you'll need to install it in
a slightly different way so you can see the effects of your changes right away
without having to go through the install cycle every time you change the code.

It is highly recommended to use virtualenv for development. If you don't know
what a virtualenv is, this `guide
<http://docs.python-guide.org/en/latest/dev/virtualenvs/#virtual-environments>`_
will help you get started.

Create a virtualenv (let's call it ``pgspecial-dev``). Activate it:

::

    virtualenv ./pgspecial-dev
    source ./pgspecial-dev/bin/activate

Once the virtualenv is activated, `cd` into the local clone of pgspecial folder
and install pgspecial using pip as follows:

::

    $ pip install --editable .

    or

    $ pip install -e .

This will install the necessary dependencies as well as install pgspecial from
the working folder into the virtualenv. By installing it using `pip install -e`
we've linked the pgspecial installation with the working copy. So any changes
made to the code is immediately available in the installed version of
pgspecial.

Adding PostgreSQL Special (Meta) Commands
-----------------------------------------

If you want to add a new meta-command, you'll write a function that accepts 3
parameters. Then you'll mark it with a ``@special_command`` decorator. For
an example, look at ``list_roles`` in ``dbcommands.py``:

  ::

    @special_command('\\du', '\\du[+] [pattern]', 'List roles.')
    def list_roles(cur, pattern, verbose):
        # some code here
        return [(None, cur, headers, cur.statusmessage)]

Things to note:

* Your function should return 4 items: ``title, cur, headers, status``.
* ``title`` is optional. It is something you can print out as first line of your
  output.
* ``cur`` is cursor that contains records to iterate.
* ``headers`` is result table's list of column headers.
* ``status`` is optional. If provided, it will be printed out last.

Now, take a closer look at the decorator. The first item in a tuple of
arguments is the command's name. It should be unique. The second item is this
command's syntax. The third item in the tuple is a string which is
the documentation for that special command.

The example command here, ``\du``, is a meta-command that lists all roles in
the databases. The way you can see the SQL statement issued by PostgreSQL when
this command is executed is to launch `psql -E` and entering ``\du``.

That will print the results and also print the sql statement that was executed
to produce that result. In most cases it's a single sql statement, but
sometimes it's a series of sql statements that feed the results to each other
to get to the final result.

Running the tests
-----------------

The tests are using default user ``postgres`` at ``localhost``, without
the password (authentication mode ``trust``). This can be changed in
``tests/db_utils.py``.

First, install the requirements for testing:

::

    $ pip install -r requirements-dev.txt

After that, tests can be run with:

::

    $ cd tests
    $ py.test

Enforcing the code style (linting)
------------------------------

When you submit a PR, the changeset is checked for pep8 compliance using
`black <https://github.com/psf/black>`_. If you see a build failing because
of these checks, install ``black`` and apply style fixes:

::

    $ pip install black
    $ black .

Then commit and push the fixes.

To enforce ``black`` applied on every commit, we also suggest installing ``pre-commit`` and
using the ``pre-commit`` hooks available in this repo:

::

    $ pip install pre-commit
    $ pre-commit install

Git blame
---------

Use ``git blame my_file.py --ignore-revs-file .git-blame-ignore-revs`` to exclude irrelevant commits
(specifically Black) from ``git blame``. For more information,
see `here <https://github.com/psf/black#migrating-your-code-style-without-ruining-git-blame>`_.
