#!/usr/bin/env python3
"""Offline-Proben am echten CLI mit ZIPs/Locks auf Platte, ohne Netz/Mock."""

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
GOOD = "demo-1.0-cp312-cp312-manylinux_2_28_x86_64.whl"
NEGATIVE = []


def wheel(folder, name=GOOD, files=None):
    path = folder / "wheels" / name
    path.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key, value in (files or {"demo/__init__.py": b"VALUE = 1\n"}).items():
            archive.writestr(key, value)
    return path


def lock(folder, paths):
    lines = []
    for path in paths:
        parts = path.name.split("-")
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{parts[0]}=={parts[1]} \\\n    --hash=sha256:{sha}\n")
    (folder / "requirements.lock").write_text("".join(lines), encoding="ascii")


def call(script, *args, cwd=None):
    env = os.environ.copy()
    env["PYTHON"] = sys.executable
    values = [a.as_posix() if isinstance(a, Path) else str(a) for a in args]
    return subprocess.run([os.environ.get("REZEPT_BASH", "bash"), script.as_posix(), *values], cwd=cwd, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def positive(folder, target="linux"):
    result = call(HERE / "bauen.sh", "--pruefen", folder, target)
    assert result.returncode == 0, result.stdout


def negative(folder, rule, mode="--pruefen", target="linux", extra=()):
    args = (mode, folder, target, *extra)
    result = call(HERE / "bauen.sh", *args)
    assert result.returncode != 0 and f"{rule}:" in result.stdout, (rule, result.stdout)
    NEGATIVE.append((rule, args, None))


def main(root):
    def fixture(label, name=GOOD, files=None):
        folder = root / label
        folder.mkdir()
        lock(folder, [wheel(folder, name, files)])
        return folder

    valid = fixture("gueltig")
    positive(valid)
    for i, tag in enumerate(("py3-none-any", "py2.py3-none-any", "cp312-abi3-manylinux2014_x86_64", "cp312-cp312-manylinux_2_41_x86_64")):
        positive(fixture(f"gueltiger-tag-{i}", f"demo-1.0-{tag}.whl"))
    positive(fixture("windows", "demo-1.0-cp312-cp312-win_amd64.whl"), "windows")
    for i, tag in enumerate(("cp311-cp311-manylinux_2_28_x86_64", "cp312-cp312-musllinux_1_2_x86_64", "cp312-cp312-manylinux_2_42_x86_64", "cp312-cp312-manylinux_2_28_aarch64", "cp312-cp312-linux_x86_64", "cp312-cp312-win_amd64", "cp313-abi3-manylinux_2_28_x86_64", "cp312-cp312-manylinux_2_028_x86_64")):
        negative(fixture(f"falscher-tag-{i}", f"demo-1.0-{tag}.whl"), "tag")
    negative(valid, "tag", target="windows")
    negative(valid, "ziel", target="arm64")
    folder = fixture("sdist")
    (folder / "wheels" / "demo-1.0.tar.gz").write_bytes(b"sdist")
    negative(folder, "sdist")
    folder = fixture("wheel-ohne-lock")
    wheel(folder, "extra-1.0-py3-none-any.whl", {"extra.py": b""})
    negative(folder, "wheel-ohne-lock")
    folder = fixture("lock-ohne-wheel")
    with (folder / "requirements.lock").open("a") as stream:
        stream.write("extra==1.0 --hash=sha256:" + "0" * 64 + "\n")
    negative(folder, "lock-ohne-wheel")
    folder = fixture("wheel-doppelt")
    wheel(folder, "demo-1.0-py3-none-any.whl")
    negative(folder, "wheel-doppelt")
    folder = fixture("version")
    path = folder / "requirements.lock"
    path.write_text(path.read_text().replace("==1.0", "==2.0"))
    negative(folder, "version")
    folder = fixture("hash")
    with (folder / "wheels" / GOOD).open("ab") as stream:
        stream.write(b"manipuliert")
    negative(folder, "hash")
    for label, content, rule in (
        ("option", "--index-url https://example.org/simple\n", "lock-format"),
        ("marker", "demo==1.0 ; python_version > '3'\n", "lock-hash"),
        ("hash-fehlt", "demo==1.0\n", "lock-hash"),
        ("lock-doppelt", ("demo==1.0 --hash=sha256:" + "0" * 64 + "\n") * 2, "lock-doppelt"),
        ("hash-doppelt", "demo==1.0 " + ("--hash=sha256:" + "0" * 64 + " ") * 2, "lock-hash-doppelt"),
        ("hash-zahl", "demo==1.0 " + " ".join(f"--hash=sha256:{i:064x}" for i in range(65)), "lock-zeile"),
        ("lock-leer", "# leer\n", "lock-anzahl"),
        ("lock-fortsetzung", "demo==1.0 \\", "lock-fortsetzung"),
        ("lock-ascii", "# ä\n", "lock-ascii"),
        ("lock-cr", "demo\r==1.0\n", "lock-cr"),
        ("lock-zeile", "#" * 4097, "lock-zeile"),
        ("lock-groesse", "#" * (1024 * 1024 + 1), "lock-groesse"),
        ("lock-anzahl", "".join(f"x{i}==1 --hash=sha256:{0:064x}\n" for i in range(257)), "lock-anzahl"),
        ("lock-hash-zahl", "demo==1.0 \\\n" + "".join(f" --hash=sha256:{i:064x}" + (" \\\n" if i < 64 else "\n") for i in range(65)), "lock-hash-zahl"),
    ):
        folder = fixture(label)
        (folder / "requirements.lock").write_text(content, encoding="utf-8")
        negative(folder, rule)
    for i, line in enumerate(("--index-url https://example.org/simple", "-r other.in", "demo @ https://example.org/a.whl", "./lokal", "demo; os_name == 'nt'", "demo --extra-index-url https://example.org", "demo[extra]")):
        folder = fixture(f"eingabe-{i}")
        (folder / "requirements.in").write_text(line)
        negative(folder, "eingabe", mode="--eingabe")
    folder = fixture("eingabe-leer")
    (folder / "requirements.in").write_text("# leer\n")
    negative(folder, "eingabe-leer", mode="--eingabe")
    folder = fixture("ausgabe")
    (folder / "requirements.in").write_text("pandas\n")
    shutil.rmtree(folder / "wheels")
    (folder / "wheels").write_text("kein Ordner")
    negative(folder, "ausgabe", mode="--eingabe")
    (valid / "requirements.in").write_text("pandas==3.0.*\nnumpy>=2,<3 # Version erlaubt\n")
    assert call(HERE / "bauen.sh", "--eingabe", valid).returncode == 0
    negative(valid, "aufruf", mode="--unbekannt")
    for label, name, rule in (("wheel-name", "demo.whl", "wheel-name"), ("wheel-build", "demo-1.0-bad-py3-none-any.whl", "wheel-build"), ("wheel-tag-format", "demo-1.0-py3!-none-any.whl", "wheel-tag-format")):
        folder = fixture(label)
        (folder / "wheels" / GOOD).rename(folder / "wheels" / name)
        negative(folder, rule)
    folder = fixture("wheel-unterordner")
    (folder / "wheels" / "unterordner").mkdir()
    negative(folder, "wheel-datei")
    folder = fixture("zip-pfad", files={"../ausbruch.py": b""})
    negative(folder, "zip-pfad")
    folder = fixture("zip-doppelt", files={"demo.py": b"", "DEMO.py": b""})
    negative(folder, "zip-doppelt")
    folder = fixture("zip-typ")
    path = folder / "wheels" / GOOD
    with zipfile.ZipFile(path, "w") as archive:
        item = zipfile.ZipInfo("link")
        item.create_system = 3
        item.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(item, "../ziel")
    lock(folder, [path])
    negative(folder, "zip-typ")
    folder = fixture("dateien", files={f"f{i}": b"" for i in range(30_001)})
    negative(folder, "dateien")
    folder = fixture("groesse")
    path = folder / "wheels" / GOOD
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        with archive.open("gross", "w") as stream:
            for _ in range(300):
                stream.write(b"x" * 1024 * 1024)
            stream.write(b"x")
    lock(folder, [path])
    negative(folder, "groesse")
    # Gleiche Locks erlauben zwei unterschiedliche, jeweils gültige Wheels.
    other = fixture("gegenprobe", files={"demo/__init__.py": b"VALUE = 2\n"})
    hashes = [hashlib.sha256((f / "wheels" / GOOD).read_bytes()).hexdigest() for f in (valid, other)]
    for f in (valid, other):
        (f / "requirements.lock").write_text("demo==1.0 " + " ".join("--hash=sha256:" + h for h in hashes))
    negative(valid, "gegenprobe", mode="--gegenprobe", extra=(other,))
    # Links brauchen unter Windows ggf. Entwicklerrechte; unter Linux Pflicht.
    for label, relative, rule in (("eingabe-link", "requirements.in", "eingabe-link"), ("lock-link", "requirements.lock", "lock-link"), ("wheels-link", "wheels", "wheels-link"), ("wheel-link", "wheels/" + GOOD, "wheel-datei")):
        folder = fixture(label)
        (folder / "requirements.in").write_text("pandas\n")
        path = folder / relative
        dest = folder / ("original-" + path.name)
        path.rename(dest)
        try:
            path.symlink_to(dest, target_is_directory=dest.is_dir())
        except OSError:
            if os.name != "nt":
                raise
            print(f"SKIP {label}: Windows erlaubt hier keine Symlinks.")
            continue
        negative(folder, rule, mode="--eingabe" if label == "eingabe-link" else "--pruefen")
    # Verdichten erhält den heruntergeladenen, bereits geprüften Hash.
    assert call(HERE / "bauen.sh", "--verdichten", valid).returncode == 0
    positive(valid)
    for value in ("../flucht", "/absolut", "a/../../b", ".hidden", "a/.hidden", "a//b", "a;echo", "a b"):
        args = ("--workflow-ordner", value)
        result = call(HERE / "bauen.sh", *args)
        assert result.returncode != 0 and "workflow-ordner:" in result.stdout, result.stdout
        NEGATIVE.append(("workflow-ordner", args, None))
    for value in ("main", "release", "wheels/fremd", "refs/heads/main"):
        args = ("--pr-zweig", value)
        result = call(HERE / "bauen.sh", *args)
        assert result.returncode != 0 and "pr-zweig:" in result.stdout, result.stdout
        NEGATIVE.append(("pr-zweig", args, None))
    link = root / "linked"
    try:
        link.symlink_to(valid, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        print("SKIP workflow-link: Windows erlaubt hier keine Symlinks.")
    else:
        result = call(HERE / "bauen.sh", "--workflow-ordner", "linked", cwd=root)
        assert result.returncode != 0 and "workflow-link:" in result.stdout, result.stdout
        NEGATIVE.append(("workflow-link", ("--workflow-ordner", "linked"), root))
    print(f"OK: gültige Linux-/Windows-Wheels und {len(NEGATIVE)} Negativproben am echten CLI.")

    mutation = root / "mutation"
    mutation.mkdir()
    shutil.copyfile(HERE / "bauen.sh", mutation / "bauen.sh")
    source = (HERE / "bauen.py").read_text(encoding="utf-8")
    killed = 0
    # Je Sperre den gemeinsamen Ablehnungszweig nur für diese Regel entfernen.
    for rule in sorted({rule for rule, _, _ in NEGATIVE}):
        mutated = source.replace("if condition:\n", f"if condition and rule != {rule!r}:\n", 1)
        (mutation / "bauen.py").write_text(mutated, encoding="utf-8", newline="\n")
        detected = False
        for case_rule, args, cwd in NEGATIVE:
            if case_rule != rule:
                continue
            result = call(mutation / "bauen.sh", *args, cwd=cwd)
            # Dies ist exakt dieselbe Assertion wie in negative(), nun muss sie rot sein.
            if not (result.returncode != 0 and f"{rule}:" in result.stdout):
                detected = True
                break
        assert detected, f"Mutation überlebt: {rule}"
        killed += 1
    (mutation / "bauen.py").write_text(source, encoding="utf-8", newline="\n")
    assert call(mutation / "bauen.sh", "--pruefen", valid).returncode == 0
    print(f"OK: {killed}/{killed} Mutationsproben rot; unveränderte Fassung wieder grün.")
    if shutil.which("uv"):
        wrong = source.replace('UV_VERSION = "0.11.3"', 'UV_VERSION = "0.0.0"')
        (mutation / "bauen.py").write_text(wrong, encoding="utf-8", newline="\n")
        result = call(mutation / "bauen.sh", "--werkzeuge")
        assert result.returncode != 0 and "uv-version:" in result.stdout, result.stdout
        (mutation / "bauen.py").write_text(wrong.replace("if condition:\n", "if condition and rule != 'uv-version':\n", 1), encoding="utf-8", newline="\n")
        assert call(mutation / "bauen.sh", "--werkzeuge").returncode == 0
        (mutation / "bauen.py").write_text(source, encoding="utf-8", newline="\n")
        print("OK: falsche uv-Version am echten uv abgewiesen; Mutation rot.")
    else:
        print("SKIP uv-Version: uv nicht installiert (Offline-Prüfung bleibt verfügbar).")

    def load(path, name):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    env_probe = [sys.executable, "-I", "-c", "import os; assert not any(k in os.environ for k in ('UV_INDEX', 'PIP_EXTRA_INDEX_URL', 'PYTHONPATH')); assert os.environ['PIP_CONFIG_FILE'] == os.devnull"]
    keys = ("UV_INDEX", "PIP_EXTRA_INDEX_URL", "PYTHONPATH")
    saved = {k: os.environ.get(k) for k in keys}
    try:
        for key in keys:
            os.environ[key] = "https://example.org/unerlaubt"
        original = load(HERE / "bauen.py", "original")
        original.run(env_probe, HERE)  # echter Kindprozess sieht keine Index-Optionen
        (mutation / "bauen.py").write_text(source.replace("env=clean_env()", "env=os.environ.copy()"), encoding="utf-8", newline="\n")
        mutant = load(mutation / "bauen.py", "mutant")
        try:
            mutant.run(env_probe, HERE)
        except ValueError:
            pass  # dieselbe Erfolgsassertion wird ohne Bereinigung rot
        else:
            raise AssertionError("Mutation Umgebungsbereinigung überlebt")
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        (mutation / "bauen.py").write_text(source, encoding="utf-8", newline="\n")
    print("OK: private Index-/Python-Umgebungsoptionen am echten Kindprozess entfernt; Mutation rot.")

    def git(repo, *args):
        result = subprocess.run(["git", "-C", str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert result.returncode == 0, result.stdout
        return result.stdout.strip()

    def pr_case(label, script, branch="wheels/1-1"):
        repo = root / label
        repo.mkdir()
        git(repo, "init", "-b", "main")
        (repo / "skript").mkdir()
        (repo / "skript" / "requirements.in").write_text("demo\n")
        git(repo, "add", ".")
        git(repo, "commit", "-m", "Fixture")
        base = git(repo, "rev-parse", "main")
        result = call(script, "skript", valid, branch, "linux", cwd=repo)
        return repo, base, result

    # Test-Identität nur im Prozess, keine Änderung der Git-Konfiguration.
    for role in ("AUTHOR", "COMMITTER"):
        os.environ[f"GIT_{role}_NAME"] = "JanuaPort GmbH"
        os.environ[f"GIT_{role}_EMAIL"] = "opensource@januaport.ai"
    repo, base, result = pr_case("pr", HERE / "pr-vorbereiten.sh")
    assert result.returncode == 0, result.stdout
    assert git(repo, "rev-parse", "main") == base
    assert git(repo, "branch", "--show-current") == "wheels/1-1"
    changes = set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines())
    assert changes == {"skript/requirements.lock", "skript/wheels/" + GOOD}, changes
    prior = git(repo, "rev-parse", "HEAD")
    result = call(HERE / "pr-vorbereiten.sh", "skript", valid, "wheels/1-2", "linux", cwd=repo)
    assert result.returncode == 0 and git(repo, "rev-parse", "HEAD") == prior, result.stdout
    repo, base, result = pr_case("pr-main", HERE / "pr-vorbereiten.sh", "main")
    assert result.returncode != 0 and "pr-zweig:" in result.stdout and git(repo, "rev-parse", "main") == base
    text = (HERE / "pr-vorbereiten.sh").read_text().replace('git switch -c "$zweig"', ': # Mutationsprobe: Zweigwechsel entfernt')
    (mutation / "pr-vorbereiten.sh").write_text(text, encoding="utf-8", newline="\n")
    repo, base, result = pr_case("pr-mutation", mutation / "pr-vorbereiten.sh")
    assert result.returncode == 0, result.stdout
    assert git(repo, "rev-parse", "main") != base
    print("OK: echter Git-Adapter committet nur den PR-Zweig und zwei Ausgabepfade; main-Versuch abgewiesen; Mutation rot.")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix=".wheels-tests-", dir=HERE) as temporary:
        main(Path(temporary))
