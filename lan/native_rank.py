"""Validated echo of one caller's current native rank, never rating authority.

The native adapter selects its category/extra record from the game's cache, or
mirrors the verified native missing-entry constructor if no such record exists.
These fields preserve its own result UI; they must not update account Elo,
another player, or persistent rank statistics.
"""
from __future__ import annotations

import math
import struct
import unicodedata


_FIELDS=frozenset(('rank_title','rank_point','prev_need_point','next_need_point',
    'win_streak','win_streak_r_bits','app_multiplayer_mode','battle_type',
    'pvp_extra_type','rank_range','rank'))


def _integer(value,lower,upper):
    if type(value) is not int or not lower<=value<=upper:
        raise ValueError('invalid native rank integer')
    return value


def validate_rank_snapshot(snapshot):
    """Return a fresh native JSON rank object after exact typed validation.

    Float32 bits avoid the native process locale changing decimal formatting.
    Their finite value is converted only for this caller's response projection.
    """
    if type(snapshot) is not dict or set(snapshot)!=_FIELDS:
        raise ValueError('invalid native rank snapshot fields')
    title=snapshot['rank_title']
    if type(title) is not str or any(unicodedata.category(c)=='Cc' for c in title):
        raise ValueError('invalid native rank title')
    try:
        encoded=title.encode('utf-8')
    except UnicodeEncodeError:
        raise ValueError('invalid native rank title') from None
    if len(encoded)>128:
        raise ValueError('native rank title exceeds bound')
    result={'rank_title':title}
    for field in ('rank_point','prev_need_point','next_need_point'):
        result[field]=_integer(snapshot[field],-(2**31),2**31-1)
    result['win_streak']=_integer(snapshot['win_streak'],0,2**32-1)
    bits=_integer(snapshot['win_streak_r_bits'],0,2**32-1)
    value=struct.unpack('<f',struct.pack('<I',bits))[0]
    if not math.isfinite(value):
        raise ValueError('nonfinite native rank ratio')
    result['win_streak_r']=value
    for field in ('app_multiplayer_mode','battle_type','pvp_extra_type'):
        result[field]=_integer(snapshot[field],0,255)
    for field in ('rank_range','rank'):
        result[field]=_integer(snapshot[field],-128,127)
    return result
