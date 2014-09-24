# coding: utf-8
import asyncio
from functools import wraps
import socket
import unittest

from kademlia_aio import KademliaNode, get_identifier


def async_unit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(func)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coro(*args, **kwargs))
    return wrapper


class KademliaNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_loop = asyncio.get_event_loop()
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)

        cls.node1_address = ('127.0.0.1', 32001)
        future = cls.loop.create_datagram_endpoint(KademliaNode, local_addr=cls.node1_address)
        cls.transport1, cls.node1 = cls.loop.run_until_complete(future)
        cls.node1.reply_timeout = 1

        cls.node2_address = ('127.0.0.1', 32002)
        future = cls.loop.create_datagram_endpoint(KademliaNode, local_addr=cls.node2_address)
        cls.transport2, cls.node2 = cls.loop.run_until_complete(future)
        cls.node2.reply_timeout = 1

    @classmethod
    def tearDownClass(cls):
        cls.loop.stop()
        asyncio.set_event_loop(cls.original_loop)

    @async_unit
    def test_timeout(self):
        try:
            yield from self.node1.ping(('127.0.0.1', 32003), self.node1.identifier)
            self.assertFalse(True, 'should have timed out')
        except socket.timeout:
            pass

    @async_unit
    def test_ping(self):
       reply = yield from self.node1.ping(self.node2_address, self.node1.identifier)
       self.assertEqual(reply, self.node2.identifier)

    @async_unit
    def test_store(self):
        key = get_identifier('hello')
        reply = yield from self.node1.store(self.node2_address, self.node1.identifier, key, 'world')
        self.assertTrue(reply)
        stored = yield from self.node1.find_value(self.node2_address, self.node1.identifier, key)
        self.assertEqual('world', stored)