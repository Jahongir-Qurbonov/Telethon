import logging
import struct

from .abcs import (
    BadLenError,
    BadStatusError,
    MissingBytesError,
    Transport,
    UnpackedOffset,
)


class Intermediate(Transport):
    __slots__ = ("_init",)

    """
    Implementation of the [intermediate transport]:

    ```text
    +----+----...----+
    | len|  payload  |
    +----+----...----+
     ^^^^ 4 bytes
    ```

    [intermediate transport]: https://core.telegram.org/mtproto/mtproto-transports#intermediate
    """

    TAG = struct.pack("<I", 0xEEEEEEEE)

    def __init__(self) -> None:
        self._init = False

    def pack(self, buffer: bytearray):
        length = len(buffer)
        assert length % 4 == 0

        buffer[:0] = struct.pack("<i", length)
        if not self.init:
            buffer[:0] = self.TAG
            self.init = True

    def unpack(self, buffer: bytes | bytearray | memoryview) -> UnpackedOffset:
        if len(buffer) < 4:
            raise MissingBytesError()

        length = struct.unpack("<i", buffer[0:4])[0]
        if len(buffer) < length:
            raise MissingBytesError()

        if length <= 4:
            if length >= 4:
                data = struct.unpack("<i", buffer[4:8])[0]
                raise BadStatusError(status=-data)
            raise BadLenError(got=length)

        return UnpackedOffset(
            data_start=4,
            data_end=4 + length,
            next_offset=4 + length,
        )

    def reset(self):
        logging.info("resetting sending of header in intermediate transport")
        self._init = False
