"""Conservative Sparking ZERO save inspection and earned-content unlocks.

Only existing, explicitly selected tagged gameplay-unlock booleans are changed.
No DLL/Steam/DLC ownership, story, rank, inventory count or unknown field edits.
The actual game must be closed; callers must supply a fail-closed running check.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import struct
import tempfile
from dataclasses import dataclass
from typing import Callable
import uuid

try:
    from save_catalog import BASE_KEYS
except ImportError:
    from .save_catalog import BASE_KEYS

MAX_FILE = 32 * 1024 * 1024
MAX_PLAIN = 32 * 1024 * 1024
MAX_ROWS = 50000


class SaveError(ValueError):
    """The operation is unsafe or this save layout is unsupported."""


class _Random:
    def __init__(self, seed=0):
        self.seed(seed)

    def seed(self, seed):
        seed &= 0xffffffff
        self.state = []
        for i in range(1, 5):
            seed = ((seed ^ (seed >> 30)) * 0x384B5D41 + i) & 0xffffffff
            self.state.append(seed)

    def next(self):
        x, y, z, w = self.state
        t = (x ^ (x << 11)) & 0xffffffff
        value = (w ^ (w >> 19) ^ t ^ (t >> 8)) & 0xffffffff
        self.state = [y, z, w, value]
        return value

    def word(self):
        low, high = self.next(), self.next()
        return (high << 32) | low


def _xor(data, random):
    out = bytearray(data)
    for i in range(len(out)):
        if i % 8 == 0:
            word = random.word()
        out[i] ^= word & 255
        word >>= 8
    return bytes(out)


def _payload_seed(key, digest):
    for byte in digest:
        key = ((key >> 8) | ((key ^ byte) << 56)) & 0xffffffffffffffff
    return key & 0xffffffff


def decode_envelope(data: bytes) -> bytes:
    if not 16 <= len(data) <= MAX_FILE:
        raise SaveError('Unsupported save envelope size')
    n = len(data) - 16
    stride = n // 17
    prefix = n - stride * 16
    payload = bytearray(data[:prefix])
    digest = bytearray(16)
    cursor = prefix
    for i in range(15, -1, -1):
        digest[i] = data[cursor]
        payload.extend(data[cursor + 1:cursor + 1 + stride])
        cursor += stride + 1
    random = _Random()
    key = random.word()
    random.seed(key)
    digest = _xor(digest, random)
    random.seed(_payload_seed(key, digest))
    payload = _xor(payload, random)
    if hashlib.md5(payload).digest() != digest:
        raise SaveError('Save integrity check failed; no changes were made')
    return payload


def encode_envelope(payload: bytes) -> bytes:
    if len(payload) > MAX_FILE - 16:
        raise SaveError('Save payload too large')
    digest = hashlib.md5(payload).digest()
    random = _Random()
    key = random.word()
    random.seed(key)
    encrypted_digest = _xor(digest, random)
    random.seed(_payload_seed(key, digest))
    encrypted = _xor(payload, random)
    stride = len(payload) // 17
    prefix = len(payload) - stride * 16
    out = bytearray(encrypted[:prefix])
    cursor = prefix
    for i in range(15, -1, -1):
        out.append(encrypted_digest[i])
        out.extend(encrypted[cursor:cursor + stride])
        cursor += stride
    return bytes(out)


def _zstd():
    try:
        import zstandard
    except ImportError as exc:
        raise SaveError('This launcher build is missing bundled Zstandard support') from exc
    return zstandard


def decode_save(data: bytes) -> bytes:
    payload = decode_envelope(data)
    if payload[:5] != b'\x02\x28\xb5\x2f\xfd':
        raise SaveError('Unsupported save compression framing')
    zstd = _zstd()
    try:
        size = zstd.frame_content_size(payload[1:])
        if size < 0 or size > MAX_PLAIN:
            raise SaveError('Unsupported decompressed save size')
        return zstd.ZstdDecompressor().decompress(payload[1:], max_output_size=MAX_PLAIN,
                                                 allow_extra_data=False)
    except zstd.ZstdError as exc:
        raise SaveError('Invalid compressed save') from exc


def encode_save(plain: bytes) -> bytes:
    if len(plain) > MAX_PLAIN:
        raise SaveError('Save data too large')
    return encode_envelope(b'\x02' + _zstd().ZstdCompressor(level=3).compress(plain))


@dataclass(frozen=True)
class _Property:
    name: str
    kind: str
    start: int
    payload: int
    end: int
    size_offset: int
    extra: tuple[str, ...] = ()
    bool_offset: int | None = None


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.tags = 0

    def require(self, pos, size, end):
        if pos < 0 or size < 0 or pos + size > end or end > len(self.data):
            raise SaveError('Truncated or inconsistent tagged save')

    def uint(self, pos, end):
        self.require(pos, 4, end)
        return struct.unpack_from('<I', self.data, pos)[0], pos + 4

    def string(self, pos, end):
        self.require(pos, 4, end)
        size = struct.unpack_from('<i', self.data, pos)[0]
        pos += 4
        if not 1 <= abs(size) <= 4096:
            raise SaveError('Unsupported FString size')
        width = 1 if size > 0 else 2
        count = abs(size) * width
        self.require(pos, count, end)
        raw = self.data[pos:pos + count]
        if raw[-width:] != bytes(width):
            raise SaveError('Unterminated FString')
        try:
            value = raw[:-width].decode('utf-8' if width == 1 else 'utf-16-le')
        except UnicodeError as exc:
            raise SaveError('Invalid FString encoding') from exc
        return value, pos + count

    def properties(self, pos, end):
        result = []
        names = set()
        while True:
            self.tags += 1
            if self.tags > 1000000:
                raise SaveError('Too many property tags')
            start = pos
            name, pos = self.string(pos, end)
            if name == 'None':
                return result, pos
            if name in names:
                raise SaveError('Duplicate property name')
            names.add(name)
            kind, pos = self.string(pos, end)
            size_offset = pos
            size, pos = self.uint(pos, end)
            index, pos = self.uint(pos, end)
            if index != 0:
                raise SaveError('Unsupported static-array property')
            extra = []
            bool_offset = None
            if kind == 'StructProperty':
                value, pos = self.string(pos, end)
                extra.append(value)
                self.require(pos, 16, end)
                pos += 16
            elif kind == 'MapProperty':
                for _ in range(2):
                    value, pos = self.string(pos, end)
                    extra.append(value)
            elif kind in ('ArrayProperty', 'SetProperty', 'ByteProperty', 'EnumProperty'):
                value, pos = self.string(pos, end)
                extra.append(value)
            elif kind == 'BoolProperty':
                self.require(pos, 1, end)
                if size != 0 or self.data[pos] not in (0, 1):
                    raise SaveError('Invalid boolean property')
                bool_offset = pos
                pos += 1
            elif kind not in ('IntProperty', 'UInt32Property', 'Int64Property',
                              'UInt64Property', 'FloatProperty', 'DoubleProperty',
                              'StrProperty', 'NameProperty', 'ObjectProperty',
                              'SoftObjectProperty', 'TextProperty'):
                raise SaveError('Unsupported property type: ' + kind)
            self.require(pos, 1, end)
            guid = self.data[pos]
            pos += 1
            if guid not in (0, 1):
                raise SaveError('Invalid property GUID marker')
            if guid:
                self.require(pos, 16, end)
                pos += 16
            self.require(pos, size, end)
            result.append(_Property(name, kind, start, pos, pos + size, size_offset,
                                    tuple(extra), bool_offset))
            pos += size

    def map_rows(self, prop):
        if prop.kind != 'MapProperty' or prop.extra != ('StructProperty', 'StructProperty'):
            raise SaveError('Unsupported unlock map layout: ' + prop.name)
        removed, pos = self.uint(prop.payload, prop.end)
        count, pos = self.uint(pos, prop.end)
        if removed or count > MAX_ROWS:
            raise SaveError('Unsupported removed keys or excessive map size')
        rows = []
        keys = set()
        for _ in range(count):
            key_props, pos = self.properties(pos, prop.end)
            if len(key_props) != 1 or key_props[0].name != 'Key' or key_props[0].kind != 'NameProperty':
                raise SaveError('Unsupported unlock row key')
            key_prop = key_props[0]
            key, key_end = self.string(key_prop.payload, key_prop.end)
            if key_end != key_prop.end or key in keys:
                raise SaveError('Invalid or duplicate unlock row key')
            keys.add(key)
            value_props, pos = self.properties(pos, prop.end)
            rows.append((key, value_props))
        if pos != prop.end:
            raise SaveError('Unexpected unlock map trailing bytes')
        return rows


@dataclass(frozen=True)
class CategorySummary:
    name: str
    total: int
    eligible: int
    already_unlocked: int
    changes: int
    skipped: int


@dataclass(frozen=True)
class SaveInspection:
    path: Path
    sha256: str
    version: int
    categories: tuple[CategorySummary, ...]


@dataclass(frozen=True)
class UnlockPlan:
    path: Path
    mode: str
    sha256: str
    version: int
    categories: tuple[CategorySummary, ...]
    changed_rows: int
    # Immutable expected byte edits. Apply independently re-derives these.
    edits: tuple[tuple[int, int, bytes], ...]
    file_identity: tuple[int, int, int, int, int]

    @property
    def summary(self):
        labels = {'CharacterDataList': 'Characters', 'CharacterItemDataList': 'Items',
                  'BattleBGMDataList': 'Battle music', 'BGMDataList': 'Music'}
        lines = [f'{labels.get(v.name, v.name)}: {v.changes} to unlock'
                 for v in self.categories if v.changes]
        return ('\n'.join(lines) or 'No eligible locked entries found.') + (
            '\nOnly verified base-game catalog entries are included. DLC and unknown entries '
            'are excluded. Story progress, rank, ownership and other save data are unchanged.'
            '\nThe original save will be backed up beside the selected file. '
            'Game acceptance has not yet been verified; keep the backup.')


@dataclass(frozen=True)
class UnlockResult:
    backup_path: Path | None
    changed_rows: int
    sha256: str

    @property
    def backup(self):
        return self.backup_path

    def __str__(self):
        if not self.changed_rows:
            return 'No changes were needed.'
        return f'Updated {self.changed_rows} entries. Original backup: {self.backup_path}'


SUPPORTED_MODES = ('characters', 'everything')
SUPPORTED_CATEGORIES = ('CharacterDataList', 'CharacterItemDataList',
                        'BattleBGMDataList', 'BGMDataList')


def _named(props, name, kind):
    prop = next((v for v in props if v.name == name), None)
    if prop is None or prop.kind != kind:
        raise SaveError('Missing or unexpected ' + name + ' property')
    return prop


def _analyze(plain, mode):
    if mode not in SUPPORTED_MODES:
        raise SaveError('Unknown unlock mode')
    reader = _Reader(plain)
    props, end = reader.properties(0, len(plain))
    if plain[end:] != b'\0\0\0\0':
        raise SaveError('Unsupported save object trailer')
    slot = _named(props, 'SlotName', 'StrProperty')
    slot_name, slot_end = reader.string(slot.payload, slot.end)
    if slot_name != 'MainGameSaveData' or slot_end != slot.end:
        raise SaveError('Select MainGameSaveData, not SystemSaveData')
    version_prop = _named(props, 'DataVersion', 'UInt32Property')
    if version_prop.end - version_prop.payload != 4:
        raise SaveError('Invalid save version field')
    version = struct.unpack_from('<I', plain, version_prop.payload)[0]
    if version != 12:
        raise SaveError('Only verified save DataVersion 12 is supported')
    summaries = []
    edits = []
    for category in SUPPORTED_CATEGORIES:
        prop = _named(props, category, 'MapProperty')
        rows = reader.map_rows(prop)
        eligible = already = changes = skipped = 0
        category_edits = []
        category_delta = 0
        enabled = mode == 'everything' or category == 'CharacterDataList'
        for key, fields in rows:
            detail = _named(fields, 'UnLockDetail', 'StructProperty')
            if detail.extra != ('SSUnLockDetail',):
                raise SaveError('Unsupported unlock detail struct')
            details, detail_end = reader.properties(detail.payload, detail.end)
            if detail_end != detail.end:
                raise SaveError('Invalid unlock detail bounds')
            gameplay = _named(details, 'bGamePlayUnLock', 'BoolProperty')
            dlc = _named(details, 'bDLCUnLock', 'BoolProperty')
            unlock_mode = _named(fields, 'UnLockMode', 'EnumProperty')
            if unlock_mode.extra != ('EKoratUnLockMode',):
                raise SaveError('Unsupported unlock mode enum')
            state, state_end = reader.string(unlock_mode.payload, unlock_mode.end)
            if state_end != unlock_mode.end or state not in (
                    'EKoratUnLockMode::Lock', 'EKoratUnLockMode::New',
                    'EKoratUnLockMode::Checked', 'EKoratUnLockMode::CheckedLock'):
                raise SaveError('Unsupported unlock mode value')
            # DLC flag is never an eligibility classifier. Original asset
            # explicit Default/Shop allowlist is required, independently.
            if key not in BASE_KEYS[category] or plain[dlc.bool_offset] != 0:
                skipped += 1
                continue
            eligible += 1
            if plain[gameplay.bool_offset] == 1:
                already += 1
                continue
            if state != 'EKoratUnLockMode::Lock':
                # Do not normalize inconsistent or unexplained states.
                skipped += 1
                continue
            if not enabled:
                continue
            changes += 1
            category_edits.append((gameplay.bool_offset, 1, b'\x01'))
            value = b'EKoratUnLockMode::New\0'
            encoded = struct.pack('<i', len(value)) + value
            old_size = unlock_mode.end - unlock_mode.payload
            delta = len(encoded) - old_size
            category_delta += delta
            category_edits.extend(((unlock_mode.payload, old_size, encoded),
                                   (unlock_mode.size_offset, 4,
                                    struct.pack('<I', len(encoded)))))
        if category_delta:
            category_edits.append((prop.size_offset, 4,
                                   struct.pack('<I', prop.end - prop.payload + category_delta)))
        edits.extend(category_edits)
        summaries.append(CategorySummary(category, len(rows), eligible, already, changes, skipped))
    edits.sort()
    if any(a[0] + a[1] > b[0] for a, b in zip(edits, edits[1:])):
        raise SaveError('Overlapping save edits')
    return version, tuple(summaries), tuple(edits)


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _same_open_file(path_info, handle_info, *, windows=None):
    # Windows path stat and descriptor fstat can expose different ctime
    # semantics. Compare the shared identity/size/mtime fields across APIs;
    # retain full ctime checks within EACH API before/after the read.
    windows = os.name == 'nt' if windows is None else windows
    left, right = _identity(path_info), _identity(handle_info)
    return left[:4] == right[:4] if windows else left == right


def _read_source(path):
    path = Path(path).absolute()
    for ancestor in (path.parent, *path.parent.parents):
        if ancestor.is_symlink() or (hasattr(ancestor, 'is_junction') and ancestor.is_junction()):
            raise SaveError('Save directory must not contain symlinks or junctions')
    if path.name != 'MainGameSaveData':
        raise SaveError('Select the MainGameSaveData file')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SaveError('Save must be a regular, unlinked file (no symlinks/hard links)')
    if not 16 <= info.st_size <= MAX_FILE:
        raise SaveError('Unsupported save file size')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or not _same_open_file(info, opened)):
            raise SaveError('Save changed while opening')
        data = stream.read(MAX_FILE + 1)
        if _identity(os.fstat(stream.fileno())) != _identity(opened):
            raise SaveError('Save changed while reading')
    if len(data) != info.st_size or _identity(path.lstat()) != _identity(info):
        raise SaveError('Save changed while reading')
    return path, data, info


def inspect_save(path) -> SaveInspection:
    """Read-only schema/integrity check and bounded category counts."""
    path, data, _ = _read_source(path)
    version, categories, _ = _analyze(decode_save(data), 'everything')
    return SaveInspection(path, hashlib.sha256(data).hexdigest(), version, categories)


def plan_unlock(path, mode='characters') -> UnlockPlan:
    """Create a preview; does not create backups, locks or changed save files."""
    path, data, info = _read_source(path)
    version, categories, edits = _analyze(decode_save(data), mode)
    return UnlockPlan(path, mode, hashlib.sha256(data).hexdigest(), version,
                      categories, sum(v.changes for v in categories), edits, _identity(info))


def _patched(plain, edits):
    parts = []
    cursor = 0
    for pos, size, replacement in edits:
        if pos < cursor or pos + size > len(plain):
            raise SaveError('Invalid save edit bounds')
        parts.extend((plain[cursor:pos], replacement))
        cursor = pos + size
    parts.append(plain[cursor:])
    return b''.join(parts)


def _check_closed(game_running):
    if not callable(game_running) or game_running() is not False:
        raise SaveError('Close all game instances before changing a save')


def apply_unlock(plan: UnlockPlan, *, confirmed: bool,
                 game_running: Callable[[], bool]) -> UnlockResult:
    """Confirm, re-plan, backup and atomically replace exactly the selected file.

    The mandatory callback must return the bool False only when all game
    instances are known closed. A stale/forged plan, changed source or concurrent
    cooperating launcher refuses. Backups are never automatically removed.
    """
    if confirmed is not True or not isinstance(plan, UnlockPlan):
        raise SaveError('Explicit unlock confirmation is required')
    _check_closed(game_running)
    lock = plan.path.with_name(plan.path.name + '.SzeroLAN.lock')
    lock_fd = None
    temporary = None
    backup = None
    try:
        try:
            lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise SaveError('Another save operation is active; check the save lock file') from exc
        fresh = plan_unlock(plan.path, plan.mode)
        if fresh != plan:
            raise SaveError('Save changed since preview; inspect it again')
        path, original, info = _read_source(plan.path)
        if _identity(info) != plan.file_identity or hashlib.sha256(original).hexdigest() != plan.sha256:
            raise SaveError('Save changed since preview')
        if not info.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            raise SaveError('The save is read-only')
        if not plan.changed_rows:
            return UnlockResult(None, 0, plan.sha256)
        plain = decode_save(original)
        modified = _patched(plain, plan.edits)
        # A second structural pass must be idempotent for selected categories.
        _, _, remaining = _analyze(modified, plan.mode)
        if remaining:
            raise SaveError('Unlock validation is not idempotent')
        encoded = encode_save(modified)
        if decode_save(encoded) != modified:
            raise SaveError('Re-encoded save verification failed')
        _check_closed(game_running)
        backup = path.with_name(path.name + '.SzeroLAN-backup-' + uuid.uuid4().hex + '.bak')
        backup_fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(backup_fd, 'wb') as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        if backup.read_bytes() != original:
            raise SaveError('Backup verification failed; save was not changed')
        descriptor, name = tempfile.mkstemp(prefix='.SzeroLAN-save-', dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(info.st_mode))
        if temporary.read_bytes() != encoded:
            raise SaveError('Temporary save verification failed')
        _check_closed(game_running)
        _, current, current_info = _read_source(path)
        if _identity(current_info) != plan.file_identity or current != original:
            raise SaveError('Save changed during preparation; original was not replaced')
        os.replace(temporary, path)
        temporary = None
        return UnlockResult(backup, plan.changed_rows, hashlib.sha256(encoded).hexdigest())
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if lock_fd is not None:
            os.close(lock_fd)
            lock.unlink(missing_ok=True)
