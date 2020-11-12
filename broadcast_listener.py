import orwell_common.logging
import orwell_common.broadcast_listener


def main():
    orwell_common.logging.configure_logging(False)
    listener = orwell_common.broadcast_listener.BroadcastListener(9080)
    import sys
    argc = len(sys.argv)
    if argc > 1:
        max_loops = int(sys.argv[1])
        # put only max_loops - 1 ports so that last response will be goodbye
        for i in range(max_loops - 1):
            listener.add_socket_port(i)
    else:
        max_loops = 0
        listener.add_socket_port(9012)
    listener.run(max_loops)


if '__main__' == __name__:
    main()
