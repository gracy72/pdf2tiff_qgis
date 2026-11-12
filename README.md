# PDF2TIFF — lossless PDF to TIFF converter (GDAL) for QGIS

[![QGIS](https://img.shields.io/badge/QGIS-3.22%2B%20%7C%204.x-93b023)](https://qgis.org)
[![License](https://img.shields.io/badge/license-GPL--2.0--or--later-blue)](LICENSE)

**English** | [Polski](#polski)

A QGIS plugin that converts PDF files to GeoTIFF losslessly with `gdal_translate`:

* converts **every `*.pdf`** in a folder (optionally including subfolders) to `*.tif`,
* **multipage PDFs**: by default saves **drawings only** (A4 description pages are skipped);
  you can also choose all pages or an explicit page list,
* renders at the chosen **DPI** and writes a **GeoTIFF with lossless DEFLATE compression**,
* shows **two progress bars** (current file and overall) plus a **live log**,
* has a **STOP** button (aborts the running GDAL process),
* options: **skip existing TIFF** and **subfolders** (folder structure is recreated),
* registers a **Processing algorithm** (usable in models and `qgis_process`),
* **6 interface languages**: English, Polish, French, German, Spanish, Chinese.

For raster PDFs (e.g. PZT drawings exported from CAD) **200 DPI is the native resolution**,
i.e. a 1:1 copy — exactly as sharp as the PDF. Higher DPI (400/600) only interpolates.

---

## Interface language

All messages, tooltips, the log and the Processing algorithm descriptions come from
`i18n.py`. The language is taken from the **QGIS locale setting** (`locale/userLocale`,
the same one that drives the QGIS interface), so a Polish QGIS shows Polish, an English
QGIS shows English, and so on. Supported: `en`, `pl`, `fr`, `de`, `es`, `zh`.

* fallback language is English (missing keys never break the UI),
* the language can be forced with the environment variable `PDF2TIFF_LANG`
  (e.g. `PDF2TIFF_LANG=de`), which is handy for testing.

## Command used

```
gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff
    -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER
    "input.pdf" "output.tif"
```

`gdal_translate` is auto-detected: current QGIS install → `PATH` → `C:\QGIS\bin` →
`C:\OSGeo4W\bin` → `C:\Program Files\QGIS*` → `C:\Program Files\OSGeo4W*`.
You can also point to it manually in the plugin window.

## Checking the DPI of a PDF

```
gdalinfo "file.pdf"
```

The `Size is ...` field shows the size at the default 150 DPI render.
Native DPI = `width_px / page_width_in_inches`.

---

## Multipage PDFs

GDAL exposes every PDF page as a separate subdataset (`PDF:<page>:<file>`), so the plugin
converts pages one by one and writes separate files:

| PDF | Output files |
|---|---|
| 1 page | `name.tif` |
| many pages | `name_p01.tif`, `name_p02.tif`, … (`name_p001.tif` above 99 pages) |

Page selection modes (group **"PDF pages"** in the window, parameter **"PDF pages"** in the
algorithm):

| Mode | What it does |
|---|---|
| **Drawings only (default)** | saves pages **larger than the chosen sheet format** (default A3, i.e. larger than A4); A4 description pages and other text pages are skipped |
| **All pages** | every page of the PDF |
| **Selected pages** | a list of page numbers, e.g. `1,3,5-8` (empty = all) |

Extra settings for the "drawings only" mode:

* **Minimum drawing sheet size** — A4 (no format filter) / A3 (default) / A2 / A1 / A0.
* **Minimum ink coverage (%)** — 0 = filter off; higher values drop nearly blank pages.

Rules and safety nets:

* page size is read from the PDF metadata (px / 72 DPI × 25.4 = mm), so the analysis is fast,
* **single-page PDFs are always converted** (heuristics make no sense there),
* if **no** page is larger than the chosen format (e.g. the whole PDF is A4 drawings), the
  format filter is switched off and all pages are converted — with a note in the log,
* every decision (page number, sheet size, reason for skipping) goes to the log, e.g.:

```
[1/3] PB P&R Lesnica_zatwierdzony_PnB.pdf  (pages: 172, to convert: 26)
        page 1: skipped (210 x 297 mm (smaller than A3))
        ...
        page 38 -> PB P&R Lesnica_zatwierdzony_PnB_p038.tif
            OK  (4661, 2992 px, DPI 200, lossless)
```

---

## Installation

### 1. From the ZIP file (easiest)

1. Download `pdf2tiff_qgis.zip` from *Releases* (or zip this folder).
2. QGIS → **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Tick **"Enable"**; the icon appears in the toolbar.

### 2. Manually (profile folder)

Copy the whole folder to:

```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\pdf2tiff        (QGIS 3)
%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\pdf2tiff        (QGIS 4)
```

…and for portable QGIS (e.g. `C:\QGIS\QGIS_start.bat`) to:

```
C:\QGIS\QGIS_PROFILE\profiles\default\python\plugins\pdf2tiff
```

The folder name **must** be `pdf2tiff`.

### 3. From the QGIS plugin repository

Once published at <https://plugins.qgis.org>, install through
**Plugins → Manage and Install Plugins → All**.

---

## Usage

### Plugin window

Menu **Plugins → PDF -> TIFF** or the toolbar icon.

| Field | Meaning |
|---|---|
| **PDF folder** | folder with the PDF files to convert |
| **TIFF folder** | where to write the TIFF files (empty = next to the PDFs) |
| **gdal_translate** | path to `gdal_translate.exe` (auto-detected by default) |
| **DPI** | 200 for raster PDFs (no quality loss) |
| **Skip existing TIFF** | does not overwrite files converted earlier |
| **Subfolders** | processes subfolders and recreates their structure in the output folder |
| **PDF pages** | page mode: drawings only / all / selected |
| **Minimum drawing sheet size** | from which sheet size a page counts as a drawing (A3 = larger than A4) |
| **Minimum ink coverage (%)** | drops nearly blank pages (0 = filter off) |
| **START / STOP** | start conversion / abort (kills the running GDAL process) |

Upper bar = progress of the current file, lower bar = overall progress, text box = log.
Field values are remembered in the QGIS profile.

> The labels above are the English ones; in a Polish QGIS the same controls are in Polish
> (see the [Polski](#polski) section) — the language follows the QGIS locale.

### Processing toolbox

Processing toolbox → **PDF conversion → Convert PDF to TIFF (lossless)**.
Parameters: PDF folder, output folder, DPI, **PDF pages** (drawings only / all / selected),
**Selected pages** (e.g. `1,3,5-8`), **Minimum drawing sheet size**,
**Minimum ink coverage in percent**, *Skip existing TIFF*, *Process subfolders*,
`gdal_translate` path (empty = detect). Works in models and in `qgis_process` as well.

### Standalone script (no plugin needed)

**`skrypt_pdf2tiff.py`** works on its own (keep `i18n.py` next to it for translations;
without it the script falls back to English):

* **Processing toolbox → Scripts → Add Script from File…** and pick `skrypt_pdf2tiff.py`,
  then run it from **Scripts → PDF conversion**;
* or from the **Python console**:

```python
import sys
sys.path.append(r"C:\path\to\the\script\folder")

from skrypt_pdf2tiff import konwertuj_pdf_do_tiff

konwertuj_pdf_do_tiff(
    r"D:\PZT",               # folder with PDFs
    r"D:\PZT_TIF",           # output folder (None = next to the PDFs)
    dpi=200,
    podkatalogi=True,        # subfolders
    pomijaj_istniejace=True, # skip existing TIFF
    tryb_stron=TRYB_RYSUNKI,  # TRYB_RYSUNKI | TRYB_WSZYSTKIE | TRYB_WYBRANE
    lista_stron='',           # e.g. '1,3,5-8' (for TRYB_WYBRANE)
    min_format='A3',          # from which sheet size a page is a drawing
    min_tusz=0.0,             # min. ink coverage in % (0 = no filter)
)
```

The function returns a dict `{'udane':…, 'bledy':…, 'pominiete':…, 'pliki':…}`
(`udane`/`bledy` are counted in pages).

---

## Project files

| File | Role |
|---|---|
| `__init__.py` | `classFactory` — plugin entry point |
| `metadata.txt` | plugin metadata (name, version, author, repository, changelog) |
| `plugin.py` | registration: icon, menu, Processing provider |
| `dialog.py` | converter window (folders, DPI, page selection, options, progress bars, log) |
| `converter.py` | logic: GDAL detection, file list, paths, arguments, PDF page selection, `QThread` + `QProcess` |
| `algorithm.py` | Processing algorithm (`pdf_to_tiff`) + provider |
| `i18n.py` | translations for 6 languages + language detection (QGIS locale) |
| `skrypt_pdf2tiff.py` | standalone script (Processing / Python console) |
| `icon.png` | 64×64 icon (generated by `tools/make_icon.py`) |
| `tools/` | icon generator, ZIP packer, tests (not part of the plugin package) |

## Requirements

* QGIS **3.22+** (PyQt5) or QGIS **4.x** (PyQt6) — both are supported,
* `gdal_translate` available (the QGIS/OSGeo4W install ships it in `bin`),
* Windows / Linux / macOS (paths are detected automatically; on Linux `PATH` is usually enough).

Tested on QGIS 4.2 (Qt6, Windows): plugin import, window, 200 DPI conversion, subfolders,
Processing algorithm and the standalone script — all working.

## Publishing to the QGIS repository (plugins.qgis.org)

1. In `metadata.txt` adjust `author`, `email`, `repository`, `tracker`, `homepage`
   (already set to `gracy72` — change if you publish from another account).
2. Raise `version=` and add a `changelog=` entry.
3. Pack the plugin so that the archive contains **one top-level folder** named after the
   plugin id (`pdf2tiff/`) with `metadata.txt` and the rest inside.
   The easy way: `python tools/make_zip.py` (creates `pdf2tiff_qgis.zip`).
4. <https://plugins.qgis.org/plugins/> → log in → **Add plugin** → upload the ZIP.
5. The reviewer checks `metadata.txt`, that `unload()` works and that there are no
   dependencies outside QGIS.

## License

GNU General Public License v2.0 or later (GPL-2.0-or-later), as required by the QGIS
plugin repository. See `LICENSE`.

## Author

Gracjan Blachowicz — plugin author.

---

# Polski

Konwerter PDF → TIFF dla QGIS (bezstratny, GDAL).

Wtyczka QGIS do bezstratnej konwersji PDF-ów na GeoTIFF przy pomocy `gdal_translate`:

* konwertuje **wszystkie pliki `*.pdf`** z wybranego katalogu (opcjonalnie z podkatalogami) do `*.tif`,
* **PDF wielostronicowe**: domyślnie zapisuje **tylko rysunki** (pomija opisówki), do wyboru też wszystkie strony albo wskazana lista,
* renderuje PDF w zadanym **DPI** i zapisuje **GeoTIFF z kompresją bezstratną DEFLATE** — jakość nie jest tracona,
* pokazuje **dwa paski postępu** (bieżący plik i całość) oraz **log na bieżąco**,
* ma przycisk **STOP** (przerywa bieżący proces GDAL),
* opcje: **„Pomijaj istniejące TIFF”** i **„Podkatalogi”** (zachowanie struktury katalogów),
* dodatkowo rejestruje **algorytm w Panelu przetwarzania** (do modeli i `qgis_process`),
* **6 języków interfejsu**: polski, angielski, francuski, niemiecki, hiszpański, chiński.

Dla PDF rastrowych (np. PZT generowany z CAD) **200 DPI = natywna rozdzielczość**, czyli
odtworzenie 1:1 — dokładnie tak samo wyraźnie jak w PDF. Wyższe DPI (400/600) to już
interpolacja: gładsze, ale bez nowego detalu.

## Język interfejsu

Wszystkie komunikaty, podpowiedzi, log oraz opisy algorytmu Processing pochodzą z modułu
`i18n.py`. Język jest brany z **ustawień QGIS** (`locale/userLocale` — ten sam, który
wybiera język interfejsu QGIS), więc QGIS po polsku pokazuje polskie komunikaty, a po
angielsku angielskie. Obsługiwane: `pl`, `en`, `fr`, `de`, `es`, `zh`.

* językiem zapasowym jest angielski (brakujący klucz nigdy nie psuje interfejsu),
* język można wymusić zmienną środowiskową `PDF2TIFF_LANG` (np. `PDF2TIFF_LANG=en`),
  co ułatwia testowanie.

---

## Wywoływana komenda

Wtyczka uruchamia dokładnie to:

```
gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff
    -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER
    "wejście.pdf" "wyjście.tif"
```

`gdal_translate` jest wykrywany automatycznie: bieżąca instalacja QGIS → `PATH` →
`C:\QGIS\bin` → `C:\OSGeo4W\bin` → `C:\Program Files\QGIS*` → `C:\Program Files\OSGeo4W*`.
Ścieżkę można też wskazać ręcznie w oknie wtyczki.

## Jak sprawdzić DPI PDF-a

```
gdalinfo "plik.pdf"
```

W polu `Size is ...` widać rozmiar dla domyślnego renderu (150 DPI).
Natywne DPI = `szerokość_px / szerokość_strony_w_calach`.

---

## PDF wielostronicowe

GDAL udostępnia każdą stronę PDF-a jako osobny podzbiór (`PDF:<numer>:<plik>`), więc
wtyczka konwertuje strony pojedynczo i zapisuje osobne pliki:

| PDF | Pliki wynikowe |
|---|---|
| 1 strona | `nazwa.tif` |
| wiele stron | `nazwa_p01.tif`, `nazwa_p02.tif`, … (`nazwa_p001.tif` powyżej 99 stron) |

Tryby wyboru stron (grupa **„Strony PDF”** w oknie, parametr **„Strony PDF”** w algorytmie):

| Tryb | Co robi |
|---|---|
| **Tylko rysunki (domyślnie)** | zapisuje strony **większe niż wybrany format** (domyślnie A3, czyli większe niż A4); opisówki A4 i inne strony tekstowe są pomijane |
| **Wszystkie strony** | każda strona PDF-a |
| **Wskazane strony** | lista numerów, np. `1,3,5-8` (puste = wszystkie) |

Dodatkowe ustawienia trybu „tylko rysunki”:

* **Min. format rysunku** — A4 (bez filtra formatu) / A3 (domyślnie) / A2 / A1 / A0.
* **Min. pokrycie tuszem (%)** — 0 = filtr wyłączony; wyższe wartości odsiewają strony prawie puste.

Zasady działania i bezpieczniki:

* format strony jest liczony z metadanych PDF-a (px / 72 DPI × 25,4 = mm), więc analiza jest szybka,
* **PDF jednostronicowe są zawsze konwertowane** (heurystyki nie mają sensu),
* jeżeli **żadna** strona nie jest większa niż wybrany format (np. cały PDF to rysunki na A4),
  filtr formatu jest wyłączany i konwertowane są wszystkie strony — z odpowiednim komunikatem w logu,
* każda decyzja (numer strony, format, powód pominięcia) trafia do logu, np.:

```
[1/3] PB P&R Leśnica_zatwierdzony_PnB.pdf  (stron: 172, do konwersji: 26)
        str. 1: pominięta (210 x 297 mm (mniejsza niż A3))
        ...
        str. 38 -> PB P&R Leśnica_zatwierdzony_PnB_p038.tif
            OK  (4661, 2992 px, DPI 200, bezstratnie)
```

---

## Instalacja

### 1. Z pliku ZIP (najprościej)

1. Pobierz `pdf2tiff_qgis.zip` z sekcji *Releases* (albo spakuj ten katalog).
2. QGIS → **Wtyczki → Zarządzanie wtyczkami → Zainstaluj z pliku ZIP**.
3. Zaznacz **„Włącz”**, ikona pojawi się na pasku narzędzi.

### 2. Ręcznie (katalog profilu)

Skopiuj cały ten katalog do:

```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\pdf2tiff        (QGIS 3)
%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\pdf2tiff        (QGIS 4)
```

...a przy QGIS portable (np. `C:\QGIS\QGIS_start.bat`) do:

```
C:\QGIS\QGIS_PROFILE\profiles\default\python\plugins\pdf2tiff
```

Nazwa katalogu **musi** brzmieć `pdf2tiff`.

### 3. Z repozytorium QGIS

Po zgłoszeniu wtyczki do <https://plugins.qgis.org> instalacja idzie z
**Wtyczki → Zarządzanie wtyczkami → Wszystkie**.

---

## Użycie

### Okno wtyczki

Menu **Wtyczki → PDF -> TIFF** albo ikona na pasku narzędzi.

| Pole | Znaczenie |
|---|---|
| **Katalog PDF** | katalog z plikami PDF do konwersji |
| **Katalog TIFF** | gdzie zapisać pliki TIFF (puste = obok plików PDF) |
| **gdal_translate** | ścieżka do `gdal_translate.exe` (domyślnie wykrywana) |
| **DPI** | 200 dla PDF rastrowych (bez utraty jakości) |
| **Pomijaj istniejące TIFF** | nie nadpisuje już przekonwertowanych plików |
| **Podkatalogi** | przetwarza podkatalogi i odtwarza ich strukturę w katalogu docelowym |
| **Strony PDF** | tryb wyboru stron: tylko rysunki / wszystkie / wskazane |
| **Min. format rysunku** | od jakiego formatu strona jest uznawana za rysunek (A3 = większe niż A4) |
| **Min. pokrycie tuszem (%)** | odrzuca strony prawie puste (0 = filtr wyłączony) |
| **START / STOP** | start konwersji / przerwanie (kończy bieżący proces GDAL) |

Górny pasek = postęp bieżącego pliku, dolny = postęp całości, pole tekstowe = log.
Wartości pól są zapamiętywane w profilu QGIS.

> Powyższe nazwy pól to wersja polska; w QGIS angielskim te same kontrolki są po angielsku —
> język idzie za ustawieniem QGIS (patrz sekcja [English](#pdf2tiff--lossless-pdf-to-tiff-converter-gdal-for-qgis)).

### Panel przetwarzania (Processing)

Panel przetwarzania → **Konwersja PDF → Konwertuj PDF do TIFF (bezstratnie)**.
Parametry: katalog PDF, katalog wynikowy, DPI, **Strony PDF** (tylko rysunki / wszystkie /
wskazane), **Wskazane strony** (np. `1,3,5-8`), **Minimalny format rysunku**,
**Minimalne pokrycie tuszem w procentach**, *Pomijaj istniejące TIFF*, *Przetwarzaj podkatalogi*,
ścieżka `gdal_translate` (puste = wykryj). Algorytm działa też w modelach i w `qgis_process`.

### Sam skrypt, bez wtyczki

Plik **`skrypt_pdf2tiff.py`** jest samodzielny (nie wymaga instalacji wtyczki). Tłumaczenia
bierze z `i18n.py`, jeśli leży obok; bez niego używa komunikatów angielskich.

* **Panel przetwarzania → Skrypty → Dodaj skrypt z pliku…** i wskaż `skrypt_pdf2tiff.py`,
  potem uruchamiaj z grupy **Skrypty → Konwersja PDF**;
* albo w **konsoli Pythona**:

```python
import sys
sys.path.append(r"C:\ścieżka\do\katalogu\z\skryptem")

from skrypt_pdf2tiff import konwertuj_pdf_do_tiff

konwertuj_pdf_do_tiff(
    r"D:\PZT",               # katalog z PDF
    r"D:\PZT_TIF",           # katalog wynikowy (None = obok PDF)
    dpi=200,
    podkatalogi=True,
    pomijaj_istniejace=True,
    tryb_stron=TRYB_RYSUNKI,  # TRYB_RYSUNKI | TRYB_WSZYSTKIE | TRYB_WYBRANE
    lista_stron='',           # np. '1,3,5-8' (dla TRYB_WYBRANE)
    min_format='A3',          # od jakiego formatu strona jest rysunkiem
    min_tusz=0.0,             # min. pokrycie tuszem w % (0 = bez filtra)
)
```

Funkcja zwraca słownik `{'udane':…, 'bledy':…, 'pominiete':…, 'pliki':…}`
(`udane`/`bledy` liczone są w stronach).

---

## Pliki projektu

| Plik | Rola |
|---|---|
| `__init__.py` | `classFactory` — punkt wejścia wtyczki QGIS |
| `metadata.txt` | metadane wtyczki (nazwa, wersja, autor, repozytorium, changelog) |
| `plugin.py` | rejestracja: ikona, menu, dostawca algorytmów Processing |
| `dialog.py` | okno konwertera (katalogi, DPI, wybór stron, opcje, paski postępu, log) |
| `converter.py` | logika: wykrywanie GDAL, lista plików, ścieżki, argumenty, wybór stron PDF, `QThread` z `QProcess` |
| `algorithm.py` | algorytm Processing (`pdf_to_tiff`) + dostawca |
| `i18n.py` | tłumaczenia na 6 języków + wykrywanie języka (ustawienia QGIS) |
| `skrypt_pdf2tiff.py` | samodzielny skrypt (Processing / konsola Pythona) |
| `icon.png` | ikona 64×64 (generowana przez `tools/make_icon.py`) |
| `tools/` | generator ikony, pakowanie ZIP i test (nie są częścią paczki wtyczki) |

## Wymagania

* QGIS **3.22+** (PyQt5) lub QGIS **4.x** (PyQt6) — kod obsługuje oba,
* `gdal_translate` w systemie: instalacja QGIS/OSGeo4W zawiera go w `bin`,
* Windows / Linux / macOS (ścieżki wykrywane automatycznie; na Linuksie zwykle wystarczy `PATH`).

Testowane na QGIS 4.2 (Qt6, Windows): import wtyczki, okno, konwersja 200 DPI,
zachowanie podkatalogów, algorytm Processing i skrypt — wszystko działa.

## Publikacja w repozytorium QGIS (plugins.qgis.org)

1. W `metadata.txt` popraw `author`, `email`, `repository`, `tracker`, `homepage` (są już ustawione
   na `gracy72` — zmień, jeśli publikujesz z innego konta).
2. Podnieś `version=` i dopisz wpis w `changelog=`.
3. Spakuj wtyczkę tak, aby w archiwum była **jeden katalog na najwyższym poziomie** o nazwie
   równej identyfikatorowi wtyczki (`pdf2tiff/`), a w nim `metadata.txt` i reszta plików.
   Najprościej: `python tools/make_zip.py` (tworzy `pdf2tiff_qgis.zip`).
4. <https://plugins.qgis.org/plugins/> → zaloguj się → **Add plugin** → wgraj ZIP.
5. Recenzent sprawdzi m.in. `metadata.txt`, obsługę `unload()`, brak zależności spoza QGIS.

## Licencja

GNU General Public License v2.0 lub późniejsza (GPL-2.0-or-later) — jak wymaga
repozytorium wtyczek QGIS. Szczegóły w pliku `LICENSE`.

## Autor

Gracjan Blachowicz — autor wtyczki.
