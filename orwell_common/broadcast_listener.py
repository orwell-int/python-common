import logging
import socket
import threading

import orwell_common.logging

LOGGER = logging.getLogger(__name__.replace("orwell_common", "orwell.common"))


class BroadcastListener(threading.Thread):
    """
    """

    ADMIN = bytearray("admin", "ascii")
    ROBOT = bytearray("robot", "ascii")

    def __init__(self, port=9081, admin_port=9082):
        """
        """
        threading.Thread.__init__(self)
        self._socket_ports = []
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(('', port))
        self._admin_port = admin_port

    def add_socket_port(self, socket_port):
        self._socket_ports.append(socket_port)

    def _get_robot_port(self):
        if self._socket_ports:
            port = self._socket_ports.pop(0)
            data = bytearray("{local_port}".format(local_port=port), "ascii")
        else:
            data = b"Goodbye"
        return data

    def _get_admin_port(self):
        data = bytearray("{admin_port}".format(admin_port=self._admin_port), "ascii")
        return data

    def run(self, max_loops=0):
        """
        max_loops: if greater than zero maximum number of loops performed
        before exiting, otherwise ignored.
        """
        loops = 0
        while (max_loops <= 0) or (loops < max_loops):
            if max_loops > 0:
                loops += 1
            message = None
            try:
                message, address = self._socket.recvfrom(4096)
            except socket.timeout:
                pass
            except BlockingIOError:
                pass
            if message:
                try:
                    LOGGER.info(
                            "Received UDP broadcast '{message}' "
                            "from {address}".format(
                                message=message, address=address))
                    if message.startswith(BroadcastListener.ADMIN):
                        method = self._get_admin_port
                    elif message.startswith(BroadcastListener.ROBOT):
                        method = self._get_robot_port
                    else:
                        method = self._get_robot_port
                    data = method()
                    LOGGER.info("Try to send response to broadcast: {data}".format(data=data))
                    self._socket.sendto(data, address)
                    LOGGER.info("Success")
                except socket.timeout:
                    LOGGER.info("Tried to send response but socket.timeout occurred")
                except BlockingIOError:
                    LOGGER.info("Tried to send response but BlockingIOError occurred")
