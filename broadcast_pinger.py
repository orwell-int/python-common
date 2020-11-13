import queue
import sys

import orwell_common.logging
import orwell_common.broadcast_pinger


def main():
    orwell_common.logging.configure_logging(False)
    message_queue = queue.Queue()
    argc = len(sys.argv)
    if argc > 1:
        max_loops = int(sys.argv[1])
    else:
        max_loops = 0
    pinger = orwell_common.broadcast_pinger.BroadcastPinger(message_queue)
    pinger.run(max_loops)


if '__main__' == __name__:
    main()
