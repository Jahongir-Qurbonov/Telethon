from abc import ABC, abstractmethod
from collections.abc import Callable

OutFn = Callable[[bytes | bytearray | memoryview], None]


class UnpackedOffset:
    __slots__ = ("data_start", "data_end", "next_offset")

    def __init__(self, *, data_start: int, data_end: int, next_offset: int) -> None:
        self.data_start = data_start
        self.data_end = data_end
        self.next_offset = next_offset


class Transport(ABC):
    # Python's stream writer has a synchronous write (buffer append) followed
    # by drain. The buffer is externally managed, so `write` is used as input.
    @abstractmethod
    def pack(self, buffer: bytearray) -> None:
        pass

    @abstractmethod
    def unpack(self, buffer: bytes | bytearray | memoryview) -> UnpackedOffset:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass


class MissingBytesError(ValueError):
    def __init__(self) -> None:
        super().__init__("need more bytes")


class BadLenError(ValueError):
    def __init__(self, *, got: int) -> None:
        super().__init__(f"bad len (got {got})")


class BadSeqError(ValueError):
    def __init__(self, *, expected: int, got: int) -> None:
        super().__init__(f"bad seq (expected {expected}, got {got})")


class BadCrcError(ValueError):
    def __init__(self, *, expected: int, got: int) -> None:
        super().__init__(f"bad crc (expected {expected}, got {got})")


class BadStatusError(ValueError):
    def __init__(self, *, status: int) -> None:
        super().__init__(f"bad status (negative length -{status})")
        self.status = status


TransportError = (
    MissingBytesError | BadLenError | BadSeqError | BadCrcError | BadStatusError
)

TransportErrors = (
    MissingBytesError,
    BadLenError,
    BadSeqError,
    BadCrcError,
    BadStatusError,
)
