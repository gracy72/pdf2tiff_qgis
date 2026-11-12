# -*- coding: utf-8 -*-
"""
Tlumaczenia wtyczki PDF2TIFF (i18n).

Jezyk jest brany z ustawien QGIS (klucz "locale/userLocale", ten sam, ktory
wybiera jezyk interfejsu QGIS), a gdy go nie ma - z ustawien systemowych.
Mozna go tez wymusic zmienna srodowiskowa PDF2TIFF_LANG (np. PDF2TIFF_LANG=de).

Obslugiwane jezyki: en (domyslny), pl, fr, de, es, zh.
Klucze, ktorych brakuje w danym jezyku, sa brane z tabeli angielskiej.
"""

import os

try:                                    # w QGIS (wtyczka, skrypt w panelu Processing)
    from qgis.PyQt.QtCore import QLocale
except ImportError:                     # poza QGIS wystarczy PDF2TIFF_LANG
    QLocale = None

FALLBACK = 'en'

#: (kod, nazwa jezyka) - kolejnosc wyswietlania
LANGUAGES = [
    ('en', 'English'),
    ('pl', 'Polski'),
    ('fr', 'Francais'),
    ('de', 'Deutsch'),
    ('es', 'Espanol'),
    ('zh', 'Chinese'),
]

#: Klucze wspolne dla wszystkich jezykow (napisane raz, w tabeli EN)
TRANSLATIONS = {
    'en': {
        # --- okno
        'title': 'PDF -> TIFF converter  (lossless, GDAL)',
        'lbl_in': 'PDF folder:',
        'lbl_out': 'TIFF folder:',
        'lbl_gdal': 'gdal_translate:',
        'ph_out': 'empty = save next to the PDF files',
        'browse': 'Browse...',
        'dpi': 'DPI:',
        'skip': 'Skip existing TIFF',
        'subfolders': 'Subfolders',
        'start': 'START',
        'stop': 'STOP',
        'pages_group': 'PDF pages',
        'mode_drawings': 'Drawings only (default)',
        'mode_all': 'All pages',
        'mode_custom': 'Selected pages:',
        'tip_mode_drawings': ('Saves pages larger than the chosen sheet format. In a typical PDF\n'
                              '(A4 description + A3/A2/A1/A0 drawings) only drawings are kept.'),
        'ph_pages': 'e.g. 1,3,5-8   (empty = all pages)',
        'lbl_format': 'Min. drawing sheet size:',
        'lbl_ink': 'Min. ink coverage (%):',
        'tip_format': ('Minimum sheet format of a page treated as a drawing.\n'
                       'A3 = pages larger than A4 (A3, A2, A1, A0 and their rotations).\n'
                       'A4 = no format filter (all non-empty pages).'),
        'tip_ink': ('Minimum ink coverage of a page (%). 0 = filter off.\n'
                    'Helps to drop nearly blank pages (e.g. dirty scans).'),
        'pages_info': ('A drawing is a page larger than the chosen sheet format; single-page PDFs '
                       'are always converted. Every decision is written to the log.'),
        'status_ready': 'Ready.',
        'tip_pb_file': 'Progress of the current file',
        'tip_pb_total': 'Overall progress',
        'hi_1': 'PDF -> TIFF converter (lossless). Choose the PDF folder and press START.',
        'hi_2': 'Tip: for raster PDFs 200 DPI is the native resolution (1:1, no quality loss).',
        'hi_3': 'TIFF compression: DEFLATE (lossless).',
        'hi_4': ('Multipage PDFs: by default only drawings are saved (pages larger than the chosen '
                 'format), as name_p01.tif, name_p02.tif, ...'),
        'warn_gdal': 'gdal_translate not found:\n%(path)s\n\nPoint to a valid gdal_translate.exe.',
        'warn_in_dir': 'Choose an existing folder with PDF files.',
        'info_no_pdf': 'No *.pdf files found in the folder.',
        'empty_path': '(empty path)',
        'log_start': '=== START ===',
        'log_files': 'Files to convert    : %(count)d',
        'log_in': 'Source folder       : %(path)s',
        'log_out': 'Target folder       : %(path)s',
        'log_dpi': 'DPI / compression   : %(dpi)d / DEFLATE (lossless)',
        'log_pages': 'Pages               : %(mode)s',
        'log_ink': 'Min. ink coverage   : %(ink).1f%%',
        'log_skip': 'Mode                : skipping existing TIFF files',
        'mode_text_all': 'all pages',
        'mode_text_custom': 'selected pages: %(spec)s',
        'mode_text_drawings': 'drawings only (min. sheet %(fmt)s)',
        'all_pages_word': 'all',
        'log_stop_req': 'Stopping...',
        'log_done': '=== DONE: pages ok=%(ok)d, errors=%(fail)d ===',
        'status_done': 'Finished. Pages ok: %(ok)d, errors: %(fail)d.',
        'msg_done': 'Conversion finished.\nPages ok: %(ok)d\nErrors: %(fail)d',
        'choose_in': 'Choose the folder with PDF files',
        'choose_out': 'Choose the output folder for TIFF files',
        'choose_gdal': 'Point to gdal_translate.exe',
        'filter_gdal': 'gdal_translate (gdal_translate.exe);;Programs (*.exe);;All files (*)',
        # --- konwerter
        'err_run_gdal': 'ERROR: cannot start gdal_translate (%(err)s)',
        'err_start_gdal': 'ERROR: cannot start gdal_translate',
        'err_start_gdal_sync': 'Cannot start gdal_translate: %(path)s',
        'err_read_pages': '%(name)s: cannot read pages (%(err)s)',
        'status_analyse': 'Analysing pages [%(i)d/%(n)d] %(name)s',
        'log_file': '[%(i)d/%(n)d] %(name)s  (pages: %(pages)d, to convert: %(todo)d)',
        'log_page_skipped': '        page %(page)d: skipped (%(reason)s)',
        'log_no_pages': '        no pages to convert',
        'err_mkdir': '        ERROR: cannot create folder %(dir)s (%(err)s)',
        'status_page': '[%(i)d/%(n)d] %(name)s  page %(page)d/%(pages)d',
        'log_page': '        page %(page)d -> %(file)s',
        'log_page_exists': '            skipped (TIFF already exists)',
        'log_page_ok': '            OK  (%(size)s px, DPI %(dpi)d, lossless)',
        'log_page_ok_short': '            OK  (DPI %(dpi)d, lossless)',
        'log_page_aborted': '            ABORTED',
        'log_page_error': '            ERROR (code %(rc)d)',
        'reason_too_small': '%(size)s (smaller than %(fmt)s)',
        'reason_ink': '%(size)s, ink %(ink).2f%% (min. %(min).2f%%)',
        'reason_kept': '%(size)s, ink %(ink).2f%%',
        'note_no_big': ('no page is larger than %(fmt)s - converting all pages '
                        '(change "Min. drawing sheet size" to filter)'),
        'note_custom': 'selected pages (%(count)d of %(total)d): %(list)s',
        'sync_pages': '        pages: %(pages)d, to convert: %(todo)d',
        'sync_page_skip': '        page %(page)d -> %(file)s : skipped (file exists)',
        'sync_page_ok': '        page %(page)d -> %(file)s : OK (%(size)s px)',
        'sync_page_ok_short': '        page %(page)d -> %(file)s : OK',
        'sync_page_err': '        page %(page)d -> %(file)s : ERROR (code %(rc)d)',
        # --- algorytm Processing
        'alg_name': 'Convert PDF to TIFF (lossless)',
        'alg_group': 'PDF conversion',
        'alg_help': (
            'Converts *.pdf files from a folder to *.tif with gdal_translate: rendering at the '
            'chosen DPI, lossless DEFLATE compression.\n\n'
            'Multipage PDFs: every page is a separate GDAL subdataset. By default only drawings '
            'are saved (pages larger than the chosen sheet format - A3 means "larger than A4"), '
            'so A4 description pages are skipped. You can also choose all pages or a page list, '
            'e.g. 1,3,5-8.\n\n'
            'File names: single-page PDF -> name.tif, multipage PDF -> name_p01.tif, name_p02.tif, '
            '...\n\n'
            'For raster PDFs (e.g. drawings exported from CAD) 200 DPI is the native resolution '
            '(1:1). Higher DPI only interpolates.\n\n'
            'Command used:\n'
            'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff -co COMPRESS=DEFLATE '
            '-co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER "input.pdf" "output.tif"'
        ),
        'p_input': 'Folder with PDF files',
        'p_output': 'Output folder (TIFF)',
        'p_dpi': 'Rendering DPI (200 = native for raster PDFs)',
        'p_page_mode': 'PDF pages',
        'p_pages': 'Selected pages (e.g. 1,3,5-8; empty = all)',
        'p_min_format': 'Minimum drawing sheet size',
        'p_min_ink': 'Minimum ink coverage in percent (0 = no filter)',
        'p_skip': 'Skip existing TIFF',
        'p_recursive': 'Process subfolders',
        'p_gdal': 'gdal_translate (empty = detect automatically)',
        'opt_mode_drawings': 'drawings only (default)',
        'opt_mode_all': 'all pages',
        'opt_mode_custom': 'selected pages',
        'mode_line': 'Pages mode      : %(mode)s',
        'mode_line_drawings': 'Pages mode      : %(mode)s (min. sheet %(fmt)s, min. ink %(ink).1f%%)',
        'info_gdal': 'gdal_translate : %(path)s',
        'info_in': 'Source folder  : %(path)s',
        'info_out': 'Target folder  : %(path)s',
        'info_dpi': 'DPI / compression: %(dpi)d / DEFLATE (lossless)',
        'info_files': 'Files to convert: %(count)d',
        'info_cancel': 'Cancelled by the user.',
        'info_mkdir': 'Cannot create folder %(dir)s (%(err)s)',
        'info_done': '=== DONE: pages ok=%(ok)d, errors=%(fail)d, skipped=%(skip)d ===',
        'exc_no_gdal': 'gdal_translate not found: %(path)s',
        'exc_no_in': 'Source folder does not exist: %(path)s',
        'exc_no_out': 'Choose the output folder.',
        'exc_no_pdf': 'No *.pdf files found in the folder.',
        # --- wtyczka
        'menu': '&PDF -> TIFF',
        'plugin_tip': 'PDF2TIFF - lossless PDF to TIFF converter (GDAL)',
    },
    'pl': {
        'title': 'Konwerter PDF -> TIFF  (bezstratny, GDAL)',
        'lbl_in': 'Katalog PDF:',
        'lbl_out': 'Katalog TIFF:',
        'lbl_gdal': 'gdal_translate:',
        'ph_out': 'puste = zapis obok plików PDF',
        'browse': 'Wybierz...',
        'dpi': 'DPI:',
        'start': 'START',
        'stop': 'STOP',
        'skip': 'Pomijaj istniejące TIFF',
        'subfolders': 'Podkatalogi',
        'pages_group': 'Strony PDF',
        'mode_drawings': 'Tylko rysunki (domyślnie)',
        'mode_all': 'Wszystkie strony',
        'mode_custom': 'Wskazane strony:',
        'tip_mode_drawings': ('Zapisuje strony większe niż wybrany format. W typowych PDF-ach\n'
                              '(opisówka A4 + rysunki A3/A2/A1/A0) zostają same rysunki.'),
        'ph_pages': 'np. 1,3,5-8   (puste = wszystkie strony)',
        'lbl_format': 'Min. format rysunku:',
        'lbl_ink': 'Min. pokrycie tuszem (%):',
        'tip_format': ('Minimalny format strony uznawanej za rysunek.\n'
                       'A3 = strony większe niż A4 (A3, A2, A1, A0 oraz ich obroty).\n'
                       'A4 = bez filtra formatu (wszystkie strony niepuste).'),
        'tip_ink': ('Minimalne pokrycie strony tuszem (%). 0 = filtr wyłączony.\n'
                    'Pomaga odrzucić strony puste (np. skany z plamami).'),
        'pages_info': ('Rysunek = strona większa niż wybrany format; PDF jednostronicowe są zawsze '
                       'konwertowane. Każda decyzja jest zapisywana w logu.'),
        'status_ready': 'Gotowy.',
        'tip_pb_file': 'Postęp bieżącego pliku',
        'tip_pb_total': 'Postęp całej konwersji',
        'hi_1': 'Konwerter PDF -> TIFF (bezstratny). Wskaż katalog z PDF i naciśnij START.',
        'hi_2': 'Wskazówka: dla PDF rastrowych 200 DPI = natywna rozdzielczość (1:1, bez utraty jakości).',
        'hi_3': 'Kompresja TIFF: DEFLATE (bezstratna).',
        'hi_4': ('PDF wielostronicowe: domyślnie zapisywane są tylko rysunki (strony większe niż '
                 'wybrany format), jako nazwa_p01.tif, nazwa_p02.tif, ...'),
        'warn_gdal': ('Nie znaleziono gdal_translate:\n%(path)s\n\n'
                      'Wskaż poprawną ścieżkę do gdal_translate.exe.'),
        'warn_in_dir': 'Wybierz istniejący katalog z plikami PDF.',
        'info_no_pdf': 'W katalogu nie znaleziono plików *.pdf.',
        'empty_path': '(pusta ścieżka)',
        'log_start': '=== START ===',
        'log_files': 'Plików do konwersji : %(count)d',
        'log_in': 'Katalog źródłowy    : %(path)s',
        'log_out': 'Katalog docelowy    : %(path)s',
        'log_dpi': 'DPI / kompresja     : %(dpi)d / DEFLATE (bezstratna)',
        'log_pages': 'Strony              : %(mode)s',
        'log_ink': 'Min. pokrycie tuszem: %(ink).1f%%',
        'log_skip': 'Tryb                : pomijanie istniejących TIFF',
        'mode_text_all': 'wszystkie strony',
        'mode_text_custom': 'wskazane strony: %(spec)s',
        'mode_text_drawings': 'tylko rysunki (min. format %(fmt)s)',
        'all_pages_word': 'wszystkie',
        'log_stop_req': 'Żądanie zatrzymania...',
        'log_done': '=== KONIEC: udane strony=%(ok)d, błędy=%(fail)d ===',
        'status_done': 'Zakończono. Udane strony: %(ok)d, błędy: %(fail)d.',
        'msg_done': 'Konwersja zakończona.\nUdane strony: %(ok)d\nBłędy: %(fail)d',
        'choose_in': 'Wybierz katalog z plikami PDF',
        'choose_out': 'Wybierz katalog docelowy na pliki TIFF',
        'choose_gdal': 'Wskaż program gdal_translate.exe',
        'filter_gdal': 'gdal_translate (gdal_translate.exe);;Programy (*.exe);;Wszystkie pliki (*)',
        'err_run_gdal': 'BŁĄD: nie można uruchomić gdal_translate (%(err)s)',
        'err_start_gdal': 'BŁĄD: nie można uruchomić gdal_translate',
        'err_start_gdal_sync': 'Nie można uruchomić gdal_translate: %(path)s',
        'err_read_pages': '%(name)s: nie można odczytać stron (%(err)s)',
        'status_analyse': 'Analiza stron [%(i)d/%(n)d] %(name)s',
        'log_file': '[%(i)d/%(n)d] %(name)s  (stron: %(pages)d, do konwersji: %(todo)d)',
        'log_page_skipped': '        str. %(page)d: pominięta (%(reason)s)',
        'log_no_pages': '        brak stron do konwersji',
        'err_mkdir': '        BŁĄD: nie można utworzyć katalogu %(dir)s (%(err)s)',
        'status_page': '[%(i)d/%(n)d] %(name)s  str. %(page)d/%(pages)d',
        'log_page': '        str. %(page)d -> %(file)s',
        'log_page_exists': '            pominięto (plik TIFF już istnieje)',
        'log_page_ok': '            OK  (%(size)s px, DPI %(dpi)d, bezstratnie)',
        'log_page_ok_short': '            OK  (DPI %(dpi)d, bezstratnie)',
        'log_page_aborted': '            PRZERWANO',
        'log_page_error': '            BŁĄD (kod %(rc)d)',
        'reason_too_small': '%(size)s (mniejsza niż %(fmt)s)',
        'reason_ink': '%(size)s, tusz %(ink).2f%% (min. %(min).2f%%)',
        'reason_kept': '%(size)s, tusz %(ink).2f%%',
        'note_no_big': ('żadna strona nie jest większa niż %(fmt)s - konwertuję wszystkie strony '
                        '(zmień "Min. format rysunku", aby filtrować)'),
        'note_custom': 'wybrane strony (%(count)d z %(total)d): %(list)s',
        'sync_pages': '        stron: %(pages)d, do konwersji: %(todo)d',
        'sync_page_skip': '        str. %(page)d -> %(file)s : pominięto (plik istnieje)',
        'sync_page_ok': '        str. %(page)d -> %(file)s : OK (%(size)s px)',
        'sync_page_ok_short': '        str. %(page)d -> %(file)s : OK',
        'sync_page_err': '        str. %(page)d -> %(file)s : BŁĄD (kod %(rc)d)',
        'alg_name': 'Konwertuj PDF do TIFF (bezstratnie)',
        'alg_group': 'Konwersja PDF',
        'alg_help': (
            'Konwertuje pliki *.pdf z katalogu do plików *.tif przy pomocy gdal_translate: '
            'renderowanie w zadanym DPI i kompresja bezstratna DEFLATE.\n\n'
            'PDF wielostronicowe: każda strona to osobny podzbiór GDAL. Domyślnie zapisywane są '
            'tylko rysunki (strony większe niż wybrany format - A3 oznacza "większe niż A4"), '
            'opisówki A4 są pomijane. Można też wybrać wszystkie strony albo listę stron, '
            'np. 1,3,5-8.\n\n'
            'Nazwy plików: PDF jednostronicowy -> nazwa.tif, wielostronicowy -> nazwa_p01.tif, '
            'nazwa_p02.tif, ...\n\n'
            'Dla PDF rastrowych (np. rysunki z CAD) 200 DPI = natywna rozdzielczość (1:1). '
            'Wyższe DPI to już interpolacja.\n\n'
            'Wywoływana komenda:\n'
            'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff -co COMPRESS=DEFLATE '
            '-co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER "wejście.pdf" "wyjście.tif"'
        ),
        'p_input': 'Katalog z plikami PDF',
        'p_output': 'Katalog wynikowy (TIFF)',
        'p_dpi': 'DPI renderowania (200 = natywne dla PDF rastrowych)',
        'p_page_mode': 'Strony PDF',
        'p_pages': 'Wskazane strony (np. 1,3,5-8; puste = wszystkie)',
        'p_min_format': 'Minimalny format rysunku',
        'p_min_ink': 'Minimalne pokrycie tuszem w procentach (0 = bez filtra)',
        'p_skip': 'Pomijaj istniejące TIFF',
        'p_recursive': 'Przetwarzaj podkatalogi',
        'p_gdal': 'gdal_translate (puste = wykryj automatycznie)',
        'opt_mode_drawings': 'tylko rysunki (domyślnie)',
        'opt_mode_all': 'wszystkie strony',
        'opt_mode_custom': 'wskazane strony',
        'mode_line': 'Tryb stron      : %(mode)s',
        'mode_line_drawings': 'Tryb stron      : %(mode)s (min. format %(fmt)s, min. tusz %(ink).1f%%)',
        'info_gdal': 'gdal_translate : %(path)s',
        'info_in': 'Katalog źródłowy: %(path)s',
        'info_out': 'Katalog docelowy: %(path)s',
        'info_dpi': 'DPI / kompresja : %(dpi)d / DEFLATE (bezstratna)',
        'info_files': 'Plików do konwersji: %(count)d',
        'info_cancel': 'Przerwano na żądanie użytkownika.',
        'info_mkdir': 'Nie można utworzyć katalogu %(dir)s (%(err)s)',
        'info_done': '=== KONIEC: udane strony=%(ok)d, błędy=%(fail)d, pominięte=%(skip)d ===',
        'exc_no_gdal': 'Nie znaleziono gdal_translate: %(path)s',
        'exc_no_in': 'Katalog źródłowy nie istnieje: %(path)s',
        'exc_no_out': 'Wskaż katalog wynikowy.',
        'exc_no_pdf': 'W katalogu nie znaleziono plików *.pdf.',
        'menu': '&PDF -> TIFF',
        'plugin_tip': 'PDF2TIFF - konwerter PDF do TIFF (bezstratny, GDAL)',
    },
    'fr': {
        'title': 'Convertisseur PDF -> TIFF  (sans perte, GDAL)',
        'lbl_in': 'Dossier PDF :',
        'lbl_out': 'Dossier TIFF :',
        'lbl_gdal': 'gdal_translate :',
        'ph_out': 'vide = enregistrer à côté des PDF',
        'browse': 'Parcourir...',
        'dpi': 'DPI :',
        'start': 'DÉMARRER',
        'stop': 'ARRÊTER',
        'skip': 'Ignorer les TIFF existants',
        'subfolders': 'Sous-dossiers',
        'pages_group': 'Pages du PDF',
        'mode_drawings': 'Dessins seulement (par défaut)',
        'mode_all': 'Toutes les pages',
        'mode_custom': 'Pages choisies :',
        'tip_mode_drawings': ('Enregistre les pages plus grandes que le format choisi. Dans un PDF '
                              'typique (A4 descriptif + dessins A3/A2/A1/A0), seuls les dessins restent.'),
        'ph_pages': 'p. ex. 1,3,5-8   (vide = toutes les pages)',
        'lbl_format': 'Format minimal du dessin :',
        'lbl_ink': 'Couverture d\'encre min. (%) :',
        'tip_format': ('Format minimal d\'une page considérée comme un dessin.\n'
                       'A3 = pages plus grandes que A4 (A3, A2, A1, A0 et leurs rotations).\n'
                       'A4 = aucun filtre de format.'),
        'tip_ink': ('Couverture d\'encre minimale de la page (%). 0 = filtre désactivé.\n'
                    'Élimine les pages presque vides.'),
        'pages_info': ('Un dessin = page plus grande que le format choisi ; les PDF d\'une page sont '
                       'toujours convertis. Chaque décision est écrite dans le journal.'),
        'status_ready': 'Prêt.',
        'tip_pb_file': 'Progression du fichier courant',
        'tip_pb_total': 'Progression globale',
        'hi_1': 'Convertisseur PDF -> TIFF (sans perte). Choisissez le dossier PDF et cliquez sur START.',
        'hi_2': 'Astuce : pour les PDF raster, 200 DPI = résolution native (1:1, sans perte).',
        'hi_3': 'Compression TIFF : DEFLATE (sans perte).',
        'hi_4': ('PDF multipages : par défaut seuls les dessins sont enregistrés (pages plus grandes '
                 'que le format choisi), sous les noms nom_p01.tif, nom_p02.tif, ...'),
        'warn_gdal': 'gdal_translate introuvable :\n%(path)s\n\nIndiquez le chemin de gdal_translate.exe.',
        'warn_in_dir': 'Choisissez un dossier existant contenant des PDF.',
        'info_no_pdf': 'Aucun fichier *.pdf dans le dossier.',
        'empty_path': '(chemin vide)',
        'log_start': '=== DÉBUT ===',
        'log_files': 'Fichiers à convertir : %(count)d',
        'log_in': 'Dossier source      : %(path)s',
        'log_out': 'Dossier cible       : %(path)s',
        'log_dpi': 'DPI / compression   : %(dpi)d / DEFLATE (sans perte)',
        'log_pages': 'Pages               : %(mode)s',
        'log_ink': 'Encre min.          : %(ink).1f%%',
        'log_skip': 'Mode                : ignorer les TIFF existants',
        'mode_text_all': 'toutes les pages',
        'mode_text_custom': 'pages choisies : %(spec)s',
        'mode_text_drawings': 'dessins seulement (format min. %(fmt)s)',
        'all_pages_word': 'toutes',
        'log_stop_req': 'Arrêt demandé...',
        'log_done': '=== FIN : pages ok=%(ok)d, erreurs=%(fail)d ===',
        'status_done': 'Terminé. Pages ok : %(ok)d, erreurs : %(fail)d.',
        'msg_done': 'Conversion terminée.\nPages ok : %(ok)d\nErreurs : %(fail)d',
        'choose_in': 'Choisir le dossier contenant les PDF',
        'choose_out': 'Choisir le dossier de sortie des TIFF',
        'choose_gdal': 'Indiquer gdal_translate.exe',
        'filter_gdal': 'gdal_translate (gdal_translate.exe);;Programmes (*.exe);;Tous les fichiers (*)',
        'err_run_gdal': 'ERREUR : impossible de lancer gdal_translate (%(err)s)',
        'err_start_gdal': 'ERREUR : impossible de lancer gdal_translate',
        'err_start_gdal_sync': 'Impossible de lancer gdal_translate : %(path)s',
        'err_read_pages': '%(name)s : impossible de lire les pages (%(err)s)',
        'status_analyse': 'Analyse des pages [%(i)d/%(n)d] %(name)s',
        'log_file': '[%(i)d/%(n)d] %(name)s  (pages : %(pages)d, à convertir : %(todo)d)',
        'log_page_skipped': '        page %(page)d : ignorée (%(reason)s)',
        'log_no_pages': '        aucune page à convertir',
        'err_mkdir': '        ERREUR : impossible de créer le dossier %(dir)s (%(err)s)',
        'status_page': '[%(i)d/%(n)d] %(name)s  page %(page)d/%(pages)d',
        'log_page': '        page %(page)d -> %(file)s',
        'log_page_exists': '            ignoré (le TIFF existe déjà)',
        'log_page_ok': '            OK  (%(size)s px, DPI %(dpi)d, sans perte)',
        'log_page_ok_short': '            OK  (DPI %(dpi)d, sans perte)',
        'log_page_aborted': '            INTERROMPU',
        'log_page_error': '            ERREUR (code %(rc)d)',
        'reason_too_small': '%(size)s (plus petite que %(fmt)s)',
        'reason_ink': '%(size)s, encre %(ink).2f%% (min. %(min).2f%%)',
        'reason_kept': '%(size)s, encre %(ink).2f%%',
        'note_no_big': ('aucune page n\'est plus grande que %(fmt)s - conversion de toutes les pages '
                        '(modifiez "Format minimal du dessin" pour filtrer)'),
        'note_custom': 'pages choisies (%(count)d sur %(total)d) : %(list)s',
        'sync_pages': '        pages : %(pages)d, à convertir : %(todo)d',
        'sync_page_skip': '        page %(page)d -> %(file)s : ignoré (fichier existant)',
        'sync_page_ok': '        page %(page)d -> %(file)s : OK (%(size)s px)',
        'sync_page_ok_short': '        page %(page)d -> %(file)s : OK',
        'sync_page_err': '        page %(page)d -> %(file)s : ERREUR (code %(rc)d)',
        'alg_name': 'Convertir PDF en TIFF (sans perte)',
        'alg_group': 'Conversion PDF',
        'alg_help': (
            'Convertit les fichiers *.pdf d\'un dossier en *.tif avec gdal_translate : rendu au DPI '
            'choisi, compression DEFLATE sans perte.\n\n'
            'PDF multipages : chaque page est un sous-jeu GDAL. Par défaut seuls les dessins sont '
            'enregistrés (pages plus grandes que le format choisi - A3 = "plus grand que A4").\n\n'
            'Noms : PDF d\'une page -> nom.tif, PDF multipages -> nom_p01.tif, nom_p02.tif, ...\n\n'
            'Commande utilisée :\n'
            'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff -co COMPRESS=DEFLATE '
            '-co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER "entree.pdf" "sortie.tif"'
        ),
        'p_input': 'Dossier contenant les PDF',
        'p_output': 'Dossier de sortie (TIFF)',
        'p_dpi': 'DPI de rendu (200 = natif pour les PDF raster)',
        'p_page_mode': 'Pages du PDF',
        'p_pages': 'Pages choisies (p. ex. 1,3,5-8 ; vide = toutes)',
        'p_min_format': 'Format minimal du dessin',
        'p_min_ink': 'Couverture d\'encre minimale en pour cent (0 = pas de filtre)',
        'p_skip': 'Ignorer les TIFF existants',
        'p_recursive': 'Traiter les sous-dossiers',
        'p_gdal': 'gdal_translate (vide = détection automatique)',
        'opt_mode_drawings': 'dessins seulement (par défaut)',
        'opt_mode_all': 'toutes les pages',
        'opt_mode_custom': 'pages choisies',
        'mode_line': 'Mode des pages  : %(mode)s',
        'mode_line_drawings': 'Mode des pages  : %(mode)s (format min. %(fmt)s, encre min. %(ink).1f%%)',
        'info_gdal': 'gdal_translate : %(path)s',
        'info_in': 'Dossier source  : %(path)s',
        'info_out': 'Dossier cible   : %(path)s',
        'info_dpi': 'DPI / compression : %(dpi)d / DEFLATE (sans perte)',
        'info_files': 'Fichiers à convertir : %(count)d',
        'info_cancel': 'Interrompu par l\'utilisateur.',
        'info_mkdir': 'Impossible de créer le dossier %(dir)s (%(err)s)',
        'info_done': '=== FIN : pages ok=%(ok)d, erreurs=%(fail)d, ignorées=%(skip)d ===',
        'exc_no_gdal': 'gdal_translate introuvable : %(path)s',
        'exc_no_in': 'Le dossier source n\'existe pas : %(path)s',
        'exc_no_out': 'Indiquez le dossier de sortie.',
        'exc_no_pdf': 'Aucun fichier *.pdf dans le dossier.',
        'menu': '&PDF -> TIFF',
        'plugin_tip': 'PDF2TIFF - convertisseur PDF vers TIFF sans perte (GDAL)',
    },
    'de': {
        'title': 'PDF -> TIFF Konverter  (verlustfrei, GDAL)',
        'lbl_in': 'PDF-Ordner:',
        'lbl_out': 'TIFF-Ordner:',
        'lbl_gdal': 'gdal_translate:',
        'ph_out': 'leer = neben den PDF-Dateien speichern',
        'browse': 'Auswählen...',
        'dpi': 'DPI:',
        'start': 'START',
        'stop': 'STOPP',
        'skip': 'Vorhandene TIFF überspringen',
        'subfolders': 'Unterordner',
        'pages_group': 'PDF-Seiten',
        'mode_drawings': 'Nur Zeichnungen (Standard)',
        'mode_all': 'Alle Seiten',
        'mode_custom': 'Ausgewählte Seiten:',
        'tip_mode_drawings': ('Speichert Seiten, die größer als das gewählte Format sind. In typischen '
                              'PDFs (A4-Beschreibung + A3/A2/A1/A0-Zeichnungen) bleiben nur Zeichnungen.'),
        'ph_pages': 'z. B. 1,3,5-8   (leer = alle Seiten)',
        'lbl_format': 'Min. Zeichnungsformat:',
        'lbl_ink': 'Min. Tintenabdeckung (%):',
        'tip_format': ('Minimales Format einer Seite, die als Zeichnung gilt.\n'
                       'A3 = größer als A4 (A3, A2, A1, A0 und deren Drehungen).\n'
                       'A4 = kein Formatfilter.'),
        'tip_ink': ('Minimale Tintenabdeckung der Seite (%). 0 = Filter aus.\n'
                    'Entfernt fast leere Seiten.'),
        'pages_info': ('Zeichnung = Seite größer als das gewählte Format; einseitige PDFs werden '
                       'immer konvertiert. Jede Entscheidung steht im Protokoll.'),
        'status_ready': 'Bereit.',
        'tip_pb_file': 'Fortschritt der aktuellen Datei',
        'tip_pb_total': 'Gesamtfortschritt',
        'hi_1': 'PDF -> TIFF Konverter (verlustfrei). PDF-Ordner wählen und START drücken.',
        'hi_2': 'Tipp: bei Raster-PDFs ist 200 DPI die native Auflösung (1:1, ohne Qualitätsverlust).',
        'hi_3': 'TIFF-Komprimierung: DEFLATE (verlustfrei).',
        'hi_4': ('Mehrseitige PDFs: standardmäßig werden nur Zeichnungen gespeichert (Seiten größer als '
                 'das gewählte Format), als name_p01.tif, name_p02.tif, ...'),
        'warn_gdal': 'gdal_translate nicht gefunden:\n%(path)s\n\nBitte den Pfad zu gdal_translate.exe angeben.',
        'warn_in_dir': 'Bitte einen vorhandenen Ordner mit PDF-Dateien wählen.',
        'info_no_pdf': 'Keine *.pdf-Dateien im Ordner gefunden.',
        'empty_path': '(leerer Pfad)',
        'log_start': '=== START ===',
        'log_files': 'Zu konvertieren    : %(count)d',
        'log_in': 'Quellordner        : %(path)s',
        'log_out': 'Zielordner         : %(path)s',
        'log_dpi': 'DPI / Kompression   : %(dpi)d / DEFLATE (verlustfrei)',
        'log_pages': 'Seiten             : %(mode)s',
        'log_ink': 'Min. Tinte         : %(ink).1f%%',
        'log_skip': 'Modus              : vorhandene TIFF überspringen',
        'mode_text_all': 'alle Seiten',
        'mode_text_custom': 'ausgewählte Seiten: %(spec)s',
        'mode_text_drawings': 'nur Zeichnungen (min. Format %(fmt)s)',
        'all_pages_word': 'alle',
        'log_stop_req': 'Abbruch angefordert...',
        'log_done': '=== ENDE: Seiten ok=%(ok)d, Fehler=%(fail)d ===',
        'status_done': 'Fertig. Seiten ok: %(ok)d, Fehler: %(fail)d.',
        'msg_done': 'Konvertierung beendet.\nSeiten ok: %(ok)d\nFehler: %(fail)d',
        'choose_in': 'Ordner mit PDF-Dateien wählen',
        'choose_out': 'Zielordner für TIFF-Dateien wählen',
        'choose_gdal': 'gdal_translate.exe auswählen',
        'filter_gdal': 'gdal_translate (gdal_translate.exe);;Programme (*.exe);;Alle Dateien (*)',
        'err_run_gdal': 'FEHLER: gdal_translate kann nicht gestartet werden (%(err)s)',
        'err_start_gdal': 'FEHLER: gdal_translate kann nicht gestartet werden',
        'err_start_gdal_sync': 'gdal_translate kann nicht gestartet werden: %(path)s',
        'err_read_pages': '%(name)s: Seiten können nicht gelesen werden (%(err)s)',
        'status_analyse': 'Seitenanalyse [%(i)d/%(n)d] %(name)s',
        'log_file': '[%(i)d/%(n)d] %(name)s  (Seiten: %(pages)d, zu konvertieren: %(todo)d)',
        'log_page_skipped': '        Seite %(page)d: übersprungen (%(reason)s)',
        'log_no_pages': '        keine Seiten zu konvertieren',
        'err_mkdir': '        FEHLER: Ordner %(dir)s kann nicht erstellt werden (%(err)s)',
        'status_page': '[%(i)d/%(n)d] %(name)s  Seite %(page)d/%(pages)d',
        'log_page': '        Seite %(page)d -> %(file)s',
        'log_page_exists': '            übersprungen (TIFF existiert bereits)',
        'log_page_ok': '            OK  (%(size)s px, DPI %(dpi)d, verlustfrei)',
        'log_page_ok_short': '            OK  (DPI %(dpi)d, verlustfrei)',
        'log_page_aborted': '            ABGEBROCHEN',
        'log_page_error': '            FEHLER (Code %(rc)d)',
        'reason_too_small': '%(size)s (kleiner als %(fmt)s)',
        'reason_ink': '%(size)s, Tinte %(ink).2f%% (min. %(min).2f%%)',
        'reason_kept': '%(size)s, Tinte %(ink).2f%%',
        'note_no_big': ('keine Seite ist größer als %(fmt)s - alle Seiten werden konvertiert '
                        '("Min. Zeichnungsformat" ändern, um zu filtern)'),
        'note_custom': 'ausgewählte Seiten (%(count)d von %(total)d): %(list)s',
        'sync_pages': '        Seiten: %(pages)d, zu konvertieren: %(todo)d',
        'sync_page_skip': '        Seite %(page)d -> %(file)s : übersprungen (Datei existiert)',
        'sync_page_ok': '        Seite %(page)d -> %(file)s : OK (%(size)s px)',
        'sync_page_ok_short': '        Seite %(page)d -> %(file)s : OK',
        'sync_page_err': '        Seite %(page)d -> %(file)s : FEHLER (Code %(rc)d)',
        'alg_name': 'PDF in TIFF konvertieren (verlustfrei)',
        'alg_group': 'PDF-Konvertierung',
        'alg_help': (
            'Konvertiert *.pdf-Dateien eines Ordners mit gdal_translate in *.tif: Rendern mit dem '
            'gewählten DPI, verlustfreie DEFLATE-Kompression.\n\n'
            'Mehrseitige PDFs: jede Seite ist ein eigenes GDAL-Subdataset. Standardmäßig werden nur '
            'Zeichnungen gespeichert (Seiten größer als das gewählte Format - A3 = "größer als A4").\n\n'
            'Dateinamen: einseitiges PDF -> name.tif, mehrseitig -> name_p01.tif, name_p02.tif, ...\n\n'
            'Verwendeter Befehl:\n'
            'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff -co COMPRESS=DEFLATE '
            '-co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER "eingabe.pdf" "ausgabe.tif"'
        ),
        'p_input': 'Ordner mit PDF-Dateien',
        'p_output': 'Zielordner (TIFF)',
        'p_dpi': 'Render-DPI (200 = nativ für Raster-PDFs)',
        'p_page_mode': 'PDF-Seiten',
        'p_pages': 'Ausgewählte Seiten (z. B. 1,3,5-8; leer = alle)',
        'p_min_format': 'Minimales Zeichnungsformat',
        'p_min_ink': 'Minimale Tintenabdeckung in Prozent (0 = kein Filter)',
        'p_skip': 'Vorhandene TIFF überspringen',
        'p_recursive': 'Unterordner verarbeiten',
        'p_gdal': 'gdal_translate (leer = automatisch erkennen)',
        'opt_mode_drawings': 'nur Zeichnungen (Standard)',
        'opt_mode_all': 'alle Seiten',
        'opt_mode_custom': 'ausgewählte Seiten',
        'mode_line': 'Seitenmodus     : %(mode)s',
        'mode_line_drawings': 'Seitenmodus     : %(mode)s (min. Format %(fmt)s, min. Tinte %(ink).1f%%)',
        'info_gdal': 'gdal_translate : %(path)s',
        'info_in': 'Quellordner    : %(path)s',
        'info_out': 'Zielordner     : %(path)s',
        'info_dpi': 'DPI / Kompression: %(dpi)d / DEFLATE (verlustfrei)',
        'info_files': 'Zu konvertieren: %(count)d',
        'info_cancel': 'Vom Benutzer abgebrochen.',
        'info_mkdir': 'Ordner %(dir)s kann nicht erstellt werden (%(err)s)',
        'info_done': '=== ENDE: Seiten ok=%(ok)d, Fehler=%(fail)d, übersprungen=%(skip)d ===',
        'exc_no_gdal': 'gdal_translate nicht gefunden: %(path)s',
        'exc_no_in': 'Quellordner existiert nicht: %(path)s',
        'exc_no_out': 'Bitte den Zielordner angeben.',
        'exc_no_pdf': 'Keine *.pdf-Dateien im Ordner gefunden.',
        'menu': '&PDF -> TIFF',
        'plugin_tip': 'PDF2TIFF - verlustfreier PDF-zu-TIFF-Konverter (GDAL)',
    },
    'es': {
        'title': 'Convertidor PDF -> TIFF  (sin pérdida, GDAL)',
        'lbl_in': 'Carpeta PDF:',
        'lbl_out': 'Carpeta TIFF:',
        'lbl_gdal': 'gdal_translate:',
        'ph_out': 'vacío = guardar junto a los PDF',
        'browse': 'Examinar...',
        'dpi': 'DPI:',
        'start': 'INICIAR',
        'stop': 'DETENER',
        'skip': 'Omitir TIFF existentes',
        'subfolders': 'Subcarpetas',
        'pages_group': 'Páginas del PDF',
        'mode_drawings': 'Solo planos (por defecto)',
        'mode_all': 'Todas las páginas',
        'mode_custom': 'Páginas indicadas:',
        'tip_mode_drawings': ('Guarda las páginas mayores que el formato elegido. En un PDF típico '
                              '(A4 descriptivo + planos A3/A2/A1/A0) solo quedan los planos.'),
        'ph_pages': 'p. ej. 1,3,5-8   (vacío = todas las páginas)',
        'lbl_format': 'Formato mínimo del plano:',
        'lbl_ink': 'Cobertura mínima de tinta (%):',
        'tip_format': ('Formato mínimo de una página considerada plano.\n'
                       'A3 = páginas mayores que A4 (A3, A2, A1, A0 y sus giros).\n'
                       'A4 = sin filtro de formato.'),
        'tip_ink': ('Cobertura mínima de tinta de la página (%). 0 = filtro desactivado.\n'
                    'Descarta páginas casi vacías.'),
        'pages_info': ('Plano = página mayor que el formato elegido; los PDF de una página se '
                       'convierten siempre. Cada decisión se escribe en el registro.'),
        'status_ready': 'Listo.',
        'tip_pb_file': 'Progreso del archivo actual',
        'tip_pb_total': 'Progreso total',
        'hi_1': 'Convertidor PDF -> TIFF (sin pérdida). Elija la carpeta PDF y pulse START.',
        'hi_2': 'Consejo: en PDF raster 200 DPI es la resolución nativa (1:1, sin pérdida).',
        'hi_3': 'Compresión TIFF: DEFLATE (sin pérdida).',
        'hi_4': ('PDF de varias páginas: por defecto se guardan solo los planos (páginas mayores que '
                 'el formato elegido), como nombre_p01.tif, nombre_p02.tif, ...'),
        'warn_gdal': 'No se encontró gdal_translate:\n%(path)s\n\nIndique la ruta de gdal_translate.exe.',
        'warn_in_dir': 'Elija una carpeta existente con archivos PDF.',
        'info_no_pdf': 'No se encontraron archivos *.pdf en la carpeta.',
        'empty_path': '(ruta vacía)',
        'log_start': '=== INICIO ===',
        'log_files': 'Archivos a convertir: %(count)d',
        'log_in': 'Carpeta origen      : %(path)s',
        'log_out': 'Carpeta destino     : %(path)s',
        'log_dpi': 'DPI / compresión    : %(dpi)d / DEFLATE (sin pérdida)',
        'log_pages': 'Páginas             : %(mode)s',
        'log_ink': 'Tinta mínima        : %(ink).1f%%',
        'log_skip': 'Modo                : omitir TIFF existentes',
        'mode_text_all': 'todas las páginas',
        'mode_text_custom': 'páginas indicadas: %(spec)s',
        'mode_text_drawings': 'solo planos (formato mín. %(fmt)s)',
        'all_pages_word': 'todas',
        'log_stop_req': 'Solicitando parada...',
        'log_done': '=== FIN: páginas ok=%(ok)d, errores=%(fail)d ===',
        'status_done': 'Terminado. Páginas ok: %(ok)d, errores: %(fail)d.',
        'msg_done': 'Conversión terminada.\nPáginas ok: %(ok)d\nErrores: %(fail)d',
        'choose_in': 'Elija la carpeta con archivos PDF',
        'choose_out': 'Elija la carpeta de salida para los TIFF',
        'choose_gdal': 'Indique gdal_translate.exe',
        'filter_gdal': 'gdal_translate (gdal_translate.exe);;Programas (*.exe);;Todos los archivos (*)',
        'err_run_gdal': 'ERROR: no se puede iniciar gdal_translate (%(err)s)',
        'err_start_gdal': 'ERROR: no se puede iniciar gdal_translate',
        'err_start_gdal_sync': 'No se puede iniciar gdal_translate: %(path)s',
        'err_read_pages': '%(name)s: no se pueden leer las páginas (%(err)s)',
        'status_analyse': 'Analizando páginas [%(i)d/%(n)d] %(name)s',
        'log_file': '[%(i)d/%(n)d] %(name)s  (páginas: %(pages)d, a convertir: %(todo)d)',
        'log_page_skipped': '        página %(page)d: omitida (%(reason)s)',
        'log_no_pages': '        no hay páginas para convertir',
        'err_mkdir': '        ERROR: no se puede crear la carpeta %(dir)s (%(err)s)',
        'status_page': '[%(i)d/%(n)d] %(name)s  página %(page)d/%(pages)d',
        'log_page': '        página %(page)d -> %(file)s',
        'log_page_exists': '            omitido (el TIFF ya existe)',
        'log_page_ok': '            OK  (%(size)s px, DPI %(dpi)d, sin pérdida)',
        'log_page_ok_short': '            OK  (DPI %(dpi)d, sin pérdida)',
        'log_page_aborted': '            INTERRUMPIDO',
        'log_page_error': '            ERROR (código %(rc)d)',
        'reason_too_small': '%(size)s (menor que %(fmt)s)',
        'reason_ink': '%(size)s, tinta %(ink).2f%% (mín. %(min).2f%%)',
        'reason_kept': '%(size)s, tinta %(ink).2f%%',
        'note_no_big': ('ninguna página es mayor que %(fmt)s - se convierten todas las páginas '
                        '(cambie "Formato mínimo del plano" para filtrar)'),
        'note_custom': 'páginas indicadas (%(count)d de %(total)d): %(list)s',
        'sync_pages': '        páginas: %(pages)d, a convertir: %(todo)d',
        'sync_page_skip': '        página %(page)d -> %(file)s : omitido (el archivo existe)',
        'sync_page_ok': '        página %(page)d -> %(file)s : OK (%(size)s px)',
        'sync_page_ok_short': '        página %(page)d -> %(file)s : OK',
        'sync_page_err': '        página %(page)d -> %(file)s : ERROR (código %(rc)d)',
        'alg_name': 'Convertir PDF a TIFF (sin pérdida)',
        'alg_group': 'Conversión de PDF',
        'alg_help': (
            'Convierte los archivos *.pdf de una carpeta a *.tif con gdal_translate: renderizado al '
            'DPI elegido y compresión DEFLATE sin pérdida.\n\n'
            'PDF de varias páginas: cada página es un subconjunto GDAL. Por defecto solo se guardan '
            'los planos (páginas mayores que el formato elegido - A3 = "mayor que A4").\n\n'
            'Nombres: PDF de una página -> nombre.tif, varias páginas -> nombre_p01.tif, '
            'nombre_p02.tif, ...\n\n'
            'Comando utilizado:\n'
            'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff -co COMPRESS=DEFLATE '
            '-co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER "entrada.pdf" "salida.tif"'
        ),
        'p_input': 'Carpeta con archivos PDF',
        'p_output': 'Carpeta de salida (TIFF)',
        'p_dpi': 'DPI de renderizado (200 = nativo para PDF raster)',
        'p_page_mode': 'Páginas del PDF',
        'p_pages': 'Páginas indicadas (p. ej. 1,3,5-8; vacío = todas)',
        'p_min_format': 'Formato mínimo del plano',
        'p_min_ink': 'Cobertura mínima de tinta en porcentaje (0 = sin filtro)',
        'p_skip': 'Omitir TIFF existentes',
        'p_recursive': 'Procesar subcarpetas',
        'p_gdal': 'gdal_translate (vacío = detectar automáticamente)',
        'opt_mode_drawings': 'solo planos (por defecto)',
        'opt_mode_all': 'todas las páginas',
        'opt_mode_custom': 'páginas indicadas',
        'mode_line': 'Modo de páginas: %(mode)s',
        'mode_line_drawings': 'Modo de páginas: %(mode)s (formato mín. %(fmt)s, tinta mín. %(ink).1f%%)',
        'info_gdal': 'gdal_translate : %(path)s',
        'info_in': 'Carpeta origen : %(path)s',
        'info_out': 'Carpeta destino: %(path)s',
        'info_dpi': 'DPI / compresión: %(dpi)d / DEFLATE (sin pérdida)',
        'info_files': 'Archivos a convertir: %(count)d',
        'info_cancel': 'Cancelado por el usuario.',
        'info_mkdir': 'No se puede crear la carpeta %(dir)s (%(err)s)',
        'info_done': '=== FIN: páginas ok=%(ok)d, errores=%(fail)d, omitidas=%(skip)d ===',
        'exc_no_gdal': 'No se encontró gdal_translate: %(path)s',
        'exc_no_in': 'La carpeta de origen no existe: %(path)s',
        'exc_no_out': 'Indique la carpeta de salida.',
        'exc_no_pdf': 'No se encontraron archivos *.pdf en la carpeta.',
        'menu': '&PDF -> TIFF',
        'plugin_tip': 'PDF2TIFF - convertidor de PDF a TIFF sin pérdida (GDAL)',
    },
    'zh': {
        'title': 'PDF -> TIFF 转换器（无损，GDAL）',
        'lbl_in': 'PDF 文件夹：',
        'lbl_out': 'TIFF 文件夹：',
        'lbl_gdal': 'gdal_translate：',
        'ph_out': '留空 = 保存在 PDF 旁边',
        'browse': '浏览...',
        'dpi': 'DPI：',
        'start': '开始',
        'stop': '停止',
        'skip': '跳过已有 TIFF',
        'subfolders': '子文件夹',
        'pages_group': 'PDF 页面',
        'mode_drawings': '仅图纸（默认）',
        'mode_all': '所有页面',
        'mode_custom': '指定页面：',
        'tip_mode_drawings': '保存大于所选图幅格式的页面。典型 PDF（A4 说明书 + A3/A2/A1/A0 图纸）中只保留图纸。',
        'ph_pages': '例如 1,3,5-8（留空 = 所有页面）',
        'lbl_format': '最小图纸图幅：',
        'lbl_ink': '最小墨迹覆盖（%）：',
        'tip_format': ('被判定为图纸的页面最小图幅。\n'
                       'A3 = 大于 A4 的页面（A3、A2、A1、A0 及横向）。\n'
                       'A4 = 不按图幅过滤。'),
        'tip_ink': '页面的最小墨迹覆盖（%）。0 = 关闭过滤，可去掉几乎空白的页面。',
        'pages_info': '图纸 = 大于所选图幅的页面；单页 PDF 总是转换。每个判断都会写入日志。',
        'status_ready': '就绪。',
        'tip_pb_file': '当前文件进度',
        'tip_pb_total': '总进度',
        'hi_1': 'PDF -> TIFF 转换器（无损）。选择 PDF 文件夹并按 START。',
        'hi_2': '提示：对栅格 PDF，200 DPI 为原生分辨率（1:1，无质量损失）。',
        'hi_3': 'TIFF 压缩：DEFLATE（无损）。',
        'hi_4': '多页 PDF：默认只保存图纸（大于所选图幅的页面），文件名 name_p01.tif、name_p02.tif……',
        'warn_gdal': '未找到 gdal_translate：\n%(path)s\n\n请指定 gdal_translate.exe 的路径。',
        'warn_in_dir': '请选择包含 PDF 文件的文件夹。',
        'info_no_pdf': '文件夹中没有 *.pdf 文件。',
        'empty_path': '（空路径）',
        'log_start': '=== 开始 ===',
        'log_files': '待转换文件          : %(count)d',
        'log_in': '源文件夹            : %(path)s',
        'log_out': '目标文件夹          : %(path)s',
        'log_dpi': 'DPI / 压缩          : %(dpi)d / DEFLATE（无损）',
        'log_pages': '页面                : %(mode)s',
        'log_ink': '最小墨迹            : %(ink).1f%%',
        'log_skip': '模式                : 跳过已有 TIFF',
        'mode_text_all': '所有页面',
        'mode_text_custom': '指定页面：%(spec)s',
        'mode_text_drawings': '仅图纸（最小图幅 %(fmt)s）',
        'all_pages_word': '全部',
        'log_stop_req': '正在停止...',
        'log_done': '=== 结束：成功页面=%(ok)d，错误=%(fail)d ===',
        'status_done': '完成。成功页面：%(ok)d，错误：%(fail)d。',
        'msg_done': '转换完成。\n成功页面：%(ok)d\n错误：%(fail)d',
        'choose_in': '选择包含 PDF 文件的文件夹',
        'choose_out': '选择 TIFF 输出文件夹',
        'choose_gdal': '指定 gdal_translate.exe',
        'filter_gdal': 'gdal_translate (gdal_translate.exe);;程序 (*.exe);;所有文件 (*)',
        'err_run_gdal': '错误：无法启动 gdal_translate（%(err)s）',
        'err_start_gdal': '错误：无法启动 gdal_translate',
        'err_start_gdal_sync': '无法启动 gdal_translate：%(path)s',
        'err_read_pages': '%(name)s：无法读取页面（%(err)s）',
        'status_analyse': '分析页面 [%(i)d/%(n)d] %(name)s',
        'log_file': '[%(i)d/%(n)d] %(name)s（页面：%(pages)d，待转换：%(todo)d）',
        'log_page_skipped': '        第 %(page)d 页：已跳过（%(reason)s）',
        'log_no_pages': '        没有需要转换的页面',
        'err_mkdir': '        错误：无法创建文件夹 %(dir)s（%(err)s）',
        'status_page': '[%(i)d/%(n)d] %(name)s  第 %(page)d/%(pages)d 页',
        'log_page': '        第 %(page)d 页 -> %(file)s',
        'log_page_exists': '            已跳过（TIFF 已存在）',
        'log_page_ok': '            成功（%(size)s 像素，DPI %(dpi)d，无损）',
        'log_page_ok_short': '            成功（DPI %(dpi)d，无损）',
        'log_page_aborted': '            已中断',
        'log_page_error': '            错误（代码 %(rc)d）',
        'reason_too_small': '%(size)s（小于 %(fmt)s）',
        'reason_ink': '%(size)s，墨迹 %(ink).2f%%（最小 %(min).2f%%）',
        'reason_kept': '%(size)s，墨迹 %(ink).2f%%',
        'note_no_big': '没有页面大于 %(fmt)s - 转换所有页面（可修改“最小图纸图幅”来过滤）',
        'note_custom': '指定页面（%(count)d / %(total)d）：%(list)s',
        'sync_pages': '        页面：%(pages)d，待转换：%(todo)d',
        'sync_page_skip': '        第 %(page)d 页 -> %(file)s：已跳过（文件已存在）',
        'sync_page_ok': '        第 %(page)d 页 -> %(file)s：成功（%(size)s 像素）',
        'sync_page_ok_short': '        第 %(page)d 页 -> %(file)s：成功',
        'sync_page_err': '        第 %(page)d 页 -> %(file)s：错误（代码 %(rc)d）',
        'alg_name': '将 PDF 转换为 TIFF（无损）',
        'alg_group': 'PDF 转换',
        'alg_help': (
            '使用 gdal_translate 将文件夹中的 *.pdf 转换为 *.tif：按指定 DPI 渲染，DEFLATE 无损压缩。\n\n'
            '多页 PDF：每一页都是独立的 GDAL 子数据集。默认只保存图纸（大于所选图幅的页面，A3 表示“大于 A4”）。'
            '也可选择所有页面或页面列表，例如 1,3,5-8。\n\n'
            '文件名：单页 PDF -> name.tif，多页 PDF -> name_p01.tif、name_p02.tif……\n\n'
            '使用的命令：\n'
            'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff -co COMPRESS=DEFLATE '
            '-co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER "输入.pdf" "输出.tif"'
        ),
        'p_input': '包含 PDF 文件的文件夹',
        'p_output': '输出文件夹（TIFF）',
        'p_dpi': '渲染 DPI（200 = 栅格 PDF 的原生分辨率）',
        'p_page_mode': 'PDF 页面',
        'p_pages': '指定页面（例如 1,3,5-8；留空 = 全部）',
        'p_min_format': '最小图纸图幅',
        'p_min_ink': '最小墨迹覆盖百分比（0 = 不过滤）',
        'p_skip': '跳过已有 TIFF',
        'p_recursive': '处理子文件夹',
        'p_gdal': 'gdal_translate（留空 = 自动检测）',
        'opt_mode_drawings': '仅图纸（默认）',
        'opt_mode_all': '所有页面',
        'opt_mode_custom': '指定页面',
        'mode_line': '页面模式        : %(mode)s',
        'mode_line_drawings': '页面模式        : %(mode)s（最小图幅 %(fmt)s，最小墨迹 %(ink).1f%%）',
        'info_gdal': 'gdal_translate : %(path)s',
        'info_in': '源文件夹       : %(path)s',
        'info_out': '目标文件夹     : %(path)s',
        'info_dpi': 'DPI / 压缩     : %(dpi)d / DEFLATE（无损）',
        'info_files': '待转换文件     : %(count)d',
        'info_cancel': '已被用户取消。',
        'info_mkdir': '无法创建文件夹 %(dir)s（%(err)s）',
        'info_done': '=== 结束：成功页面=%(ok)d，错误=%(fail)d，跳过=%(skip)d ===',
        'exc_no_gdal': '未找到 gdal_translate：%(path)s',
        'exc_no_in': '源文件夹不存在：%(path)s',
        'exc_no_out': '请指定输出文件夹。',
        'exc_no_pdf': '文件夹中没有 *.pdf 文件。',
        'menu': '&PDF -> TIFF',
        'plugin_tip': 'PDF2TIFF - 无损 PDF 转 TIFF 转换器（GDAL）',
    },
}

_LANGUAGE = ''


def _qgis_locale():
    """Jezyk wybrany w ustawieniach QGIS ('' gdy brak)."""
    try:
        from qgis.core import QgsSettings
    except ImportError:
        return ''
    return str(QgsSettings().value('locale/userLocale', '') or '')


def _normalise(code):
    return str(code or '').replace('-', '_').split('_')[0].strip().lower()


def detect_language():
    """Jezyk interfejsu: PDF2TIFF_LANG -> QGIS -> system -> angielski."""
    system = QLocale.system().name() if QLocale is not None else ''
    for candidate in (os.environ.get('PDF2TIFF_LANG', ''), _qgis_locale(), system):
        code = _normalise(candidate)
        if code in TRANSLATIONS:
            return code
    return FALLBACK


def language():
    """Aktualny kod jezyka (leniwie wykrywany raz na sesje)."""
    global _LANGUAGE
    if not _LANGUAGE:
        _LANGUAGE = detect_language()
    return _LANGUAGE


def set_language(code):
    """Wymusza jezyk (przydatne w testach); zwraca ustawiony kod."""
    global _LANGUAGE
    normalised = _normalise(code)
    _LANGUAGE = normalised if normalised in TRANSLATIONS else FALLBACK
    return _LANGUAGE


def tr(key, **kwargs):
    """Tekst w aktualnym jezyku; brakujace klucze z tabeli angielskiej."""
    table = TRANSLATIONS.get(language()) or TRANSLATIONS[FALLBACK]
    text = table.get(key)
    if text is None:
        text = TRANSLATIONS[FALLBACK].get(key, key)
    if kwargs:
        try:
            text = text % kwargs
        except (KeyError, TypeError, ValueError):
            return text
    return text
