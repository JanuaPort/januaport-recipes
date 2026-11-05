package recipecheck

import (
	"archive/tar"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/januaport/januaport/internal/apps"
	o "github.com/januaport/januaport/internal/objektspeicher"
	"github.com/januaport/januaport/internal/skriptspeicher"
	"github.com/januaport/januaport/internal/store/sqlite"
)

const valid = `{"name":"probe","fenster":"browser","modus":"b","teams":[],"werkzeuge":[],"skripte":[]}`

func archive(t *testing.T, files map[string]o.Datei) []byte {
	t.Helper()
	var buf bytes.Buffer
	w := tar.NewWriter(&buf)
	names := make([]string, 0, len(files))
	for name := range files {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		body := files[name].Bytes
		if err := w.WriteHeader(&tar.Header{Name: name, Mode: 0644, Size: int64(len(body)), Typeflag: tar.TypeReg, ModTime: time.Unix(0, 0), Format: tar.FormatPAX}); err != nil {
			t.Fatal(err)
		}
		if _, err := w.Write(body); err != nil {
			t.Fatal(err)
		}
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}
	return buf.Bytes()
}

func service(t *testing.T) *apps.Service {
	t.Helper()
	st, err := sqlite.Open(t.Context(), filepath.Join(t.TempDir(), "probe.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = st.Close() })
	if err := skriptspeicher.New(st).Initialisieren(t.Context()); err != nil {
		t.Fatal(err)
	}
	return apps.New(st, nil).WithRecipeCatalog(func(context.Context) ([]string, error) { return []string{}, nil })
}

func TestManifestReject(t *testing.T) {
	for name, raw := range map[string]string{
		"unknown":  strings.Replace(valid, `"name":`, `"extra":true,"name":`, 1),
		"trailing": valid + ` {}`,
		"carrier":  strings.Replace(valid, `"modus":"b"`, `"modus":"a"`, 1),
		"size":     valid + strings.Repeat(" ", 8193),
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := apps.ParseManifest([]byte(raw)); err == nil {
				t.Fatal("Manifest angenommen")
			}
		})
	}
	if _, err := apps.ParseManifest([]byte(valid)); err != nil {
		t.Fatal(err)
	}
}

func TestLoadReject(t *testing.T) {
	cases := map[string]map[string]o.Datei{
		"bytes":      {"apps/probe/a.txt": {Modus: 0100644, Bytes: bytes.Repeat([]byte("x"), (4<<20)+1)}},
		"secret":     {"apps/probe/a.txt": {Modus: 0100644, Bytes: []byte("password=" + strings.Repeat("x", 12))}},
		"executable": {"apps/probe/a.txt": {Modus: 0100644, Bytes: []byte("MZ executable")}},
		"path":       {"apps/probe/../a.txt": {Modus: 0100644, Bytes: []byte("text")}},
		"mode":       {"apps/probe/a.txt": {Modus: 0120000, Bytes: []byte("text")}},
	}
	many := map[string]o.Datei{}
	for i := 0; i < 1001; i++ {
		many[fmt.Sprintf("apps/probe/%d.txt", i)] = o.Datei{Modus: 0100644}
	}
	cases["count"] = many
	for name, files := range cases {
		t.Run(name, func(t *testing.T) {
			if err := skriptspeicher.PruefeAppDateien(files); err == nil {
				t.Fatal("Lade-Regel nimmt verbotene Quelle an")
			}
		})
	}
}

func TestImportStopped(t *testing.T) {
	svc := service(t)
	data := archive(t, map[string]o.Datei{"jnpt.app.json": {Bytes: []byte(valid)}, "index.html": {Bytes: []byte("<html></html>")}})
	for _, via := range []string{"cli", "rest", "admin-mcp"} {
		in := apps.RecipeInput{Name: "probe", Data: data}
		out, err := svc.ImportRecipe(t.Context(), in, apps.Origin{Via: via}, "probe")
		if err != nil {
			t.Fatal(err)
		}
		st, err := svc.Read(t.Context())
		if err != nil {
			t.Fatal(err)
		}
		if len(st.Apps) != 1 || st.Apps[0].Status != "gestoppt" {
			t.Fatal("Import ist live")
		}
		if !slices.Contains(out.Open, "Teams leer") {
			t.Fatal(out.Open)
		}
		// Vor dem Wiederimport bewusst live setzen.
		if _, err := svc.Execute(t.Context(), apps.Request{Operation: "app_registrieren", Name: "probe", Path: "apps/probe/", Fassung: out.Revision, BasisFassung: out.Revision, Status: "live", Ja: true}, apps.Origin{Via: "cli"}); err != nil {
			t.Fatal(err)
		}
	}
}

func TestImportReject(t *testing.T) {
	for name, body := range map[string]string{
		"secret":     "password=" + strings.Repeat("x", 12),
		"executable": "MZ executable",
	} {
		t.Run(name, func(t *testing.T) {
			svc := service(t)
			data := archive(t, map[string]o.Datei{"jnpt.app.json": {Bytes: []byte(valid)}, "bad.txt": {Bytes: []byte(body)}})
			if _, err := svc.ImportRecipe(t.Context(), apps.RecipeInput{Name: "probe", Data: data}, apps.Origin{Via: "cli"}, "probe"); err == nil {
				t.Fatal("Verbotener Import angenommen")
			}
			st, err := svc.Read(t.Context())
			if err != nil || len(st.Apps) != 0 {
				t.Fatal("Abgewiesener Import gespeichert", err)
			}
		})
	}
	for _, origin := range []apps.Origin{{Via: "mcp"}, {Via: "cli", App: "probe"}} {
		t.Run("origin-"+origin.Via, func(t *testing.T) {
			svc := service(t)
			data := archive(t, map[string]o.Datei{"jnpt.app.json": {Bytes: []byte(valid)}})
			if _, err := svc.ImportRecipe(t.Context(), apps.RecipeInput{Name: "probe", Data: data}, origin, "probe"); err == nil {
				t.Fatal("Import ohne Admin angenommen")
			}
		})
	}
}

func TestBindingAndExport(t *testing.T) {
	svc := service(t)
	m := apps.Manifest{Name: "probe", Window: "browser", Mode: "a", TokenID: "1111111111111111", Teams: []string{"quelle"}, Tools: []string{}, Scripts: []string{}}
	raw, err := json.Marshal(m)
	if err != nil {
		t.Fatal(err)
	}
	data := archive(t, map[string]o.Datei{"jnpt.app.json": {Bytes: raw}})
	if _, err := svc.ImportRecipe(t.Context(), apps.RecipeInput{Name: "probe", Data: data}, apps.Origin{Via: "cli"}, "probe"); err != apps.ErrRecipeToken {
		t.Fatal("Fehlender neuer Traeger", err)
	}
	out, err := svc.ImportRecipe(t.Context(), apps.RecipeInput{Name: "ziel", Data: data, TokenID: "2222222222222222", Teams: []string{"ziel"}}, apps.Origin{Via: "cli"}, "probe")
	if err != nil {
		t.Fatal(err)
	}
	state, err := svc.Read(t.Context())
	if err != nil {
		t.Fatal(err)
	}
	got := state.Apps[0].Manifest
	if got.Name != "ziel" || got.TokenID != "2222222222222222" || !slices.Equal(got.Teams, []string{"ziel"}) {
		t.Fatal("Quellbindung uebernommen")
	}
	a, err := svc.ExportRecipe(t.Context(), "ziel", out.Revision, apps.Origin{Via: "cli"})
	if err != nil {
		t.Fatal(err)
	}
	b, err := svc.ExportRecipe(t.Context(), "ziel", out.Revision, apps.Origin{Via: "cli"})
	if err != nil || !bytes.Equal(a, b) {
		t.Fatal("Export nicht deterministisch", err)
	}
	r := tar.NewReader(bytes.NewReader(a))
	h, err := r.Next()
	if err != nil {
		t.Fatal(err)
	}
	if h.Name != "jnpt.app.json" || h.Mode != 0644 || h.Uid != 0 || h.Gid != 0 || h.ModTime.Unix() != 0 {
		t.Fatal("TAR-Metadaten", h)
	}
	var portable apps.Manifest
	if err := json.NewDecoder(r).Decode(&portable); err != nil {
		t.Fatal(err)
	}
	if len(portable.Teams) != 0 || portable.TokenID != "" {
		t.Fatal("Bindung exportiert")
	}
}

func TestArchiveReject(t *testing.T) {
	for _, kind := range []string{"link", "duplicate", "path", "count", "bytes"} {
		t.Run(kind, func(t *testing.T) {
			files := map[string]o.Datei{"jnpt.app.json": {Bytes: []byte(valid)}}
			if kind == "path" {
				files["../other.txt"] = o.Datei{Bytes: []byte("text")}
			}
			if kind == "count" {
				for i := 0; i < 1000; i++ {
					files[fmt.Sprintf("%d.txt", i)] = o.Datei{}
				}
			}
			data := archive(t, files)
			if kind == "bytes" {
				data = append(data, make([]byte, 4<<20)...)
			}
			if kind == "link" || kind == "duplicate" {
				var buf bytes.Buffer
				w := tar.NewWriter(&buf)
				_ = w.WriteHeader(&tar.Header{Name: "jnpt.app.json", Mode: 0644, Size: int64(len(valid))})
				_, _ = w.Write([]byte(valid))
				h := &tar.Header{Name: "jnpt.app.json", Mode: 0644, Size: int64(len(valid))}
				if kind == "link" {
					h.Name = "linked.txt"
					h.Typeflag = tar.TypeSymlink
					h.Linkname = "jnpt.app.json"
					h.Size = 0
				}
				if err := w.WriteHeader(h); err != nil {
					t.Fatal(err)
				}
				if kind == "duplicate" {
					_, _ = w.Write([]byte(valid))
				}
				if err := w.Close(); err != nil {
					t.Fatal(err)
				}
				data = buf.Bytes()
			}
			svc := service(t)
			if _, err := svc.ImportRecipe(t.Context(), apps.RecipeInput{Name: "probe", Data: data}, apps.Origin{Via: "cli"}, "probe"); err == nil {
				t.Fatal("Ungueltiges Archiv angenommen")
			}
			st, err := svc.Read(t.Context())
			if err != nil || len(st.Apps) != 0 {
				t.Fatal("Archiv teilweise gespeichert", err)
			}
		})
	}
}

func TestCoreGaps(t *testing.T) {
	// Diese Akzeptanz ist ein offener Kernpunkt, keine Zusage der Rezeptprüfung.
	for _, body := range [][]byte{[]byte("<script>alert(1)</script>"), {137, 80, 78, 71, 13, 10, 26, 10}, {0, 0, 1, 0}} {
		if err := skriptspeicher.PruefeAppDateien(map[string]o.Datei{"apps/probe/source.txt": {Modus: 0100644, Bytes: body}}); err != nil {
			t.Fatalf("Kerngrenze hat sich geaendert: %v", err)
		}
	}
}

func TestExamples(t *testing.T) {
	for _, name := range []string{"steuer", "monitor"} {
		t.Run(name, func(t *testing.T) {
			root := filepath.Join(os.Getenv("RECIPE_ROOT"), "rezepte", name+"-app", "app")
			files := map[string]o.Datei{}
			err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
				if err != nil {
					return err
				}
				if d.IsDir() {
					return nil
				}
				b, err := os.ReadFile(path)
				if err != nil {
					return err
				}
				rel, err := filepath.Rel(root, path)
				if err != nil {
					return err
				}
				files[filepath.ToSlash(rel)] = o.Datei{Modus: 0100644, Bytes: b}
				return nil
			})
			if err != nil {
				t.Fatal(err)
			}
			raw := files["jnpt.app.json"].Bytes
			var m apps.Manifest
			if err := json.Unmarshal(raw, &m); err != nil {
				t.Fatal(err)
			}
			if m.Name != name {
				t.Fatalf("App-Name=%q, Browser-Name=%q", m.Name, name)
			}
			if m.TokenID != "" || len(m.Teams) != 0 {
				t.Fatal("Betreiberbindung im Rezept")
			}
			if m.Mode == "a" {
				if _, err := apps.ParseManifest(raw); err == nil {
					t.Fatal("Modus a ohne Träger angenommen")
				}
				m.TokenID = "0000000000000000"
			}
			bound, err := json.Marshal(m)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := apps.ParseManifest(bound); err != nil {
				t.Fatal(err)
			}
			load := map[string]o.Datei{}
			total := 0
			for p, f := range files {
				load["apps/"+name+"/"+p] = f
				total += len(f.Bytes)
				if err := skriptspeicher.PruefeAppDateien(map[string]o.Datei{"apps/" + name + "/" + p: f}); err != nil {
					t.Fatalf("%s: %v", p, err)
				}
			}
			if err := skriptspeicher.PruefeAppDateien(load); err != nil {
				t.Fatal(err)
			}
			pack := func() []byte {
				out := filepath.Join(t.TempDir(), "app.tar")
				cmd := exec.Command("python", filepath.Join(os.Getenv("RECIPE_ROOT"), "pruefung", "app-rezepte", "pack.py"), root, out)
				if log, err := cmd.CombinedOutput(); err != nil {
					t.Fatalf("Packen: %v %s", err, log)
				}
				data, err := os.ReadFile(out)
				if err != nil {
					t.Fatal(err)
				}
				return data
			}
			data := pack()
			if len(data) > 4<<20 {
				t.Fatal("TAR zu groß")
			}
			if !bytes.Equal(data, pack()) {
				t.Fatal("TAR nicht deterministisch")
			}
			in := apps.RecipeInput{Name: name, Data: data, TokenID: m.TokenID}
			if err := apps.PruefeRezept(in); err != nil {
				t.Fatal(err)
			}
			svc := service(t)
			out, err := svc.ImportRecipe(t.Context(), in, apps.Origin{Via: "cli"}, "probe")
			if err != nil {
				t.Fatal(err)
			}
			st, err := svc.Read(t.Context())
			if err != nil {
				t.Fatal(err)
			}
			if len(st.Apps) != 1 || st.Apps[0].Status != "gestoppt" {
				t.Fatal("Beispiel nach Import live")
			}
			for _, tool := range m.Tools {
				if !slices.Contains(out.Open, "Werkzeug "+tool+" fehlt") {
					t.Fatal(out.Open)
				}
			}
			for _, pin := range m.Scripts {
				if !slices.Contains(out.Open, "Skript-Pin "+pin+" fehlt") {
					t.Fatal(out.Open)
				}
			}
			if !slices.Contains(out.Open, "Teams leer") {
				t.Fatal(out.Open)
			}
			t.Logf("Dateien=%d Bytes=%d TAR=%d offene_punkte=%v", len(files), total, len(data), out.Open)
		})
	}
}
