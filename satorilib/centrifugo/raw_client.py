'''examples'''
'''
import asyncio
import logging
import signal
from centrifuge import (
    Client,
    ClientEventHandler,
    SubscriptionEventHandler,
    ConnectedContext,
    DisconnectedContext,
    PublicationContext,
    CentrifugeError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)

class MyClientEventHandler(ClientEventHandler):
    async def on_connected(self, ctx: ConnectedContext) -> None:
        logging.info("✅ Connected to Centrifugo server")
    
    async def on_disconnected(self, ctx: DisconnectedContext) -> None:
        logging.info("❌ Disconnected from Centrifugo server")

class MySubscriptionEventHandler(SubscriptionEventHandler):
    async def on_publication(self, ctx: PublicationContext) -> None:
        logging.info(f"📨 Received publication: {ctx.pub.data}")
    
    async def on_subscribed(self, ctx) -> None:
        logging.info("🔔 Subscribed to channel")
    
    async def on_unsubscribed(self, ctx) -> None:
        logging.info("🔕 Unsubscribed from channel")

async def get_client_token() -> str:
    # Replace with your JWT token generation logic
    # This token should be generated on your backend
    return "your_jwt_token_here"

async def main():
    # Create client
    client = Client(
        "ws://centrifugo.satorinet.io/connection/websocket",
        get_token=get_client_token,
        events=MyClientEventHandler(),
    )
    
    # Create subscription
    sub = client.new_subscription(
        "your_channel_name",  # Replace with your channel
        events=MySubscriptionEventHandler(),
    )
    
    try:
        # Connect to server
        await client.connect()
        
        # Subscribe to channel
        await sub.subscribe()
        
        # Example: Publish a test message
        await sub.publish(data={
            "message": "Hello from Python client!",
            "timestamp": asyncio.get_event_loop().time()
        })
        
        logging.info("🚀 Client connected and subscribed. Press Ctrl+C to exit")
        
        # Keep the connection alive
        await asyncio.Event().wait()
        
    except CentrifugeError as e:
        logging.error(f"❌ Centrifuge error: {e}")
    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
    finally:
        # Cleanup
        await client.disconnect()
        logging.info("🔄 Client disconnected")

if __name__ == "__main__":
    # Handle graceful shutdown
    def signal_handler():
        logging.info("🛑 Received exit signal")
        asyncio.current_task().cancel()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Goodbye!")
'''