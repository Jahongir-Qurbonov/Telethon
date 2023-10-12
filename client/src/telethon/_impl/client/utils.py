import itertools
import sys
import time
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Union

from ..tl import abcs, types
from .types import Channel, Chat, Group, User

_last_id = 0


def generate_random_id() -> int:
    global _last_id
    if _last_id == 0:
        _last_id = int(time.time() * 1e9)
    _last_id += 1
    return _last_id


def build_chat_map(users: List[abcs.User], chats: List[abcs.Chat]) -> Dict[int, Chat]:
    users_iter = (User._from_raw(u) for u in users)
    chats_iter = (
        Channel._from_raw(c)
        if isinstance(c, (types.Channel, types.ChannelForbidden)) and c.broadcast
        else Group._from_raw(c)
        for c in chats
    )

    # https://github.com/python/mypy/issues/2115
    result: Dict[int, Chat] = {
        c.id: c for c in itertools.chain(users_iter, chats_iter)  # type: ignore [attr-defined, misc]
    }

    if len(result) != len(users) + len(chats):
        # The fabled ID collision between different chat types.
        counter: DefaultDict[int, List[Union[abcs.User, abcs.Chat]]] = defaultdict(list)
        for user in users:
            if (id := getattr(user, "id", None)) is not None:
                counter[id].append(user)
        for chat in chats:
            if (id := getattr(chat, "id", None)) is not None:
                counter[id].append(chat)

        for k, v in counter.items():
            if len(v) > 1:
                # TODO proper logger
                for x in v:
                    print(x, file=sys.stderr)

                raise RuntimeError(
                    f"chat identifier collision: {k}; please report this"
                )

    return result


def peer_id(peer: abcs.Peer) -> int:
    if isinstance(peer, types.PeerUser):
        return peer.user_id
    elif isinstance(peer, types.PeerChat):
        return peer.chat_id
    elif isinstance(peer, types.PeerChannel):
        return peer.channel_id
    else:
        raise RuntimeError("unexpected case")


def expand_peer(peer: abcs.Peer, *, broadcast: Optional[bool]) -> Chat:
    if isinstance(peer, types.PeerUser):
        return User._from_raw(types.UserEmpty(id=peer.user_id))
    elif isinstance(peer, types.PeerChat):
        return Group._from_raw(types.ChatEmpty(id=peer.chat_id))
    elif isinstance(peer, types.PeerChannel):
        if broadcast is None:
            broadcast = True  # assume broadcast by default (Channel type is more accurate than Group)

        channel = types.ChannelForbidden(
            broadcast=broadcast,
            megagroup=not broadcast,
            id=peer.channel_id,
            access_hash=0,
            title="",
            until_date=None,
        )

        return Channel._from_raw(channel) if broadcast else Group._from_raw(channel)
    else:
        raise RuntimeError("unexpected case")