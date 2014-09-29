'''
Creates a Kademlia client on port 10000 for interactive testing.  To start it, run
`python kademlia_aio.local_client`.
'''
import asyncio
import logging
import random
import sys

import IPython

from kademlia_aio.services import logging_to_console, setup_event_loop, start_node

logger = logging.getLogger(__name__)

logging_to_console()
setup_event_loop()

ports = range(9000, 9010)

loop = asyncio.get_event_loop()
node = start_node('127.0.0.1', 10000)

def ping_all_local():
    for port in ports:
        loop.run_until_complete(node.ping(('127.0.0.1', port), node.identifier))

def ping_one_local():
    loop.run_until_complete(node.ping(('127.0.0.1', random.choice(ports)), node.identifier))

IPython.embed()
