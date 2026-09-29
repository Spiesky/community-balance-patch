#!/usr/bin/env python3
"""Minimal Total War .pack reader (PFH5/PFH6) - list and extract entries."""
import struct, sys, os

FLAG_HAS_EXTENDED_HEADER = 0x0100
FLAG_HAS_INDEX_TIMESTAMPS = 0x0040
FLAG_HAS_ENCRYPTED_INDEX = 0x0080
FLAG_HAS_ENCRYPTED_DATA = 0x0010


def read_cstr(buf, pos):
    end = buf.index(b"\x00", pos)
    return buf[pos:end].decode("utf-8", "replace"), end + 1


class Pack:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        self.parse_header()

    def parse_header(self):
        f = self.f
        magic = f.read(4)
        if magic not in (b"PFH5", b"PFH6", b"PFH4"):
            raise ValueError("not a pack: %r" % magic)
        self.magic = magic.decode()
        (self.bitmask, self.dep_count, self.dep_size,
         self.file_count, self.file_index_size) = struct.unpack("<5I", f.read(20))
        f.read(4)  # timestamp
        header_size = 28
        if self.bitmask & FLAG_HAS_EXTENDED_HEADER:
            # game version u32, build u32, authoring tool char[8], reserved u32
            f.read(20)
            header_size += 20
        self.header_size = header_size
        self.encrypted = bool(self.bitmask & (FLAG_HAS_ENCRYPTED_INDEX | FLAG_HAS_ENCRYPTED_DATA))

        deps = f.read(self.dep_size)
        self.deps = [d.decode("utf-8", "replace") for d in deps.split(b"\x00") if d]

        idx = f.read(self.file_index_size)
        self.entries = []
        self.flags = {}                       # name -> per-entry flag byte (1 = compressed)
        pos = 0
        data_off = self.header_size + self.dep_size + self.file_index_size
        has_ts = bool(self.bitmask & FLAG_HAS_INDEX_TIMESTAMPS)
        for _ in range(self.file_count):
            size = struct.unpack_from("<I", idx, pos)[0]
            pos += 4
            if has_ts:
                pos += 4
            flag = idx[pos]
            pos += 1  # per-entry flag byte (compression)
            name, pos = read_cstr(idx, pos)
            name = name.replace("\\", "/")
            self.entries.append((name, data_off, size))
            if flag:
                self.flags[name] = flag
            data_off += size

    def get(self, name):
        for n, off, size in self.entries:
            if n == name:
                self.f.seek(off)
                data = self.f.read(size)
                if self.flags.get(n):
                    data = decompress_entry(data)
                return data
        return None


def decompress_entry(data):
    """Vanilla packs (flag byte 1) store u32 uncompressed size + a compressed
    frame: Zstandard (28 B5 2F FD) for textures, LZ4 (04 22 4D 18) for text.
    Mod packs written by RPFM are uncompressed (flag 0) and never come here."""
    magic = data[4:8]
    if magic == b"\x28\xb5\x2f\xfd":
        import zstandard
        size = struct.unpack_from("<I", data, 0)[0]
        return zstandard.ZstdDecompressor().decompress(data[4:], max_output_size=max(size, 1))
    if magic == b"\x04\x22\x4d\x18":
        import lz4.frame
        return lz4.frame.decompress(data[4:])
    return data                                # unknown scheme: hand back the raw bytes


if __name__ == "__main__":
    p = Pack(sys.argv[1])
    print("magic=%s bitmask=0x%x files=%d encrypted=%s" % (p.magic, p.bitmask, p.file_count, p.encrypted))
    print("deps:", p.deps)
    mode = sys.argv[2] if len(sys.argv) > 2 else "tables"
    if mode == "all":
        for n, off, size in p.entries:
            print("%10d  %s" % (size, n))
    elif mode == "tables":
        seen = {}
        for n, off, size in p.entries:
            if n.startswith("db/"):
                t = n.split("/")[1]
                seen.setdefault(t, []).append((n, size))
        for t in sorted(seen):
            print(t)
            for n, size in seen[t]:
                print("    %8d  %s" % (size, n))
    elif mode == "extract":
        out = sys.argv[4]
        data = p.get(sys.argv[3])
        open(out, "wb").write(data)
        print("wrote", out, len(data))
