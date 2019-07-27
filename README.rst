`cfgs`
-------------

Simple, correct handling of config, data and cache files
==================================================================

Like everyone else, I wrote a lot of programs which saved config files
as dotfiles in the user's home directory like ``~/.my-program-name`` and now
everyone's home directory has dozens of these.

Then I read
`this article <https://0x46.net/thoughts/2019/02/01/dotfile-madness/>`_.

Great was my embarrasment to discover that there was a
`neat little specification <https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html>`_
for data, config and cache directories in Linux that prevents this problem, and
that I was not using it:

So I implemented a small and simple Python API as a single file, ``cfgs.py``.

It works on all versions of Python from 2.7 to 3.7, has complete test coverage,
and all the functionality is reachable from a single class, ``cfgs.App``

How it works in one sentence
===========================================

Create a ``cfgs.App`` for your application, project, or script which
handles finding, reading and writing your data and config files, and
managing your cache directories.

How to install
=====================

You can either use pip:

.. code-block:: bash

    pip install cfgs

Or if you don't like dependencies (and who does?), you can drop the source file
`cgfs.py <https://raw.githubusercontent.com/timedata-org/cfgs/master/cfgs.py>`_
right into your project.


Usage examples
==================

.. code-block:: python

    import cfgs
    app = cfgs.App('my-project')
    print(app.xdg.XDG_CACHE_HOME)
    #   /home/tom/.cache/my-project

    app.xdg.XDG_CONFIG_DIRS
    #   /etc/xdg

    with app.config.open() as f:
        f.update(name='oliver', species='dog')
        f['description'] = {'size': 'S', 'fur': 'brown'}
        print(f.filename)
    #    /home/tom/.cache/my-project/my-project.json

    # Later:
    with app.config.open() as f:
        print(f['name'])
    #    oliver

        print(f.as_dict())
    #     {'name': 'oliver', 'species': 'dog',
    #      'description': {'size': 'S', 'fur': 'brown'}


Cache
======

.. code-block:: python

    import cfgs
    cache_size = 0x10000000
    app = cfgs.App('my-project')
    directory = app.cache.directory(cache_size=cache_size)
    # TODO: rewrite cache or add features.


Using ``cfgs`` In legacy code
=============================

If you already have code to handle your config, data and cache files, then you
can just use ``cgfs`` to get the
`XDG variables <https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html>`_

.. code-block:: python

    from cfgs import XDG

    xdg = XDG()
    config_dir = xdg.XDG_CONFIG_HOME

    # Your code here - eg:
    my_config_file = os.path.join(config_dir, 'my-file.json')
    with open(my_config_file) as f:
        legacy_write_my_file(f)


``cfgs`` automatically handles data and config files, and independently, cache
directories.


API Documentation
======================

API documentation is `here <https://timedata-org.github.io/cfgs/cfgs.html>`_.

--------------------------------------

====== ======
|pic1| |pic2|
====== ======


.. |pic2| image::
          https://img.shields.io/travis/timedata-org/cfgs/master.svg?style=flat

.. |pic1| image:: https://img.shields.io/pypi/pyversions/cfgs.svg?style=flat
