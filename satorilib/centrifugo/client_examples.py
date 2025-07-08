'''publish examples are wrong here.'''
'''
import asyncio
import logging
from centrifuge import Client, SubscriptionEventHandler, ClientEventHandler
from centrifuge import PublicationContext, ConnectedContext, DisconnectedContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Simple approach - just functions, no wrapper class needed
async def create_centrifugo_client(ws_url: str, token: str) -> Client:
    """Create and return a configured Centrifugo client"""
    
    async def get_token():
        return token
    
    # Optional: Add client-level event handlers
    class MyClientEvents(ClientEventHandler):
        async def on_connected(self, ctx: ConnectedContext):
            logger.info(f"Connected! Client ID: {ctx.client}")
            
        async def on_disconnected(self, ctx: DisconnectedContext):
            logger.info(f"Disconnected: {ctx.reason}")
    
    client = Client(
        ws_url,
        events=MyClientEvents(),
        get_token=get_token)
    
    return client


# Example 1: Basic usage pattern
async def basic_example():
    """Shows the most straightforward way to use centrifuge-python"""
    
    # 1. Create client
    token = "your_jwt_token_here"
    client = await create_centrifugo_client(
        "ws://centrifugo.satorinet.io/connection/websocket",
        token)
    
    # 2. Connect
    await client.connect()
    
    # 3. Subscribe to a channel with inline handler
    class MyHandler(SubscriptionEventHandler):
        async def on_publication(self, ctx: PublicationContext):
            logger.info(f"Got data: {ctx.pub.data}")
            
    sub = client.new_subscription("streams:11451866", events=MyHandler())
    await sub.subscribe()
    
    # 4. Publish data
    await sub.publish({"input": "0.9994234"})
    
    # 5. Keep running for a bit
    await asyncio.sleep(30)
    
    # 6. Cleanup
    await client.disconnect()


# Example 2: More practical pattern for your use case
class DataStreamHandler(SubscriptionEventHandler):
    """Reusable handler for your data streams"""
    
    def __init__(self, stream_id: str, callback=None):
        self.stream_id = stream_id
        self.callback = callback
        
    async def on_publication(self, ctx: PublicationContext):
        data = ctx.pub.data
        logger.info(f"Stream {self.stream_id} received: {data}")
        
        # Your specific logic
        if 'value' in data or 'input' in data:
            value = data.get('value') or data.get('input')
            logger.info(f"Processing value: {value}")
            
            if self.callback:
                await self.callback(value, data)


async def practical_example():
    """Pattern that's closer to your actual use case"""
    
    # Setup
    token = "your_jwt_token"
    client = Client(
        "ws://centrifugo.satorinet.io/connection/websocket",
        get_token=lambda: token  # Simple lambda for token
    )
    
    await client.connect()
    
    # Subscribe to multiple streams
    streams = {}
    
    # Stream 1 with custom processing
    async def process_predictions(value, full_data):
        print(f"Prediction received: {value}")
        # Your processing logic here
    
    sub1 = client.new_subscription(
        "streams:11451866",
        events=DataStreamHandler("11451866", process_predictions)
    )
    await sub1.subscribe()
    streams["11451866"] = sub1
    
    # Stream 2 with different processing
    sub2 = client.new_subscription(
        "streams:22222222",
        events=DataStreamHandler("22222222")  # Uses default logging
    )
    await sub2.subscribe()
    streams["22222222"] = sub2
    
    # Publish to streams
    await streams["11451866"].publish({"input": "0.9994234"})
    await streams["22222222"].publish({"value": "42.0"})
    
    # Run for a while
    await asyncio.sleep(60)
    
    # Cleanup
    await client.disconnect()


# Example 3: If you need it in a class (minimal wrapper)
class SatoriCentrifugo:
    """Minimal wrapper if you need to manage state"""
    
    def __init__(self, ws_url: str, token: str):
        self.ws_url = ws_url
        self.token = token
        self.client = None
        self.subscriptions = {}
        
    async def connect(self):
        self.client = Client(
            self.ws_url,
            get_token=lambda: self.token)
        await self.client.connect()
        
    async def subscribe(self, stream_id: str, handler=None):
        """Subscribe to a stream with optional custom handler"""
        channel = f"streams:{stream_id}"
        
        if handler is None:
            handler = DataStreamHandler(stream_id)
            
        sub = self.client.new_subscription(channel, events=handler)
        await sub.subscribe()
        self.subscriptions[stream_id] = sub
        return sub
        
    async def publish(self, stream_id: str, data: dict):
        """Publish to a subscribed stream"""
        if stream_id in self.subscriptions:
            await self.subscriptions[stream_id].publish(data)
        else:
            raise ValueError(f"Not subscribed to stream {stream_id}")
            
    async def disconnect(self):
        if self.client:
            await self.client.disconnect()


# Usage in your code
async def your_application():
    """How you might use it in your actual application"""
    
    # Option 1: Direct client usage (recommended)
    client = Client(
        ws_url,
        get_token=lambda: token
    )
    await client.connect()
    
    # Create subscription
    sub = client.new_subscription(
        f"streams:{stream_id}",
        events=DataStreamHandler(stream_id)
    )
    await sub.subscribe()
    
    # Publish
    await sub.publish({"input": "0.9994234"})
    
    
    # Option 2: With minimal wrapper
    conn = SatoriCentrifugo(ws_url, wallet_address, token)
    await conn.connect()
    await conn.subscribe("11451866")
    await conn.publish("11451866", {"input": "0.9994234"})
    
    
    # Option 3: Store client directly on your existing class
    self.centrifugo = Client(ws_url, get_token=lambda: token)
    await self.centrifugo.connect()
    
    # Then use it wherever needed
    sub = self.centrifugo.new_subscription(
        f"streams:{stream_id}",
        events=DataStreamHandler(stream_id)
    )


if __name__ == "__main__":
    # Run the basic example
    asyncio.run(basic_example())
'''