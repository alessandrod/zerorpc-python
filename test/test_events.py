# -*- coding: utf-8 -*-
# Started by François-Xavier Bourlet <fx@dotcloud.com>, Nov 2011.

from nose.tools import assert_raises
import gevent

from zerorpc import zmq
import zerorpc

class MokupContext():
    _next_id = 0
    def new_msgid(self):
        new_id = MokupContext._next_id
        MokupContext._next_id += 1
        return new_id

def test_context():
    c = zerorpc.Context()
    assert c.new_msgid() is not None

def test_event():
    context = MokupContext()
    event = zerorpc.Event('mylittleevent', (None,), context=context)
    print event
    assert event.name == 'mylittleevent'
    assert event.header['message_id'] == 0
    assert event.args == (None,)

    event = zerorpc.Event('mylittleevent2', ('42',), context=context)
    print event
    assert event.name == 'mylittleevent2'
    assert event.header['message_id'] == 1
    assert event.args == ('42',)

    event = zerorpc.Event('mylittleevent3', ('a', 42), context=context)
    print event
    assert event.name == 'mylittleevent3'
    assert event.header['message_id'] == 2
    assert event.args == ('a', 42)

    event = zerorpc.Event('mylittleevent4', ('b', 21), context=context)
    print event
    assert event.name == 'mylittleevent4'
    assert event.header['message_id'] == 3
    assert event.args == ('b', 21)

    packed = event.pack()
    unpacked = zerorpc.Event.unpack(packed)
    print unpacked

    assert unpacked.name == 'mylittleevent4'
    assert unpacked.header['message_id'] == 3
    assert unpacked.args == ('b', 21)

    event = zerorpc.Event('mylittleevent5', ('c', 24, True),
            header={'lol': 'rofl'}, context=None)
    print event
    assert event.name == 'mylittleevent5'
    assert event.header['lol'] == 'rofl'
    assert event.args == ('c', 24, True)

    event = zerorpc.Event('mod', (42,), context=context)
    print event
    assert event.name == 'mod'
    assert event.header['message_id'] == 4
    assert event.args == (42,)
    event.header.update({'stream': True})
    assert event.header['stream'] is True

def test_events_req_rep():
    endpoint = 'ipc://test_events_req_rep'
    server = zerorpc.Events(zmq.REP)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.REQ)
    client.connect(endpoint)

    client.emit('myevent', ('arg1',))

    event = server.recv()
    print event
    assert event.name == 'myevent'
    assert event.args == ('arg1',)

def test_events_req_rep2():
    endpoint = 'ipc://test_events_req_rep2'
    server = zerorpc.Events(zmq.REP)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.REQ)
    client.connect(endpoint)

    for i in xrange(10):
        client.emit('myevent' + str(i), (i,))
        event = server.recv()
        print event
        assert event.name == 'myevent' + str(i)
        assert event.args == (i,)

        server.emit('answser' + str(i * 2), (i * 2,))
        event = client.recv()
        print event
        assert event.name == 'answser' + str(i * 2)
        assert event.args == (i * 2,)

def test_events_dealer_router():
    endpoint = 'ipc://test_events_dealer_router'
    server = zerorpc.Events(zmq.XREP)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.XREQ)
    client.connect(endpoint)

    for i in xrange(6):
        client.emit('myevent' + str(i), (i,))
        event = server.recv()
        print event
        assert event.name == 'myevent' + str(i)
        assert event.args == (i,)

        server.emit('answser' + str(i * 2), (i * 2,),
                xheader=dict(zmqid=event.header['zmqid']))
        event = client.recv()
        print event
        assert event.name == 'answser' + str(i * 2)
        assert event.args == (i * 2,)

def test_events_push_pull():
    endpoint = 'ipc://test_events_push_pull'
    server = zerorpc.Events(zmq.PULL)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.PUSH)
    client.connect(endpoint)

    for x in xrange(10):
        client.emit('myevent', (x,))

    for x in xrange(10):
        event = server.recv()
        print event
        assert event.name == 'myevent'
        assert event.args == (x,)

def test_events_channel_client_side():
    endpoint = 'ipc://test_events_channel_client_side'
    server_events = zerorpc.Events(zmq.XREP)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.XREQ)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('someevent', (42,))

    event = server.recv()
    print event
    assert event.args == (42,)
    assert event.header.get('zmqid', None) is not None

    server.emit('someanswer', (21,),
            xheader=dict(response_to=event.header['message_id'],
                zmqid=event.header['zmqid']))
    event = client_channel.recv()
    assert event.args == (21,)


def test_events_channel_client_side_server_send_many():
    endpoint = 'ipc://test_events_channel_client_side_server_send_many'
    server_events = zerorpc.Events(zmq.XREP)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.XREQ)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('giveme', (10,))

    event = server.recv()
    print event
    assert event.args == (10,)
    assert event.header.get('zmqid', None) is not None

    for x in xrange(10):
        server.emit('someanswer', (x,),
                xheader=dict(response_to=event.header['message_id'],
                    zmqid=event.header['zmqid']))
    for x in xrange(10):
        event = client_channel.recv()
        assert event.args == (x,)


def test_events_channel_both_side():
    endpoint = 'ipc://test_events_channel_both_side'
    server_events = zerorpc.Events(zmq.XREP)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.XREQ)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('openthat', (42,))

    event = server.recv()
    print event
    assert event.args == (42,)
    assert event.name == 'openthat'

    server_channel = server.channel(event)
    server_channel.emit('test', (21,))

    event = client_channel.recv()
    assert event.args == (21,)
    assert event.name == 'test'

    server_channel.emit('test', (22,))

    event = client_channel.recv()
    assert event.args == (22,)
    assert event.name == 'test'

    server_events.close()
    server_channel.close()
    client_channel.close()
    client_channel.close()