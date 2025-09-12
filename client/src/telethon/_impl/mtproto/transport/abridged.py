import logging
import struct

from .abcs import BadStatusError, MissingBytesError, Transport, UnpackedOffset


class Abridged(Transport):
    __slots__ = ("_init",)

    """
    Implementation of the [abridged transport]:

    ```text
    +----+----...----+
    | len|  payload  |
    +----+----...----+
     ^^^^ 1 or 4 bytes
    ```

    [abridged transport]: https://core.telegram.org/mtproto/mtproto-transports#abridged
    """

    def __init__(self) -> None:
        self._init = False

    def pack(self, buffer: bytearray) -> None:
        assert len(buffer) % 4 == 0

        length = len(buffer) // 4
        if length < 127:
            buffer[:0] = bytes([length])
        else:
            val = 0x7F | (length << 8)
            buffer[:4] = struct.pack("<i", val)

        if not self.init:
            buffer[:0] = bytes([0xEF])
            self.init = True

    def unpack(self, buffer: bytes | bytearray | memoryview) -> UnpackedOffset:
        if not buffer:
            raise MissingBytesError()

        len_byte = buffer[0]
        if len_byte < 127:
            header_len = 1
            length = len_byte
        else:
            if len(buffer) < 4:
                raise MissingBytesError()
            header_len = 4
            # '<i' is little-endian signed int
            length = struct.unpack("<i", buffer[0:4])[0] >> 8

        length = length * 4
        if len(buffer) < header_len + length:
            raise MissingBytesError()

        if header_len == 1 and length >= 4:
            data = struct.unpack("<i", buffer[1:5])[0]
            if data < 0:
                raise BadStatusError(status=-data)

        return UnpackedOffset(
            data_start=header_len,
            data_end=header_len + length,
            next_offset=header_len + length,
        )

    def reset(self):
        logging.info("resetting sending of header in abridged transport")
        self._init = False
