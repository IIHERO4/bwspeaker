import asyncio
import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from colorlog import ColoredFormatter


def main():
    console_format = "%(log_color)s[%(asctime)s] [%(module)s] [%(funcName)s] [%(levelname)s]: %(message)s %(reset)s"
    console_stdout = logging.StreamHandler()
    console_stdout.setLevel(logging.INFO)
    console_stdout.setFormatter(ColoredFormatter(console_format))

    log_file = TimedRotatingFileHandler(
        filename=f"./logs/latest.log",
        encoding="utf-8",
        when="d",
        interval=1,
    )

    log_file.setLevel(logging.DEBUG)
    logging.basicConfig(
        level=logging.DEBUG,
        datefmt="%I:%M:%S %p",
        format="[%(asctime)s] [%(module)s] [%(funcName)s] [%(levelname)s]: %(message)s",
        handlers=[console_stdout, log_file],
        force=True,
    )
    if "server" in sys.argv:
        import server.server as srv
        asyncio.get_event_loop().run_until_complete(srv.main())
        return
    import client.client as cln
    asyncio.get_event_loop().run_until_complete(cln.main())


main()
