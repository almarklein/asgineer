"""
Simple logging utils.
"""

import sys
import time
import logging
import traceback


class Formatter(logging.Formatter):
    """ Formatter that adds timestamp before the message.
    """

    def format(self, record):
        return "[{} {}] {}".format(
            record.levelname[0],
            time.strftime("%Y-%m-%d %H:%M:%S"),
            super().format(record),
        )


def format_traceback(err):
    """ Returns the string traceback for the given error object.
    """
    try:
        out = "".join(traceback.format_list(traceback.extract_tb(err.__traceback__)))
        return "\n" + out.rstrip()
    except Exception as err:  # Failsafe
        return "Woops, format_traceback fails: " + str(err)


# Get our logger
logger = logging.getLogger("asgish")
logger.propagate = False
logger.setLevel(logging.INFO)  # we actually only emit error messages atm

# Initialize the logger to write errors to stderr (but can be overriden)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(Formatter())
logger.addHandler(_handler)
