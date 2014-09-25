import asyncio
import logging
import sys

from kademlia_aio import logging_to_console, setup_event_loop, start_node

logger = logging.getLogger(__name__)

logging_to_console()
setup_event_loop()

loop = asyncio.get_event_loop()
nodes = [start_node('127.0.0.1', i) for i in range(9000, 9010)]
for index, node in enumerate(nodes):
    for i in range(9000, 9010):
        if i == 9000+index:
            continue
        loop.run_until_complete(node.ping(('127.0.0.1', i), node.identifier))

logger.info("Network is connected...")
loop.run_forever()
