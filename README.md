# PDF2TIFF — konwerter PDF do TIFF (bezstratny, GDAL) dla QGIS

Wtyczka QGIS będąca odpowiednikiem programu **`Laz_PDF_tiff`** (Lazarus / Free Pascal).
Robi dokładnie to samo, z tym samym wywołaniem GDAL, ale działa wewnątrz QGIS:

* konwertuje **wszystkie pliki `*.pdf`** z wybranego katalogu (opcjonalnie z podkatalogami) do `*.tif`,
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

Identyczna jak w wersji Lazarus:

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
| **START / STOP** | start konwersji / przerwanie (kończy bieżący proces GDAL) |

Górny pasek = postęp bieżącego pliku, dolny = postęp całości, pole tekstowe = log.
Wartości pól są zapamiętywane w profilu QGIS.

### Panel przetwarzania (Processing)

Panel przetwarzania → **Konwersja PDF → Konwertuj PDF do TIFF (bezstratnie)**.
Parametry: katalog PDF, katalog wynikowy, DPI, *Pomijaj istniejące TIFF*,
*Przetwarzaj podkatalogi*, ścieżka `gdal_translate` (puste = wykryj).
Algorytm działa też w modelach i w `qgis_process`.

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
)
```

Funkcja zwraca słownik `{'udane':…, 'bledy':…, 'pominiete':…, 'pliki':…}`.

---

## Pliki projektu

| Plik | Rola |
|---|---|
| `__init__.py` | `classFactory` — punkt wejścia wtyczki QGIS |
| `metadata.txt` | metadane wtyczki (nazwa, wersja, autor, repozytorium, changelog) |
| `plugin.py` | rejestracja: ikona, menu, dostawca algorytmów Processing |
| `dialog.py` | okno — odpowiednik formularza `TForm1` z wersji Lazarus |
| `converter.py` | logika: wykrywanie GDAL, lista plików, ścieżki, argumenty, `QThread` z `QProcess` |
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
3. Spakuj **zawartość** tego katalogu (bez `tools/`, `.git`, `__pycache__`) tak, aby w archiwum
   pliki leżały na najwyższym poziomie (`metadata.txt`, `__init__.py`, …).
   Najprościej: `python tools/make_zip.py`.
4. <https://plugins.qgis.org/plugins/> → zaloguj się → **Add plugin** → wgraj ZIP.
5. Recenzent sprawdzi m.in. `metadata.txt`, obsługę `unload()`, brak zależności spoza QGIS.

## Licencja

GNU General Public License v2.0 lub późniejsza (GPL-2.0-or-later) — jak wymaga
repozytorium wtyczek QGIS. Szczegóły w pliku `LICENSE`.

## Autor

Gracjan Blachowicz — wersja QGIS programu `Laz_PDF_tiff`.
