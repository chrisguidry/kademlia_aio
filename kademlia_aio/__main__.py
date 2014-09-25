import asyncio
import sys

from kademlia_aio import logging_to_console, setup_event_loop, start_node

logging_to_console()
setup_event_loop()
start_node(*sys.argv[1:3])

asyncio.get_event_loop().run_forever()
