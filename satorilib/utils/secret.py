# pycryptodome-3.20.0
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64



def encrypt(content, password: str) -> str:
    """
    Encrypts the content using AES encryption with a key derived from the given password.
    """
    # Generate a random salt
    salt = get_random_bytes(16)
    # Derive a key from the password
    key = PBKDF2(password, salt, dkLen=32, count=1000000)
    # Create a new AES cipher in CBC mode
    cipher = AES.new(key, AES.MODE_CBC)
    # Encrypt the content (padding it to ensure it's a multiple of the block size)
    ctBytes = cipher.encrypt(pad(content.encode(), AES.block_size))
    # Return the salt, iv, and ciphertext, all base64 encoded and concatenated
    return base64.b64encode(salt + cipher.iv + ctBytes).decode()


def decrypt(encrypted, password: str) -> str:
    """
    Decrypts the content encrypted by encrypt_content function.
    """
    # Decode the base64 encoded encrypted content
    encryptedBytes = base64.b64decode(encrypted)
    # Extract the salt, iv, and ciphertext
    salt = encryptedBytes[:16]
    iv = encryptedBytes[16:32]
    ct = encryptedBytes[32:]
    # Derive the key using the same password and salt
    key = PBKDF2(password, salt, dkLen=32, count=1000000)
    # Create a new AES cipher in CBC mode for decryption
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # Decrypt the ciphertext and unpad it
    pt = unpad(cipher.decrypt(ct), AES.block_size).decode()
    return pt


def decryptMapValues(encrypted: dict, password: str) -> dict:
    ''' decrypts all the values in the dictionary, even if it's nested '''
    decrypted = {}
    for k, v in encrypted.items():
        if isinstance(v, str):
            # Assuming decrypt is defined elsewhere
            decrypted[k] = decrypt(v, password)
        elif isinstance(v, dict):
            # Recursive call for nested dict
            decrypted[k] = decryptMapValues(v, password)
        else:
            decrypted[k] = v
    return decrypted


def encryptMapValues(content: dict, password: str, keys: list = None) -> dict:
    ''' encrypts all the values in the dictionary, even if it's nested '''
    if password is None:
        return content
    encrypted = {}
    keys = keys or []
    for k, v in content.items():
        if isinstance(v, str) and (len(k) == 0 or (len(k) > 0 and k in keys)):
            encrypted[k] = encrypt(v, password)
        elif isinstance(v, dict):
            encrypted[k] = encryptMapValues(v, password, keys)
        else:
            encrypted[k] = v
    return encrypted


def decryptMapValues(encrypted: dict, password: str, keys: list = None) -> dict:
    ''' decrypts all the values in the dictionary, even if it's nested '''
    # return {
    #    k: decrypt(v, password)
    #    if isinstance(v, str)
    #    else decryptMapValues(v, password)  # might not be a dictionary...
    #    for k, v in encrypted.items()}
    if password is None:
        return encrypted
    decrypted = {}
    keys = keys or []
    for k, v in encrypted.items():
        if isinstance(v, str) and (len(k) == 0 or (len(k) > 0 and k in keys)):
            decrypted[k] = decrypt(v, password)
        elif isinstance(v, dict):
            decrypted[k] = decryptMapValues(v, password, keys)
        else:
            decrypted[k] = v
    return decrypted

# Example usage
# password = "your_password_here"
# original_content = "Sensitive data in the YAML file."
#
# Encrypt the content
# encrypted_content = encrypt_content(original_content, password)
# print("Encrypted:", encrypted_content)
#
# Decrypt the content
# decrypted_content = decrypt_content(encrypted_content, password)
# print("Decrypted:", decrypted_content)
