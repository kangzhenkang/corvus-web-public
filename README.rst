Corvus Web
==========

**Public preview version** of `corvus-web`.
A Redis Cluster administration dashboard.

Warning
-------

This is the public preview version of our redis management
tool. There's no guarantee it'll run smoothly.

After proper preparations, we will announce the official version
under `eleme/corvus-web`, and delete this repo.

Development
-----------

We use vagrant for development. `Install vagrant`_ first.

Then run:

.. code-block:: bash

    $ git clone git@github.com:eleme/corvus-web.git
    $ cd ./corvus-web/vagrant
    $ vagrant up

Open http://localhost:10924 in you browser.


.. _Install vagrant: https://www.vagrantup.com/downloads.html
