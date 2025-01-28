import asyncio
from satorilib.datamanager.server import DataServer

async def main():
    server = DataServer("localhost", 24602)
    server.availableStreams
    await server.startServer()
    await asyncio.Future()  # Keep running

asyncio.run(main())

