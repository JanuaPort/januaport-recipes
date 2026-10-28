#!/usr/bin/env python3
"""Build und Offline-Gegenprobe; Python >= 3.10, nur Standardbibliothek."""

import hashlib
import itertools
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

UV_VERSION = "0.11.3"
PIP_VERSION = "26.0.1"
INDEX = "https://pypi.org/simple"
MAX_BYTES = 300 * 1024 * 1024
MAX_FILES = 30_000
NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
VERSION = r"[A-Za-z0-9](?:[A-Za-z0-9._+!]*[A-Za-z0-9])?"


def reject(condition, rule, message):
    if condition:
        raise ValueError(f"{rule}: {message}")


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def target_check(target):
    reject(target not in ("linux", "windows"), "ziel", "Ziel muss linux oder windows sein.")


def workflow_folder(value):
    reject(not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9._-]*(?:/[A-Za-z0-9_][A-Za-z0-9._-]*)*", value),
           "workflow-ordner", "Relativer Skriptordner ohne Punktsegmente; Zeichen: Buchstaben, Zahlen, _, -, . und /.")
    path = Path.cwd()
    for part in value.split("/"):
        path /= part
        reject(path.is_symlink(), "workflow-link", "Skriptordner enthält einen Symlink.")
    return path


def pr_branch(value):
    reject(not re.fullmatch(r"wheels/[0-9]+-[0-9]+", value), "pr-zweig", "Ausgabe nur auf einem eigenen wheels/<Lauf>-<Versuch>-Zweig.")


def output_check(folder):
    path = folder / "wheels"
    reject(path.is_symlink() or (path.exists() and not path.is_dir()), "ausgabe", "wheels/ ist kein regulärer Ordner.")


def version_check():
    version = subprocess.check_output(["uv", "--version"], text=True).split()[1]
    reject(version != UV_VERSION, "uv-version", f"uv {UV_VERSION} erforderlich, gefunden: {version}.")


def input_check(folder):
    path = folder / "requirements.in"
    reject(path.is_symlink(), "eingabe-link", "requirements.in ist ein Symlink.")
    lines = path.read_text(encoding="utf-8").splitlines()
    # Absichtlich keine Extras, Marker, URLs, Includes oder pip-Optionen.
    requirement = re.compile(
        rf"{NAME}(?:\s*(?:===|==|~=|!=|<=|>=|<|>)\s*[A-Za-z0-9.*+!_-]+"
        rf"(?:\s*,\s*(?:===|==|~=|!=|<=|>=|<|>)\s*[A-Za-z0-9.*+!_-]+)*)?"
    )
    packages = []
    for line in lines:
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        if not line or line.startswith("#"):
            continue
        reject(not requirement.fullmatch(line), "eingabe", "Eine Paketanforderung je Zeile; nur Name und Versionsbereich erlaubt.")
        packages.append(line)
    reject(not packages, "eingabe-leer", "requirements.in enthält keine Pakete.")
    return packages


def lock_read(path, raw=False):
    reject(path.is_symlink(), "lock-link", "Lock ist ein Symlink.")
    data = path.read_bytes()
    reject(not raw and len(data) > 1024 * 1024, "lock-groesse", "Lock über 1 MiB.")
    reject(any(b not in (9, 10, 13) and not 32 <= b <= 126 for b in data), "lock-ascii", "Lock muss ASCII sein.")
    reject(bool(re.search(rb"\r(?!\n|$)", data)), "lock-cr", "Wagenrücklauf mitten in einer Lock-Zeile.")
    entries = {}
    current = ""
    for line in data.decode("ascii").splitlines():
        reject(len(line) > 4096, "lock-zeile", "Lock-Zeile über 4096 Zeichen.")
        line = re.split(r"(?:^|\s)#", line, maxsplit=1)[0].strip()
        continuation = line.endswith("\\")
        current += " " + (line[:-1] if continuation else line)
        if continuation:
            continue
        if current.strip():
            tokens = current.split()
            match = re.fullmatch(rf"({NAME})==({VERSION})", tokens[0])
            reject(match is None, "lock-format", "Lock erwartet name==version ohne Optionen, URLs oder Marker.")
            name, version = match.groups()
            name = normalized(name)
            hashes = [token.removeprefix("--hash=sha256:") for token in tokens[1:]]
            reject(not hashes or any(not re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", t) for t in tokens[1:]), "lock-hash", "Jeder Eintrag braucht SHA-256-Hashes.")
            reject(len(hashes) != len(set(hashes)), "lock-hash-doppelt", "Hash doppelt im Eintrag.")
            reject(not raw and len(hashes) > 64, "lock-hash-zahl", "Mehr als 64 Hashes im Eintrag.")
            reject(name in entries, "lock-doppelt", "Paket doppelt im Lock.")
            entries[name] = (version, set(hashes))
        current = ""
    reject(bool(current.strip()), "lock-fortsetzung", "Zeilenfortsetzung am Dateiende.")
    reject(not entries or len(entries) > 256, "lock-anzahl", "Lock braucht 1 bis 256 Einträge.")
    return entries


def tag_allowed(py, abi, platform, target):
    # py2.py3-none-any ist üblich (six, python-dateutil): py3 genügt.
    if platform == "any":
        return py == "py3" and abi == "none"
    if py != "cp312" or abi not in ("cp312", "abi3", "none"):
        return False
    if target == "windows":
        return platform == "win_amd64"
    if platform in ("manylinux1_x86_64", "manylinux2010_x86_64", "manylinux2014_x86_64"):
        return True
    match = re.fullmatch(r"manylinux_2_(0|[1-9][0-9]*)_x86_64", platform)
    return bool(match and int(match[1]) <= 41)


def wheel_name(path, target):
    reject(path.is_symlink() or not path.is_file(), "wheel-datei", "wheels/ enthält einen Link oder Unterordner.")
    reject(not path.name.endswith(".whl"), "sdist", f"{path.name}: nur Wheels, keine sdist.")
    parts = path.name[:-4].split("-")
    reject(len(parts) not in (5, 6) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._]*", parts[0]) or not re.fullmatch(VERSION, parts[1]), "wheel-name", "Ungültiger Wheel-Dateiname.")
    reject(len(parts) == 6 and not re.fullmatch(r"[0-9][A-Za-z0-9_.]*", parts[2]), "wheel-build", "Ungültiger Build-Tag.")
    tags = parts[-3:]
    reject(any(not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", t) for t in tags), "wheel-tag-format", "Ungültiger Wheel-Tag.")
    reject(not any(tag_allowed(*t, target) for t in itertools.product(*(t.split(".") for t in tags))), "tag", f"{path.name}: kein Tag für Python 3.12/{target} (manylinux x86_64, glibc höchstens 2.41 bzw. win_amd64).")
    return normalized(parts[0]), parts[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else _digest(stream)


def _digest(stream):
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        value.update(chunk)
    return value.hexdigest()


def verify(folder, target, raw=False):
    target_check(target)
    entries = lock_read(folder / "requirements.lock", raw)
    wheels = folder / "wheels"
    reject(wheels.is_symlink(), "wheels-link", "wheels/ ist ein Symlink.")
    used = {}
    paths = set()
    total = count = compressed = 0
    for path in sorted(wheels.iterdir()):
        name, version = wheel_name(path, target)
        reject(name not in entries, "wheel-ohne-lock", f"{name}: Wheel ohne Lock-Eintrag.")
        reject(name in used, "wheel-doppelt", f"{name}: zwei Wheels für einen Eintrag.")
        reject(version.lower() != entries[name][0].lower(), "version", f"{name}: Version weicht vom Lock ab.")
        sha = digest(path)
        reject(sha not in entries[name][1], "hash", f"{name}: Wheel-SHA-256 fehlt im Lock.")
        used[name] = (version, sha)
        compressed += path.stat().st_size
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                segments = item.filename.rstrip("/").split("/")
                reject(any(s in ("", ".", "..") for s in segments) or "\\" in item.filename or ":" in item.filename or item.filename.startswith("/"), "zip-pfad", "Unsicherer Pfad im Wheel.")
                mode = stat.S_IFMT(item.external_attr >> 16)
                reject(mode not in (0, stat.S_IFREG, stat.S_IFDIR), "zip-typ", "Symlink oder Sonderdatei im Wheel.")
                key = item.filename.rstrip("/").casefold()
                reject(key in paths, "zip-doppelt", "Doppelter Pfad im Wheel-Satz.")
                paths.add(key)
                if item.is_dir():
                    continue
                count += 1
                reject(count > MAX_FILES, "dateien", "Mehr als 30 000 Dateien installiert.")
                # Streamen prüft tatsächliche Bytes und CRC, ohne zu installieren.
                with archive.open(item) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        total += len(chunk)
                        reject(total > MAX_BYTES, "groesse", "Mehr als 300 MiB installiert.")
    reject(set(entries) != set(used), "lock-ohne-wheel", "Lock-Eintrag ohne Wheel.")
    return used, total, count, compressed


def compact(folder, target):
    used, *_ = verify(folder, target, raw=True)
    # uv nennt auch Hashes anderer Plattformen/sdists (>64 je Paket möglich).
    # Nach Hash-Prüfung nur die tatsächlich gelieferten Wheels im Pin-Lock halten.
    (folder / "requirements.lock").write_text("".join(
        f"{name}=={version} \\\n    --hash=sha256:{sha}\n" for name, (version, sha) in sorted(used.items())
    ), encoding="ascii", newline="\n")


def compare(folder, target, probe):
    first = verify(folder, target)
    second = verify(probe, target)
    a = {p.name: digest(p) for p in (folder / "wheels").iterdir()}
    b = {p.name: digest(p) for p in (probe / "wheels").iterdir()}
    reject(a != b, "gegenprobe", "Wheel-Namen oder SHA-256 unterscheiden sich beim zweiten Download.")
    return first, second


def report(folder, target):
    used, total, count, compressed = verify(folder, target)
    lines = [f"Python-Bibliotheken ({target}, Python 3.12)", "", "| Paket | Version |", "|---|---|"]
    lines += [f"| {name} | {version} |" for name, (version, _) in sorted(used.items())]
    lines += ["", f"Gesamtgröße Wheels: {compressed} Bytes; installiert: {total} Bytes; {count} Dateien.",
              "Gegenprobe: zweiter Download mit Hash-Pflicht und identischen Wheel-SHA-256.",
              "", "Herkunft ist PyPI, geprüft sind nur die Hashes", "",
              "Paketauswahl und Lizenzen prüft der Betreiber. Nach dem Merge pinnt ein Mensch."]
    return "\n".join(lines) + "\n"


def clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("UV_", "PIP_", "PYTHON"))}
    # pip --isolated allein schließt eine globale pip.conf nicht aus.
    env["PIP_CONFIG_FILE"] = os.devnull
    return env


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, env=clean_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        text = result.stdout
        # pip und uv nennen fehlende direkte UND transitive Pakete unterschiedlich.
        match = re.search(r"(?:No matching distribution found for |Could not find a version that satisfies the requirement |Because (?:all versions of )?)([A-Za-z0-9_.-]+)", text)
        if match and ("No matching distribution" in text or re.search(r"no (?:usable )?wheels", text) or "source distribution" in text):
            platform = "manylinux" if TARGET == "linux" else "Windows/amd64"
            raise ValueError(f"Paket {match[1]} hat kein Wheel für Python 3.12/{platform}. Andere Version wählen oder weglassen.")
        raise ValueError(text.strip())
    return result.stdout


def build(folder, target):
    input_check(folder)
    output_check(folder)
    version_check()
    # Beide Downloads frisch; vorhandene Ergebnisse bleiben bei Fehler erhalten.
    with tempfile.TemporaryDirectory(prefix=".wheels-bau-", dir=folder) as temporary:
        stage = Path(temporary)
        shutil.copyfile(folder / "requirements.in", stage / "requirements.in")
        platform = "x86_64-manylinux_2_28" if target == "linux" else "x86_64-pc-windows-msvc"
        run(["uv", "--no-config", "pip", "compile", "requirements.in", "--python-version", "3.12",
             "--python-platform", platform, "--generate-hashes", "--no-header", "--no-annotate",
             "--no-sources", "--no-build", "--default-index", INDEX, "-o", "requirements.lock"], stage)
        lock_read(stage / "requirements.lock", raw=True)
        # Python 3.12 wird nur auf dem Baurechner gebraucht, nie am Läufer.
        download = ["uv", "--no-config", "run", "--isolated", "--no-project", "--no-env-file",
                    "--python", "3.12", "--with", f"pip=={PIP_VERSION}", "--default-index", INDEX,
                    "python", "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
                    "--no-cache-dir", "download", "--index-url", INDEX, "--only-binary=:all:",
                    "--require-hashes", "--no-deps", "--implementation", "cp", "--python-version", "3.12",
                    "--abi", "cp312", "--abi", "abi3", "--abi", "none", "-r", "requirements.lock"]
        if target == "windows":
            download += ["--platform", "win_amd64"]
        else:
            # pip leitet bei --platform die älteren PEP-600-Tags nicht selbst ab.
            for minor in range(28, 4, -1):
                download += ["--platform", f"manylinux_2_{minor}_x86_64"]
            for legacy in ("manylinux2014_x86_64", "manylinux2010_x86_64", "manylinux1_x86_64"):
                download += ["--platform", legacy]
        run(download + ["-d", "wheels"], stage)
        compact(stage, target)
        probe = stage / "gegenprobe"
        probe.mkdir()
        shutil.copyfile(stage / "requirements.lock", probe / "requirements.lock")
        # Eigener leerer Zielordner; --no-cache-dir verhindert Wiederverwendung.
        run(download + ["-d", "wheels"], probe)
        compare(stage, target, probe)
        summary = report(stage, target)
        old = folder / "wheels"
        output_check(folder)
        if old.exists():
            old.rename(stage / "alte-wheels")
        (stage / "wheels").rename(old)
        (stage / "requirements.lock").replace(folder / "requirements.lock")
        print(summary, end="")


def main():
    args = sys.argv[1:]
    mode = args.pop(0) if args and args[0].startswith("--") else "bauen"
    if mode == "--pr-zweig" and len(args) == 1:
        pr_branch(args[0])
        return
    if mode == "--workflow-ordner" and len(args) == 1:
        workflow_folder(args[0])
        return
    if mode == "--werkzeuge" and not args:
        version_check()
        return
    reject(not 1 <= len(args) <= (3 if mode == "--gegenprobe" else 2), "aufruf", "bauen.sh [--pruefen|--eingabe|--bericht|--verdichten] ORDNER [linux|windows]")
    folder = Path(args[0]).resolve()
    global TARGET
    TARGET = args[1] if len(args) > 1 else "linux"
    target_check(TARGET)
    if mode == "--pruefen":
        _, size, files, _ = verify(folder, TARGET)
        print(f"OK: {size} Bytes installiert, {files} Dateien.")
    elif mode == "--eingabe":
        input_check(folder)
        output_check(folder)
    elif mode == "--bericht":
        print(report(folder, TARGET), end="")
    elif mode == "--verdichten":
        compact(folder, TARGET)
    elif mode == "--gegenprobe":
        reject(len(args) != 3, "aufruf", "Gegenprobe braucht ORDNER ZIEL PROBEORDNER.")
        compare(folder, TARGET, Path(args[2]).resolve())
    elif mode == "bauen":
        build(folder, TARGET)
    else:
        reject(True, "aufruf", "Unbekannte Option.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Abbruch: {error}", file=sys.stderr)
        sys.exit(1)
