"""Bounded SESSION3 value codec. No native pointers or game calls.

This encoder is not yet used by the installed search-only RPC. It supplies
the reconstructed descriptor decoder/lifecycle adapter, not a battle signal.
"""
import base64
import re

from native_sessions import _fields, _integer, _native_stream, _native_text

MAX_FRAME = 16384
_ID = re.compile(r"[0-9a-f]{32}\Z")


def identifier(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("invalid native descriptor ID")
    return value


def encode_descriptor(descriptor, version=3):
    if type(version) is not int or version not in (3, 4):
        raise ValueError("unsupported session frame version")
    _fields(descriptor, ("profile", "compatibility", "numeric", "capacity", "field_e1",
                         "stream", "properties", "id", "members"))
    if type(descriptor["profile"]) is not int or descriptor["profile"] != 2:
        raise ValueError("SESSION3 requires profile2")
    if type(descriptor["properties"]) is not list or descriptor["properties"]:
        raise ValueError("unsupported native properties")
    numbers = descriptor["numeric"]
    if type(numbers) is not list or len(numbers) > 16:
        raise ValueError("too many native numeric values")
    tokens = [f"SESSION{version}", identifier(descriptor["id"]),
              str(_integer(descriptor["compatibility"], 0, 2**32 - 1)), str(len(numbers))]
    tokens += [str(_integer(n, -(2**31), 2**31 - 1)) for n in numbers]
    capacity = _integer(descriptor["capacity"], 1, 8 if version == 4 else 2)
    if version == 3 and capacity != 2:
        raise ValueError("SESSION3 capacity must be two")
    tokens += [str(capacity), str(_integer(descriptor["field_e1"], 0, 255))]
    stream = _native_stream(descriptor["stream"])
    if stream is None:
        tokens += ["0", "0", "0", "0", "-"]
    else:
        payload = base64.b64decode(stream["data_base64"], validate=True)
        tokens += ["1", str(len(payload)), str(stream["read_cursor"]),
                   str(stream["write_cursor"]), payload.hex() or "-"]
    members = descriptor["members"]
    if type(members) is not list or not 1 <= len(members) <= capacity:
        raise ValueError("native member count out of bounds")
    tokens.append(str(len(members)))
    seen, previous, owners = set(), -1, 0
    for member in members:
        _fields(member, ("identity_hex", "address_hex", "field_88", "optional_present",
                         "optional_value", "field_8b", "id", "join_order", "owner"))
        identity = member["identity_hex"]
        if type(identity) is not list or len(identity) != 2:
            raise ValueError("native identity pair required")
        mid = identifier(member["id"])
        order = _integer(member["join_order"], 0, 2**64 - 1)
        if mid in seen or order <= previous:
            raise ValueError("duplicate or unordered native member")
        seen.add(mid)
        previous = order
        if type(member["owner"]) is not bool or type(member["optional_present"]) is not bool:
            raise ValueError("native member flags must be booleans")
        owners += member["owner"]
        if type(member["field_8b"]) is not int or member["field_8b"] != 0:
            raise ValueError("process-local marker must not be shared")
        tokens += [mid, str(order), *[_native_text(text) for text in identity],
                   _native_text(member["address_hex"]), str(_integer(member["field_88"], 0, 255)),
                   str(int(member["optional_present"])), str(_integer(member["optional_value"], 0, 255)),
                   "0", str(int(member["owner"]))]
    if owners != 1:
        raise ValueError("native descriptor must have exactly one owner")
    frame = (" ".join(tokens) + "\n").encode("ascii")
    if len(frame) > MAX_FRAME:
        raise ValueError("native descriptor frame exceeds bound")
    return frame
