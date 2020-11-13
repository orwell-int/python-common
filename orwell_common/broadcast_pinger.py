import orwell_common.logging
import orwell_common.broadcast as broadcast

import logging
import time
import threading

LOGGER = logging.getLogger(__name__.replace("orwell_common", "orwell.common"))


class BroadcastPinger(threading.Thread):
    """
    Send broadcast messages periodically to first find the server and check that
    it remains available. Start from scratch when the server becomes unavailable.
    """

    def __init__(
            self,
            message_queue,
            sleep_duration=4,
            decoder=broadcast.ServerGameDecoder(),
            port=broadcast.DEFAULT_PORT,
            retries=2,
            timeout=3):
        """
        """
        threading.Thread.__init__(self)
        self._message_queue = message_queue
        self._sleep_duration = sleep_duration
        self._kind = decoder.kind
        self._broadcaster = broadcast.Broadcast(decoder, port, retries, timeout)

    def run(self, max_loops=0):
        """
        max_loops: if greater than zero maximum number of loops performed
        before exiting, otherwise ignored.
        """
        loops = 0
        found = False
        while (max_loops <= 0) or (loops < max_loops):
            if max_loops > 0:
                loops += 1
            if not found:
                self._broadcaster.send_all_broadcast_messages()
                answer_received = self._broadcaster.decoder.success
            else:
                answer_received = self._broadcaster.send_one_broadcast_message()
            if answer_received:
                if not found:
                    found = True
                    LOGGER.info("Made contact with %s.", self._kind.value)
                    if broadcast.Kind.SERVER_GAME == self._kind:
                        push_address = self._broadcaster.decoder.push_address
                        subscribe_address = self._broadcaster.decoder.subscribe_address
                        replier_address = self._broadcaster.decoder.reply_address
                        self._message_queue.put(
                            (push_address, subscribe_address, replier_address))
                    else:
                        assert(broadcast.Kind.PROXY_ROBOTS == self._kind)
                        robot_port = self._broadcaster.port
                        self._message_queue.put((robot_port,))
            else:
                if found:
                    LOGGER.info("Contact lost with %s.", self._kind.value)
                    self._message_queue.put(None)
                else:
                    LOGGER.info("Could not find %s.", self._kind.value)
                found = False
            time.sleep(self._sleep_duration)
