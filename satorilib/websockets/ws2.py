import asyncio
import pickle
import pandas as pd
from typing import Optional, Callable
from websockets.server import serve
from websockets.client import connect
from websockets.exceptions import ConnectionClosed

class WebSocketServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7888,
        callback: Optional[Callable] = None,
    ):
        self.host = host
        self.port = port
        self.callback = callback
        self.connections = set()
        self.queue = asyncio.Queue()

    async def handler(self, websocket):
        self.connections.add(websocket)
        try:
            async for message in websocket:
                try:
                    # Try to unpickle first, if fails treat as string
                    try:
                        data = pickle.loads(message)
                    except:
                        data = message
                    await self.queue.put(data)
                except Exception as e:
                    print(f"Error receiving message: {e}")
        except ConnectionClosed:
            pass
        finally:
            self.connections.remove(websocket)

    async def start_server(self):
        server = await serve(self.handler, self.host, self.port)
        await asyncio.gather(server.wait_closed(), self.process_queue())

    async def process_queue(self):
        while True:
            data = await self.queue.get()
            if self.callback:
                self.callback(data)

    async def broadcast(self, message):
        """Send message to all connected clients"""
        if self.connections:
            await asyncio.gather(
                *[connection.send(message) for connection in self.connections]
            )

class WebSocketClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7888,
        callback: Optional[Callable] = None,
    ):
        self.host = host
        self.port = port
        self.callback = callback
        self.websocket = None

    async def connect(self):
        """Connect to WebSocket server"""
        uri = f"ws://{self.host}:{self.port}"
        try:
            self.websocket = await connect(uri)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    async def listen(self):
        """Listen for incoming messages"""
        try:
            while True:
                message = await self.websocket.recv()
                if self.callback:
                    self.callback(message)
        except ConnectionClosed:
            pass
        except Exception as e:
            print(f"Error in listener: {e}")

    async def send(self, data):
        """Send data to the server"""
        if not self.websocket:
            raise ConnectionError("Not connected to server")
        
        try:
            if isinstance(data, pd.DataFrame):
                await self.websocket.send(pickle.dumps(data))
            else:
                await self.websocket.send(str(data))
        except Exception as e:
            print(f"Error sending message: {e}")

    async def start(self):
        """Start the client"""
        if await self.connect():
            await self.listen()

async def main():
    def message_handler(data):
        print(f"Received: {data}")

    server = WebSocketServer(callback=message_handler)
    client = WebSocketClient()

    # Start server and client asynchronously
    await asyncio.gather(
        server.start_server(),
        client.start(),
        send_data(client)
    )

async def send_data(client):
    await asyncio.sleep(1)

    df = pd.DataFrame({
        'A': [1, 2, 3],
        'B': ['a', 'b', 'c']
    })

    await client.send(df)
    await client.send("Hello World")
    await client.send("Thats a long wait")

if __name__ == "__main__":
    asyncio.run(main())
