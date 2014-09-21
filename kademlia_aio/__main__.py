import asyncio
import logging
import signal
import sys

from kademlia_aio import KademliaNode, logging_to_console

local_address, port = sys.argv[1:3]

logging_to_console()

logger = logging.getLogger(__name__)

logger.info('Starting server...')
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGINT, loop.stop)

transport, node = loop.run_until_complete(loop.create_datagram_endpoint(KademliaNode, local_addr=(local_address, int(port))))
logger.info('Listening as node %s...', node.node_identifier)

loop.run_forever()
loop.close()
logger.info('Stopped.')
