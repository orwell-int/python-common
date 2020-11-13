import sys
import asyncio

import orwell_common.logging
from orwell_common.broadcast import ServerGameDecoder
from orwell_common.broadcast import ProxyRobotsDecoder
from orwell_common.broadcast import Broadcast
from orwell_common.broadcast import AsyncBroadcast


def main():
    orwell_common.logging.configure_logging(True)
    argc = len(sys.argv)
    if argc > 1:
        function = sys.argv[1]
    else:
        function = "normal"
    if argc > 2:
        if "server_game" == sys.argv[2]:
            decoder = ServerGameDecoder
        else:
            decoder = ProxyRobotsDecoder
    else:
        decoder = ProxyRobotsDecoder
    if "normal" == function:
        broadcast = Broadcast(decoder())
        broadcast.send_all_broadcast_messages()
        print(broadcast.decoder)
    elif "async" == function:
        broadcast = AsyncBroadcast(decoder())
        asyncio.run(broadcast.async_send_all_broadcast_messages())
        print(broadcast.decoder)


if '__main__' == __name__:
    main()
