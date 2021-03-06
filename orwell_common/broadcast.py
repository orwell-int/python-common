import logging
import asyncio
import itertools
import netifaces
import socket
import struct
import enum

LOGGER = logging.getLogger(__name__.replace("orwell_common", "orwell.common"))

DEFAULT_PORT = 9080


class Kind(enum.Enum):
    SERVER_GAME = "ServerGame"
    PROXY_ROBOTS = "ProxyRobots"


class ServerGameDecoder(object):
    def __init__(self, *, version=2):
        self._push_address = None
        self._subscribe_address = None
        self._reply_address = None
        self._agent_address = None
        self._decoding_successful = False
        self._version = version

    @property
    def kind(self):
        return Kind.SERVER_GAME

    @property
    def version(self):
        return self._version

    def decode(self, sender, data):
        sender_ip, _ = sender
        # data (split on multiple lines for clarity):
        # 0xA0
        # size on 8 bytes
        # Address of puller
        # 0xA1
        # size on 8 bytes
        # Address of publisher
        # 0xA2
        # size on 8 bytes
        # Address of replier
        # 0xA3
        # size on 8 bytes
        # Address of agent
        # 0x00
        to_str = lambda x: x.decode("ascii")
        assert (data[0] == 0xa0)
        puller_size = int(data[1])
        # print("puller_size =", puller_size)
        end_puller = 2 + puller_size
        puller_address = to_str(data[2:end_puller])
        # print("puller_address =", puller_address)
        assert (data[end_puller] == 0xa1)
        publisher_size = int(data[end_puller + 1])
        # print("publisher_size =", str(publisher_size))
        end_publisher = end_puller + 2 + publisher_size
        publisher_address = to_str(data[end_puller + 2:end_publisher])
        # print("publisher_address =", publisher_address)
        assert (data[end_publisher] == 0xa2)
        replier_size = int(data[end_publisher + 1])
        # print("replier_size =", str(replier_size))
        end_replier = end_publisher + 2 + replier_size
        replier_address = to_str(data[end_publisher + 2:end_replier])
        if 0xa3 == data[end_replier]:
            agent_size = int(data[end_replier + 1])
            # print("agent_size =", str(agent_size))
            end_agent = end_replier + 2 + agent_size
            agent_address = to_str(data[end_replier + 2:end_agent])
            # print("agent_address =", agent_address)
            self._agent_address = agent_address.replace('*', sender_ip)
        else:
            assert(self.version < 2)
        self._push_address = puller_address.replace('*', sender_ip)
        self._subscribe_address = publisher_address.replace('*', sender_ip)
        self._reply_address = replier_address.replace('*', sender_ip)
        self._decoding_successful = True

    def reset(self):
        self._decoding_successful = False

    @property
    def push_address(self):
        return self._push_address

    @property
    def subscribe_address(self):
        return self._subscribe_address

    @property
    def reply_address(self):
        return self._reply_address

    @property
    def agent_address(self):
        return self._agent_address

    @property
    def success(self):
        return self._decoding_successful

    def __str__(self):
        return "push = %s ; sub = %s ; rep = %s ; agt = %s" % (
            self._push_address,
            self._subscribe_address,
            self._reply_address,
            self._agent_address)


class ProxyRobotsDecoder(object):
    def __init__(self, *, version="robot"):
        self._port = None
        self._decoding_successful = False
        self._version = version

    @property
    def kind(self):
        return Kind.PROXY_ROBOTS

    @property
    def version(self):
        return self._version

    def decode(self, sender, data):
        try:
            self._port = int(data)
            self._decoding_successful = True
        except Exception as ex:
            LOGGER.warning("Could not decode broadcast message: " + repr(data))
            LOGGER.warning(str(ex))

    def reset(self):
        self._decoding_successful = False

    @property
    def success(self):
        return self._decoding_successful

    def __str__(self):
        return "port = %s" % (self._port,)

    @property
    def port(self):
        return self._port


def get_network_ips():
    results = []
    for interface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(interface)
        if netifaces.AF_INET not in addresses:
            continue
        ipv4_addresses = addresses[netifaces.AF_INET]
        if not ipv4_addresses:
            continue
        for ipv4_address in ipv4_addresses:
            if "broadcast" not in ipv4_address:
                continue
            results.append(ipv4_address["broadcast"])
    return results[::-1]


class Broadcast(object):
    def __init__(self, decoder, port=DEFAULT_PORT, retries=2, timeout=3):
        self._port = port
        self._size = 512
        self._retries = retries
        self._timeout = timeout
        self._build_socket()
        self._ips_pool = get_network_ips()
        LOGGER.debug("ips: %s", self._ips_pool)
        self._group = None
        self._found_group = None
        self._received = False
        self._data = None
        self._sender = None
        self._decoder = decoder
        self._message = str(self._decoder.version).encode("ascii")

    def set_decoder(self, decoder):
        self._decoder = decoder

    def _build_socket(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socket.settimeout(self._timeout)
        ttl = struct.pack('b', 1)
        self._socket.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    def _get_next_group(self, force_group=None):
        if force_group is not None:
            return force_group
        if self._ips_pool:
            broadcast = self._ips_pool.pop()
            return self._get_group(broadcast)
        else:
            return None

    def _get_group(self, ip):
        group = ip, self._port
        LOGGER.debug('group = ' + str(group))
        return group

    def send_all_broadcast_messages(self):
        self.reset()
        self._received = False
        self._group = self._get_next_group(self._found_group)
        while self._group:
            tries = 0
            while (tries < self._retries) and (not self._received):
                tries += 1
                LOGGER.debug("Try " + str(tries) + " group: " + str(self._group))
                self.send_one_broadcast_message()
            if self._received:
                self._found_group = self._group
                self.decode_data()
                break
            self._group = self._get_next_group()

    def send_some_broadcast_messages(self):
        if not self._group:
            self.reset()
            self._received = False
            self._group = self._get_next_group(self._found_group)
        tries = 0
        while (tries < self._retries) and (not self._received):
            tries += 1
            LOGGER.debug("Try " + str(tries) + " group: " + str(self._group))
            self.send_one_broadcast_message()
        if self._received:
            self._found_group = self._group
            self.decode_data()
            return
        self._group = self._get_next_group()

    def reset(self):
        self._ips_pool = get_network_ips()

    def send_one_broadcast_message(self, silent=False):
        self._decoder.reset()
        self._received = False
        try:
            if not silent:
                LOGGER.debug("before sendto")
            sent = self._socket.sendto(self._message, self._group)
            if not silent:
                LOGGER.debug("after sendto ; " + repr(sent))
            while not self._received:
                try:
                    self._data, self._sender = self._socket.recvfrom(
                            self._size)
                    self._received = True
                except socket.timeout:
                    if not silent:
                        LOGGER.warning('timed out, no more responses')
                    break
                else:
                    if not silent:
                        LOGGER.info(
                            'received "%s" from %s'
                            % (repr(self._data), self._sender))
        finally:
            if not silent:
                LOGGER.info('closing socket')
            self._socket.close()
            self._build_socket()
        return self._received

    def decode_data(self):
        if not self._decoder:
            self._decoder = ServerGameDecoder()
        self._decoder.decode(self._sender, self._data)

    @property
    def decoder(self):
        return self._decoder

    @decoder.setter
    def decoder(self, value):
        self._decoder = value

    @property
    def remote_address(self):
        address, _ = self._sender
        return address


async def send(sock, message, group):
    LOGGER.debug("before sendto")
    sent = sock.sendto(message, group)
    LOGGER.debug("after sendto")
    return sent


async def recvfrom(sock, size):
    LOGGER.debug("before recvfrom")
    data, sender = sock.recvfrom(size)
    LOGGER.debug("after recvfrom")
    return data, sender


class AsyncBroadcast(Broadcast):
    def __init__(self, decoder, port=DEFAULT_PORT):
        super().__init__(decoder, port, 0, 0)
        self._ips_iterator = itertools.cycle(self._ips_pool)

    async def async_send_all_broadcast_messages(self):
        self._received = False
        self._group = self._get_group(next(self._ips_iterator))
        while True:
            await self.async_send_one_broadcast_message()
            if self._received:
                self.decode_data()
                break
            self._group = self._get_group(next(self._ips_iterator))

    async def async_send_one_broadcast_message(self):
        try:
            LOGGER.debug("before sendto")
            task = asyncio.create_task(send(self._socket, self._message, self._group))
            await task
            sent = task.result()
            LOGGER.debug("after sendto ; " + repr(sent))
            tries = 10
            while not self._received:
                try:
                    task = asyncio.create_task(recvfrom(self._socket, self._size))
                    await task
                    self._data, self._sender = task.result()
                    self._received = True
                except BlockingIOError as ex:
                    pass
                if not self._received:
                    tries -= 1
                    if tries <= 0:
                        LOGGER.info("Failed to contact %s", self._group)
                        break
                    await asyncio.sleep(0.2)
                else:
                    LOGGER.info(
                        'received "%s" from %s'
                        % (repr(self._data), self._sender))
        finally:
            LOGGER.info('closing socket')
            self._socket.close()
            self._build_socket()
