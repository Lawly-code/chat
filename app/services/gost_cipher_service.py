import struct
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor


class GostCipherService:
    # S-блоки
    S_BOX = [
        [4, 10, 9, 2, 13, 8, 0, 14, 6, 11, 1, 12, 7, 15, 5, 3],
        [14, 11, 4, 12, 6, 13, 15, 10, 2, 3, 8, 1, 0, 7, 5, 9],
        [5, 8, 1, 13, 10, 3, 4, 2, 14, 15, 12, 7, 6, 0, 9, 11],
        [7, 13, 10, 1, 0, 8, 9, 15, 14, 4, 6, 12, 11, 2, 5, 3],
        [6, 12, 7, 1, 5, 15, 13, 8, 4, 10, 9, 14, 0, 3, 11, 2],
        [4, 11, 10, 0, 7, 2, 1, 13, 3, 6, 8, 5, 9, 12, 15, 14],
        [13, 11, 4, 1, 3, 15, 5, 9, 0, 10, 14, 7, 6, 8, 2, 12],
        [1, 15, 13, 0, 5, 7, 10, 4, 9, 2, 3, 14, 6, 11, 8, 12],
    ]

    def __init__(self):
        self._executor = ThreadPoolExecutor()

    def _gost_round(self, a: int, k: int) -> int:
        t = (a + k) & 0xFFFFFFFF
        y = 0
        for i, row in enumerate(self.S_BOX):
            y |= row[(t >> (4 * i)) & 0xF] << (4 * i)
        return ((y << 11) | (y >> (32 - 11))) & 0xFFFFFFFF

    def _split_blocks(self, data: bytes, bs=8):
        return [data[i:i + bs] for i in range(0, len(data), bs)]

    def _init_cipher(self, key: bytes):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes")
        self.subkeys = [int.from_bytes(key[i * 4:(i + 1) * 4], 'little') for i in range(8)]

    def encrypt_block(self, block: bytes, key: bytes) -> bytes:
        self._init_cipher(key)
        n1, n2 = struct.unpack('<II', block)
        for i in range(24):
            n1, n2 = n2, n1 ^ self._gost_round(n2, self.subkeys[i % 8])
        for i in range(8):
            n1, n2 = n2, n1 ^ self._gost_round(n2, self.subkeys[7 - i])
        return struct.pack('<II', n2, n1)

    def decrypt_block(self, block: bytes, key: bytes) -> bytes:
        self._init_cipher(key)
        n1, n2 = struct.unpack('<II', block)
        for i in range(8):
            n1, n2 = n2, n1 ^ self._gost_round(n2, self.subkeys[i])
        for i in range(24):
            n1, n2 = n2, n1 ^ self._gost_round(n2, self.subkeys[(7 - (i % 8))])
        return struct.pack('<II', n2, n1)

    def encrypt_cfb(self, data: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        """
        Шифрование данных в режиме CFB
        
        :param data: Данные для шифрования
        :param key: Ключ шифрования
        :param iv: Вектор инициализации (опционально)
        :return: Зашифрованные данные
        """
        self._init_cipher(key)
        if iv is None:
            iv = os.urandom(8)
        elif len(iv) != 8:
            raise ValueError("IV must be 8 bytes")

        out = bytearray()
        gamma = iv
        for blk in self._split_blocks(data):
            gamma = self.encrypt_block(gamma, key)
            stream = gamma[:len(blk)]
            cx = bytes(b ^ s for b, s in zip(blk, stream))
            out += cx
            gamma = cx
        return iv + bytes(out)  # Включаем IV в выходные данные

    def decrypt_cfb(self, data: bytes, key: bytes) -> bytes:
        """
        Расшифрование данных в режиме CFB
        
        :param data: Зашифрованные данные
        :param key: Ключ шифрования
        :return: Расшифрованные данные
        """
        self._init_cipher(key)
        iv, cipher = data[:8], data[8:]

        if len(iv) != 8:
            raise ValueError("IV must be 8 bytes")

        out = bytearray()
        gamma = iv
        for blk in self._split_blocks(cipher):
            gamma = self.encrypt_block(gamma, key)
            stream = gamma[:len(blk)]
            px = bytes(c ^ s for c, s in zip(blk, stream))
            out += px
            gamma = blk
        return bytes(out)

    # Синхронные методы
    def encrypt_data(self, data: str | bytes, key: bytes) -> str | bytes:
        """
        Шифрование данных
        
        :param data: Данные для шифрования (строка или байты)
        :param key: Ключ шифрования
        :return: Зашифрованные данные в том же формате
        """
        is_str = isinstance(data, str)
        raw = data.encode('utf-8') if is_str else data
        blob = self.encrypt_cfb(raw, key)
        return blob.hex() if is_str else blob

    def decrypt_data(self, blob: str | bytes, key: bytes) -> str | bytes:
        """
        Расшифрование данных
        
        :param blob: Зашифрованные данные (строка в hex-формате или байты)
        :param key: Ключ шифрования
        :return: Расшифрованные данные в том же формате
        """
        is_str = isinstance(blob, str)
        raw = bytes.fromhex(blob) if is_str else blob
        plain = self.decrypt_cfb(raw, key)
        return plain.decode('utf-8') if is_str else plain

    # Асинхронные методы
    async def async_encrypt_data(self, data: str | bytes, key: bytes) -> str | bytes:
        """
        Асинхронное шифрование данных
        
        :param data: Данные для шифрования (строка или байты)
        :param key: Ключ шифрования
        :return: Зашифрованные данные в том же формате
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.encrypt_data, data, key)

    async def async_decrypt_data(self, blob: str | bytes, key: bytes) -> str | bytes:
        """
        Асинхронное расшифрование данных
        
        :param blob: Зашифрованные данные (строка в hex-формате или байты)
        :param key: Ключ шифрования
        :return: Расшифрованные данные в том же формате
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.decrypt_data, blob, key)
