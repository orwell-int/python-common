import logging
import threading
import socket


LOGGER = logging.getLogger(__name__)


class BroadcastListener(threading.Thread):
    """
    """
    def __init__(self, port=9081):
        """
        """
        threading.Thread.__init__(self)
        self._socket_ports = []
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(('', port))

    def add_socket_port(self, socket_port):
        self._socket_ports.append(socket_port)

    def run(self, debug=False):
        """
        """
        finished = False
        while True:
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
                    if self._socket_ports:
                        port = self._socket_ports.pop(0)
                        data = bytearray("{local_port}".format(local_port=port), "ascii")
                    else:
                        finished = True
                        data = b"Goodbye"
                    LOGGER.info("Try to send response to broadcast:{data}".format(data=data))
                    self._socket.sendto(data, address)
                    if debug and finished:
                        LOGGER.info("Exit (debug)")
                        return
                except socket.timeout:
                    LOGGER.info("Tried to send response but socket.timeout occurred")
                except BlockingIOError:
                    LOGGER.info("Tried to send response but BlockingIOError occurred")


def configure_logging(verbose=False):
    print("configure_logging")
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s '
        '%(filename)s %(lineno)d %(message)s')
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    if verbose:
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.INFO)


def main():
    configure_logging()
    listener = BroadcastListener(9080)
    listener.add_socket_port(9012)
    listener.run(debug=True)


if '__main__' == __name__:
    main()
