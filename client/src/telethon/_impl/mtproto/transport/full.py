import logging
import struct
import zlib

from .abcs import (
    BadCrcError,
    BadLenError,
    BadSeqError,
    BadStatusError,
    MissingBytesError,
    Transport,
    UnpackedOffset,
)


class Full(Transport):
    __slots__ = ("_send_seq", "_recv_seq")

    """
    Implementation of the [full transport]:

    ```text
    +----+----+----...----+----+
    | len| seq|  payload  | crc|
    +----+----+----...----+----+
     ^^^^ 4 bytes
    ```

    [full transport]: https://core.telegram.org/mtproto/mtproto-transports#full
    """

    def __init__(self) -> None:
        self._send_seq = 0
        self._recv_seq = 0

    def pack(self, buffer: bytearray) -> None:
        length = len(buffer)
        assert length % 4 == 0

        # payload len + length itself (4 bytes) + send counter (4 bytes) + crc32 (4 bytes)
        total_len = length + 4 + 4 + 4

        buffer[:0] = struct.pack("<i", self._send_seq)
        buffer[:0] = struct.pack("<i", total_len)

        crc = zlib.crc32(buffer)
        buffer.extend(struct.pack("<I", crc))

        self._send_seq += 1

    def unpack(self, buffer: bytes | bytearray | memoryview) -> UnpackedOffset:
        if len(buffer) < 4:
            raise MissingBytesError()

        total_len = len(buffer)
        length: int = struct.unpack("<i", buffer[0:4])[0]
        if length < 12:
            if length < 0:
                raise BadStatusError(status=-length)
            raise BadLenError(got=length)

        if total_len < length:
            raise MissingBytesError()

        seq = struct.unpack("<i", buffer[4:8])[0]
        if seq != self.recv_seq:
            raise BadSeqError(expected=self.recv_seq, got=seq)

        # CRC32 check
        crc = struct.unpack("<I", buffer[length - 4 : length])[0]
        valid_crc = zlib.crc32(buffer[: length - 4])
        if crc != valid_crc:
            raise BadCrcError(expected=valid_crc, got=crc)

        self.recv_seq += 1
        return UnpackedOffset(
            data_start=8,
            data_end=length - 4,
            next_offset=length,
        )

    def reset(self):
        logging.info("resetting recv and send seqs in full transport")
        self._send_seq = 0
        self._recv_seq = 0
