"""Aufruf: python pruefung/app-rezepte/check.py --core <Kern-Checkout> [--mutations]."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from policy import check_tree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run(args, cwd, env=None, success=True):
    process_env = dict(os.environ if env is None else env, PYTHONIOENCODING="utf-8")
    result = subprocess.run(args, cwd=cwd, env=process_env, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout, end="", flush=True)
    if (result.returncode == 0) != success:
        raise SystemExit("Unerwartetes Prüfergebnis: " + " ".join(args))
    if not success and "--- FAIL:" not in result.stdout and "FAIL:" not in result.stdout:
        raise SystemExit("Mutation scheitert ohne roten Test (z.B. Kompilierfehler)")


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--mutations", action="store_true")
    parser.add_argument("--browser", action="store_true", help="Zusätzlich Headless-Browser über RECIPE_BROWSER verwenden")
    args = parser.parse_args()
    core = args.core.resolve()
    source_env = dict(os.environ, RECIPE_ROOT=str(ROOT))
    (ROOT / ".arbeit").mkdir(exist_ok=True)
    run([sys.executable, "-m", "unittest", "-v", "test_policy", "test_pack"], HERE, source_env)
    run(["node", "--test", str(HERE / "mcp.test.mjs")], ROOT)
    if args.mutations:
        for mutation in ("echo", "null", "correlation", "failure", "isError", "deadline", "cleanup", "timer",
                         "name", "args", "wireArgs", "size", "raw", "fetch", "initialize", "string", "responseString", "status", "resultError", "eval", "repeat", "unknown", "duplicate"):
            print("MUTATION MCP " + mutation, flush=True)
            result = subprocess.run(["node", "--test", str(HERE / "mcp.test.mjs")], cwd=ROOT,
                                    env=dict(os.environ, MCP_MUTATION=mutation), text=True, encoding="utf-8",
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # Ein echter Assertion-Fehler muss die entfernte Sperre erkennen.
            if result.returncode == 0 or "ERR_ASSERTION" not in result.stdout or "Mutationsanker fehlt" in result.stdout:
                print(result.stdout, flush=True)
                raise SystemExit("MCP-Mutation ohne roten Assertion-Test: " + mutation)
            print("PASS: MCP-Mutation erkannt: " + mutation, flush=True)
        run(["node", "--test", str(HERE / "mcp.test.mjs")], ROOT)
    if args.browser:
        run(["node", str(HERE / "browser.mjs")], ROOT)
        if args.mutations:
            for mutation in ("confirm", "covered", "hint", "text", "read", "repeat"):
                print("MUTATION Browser " + mutation, flush=True)
                run(["node", str(HERE / "browser.mjs"), mutation], ROOT, success=False)
            run(["node", str(HERE / "browser.mjs")], ROOT)
    for name in ("steuer-app", "monitor-app"):
        source = ROOT / "rezepte" / name / "app"
        if not source.is_dir():
            raise SystemExit(f"Quellordner fehlt: {name}")
        check_tree(source)
    scratch = ROOT / ".arbeit"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="app-check-", dir=scratch) as work:
        work = Path(work)
        module = (core / "go.mod").read_text(encoding="utf-8").replace(
            "module github.com/januaport/januaport", "module github.com/januaport/januaport/recipecheck", 1)
        module += '\nrequire github.com/januaport/januaport v0.0.0\nreplace github.com/januaport/januaport => ' + json.dumps(core.as_posix()) + '\n'
        (work / "go.mod").write_text(module, encoding="utf-8")
        shutil.copyfile(core / "go.sum", work / "go.sum")
        shutil.copyfile(HERE / "core_test.go", work / "core_test.go")
        env = dict(os.environ, RECIPE_ROOT=str(ROOT))
        run(["go", "test", "-mod=mod", "-count=1", "-v", "."], work, env)
        if args.mutations:
            mutations(core, work, env)


def mutations(core, work, env):
    cases = [
        ("App-Budget", "internal/skriptspeicher/service.go", "if len(f.Bytes) > MaxWriteBytes-total {", "if false {", "TestLoadReject/bytes"),
        ("Dateizahl", "internal/objektspeicher/validate.go", "count > MaxDateien", "count > 10000", "TestLoadReject/count"),
        ("Pfad", "internal/objektspeicher/validate.go", "if !validPath(name) {", "if false && !validPath(name) {", "TestLoadReject/path"),
        ("Dateimodus", "internal/objektspeicher/validate.go", "case 0100644, 0100755:", "case 0100644, 0100755, 0120000:", "TestLoadReject/mode"),
        ("Binaer-Magic", "internal/objektspeicher/validate.go", "if executable && !exceptions.allows(name) {", "if executable && false && !exceptions.allows(name) {", "TestLoadReject/executable"),
        ("Manifest-Felder", "internal/appmanifest/manifest.go", "d.DisallowUnknownFields()", "// Mutation", "TestManifestReject/unknown"),
        ("Manifest-Traeger", "internal/appmanifest/manifest.go", '(m.Mode == "a" && m.TokenID == "")', "false", "TestManifestReject/carrier"),
        ("Manifest-Groesse", "internal/appmanifest/manifest.go", "if len(b) > 8192 {", "if false {", "TestManifestReject/size"),
        ("Manifest-EOF", "internal/appmanifest/manifest.go", "d.Decode(&extra) != io.EOF", "false", "TestManifestReject/trailing"),
        ("Import-gestoppt", "internal/apps/recipe.go", 'Status: "gestoppt", Ja: true', 'Status: "live", Ja: true', "TestImportStopped"),
        ("Import-Admin", "internal/apps/model.go", '[]string{"gui", "rest", "cli", "admin-mcp"}', '[]string{"gui", "rest", "cli", "admin-mcp", "mcp"}', "TestImportReject/origin-mcp"),
        ("Import-App-Herkunft", "internal/apps/model.go", 'return o.App == "" && slices.Contains', 'return slices.Contains', "TestImportReject/origin-cli"),
        ("Import-neuer-Traeger", "internal/apps/recipe_archive.go", 'if m.Mode == "a" && in.TokenID == "" {', 'if false {', "TestBindingAndExport"),
        ("Import-Bindung", "internal/apps/recipe_archive.go", "m.Name, m.TokenID = in.Name, in.TokenID", "m.Name = in.Name", "TestBindingAndExport"),
        ("Import-Teams", "internal/apps/recipe_archive.go", "m.Teams = append([]string{}, in.Teams...)", "// Mutation", "TestBindingAndExport"),
        ("Export-Bindung", "internal/apps/recipe.go", 'm.Teams, m.TokenID = []string{}, ""', '// Mutation', "TestBindingAndExport"),
        ("Archiv-Links", "internal/apps/recipe_archive.go", 'if h.Typeflag != tar.TypeReg || h.Linkname != "" {', 'if false && (h.Typeflag != tar.TypeReg || h.Linkname != "") {', "TestArchiveReject/link"),
        ("Archiv-Duplikat", "internal/apps/recipe_archive.go", 'if _, ok := files[h.Name]; ok {', 'if _, ok := files[h.Name]; ok && false {', "TestArchiveReject/duplicate"),
    ]
    for label, rel, old, new, test in cases:
        path = core / rel
        text = path.read_text(encoding="utf-8")
        if label == "Manifest-EOF":
            new = "func() bool { _ = d.Decode(&extra); return io.EOF != io.EOF }()"
        if text.count(old) != 1:
            raise SystemExit("Mutationsanker nicht eindeutig: " + label)
        replacement = work / "mutant.go"
        replacement.write_text(text.replace(old, new, 1), encoding="utf-8")
        overlay = work / "overlay.json"
        overlay.write_text(json.dumps({"Replace": {str(path): str(replacement)}}), encoding="utf-8")
        print("MUTATION " + label, flush=True)
        # Ersatzdatei außerhalb des Testpakets, damit Go sie nicht doppelt lädt.
        mutant = work / "overlay" / "mutant.go"
        mutant.parent.mkdir(exist_ok=True)
        replacement.replace(mutant)
        replacements = {str(path): str(mutant)}
        if label == "Import-neuer-Traeger":
            parse_path = core / "internal/appmanifest/manifest.go"
            parse_copy = work / "overlay" / "manifest.go"
            parse_copy.write_text(parse_path.read_text(encoding="utf-8").replace('(m.Mode == "a" && m.TokenID == "")', 'false', 1), encoding="utf-8")
            replacements[str(parse_path)] = str(parse_copy)
        overlay.write_text(json.dumps({"Replace": replacements}), encoding="utf-8")
        run(["go", "test", "-mod=mod", "-count=1", "-overlay", str(overlay), "-run", test, "-v", "."], work, env, success=False)
    # Geheimnisse werden an zwei Stellen geprüft; beide Sperren zusammen entfernen.
    replacements = {}
    for rel, old, new in [
        ("internal/objektspeicher/validate.go", "if _, changed := memory.Redact(appmanifest.SecretScanText(name, data)); changed {", "if _, changed := memory.Redact(appmanifest.SecretScanText(name, data)); changed && false {"),
        ("internal/skriptspeicher/service.go", "if !changed {", "if true || !changed {"),
    ]:
        path = core / rel
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise SystemExit("Geheimnis-Mutationsanker nicht eindeutig")
        target = work / "overlay" / path.name
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        replacements[str(path)] = str(target)
    overlay.write_text(json.dumps({"Replace": replacements}), encoding="utf-8")
    print("MUTATION Geheimnispruefung (beide Speicherwege)", flush=True)
    run(["go", "test", "-mod=mod", "-count=1", "-overlay", str(overlay), "-run", "TestLoadReject/secret", "-v", "."], work, env, success=False)
    # Eigene Rezeptregeln in einer isolierten Kopie mutieren.
    policy_source = (HERE / "policy.py").read_text(encoding="utf-8")
    policy_cases = [
        ('if tag == "script" and', 'if False and'),
        ('if key.lower().startswith("on") or', 'if False or'),
        ('(value or "").strip().lower().startswith("javascript:")', 'False'),
        ('if self.script and data.strip():', 'if False:'),
        ('if Path(name).suffix.lower() not in', 'if False and Path(name).suffix.lower() not in'),
        ('if "\\0" in text:', 'if False:'),
        ('data.decode("utf-8")', 'data.decode("utf-8", errors="ignore")'),
    ]
    for i, (old, new) in enumerate(policy_cases):
        (work / "policy.py").write_text(policy_source.replace(old, new, 1), encoding="utf-8")
        shutil.copyfile(HERE / "test_policy.py", work / "test_policy.py")
        # Frische Bytecode-Auswertung auch bei gleich langen Mutationen.
        cache = work / "__pycache__"
        if cache.exists():
            shutil.rmtree(cache)
        print(f"MUTATION Quellregel {i+1}", flush=True)
        run([sys.executable, "-B", "-m", "unittest", "-v", "test_policy"], work, success=False)
    (work / "policy.py").write_text(policy_source, encoding="utf-8")
    shutil.copyfile(HERE / "test_pack.py", work / "test_pack.py")
    package_source = (HERE / "pack.py").read_text(encoding="utf-8")
    package_cases = [
        ("Dateizahl", "if len(files) > 1000 or", "if False or", "test_file_budget"),
        ("Quellbudget", "if len(files) > 1000 or sum(p.stat().st_size for p in files) > 4 * 1024 * 1024:", "if False:", "test_source_budget"),
        ("Archivbudget", "if len(result) > 4 * 1024 * 1024:", "if False:", "test_archive_budget"),
    ]
    for label, old, new, test in package_cases:
        (work / "pack.py").write_text(package_source.replace(old, new, 1), encoding="utf-8")
        cache = work / "__pycache__"
        if cache.exists() and cache.resolve().is_relative_to(work.resolve()):
            shutil.rmtree(cache)
        print("MUTATION Paket " + label, flush=True)
        run([sys.executable, "-B", "-m", "unittest", "-v", "test_pack.PackageRules." + test], work, env, success=False)
    run([sys.executable, "-B", "-m", "unittest", "-v", "test_policy", "test_pack"], HERE, env)
    run(["go", "test", "-mod=mod", "-count=1", "."], work, env)


if __name__ == "__main__":
    main()
