kademlia_aio
============

The Kademlia distributed hash table, implemented for Python 3.4+ `asyncio`.

Quick Start
===========

```
$ python setup.py install
$ python -m kademlia_aio 0.0.0.0 9000 # run a server on the given local address and port
```

The `kademlia_aio.local_client` runs a node on port 10000, then launches
an IPython shell to programmatically interact with the network.

```
$ python -m kademlia_aio.local_client
In [1]: loop.run_until_complete(node.ping(('127.0.0.1', 9000), node.identifier))
Out[1]: ...the node identifier of the remote server...
In [2]: loop.run_until_complete(node.put('hello', 'world'))
Out[2]: 1 # how many nodes were able to store the result
In [3]: loop.run_until_complete(node.get('hello'))
Out[3]: 'world'
```

Resources
=========

* The original Kademlia paper: http://pdos.csail.mit.edu/~petar/papers/maymounkov-kademlia-lncs.pdf
* A more thorough specification: http://xlattice.sourceforge.net/components/protocol/kademlia/specs.html
* Inspiration from a Twisted implemenation: https://github.com/bmuller/kademlia/


The MIT License (MIT). Copyright (c) 2014 Chris Guidry <chris@theguidrys.us>
