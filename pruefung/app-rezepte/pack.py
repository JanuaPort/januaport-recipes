"""Deterministisches Austausch-TAR aus einem geprüften App-Quellordner."""
import argparse
import io
from pathlib import Path
import tarfile
from policy import check_tree


def pack(source):
    check_tree(source)
    files = sorted(p for p in source.rglob("*") if p.is_file())
    if len(files) > 1000 or sum(p.stat().st_size for p in files) > 4 * 1024 * 1024:
        raise ValueError("App-Budget überschritten")
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for path in files:
            data = path.read_bytes()
            info = tarfile.TarInfo(path.relative_to(source).as_posix())
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    result = out.getvalue()
    if len(result) > 4 * 1024 * 1024:
        raise ValueError("TAR-Budget überschritten")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_bytes(pack(args.source))
