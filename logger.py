import logging
from rich.logging import RichHandler

FORMAT = "%(message)s"

handler = RichHandler()
handler.setFormatter(logging.Formatter(FORMAT, datefmt="[%X]"))

logger = logging.getLogger("rich")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
