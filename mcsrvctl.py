import click
import os
import sys
import asyncio
from server_process import NewServerProcess, ServerAlreadyRunningError, ServerRunningError

async def start_coroutine():
    try:
        processs = await NewServerProcess.launch()
    except ServerAlreadyRunningError:
        print("Another instance of server is already running!", file=sys.stderr)
    except ServerRunningError as e:
        print("Error running server (exit code: {})".format(e.return_code), file=sys.stderr)

@click.group()
def cli():
    pass

@cli.command('start')
def start():
    os.chdir("test_server")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_coroutine())

if __name__ == "__main__":
    cli()