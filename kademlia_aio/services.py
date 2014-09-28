import asyncio
import logging
import signal

from kademlia_aio import KademliaNode

def logging_to_console():
    kademlia_logger = logging.getLogger('kademlia_aio')
    kademlia_logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    kademlia_logger.addHandler(stream_handler)

def setup_event_loop():
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.stop)

def start_node(local_address, port):
    loop = asyncio.get_event_loop()
    logger.info('Starting node on %s:%s...', local_address, port)
    transport, node = loop.run_until_complete(loop.create_datagram_endpoint(KademliaNode, local_addr=(local_address, int(port))))
    logger.info('Listening as node %s...', node.identifier)
    return node
