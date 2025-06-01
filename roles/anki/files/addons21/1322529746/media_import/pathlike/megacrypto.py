# This code is copied from mega.py library
# which is licenced under Apache License 2.0
# https://github.com/odwyersoftware/mega.py
# Modified to use pyaes instead of pycrypto

# type: ignore

import base64
import struct
import codecs
import json

from pyaes import AESModeOfOperationCBC


def makebyte(x):
    return codecs.latin_1_encode(x)[0]


def makestring(x):
    return codecs.latin_1_decode(x)[0]


def str_to_a32(b):
    if isinstance(b, str):
        b = makebyte(b)
    if len(b) % 4:
        # pad to multiple of 4
        b += b"\0" * (4 - len(b) % 4)
    return struct.unpack(">%dI" % (len(b) / 4), b)


def a32_to_str(a):
    return struct.pack(">%dI" % len(a), *a)


def base64_url_decode(data):
    data += "=="[(2 - len(data) * 3) % 4 :]
    for search, replace in (("-", "+"), ("_", "/"), (",", "")):
        data = data.replace(search, replace)
    return base64.b64decode(data)


def base64_to_a32(s):
    return str_to_a32(base64_url_decode(s))


def base64_url_encode(data):
    data = base64.b64encode(data)
    data = makestring(data)
    for search, replace in (("+", "-"), ("/", "_"), ("=", "")):
        data = data.replace(search, replace)
    return data


def aes_cbc_decrypt(data, key):
    """data is must be multiple of 16 bytes"""
    aes = AESModeOfOperationCBC(key, makebyte("\0" * 16))
    decrypted = b""
    for i in range(0, len(data), 16):
        decrypted += aes.decrypt(data[i : i + 16])
    return decrypted


def aes_cbc_decrypt_a32(data, key):
    return str_to_a32(aes_cbc_decrypt(a32_to_str(data), a32_to_str(key)))


def decrypt_attr(attr, key):
    k = a32_to_str(key)
    attr = aes_cbc_decrypt(attr, a32_to_str(key))
    attr = makestring(attr)
    attr = attr.rstrip("\0")
    return json.loads(attr[4:]) if attr[:6] == 'MEGA{"' else False


def decrypt_key(a, key):
    return sum(
        (aes_cbc_decrypt_a32(a[i : i + 4], key) for i in range(0, len(a), 4)), ()
    )
