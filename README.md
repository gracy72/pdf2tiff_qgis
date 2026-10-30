# PDF2TIFF — konwerter PDF do TIFF (bezstratny, GDAL) dla QGIS

Wtyczka QGIS do bezstratnej konwersji PDF-ów na GeoTIFF przy pomocy `gdal_translate`:

* konwertuje **wszystkie pliki `*.pdf`** z wybranego katalogu (opcjonalnie z podkatalogami) do `*.tif`,
* **PDF wielostronicowe**: domyślnie zapisuje **tylko rysunki** (pomija opisówki), do wyboru też wszystkie strony albo wskazana lista,
* renderuje PDF w zadanym **DPI** i zapisuje **GeoTIFF z kompresją bezstratną DEFLATE** — jakość nie jest tracona,
* pokazuje **dwa paski postępu** (bieżący plik i całość) oraz **log na bieżąco**,
* ma przycisk **STOP** (przerywa bieżący proces GDAL),
* opcje: **„Pomijaj istniejące TIFF”** i **„Podkatalogi”** (zachowanie struktury katalogów),
* dodatkowo rejestruje **algorytm w Panelu przetwarzania** (do modeli i `qgis_process`).

Dla PDF rastrowych (np. PZT generowany z CAD) **200 DPI = natywna rozdzielczość**, czyli
odtworzenie 1:1 — dokładnie tak samo wyraźnie jak w PDF. Wyższe DPI (400/600) to już
interpolacja: gładsze, ale bez nowego detalu.

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

### Panel przetwarzania (Processing)

Panel przetwarzania → **Konwersja PDF → Konwertuj PDF do TIFF (bezstratnie)**.
Parametry: katalog PDF, katalog wynikowy, DPI, **Strony PDF** (tylko rysunki / wszystkie /
wskazane), **Wskazane strony** (np. `1,3,5-8`), **Minimalny format rysunku**,
**Minimalne pokrycie tuszem (%)**, *Pomijaj istniejące TIFF*, *Przetwarzaj podkatalogi*,
ścieżka `gdal_translate` (puste = wykryj). Algorytm działa też w modelach i w `qgis_process`.

### Sam skrypt, bez wtyczki

Plik **`skrypt_pdf2tiff.py`** jest samodzielny (nie wymaga instalacji wtyczki):

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
