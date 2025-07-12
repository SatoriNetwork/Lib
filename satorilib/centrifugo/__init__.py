from .client import (
    create_centrifugo_client,
    create_subscription_handler,
    subscribe_to_stream,
    publish_to_stream_rest,
)

__all__ = [
    'create_centrifugo_client',
    'create_subscription_handler',
    'subscribe_to_stream',
    'publish_to_stream_rest',
]


notes= """
  token = jwt.encode({
      'sub': wallet_address,
      'iat': int(time.time()),
      'exp': int(time.time()) + 86400  # 24 hours
  }, hmac_secret, algorithm='HS256')

  print(f"Using token: {token}")

  # Use 1: REST API Publishing
  response = requests.post(
      'https://gatekeeper.satorinet.io/api/publish',
      headers={'Authorization': f'Bearer {token}'},  # Same token
      json={
          'channel': 'streams:4de07abf-8aa9-57f3-8733-284beaf54d51',
          'data': '0.12345'
      }
  )
  print(f"REST API: {response.status_code}")

  # Use 2: WebSocket Connection
  async def websocket_example():
      ws = await websockets.connect('ws://centrifugo.satorinet.io/connection/websocket')

      # Connect with same token
      await ws.send(json.dumps({
          "id": 1,
          "connect": {
              "token": token  # Same token
          }
      }))

      response = await ws.recv()
      print(f"WebSocket: {response}")
"""