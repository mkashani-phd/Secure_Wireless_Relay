# pip install pycryptodome
from typing import Optional, Tuple
from Crypto.Cipher import AES
from os import urandom



BLOCK = 16        # 128-bit AES block size in bytes
MOD128 = 1 << 128

class AESCTRAligned:
    """
    AES-CTR keystream slicer with 128-bit alignment guarantees.
    - Requires: start and length multiples of 16 bytes (128 bits).
    - PyCryptodome backend (AES.MODE_CTR, nonce=b"", initial_value=<counter>).
    - Random access: compute exactly the window you need.
    """

    @staticmethod
    def _require_alignment(iv: bytes, start_bytes: int, length_bytes: int):
        if len(iv) != BLOCK:
            raise ValueError("IV must be exactly 16 bytes (128 bits).")
        if (start_bytes % BLOCK) != 0:
            raise ValueError("start_bytes must be divisible by 16 (128-bit alignment).")
        if (length_bytes % BLOCK) != 0:
            raise ValueError("length_bytes must be divisible by 16 (128-bit alignment).")

    @staticmethod
    def _ctr_encrypt_zeros(key: bytes, iv: bytes, block_start: int, nblocks: int) -> bytes:
        """Encrypt nblocks*16 zero bytes starting at counter = iv + block_start (mod 2^128)."""
        ctr0 = (int.from_bytes(iv, "big") + block_start) % MOD128
        cipher = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=ctr0)
        return cipher.encrypt(b"\x00" * (nblocks * BLOCK))

    @classmethod
    def get_range(
        cls,
        key: bytes,
        iv: bytes,
        *,
        start_bytes: Optional[int] = None,
        length_bytes: Optional[int] = None,
        chunk_bits: Optional[int] = None,
        index: Optional[int] = None,
        return_int: bool = False,
    ) -> Tuple[bytes, Optional[int]]:
        """
        Overloaded interface:
        1) Byte-window mode: pass start_bytes and length_bytes (both multiples of 16).
        2) Chunk mode: pass chunk_bits (multiple of 128) and 1-based index.

        Returns (bytes_out, as_int or None). If return_int=True, also returns the big-endian integer.
        """

        # --- Select mode & compute start/length in BYTES ---
        if (start_bytes is not None or length_bytes is not None) and (chunk_bits is not None or index is not None):
            raise ValueError("Use either (start_bytes, length_bytes) OR (chunk_bits, index), not both.")

        if start_bytes is not None or length_bytes is not None:
            if start_bytes is None or length_bytes is None:
                raise ValueError("Provide both start_bytes and length_bytes.")
            sb, lb = int(start_bytes), int(length_bytes)

        else:
            # Chunk mode
            if chunk_bits is None or index is None:
                raise ValueError("Provide both chunk_bits and index for chunk mode.")
            if index <= 0:
                raise ValueError("index must be 1-based and >= 1.")
            if (chunk_bits % 128) != 0:
                raise ValueError("chunk_bits must be divisible by 128.")
            bytes_per_chunk = chunk_bits // 8
            sb = bytes_per_chunk * (index - 1)
            lb = bytes_per_chunk

        # Enforce 128-bit alignment and valid sizes
        cls._require_alignment(iv, sb, lb)

        # --- Compute CTR start and number of blocks ---
        block_start = sb // BLOCK
        nblocks = lb // BLOCK  # exact due to alignment

        # --- Generate aligned keystream ---
        out = cls._ctr_encrypt_zeros(key, iv, block_start, nblocks)

        if return_int:
            return out, int.from_bytes(out, "big")
        else:
            return out, None


# ----------------- Example usage -----------------
if __name__ == "__main__":
    # 32B key (AES-256) and 16B IV (128-bit). Use secure exchange/storage in practice.

    key = bytes.fromhex("00112233445566778899aabbccddeeff" * 2)
    iv  = bytes.fromhex("0f0e0d0c0b0a09080706050403020100")

    key = urandom(32)
    iv = urandom(16)

    # Mode 1: Byte window (aligned).
    # Get 4 blocks (64 bytes) starting at block 8 -> start_bytes=8*16=128, length_bytes=64
    bytes_out, as_int = AESCTRAligned.get_range(
        key, iv,
        start_bytes=128,
        length_bytes=64,
        return_int=True
    )
    print("Byte window:", len(bytes_out), bytes_out[:16].hex(), "int(head-16)~", int.from_bytes(bytes_out[:16], "big"))

    # Mode 2: Chunked by bit-length (aligned).
    # Example from your note: chunk_bits=256, index=3 → window [64..96) bytes.
    bytes_out2, as_int2 = AESCTRAligned.get_range(
        key, iv,
        chunk_bits=256*2,
        index=400,
        return_int=True
    )
    print("Chunked:", len(bytes_out2), bytes_out2[:16].hex(), "int(head-16)~", int.from_bytes(bytes_out2[:16], "big"))
