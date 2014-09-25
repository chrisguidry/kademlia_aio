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

IPython.embed()
