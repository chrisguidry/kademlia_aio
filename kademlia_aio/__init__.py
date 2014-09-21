import asyncio
from functools import wraps
import hashlib
import logging
import pickle
import random
import socket


logger = logging.getLogger(__name__)


def remote(func):
    @asyncio.coroutine
    @wraps(func)
    def inner(*args, **kwargs):
        instance, peer, *args = args
        answer = yield from instance.request(peer, inner.remote_name, *args, **kwargs)
        return answer
    inner.remote_name = func.__name__
    inner.reply_function = func
    return inner

class DatagramRPCProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.outstanding_requests = {}
        self.reply_functions = {func.remote_name: func.reply_function
                                for func in self.__class__.__dict__.values()
                                if hasattr(func, 'remote_name')}
        super(DatagramRPCProtocol, self).__init__()

    def connection_made(self, transport):
        logger.info('connection_made: %r', transport)
        self.transport = transport
        print(self.transport.__dict__)

    def datagram_received(self, data, peer):
        logger.info('data_received: %r, %r', peer, data)
        direction, message_identifier, *details = pickle.loads(data)
        if direction == 'request':
            procedure_name, args, kwargs = details
            logger.info('request from %r: %r(*%r, **%r) as message %r', peer, procedure_name, args, kwargs, message_identifier)
            answer = self.reply_functions[procedure_name](self, peer, *args, **kwargs)
            self.reply(peer, message_identifier, answer)
        elif direction == 'reply':
            answer, = details
            logger.info('reply to message %r, answer %r', message_identifier, answer)
            if message_identifier in self.outstanding_requests:
                reply = self.outstanding_requests[message_identifier]
                del self.outstanding_requests[message_identifier]
                reply.set_result(answer)

    def timed_out(self, message_identifier):
        if message_identifier in self.outstanding_requests:
            reply = self.outstanding_requests[message_identifier]
            del self.outstanding_requests[message_identifier]
            reply.set_exception(socket.timeout)

    def connection_lost(self, exception):
        logger.info('connection_lost: %r', exception)

    def error_received(self, exception):
        logger.info('error_received: %r', exception)

    def request(self, peer, procedure_name, *args, **kwargs):
        message_identifier = get_random_identifier()
        reply = asyncio.Future()
        self.outstanding_requests[message_identifier] = reply

        loop = asyncio.get_event_loop()
        loop.call_later(5, self.timed_out, message_identifier)

        message = pickle.dumps(('request', message_identifier, procedure_name, args, kwargs))
        self.transport.sendto(message, peer)

        return reply

    def reply(self, peer, message_identifier, answer):
        message = pickle.dumps(('reply', message_identifier, answer))
        self.transport.sendto(message, peer)


class KademliaNode(DatagramRPCProtocol):
    def __init__(self):
        self.node_identifier = get_random_identifier()
        self.storage = {}
        super(KademliaNode, self).__init__()

    @remote
    def ping(self, peer):
        logger.info('ping: %r', peer)
        return self.node_identifier

    @remote
    def store(self, peer, key, value):
        logger.info('store: %r, %r, %r', peer, key, value)
        self.storage[key] = value
        return True

    @remote
    def find_node(self, peer, key):
        raise NotImplementedError()

    @remote
    def find_value(self, peer, key):
        if key in self.storage:
            return self.storage[key]

        raise NotImplementedError()


def get_random_identifier():
    return hashlib.sha1(str(random.getrandbits(255)).encode()).digest()

def logging_to_console():
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(stream_handler)
