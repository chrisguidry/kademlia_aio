'''
Creates a local Kademlia network of 40 nodes on ports 9000-9039 for testing.  To start it, run
`python kademlia_aio.local_network`
'''
import asyncio
import logging

from kademlia_aio.services import logging_to_console, setup_event_loop, start_node

logger = logging.getLogger(__name__)

logging_to_console()
setup_event_loop()

ports = range(9000, 9040)

loop = asyncio.get_event_loop()
nodes = [start_node('127.0.0.1', i) for i in ports]
for index, node in enumerate(nodes):
    for port in ports:
        if port == 9000 + index:
            continue
        if port % 3 != 0:
            continue
        loop.run_until_complete(node.ping(('127.0.0.1', port), node.identifier))

logger.info("Network is connected...")
loop.run_forever()
