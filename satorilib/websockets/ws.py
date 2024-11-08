import asyncio
import time
import threading
import pickle
import pandas as pd
from typing import Optional, Callable
import queue
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
        self.server = None
        self.connections = set()
        self.queue = queue.Queue()
        self.running = False
        
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
                    self.queue.put(data)
                except Exception as e:
                    print(f"Error receiving message: {e}")
        except ConnectionClosed:
            pass
        finally:
            self.connections.remove(websocket)

    async def start_server(self):
        self.server = await serve(self.handler, self.host, self.port)
        self.running = True
        await self.server.wait_closed()

    def start(self):
        """Start the server in a separate thread"""
        def run_server():
            asyncio.run(self.start_server())
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        
        self.queue_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.queue_thread.start()

    def process_queue(self):
        while True:
            data = self.queue.get()
            if self.callback:
                self.callback(data)

    async def broadcast(self, message):
        """Send message to all connected clients"""
        if self.connections:
            await asyncio.gather(
                *[connection.send(message) for connection in self.connections]
            )

    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server:
            self.server.close()

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
        self.running = False

    async def connect(self):
        """Connect to WebSocket server"""
        uri = f"ws://{self.host}:{self.port}"
        try:
            self.websocket = await connect(uri)
            self.running = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    async def listen(self):
        """Listen for incoming messages"""
        try:
            while self.running:
                message = await self.websocket.recv()
                if self.callback:
                    self.callback(message)
        except ConnectionClosed:
            self.running = False
        except Exception as e:
            print(f"Error in listener: {e}")
            self.running = False

    async def send(self, data):
        """Send data to the server"""
        if not self.websocket:
            raise ConnectionError("Not connected to server")
        
        try:
            print(data)
            if isinstance(data, pd.DataFrame):
                await self.websocket.send(pickle.dumps(data))
            else:
                await self.websocket.send(str(data))
        except Exception as e:
            print(f"Error sending message: {e}")

    def start(self):
        """Start the client in a separate thread"""
        def run_client():
            asyncio.run(self._run())
        
        self.thread = threading.Thread(target=run_client, daemon=True)
        self.thread.start()

    async def _run(self):
        """Internal method to run the client"""
        if await self.connect():
            await self.listen()

    def stop(self):
        """Stop the client"""
        self.running = False
        if self.websocket:
            asyncio.run(self.websocket.close())

if __name__ == "__main__":
    def message_handler(data):
        print(f"Received: {data}")

    server = WebSocketServer(callback=message_handler)
    server.start()

    client = WebSocketClient()
    client.start()

    time.sleep(1)

    df = pd.DataFrame({
        'A': [1, 2, 3],
        'B': ['a', 'b', 'c']
    })
    
    asyncio.run(client.send(df)) 
    # time.sleep(1)
    asyncio.run(client.send("Hello World"))  
    asyncio.run(client.send("Thats a long wait"))  

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        client.stop()



from ws import WebSocketClient
import asyncio
import pandas as pd

def message_handler(data):
    print(f"Received: {data}")

async def main():
    # Create client with callback
    client = WebSocketClient(callback=message_handler)
    client.start()
    
    # Wait for connection to establish
    print("Waiting for connection...")
    max_retries = 5
    retry_count = 0
    
    while not client.websocket and retry_count < max_retries:
        await asyncio.sleep(1)
        retry_count += 1
        
    if not client.websocket:
        print("Failed to connect to server")
        return
        
    print("Connected!")
    
    # Now safe to send messages
    i = 0
    # while i < 3:
    try:
        df = pd.read_csv("../input.csv")
        await client.send(df)
        print("Message sent!")
    except Exception as e:
        print(f"Error sending message: {e}")
    i+=1
    # Keep the program running
    # try:
    #     while True:
    #         await asyncio.sleep(1)
    # except KeyboardInterrupt:
    #     client.stop()

if __name__ == "__main__":
    asyncio.run(main())
