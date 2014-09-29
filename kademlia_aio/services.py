import asyncio
import logging
import signal

from kademlia_aio import KademliaNode


logger = logging.getLogger(__name__)


def logging_to_console():
    '''Sends all kademlia_aio logs to standard out.'''
    kademlia_logger = logging.getLogger('kademlia_aio')
    kademlia_logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    kademlia_logger.addHandler(stream_handler)

def setup_event_loop():
    '''Prepares the global asyncio event loop for console operation, adding a signal handler to
       handle SIGINT.'''
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.stop)

def start_node(local_address, port):
    '''Starts a KademliaNode listening on the given address and port, waits for it to
       initialize on the global asyncio event loop, then returns it.'''
    loop = asyncio.get_event_loop()
    logger.info('Starting node on %s:%s...', local_address, port)
    _, node = loop.run_until_complete(loop.create_datagram_endpoint(KademliaNode, local_addr=(local_address, int(port))))
    logger.info('Listening as node %s...', node.identifier)
    return node
