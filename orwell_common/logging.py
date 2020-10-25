import logging


def configure_logging(verbose):
    print("configure_logging")
    logger = logging.getLogger("orwell")
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s '
        '%(filename)s %(lineno)d %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
