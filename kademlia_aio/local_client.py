import asyncio
import logging
import sys

import IPython

from kademlia_aio import logging_to_console, setup_event_loop, start_node, get_identifier

logger = logging.getLogger(__name__)

logging_to_console()
setup_event_loop()

loop = asyncio.get_event_loop()
node = start_node('127.0.0.1', 10000)

def ping_all_local():
    for port in range(9000, 9010):
        loop.run_until_complete(node.ping(('127.0.0.1', port), node.identifier))

IPython.embed()
