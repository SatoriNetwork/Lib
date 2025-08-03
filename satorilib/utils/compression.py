''' simple standard library compression and decompression '''

import zlib
import base64

def compress(json_str: str) -> str:
    compressed = zlib.compress(json_str.encode('utf-8'))
    return base64.b64encode(compressed).decode('utf-8')

def decompress(encoded_str: str) -> str:
    compressed = base64.b64decode(encoded_str.encode('utf-8'))
    return zlib.decompress(compressed).decode('utf-8')

## Example usage
#import json
#original_json = json.dumps({
#    "pubkey": "1s3f51s35ef47s3e543fs132f13s21ef3s54ef35s4e3f54se3f3sef35s1ef35s1ef35s4ef53s4e", 
#    "message": {
#        "timestamp": 1722739200,
#        "nonce": 1234567890,
#        "challenge": "as1fe35s3e3fs5e534s35f43s1e35fs1",
#        "signature": "s1ef3se15fs34ef43s51er3se1f35s4ef354se3541s3ef13s5f4s35f4",
#        "method": "concat"
#    },
#    "signature": "sf13e2f3sef35s4f354sef85s13ef13se1f32s1e3f1s3ef48s3f7463s54ef3s1ef35s1ef3se3f21se3f2sef1se3f"
#})
#compressed = compress(original_json)
#decompressed = decompress(compressed)
#
#print("Original:  ", original_json)
#print("Compressed:", compressed)
#print("Decompressed:", decompressed)
#assert decompressed == original_json
#