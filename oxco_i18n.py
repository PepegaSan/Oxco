"""UI strings for Oxco (German / English)."""

from __future__ import annotations

from typing import Any, Dict

DE: Dict[str, str] = {
    "app.title": "Oxco — Compare, Bitrate, Autotagger",
    "btn.settings": "Einstellungen",
    "tab.flow": "Ablauf",
    "tab.preview": "Vorschau",
    "tab.paths": "Pfade",
    "tab.filters": "Filter",
    "log.title": "Protokoll",
    "paths.compare_export": "Compare — Exportziel",
    "paths.compare_export_hint": "Ordner für exportierte Videos",
    "paths.bitrate": "Video-Bitrate (Eingang / Ausgang)",
    "paths.bitrate_in": "Zu prüfender Ordner",
    "paths.bitrate_out": "Ausgabeordner",
    "paths.tagger": "Autotagger (Einmal pro Ordner)",
    "paths.tagger_in": "Quellordner (.mp4)",
    "paths.tagger_out": "Zielordner",
    "dlg.folder": "Ordner wählen",
    "dlg.video_orig": "Original-Video",
    "dlg.video_df": "Deepfake-Video",
    "dlg.video_a": "Video A",
    "dlg.video_b": "Video B",
    "flow.step1": "1. Compare starten",
    "flow.original": "Original (Source)",
    "flow.deepfake": "Deepfake",
    "flow.file_btn": "Datei…",
    "flow.run_compare": "Compare ausführen",
    "flow.compare_stop": "Stoppen",
    "flow.compare_retry": "Erneut",
    "flow.compare_more_filters": "Weitere Schwellen: Tab „Filter“.",
    "flow.compare_src_dir": "Original-Ordner (Scan)",
    "flow.compare_df_dir": "Deepfake-Ordner (Scan)",
    "flow.compare_load_lists": "Listen laden",
    "flow.compare_recursive": "Unterordner einbeziehen",
    "flow.compare_sort": "Sortieren",
    "flow.compare_group": "Gruppieren",
    "flow.compare_sort.date_desc": "Datum (neueste zuerst)",
    "flow.compare_sort.date_asc": "Datum (älteste zuerst)",
    "flow.compare_sort.size_desc": "Größe (größte zuerst)",
    "flow.compare_sort.size_asc": "Größe (kleinste zuerst)",
    "flow.compare_sort.name_asc": "Name (A–Z)",
    "flow.compare_sort.name_desc": "Name (Z–A)",
    "flow.compare_sort.duration_desc": "Länge (längste zuerst)",
    "flow.compare_sort.duration_asc": "Länge (kürzeste zuerst)",
    "flow.compare_group.none": "Keine",
    "flow.compare_group.folder": "Unterordner",
    "flow.compare_group.date": "Datum",
    "flow.compare_group.letter": "Anfangsbuchstabe",
    "flow.compare_group.duration": "Video-Länge",
    "flow.compare_tree_name": "Datei",
    "flow.compare_tree_rel": "Pfad",
    "flow.compare_tree_size": "Größe",
    "flow.compare_tree_date": "Geändert",
    "flow.compare_tree_duration": "Länge",
    "flow.compare_tree_res": "Auflösung",
    "flow.compare_color_hint": "Gleiche Farbe = gleiche Länge und Auflösung (ffprobe, beide Listen).",
    "flow.compare_run_batch": "Compare (Auswahl)",
    "flow.compare_batch_hint": "Links genau ein Original, rechts ein oder mehrere Deepfakes markieren (Strg+Klick) — Compare führt alle nacheinander aus. Deepfake-Liste: Rechtsklick verschieben, Entf = Papierkorb.",
    "err.compare_scan_dirs": "Original- und Deepfake-Ordner setzen (gültige Verzeichnisse).",
    "err.compare_pick_orig_tree": "In der Original-Liste genau eine Datei markieren.",
    "err.compare_pick_df_tree": "In der Deepfake-Liste mindestens eine Datei markieren.",
    "log.compare_scan": "Compare-Listen: {no} Original, {nd} Deepfake.",
    "log.compare_probe_progress": "Compare-Metadaten: {cur}/{tot} …",
    "log.compare_probe_done": "Compare-Metadaten fertig — Farben nach Länge/Auflösung.",
    "log.compare_probe_no_ffprobe": "ffprobe nicht gefunden — keine Länge/Auflösung/Farben in Compare-Listen.",
    "log.compare_jump_many": "Deepfake(s) mit gleicher Länge/Auflösung markiert: {n}",
    "log.compare_jump_one": "Deepfake markiert: {name}",
    "log.compare_jump_one_more": "Deepfake markiert: {name} ({more} weitere mit gleicher Länge/Auflösung)",
    "log.compare_jump_none": "Kein Deepfake mit gleicher Länge/Auflösung wie „{name}“.",
    "log.compare_jump_none_detail": "Kein Deepfake für „{name}“ (Schlüssel: {match_key}, {nd} DF gesamt, {probed} mit Metadaten).",
    "log.compare_jump_no_meta": "Original „{name}“: Länge/Auflösung unbekannt (Metadaten-Scan abwarten).",
    "log.compare_jump_entry": "Original „{name}“ nicht in der Eintragsliste (Listen neu laden).",
    "log.compare_batch_start": "— Compare-Warteschlange: {n} Deepfake(s) für ein Original —",
    "log.compare_batch_job": "Compare {cur}/{tot}: {df}",
    "log.compare_batch_stopped": "— Warteschlange abgebrochen (Fehler oder Stopp, Code {rc}) —",
    "log.compare_batch_done": "— Compare-Warteschlange fertig —",
    "flow.step2": "2. Bitrate — Ordner scannen und transcodieren",
    "flow.tree.file": "Datei",
    "flow.tree.res": "Auflösung",
    "flow.tree.src_k": "Quelle kbps",
    "flow.tree.tgt_k": "Ziel kbps",
    "flow.tree.action": "Aktion",
    "flow.scan": "Ordner scannen",
    "flow.convert": "Konvertierung starten",
    "flow.stop": "Stop",
    "flow.step3": "3. Autotagger — Dateien umbenennen und verschieben",
    "flow.tag": "Tag im Dateinamen",
    "flow.profile": "Profilname (Fallback)",
    "flow.process": "Jetzt verarbeiten",
    "flow.tagger_tree_file": "Datei (.mp4)",
    "flow.tagger_preview": "Vorschau",
    "flow.tagger_preview_hint": "Datei markieren — Slider/Abspielen zum Erkennen der Person.",
    "flow.tagger_preview_no_file": "Keine Datei gewählt.",
    "flow.tagger_refresh": "Liste laden",
    "flow.tagger_hint": "Keine Markierung: alle Dateien im Quellordner. Mit Markierung: nur die gewählten Zeilen.",
    "flow.ctx_move_to_tagger": "In Autotagger-Quellordner verschieben",
    "flow.ctx_move_to_bitrate": "In Bitrate-Eingangsordner verschieben",
    "flow.ctx_recycle_bin": "In Papierkorb (Entf)",
    "flow.tag_route_setup": "Tag-Verteilung…",
    "flow.tag_route_distribute": "Verteilen",
    "flow.tag_route_auto": "Nach Taggen automatisch verteilen",
    "flow.tag_route_title": "Tag-Verteilung",
    "flow.tag_route_col_tag": "Tag im Dateinamen",
    "flow.tag_route_col_folder": "Zielordner",
    "flow.tag_route_add": "Zeile hinzufügen",
    "flow.tag_route_save": "Speichern & schließen",
    "flow.tag_route_remove": "Entfernen",
    "err.tag_route_no_rules": "Keine Tag-Verteilungsregeln — zuerst „Tag-Verteilung…“ einrichten.",
    "err.tag_route_out_missing": "Autotagger-Zielordner ungültig (Tab Pfade).",
    "log.tag_route_start": "— Tag-Verteilung gestartet —",
    "log.tag_route_done": "— Tag-Verteilung fertig: {moved} verschoben, {nomatch} ohne Treffer, {err} Fehler —",
    "log.tag_route_moved": "Verteilt: {name} → {dest}",
    "log.tag_route_no_match": "Kein passender Tag: {name}",
    "log.tag_route_no_rules": "Tag-Verteilung: keine gültigen Regeln.",
    "log.tag_route_unstable": "Übersprungen (Datei noch nicht fertig): {name}",
    "log.tag_route_error": "Fehler bei {name}: {err}",
    "help.tag_route.title": "Tag-Verteilung",
    "help.tag_route.body": (
        "Quelle ist immer der Autotagger-Zielordner (Tab Pfade). Pro Zeile: Tag-Text und Zielordner.\n\n"
        "Bei Tags in eckigen Klammern (wie nach dem Autotagger) muss der Klammer-Inhalt **genau** passen — "
        "[Julia] trifft nicht auf [Julia Berens]. Längere Tags haben zusätzlich Vorrang.\n\n"
        "Ohne Klammern im Dateinamen: „Julia“ trifft nicht auf „Julia Berens“ (Wortgrenze).\n\n"
        "Ohne Treffer bleibt die Datei im Zielordner des Autotaggers."
    ),
    "filters.group_compare": "Compare — Analyse und Export",
    "filters.lang_note": "Sprache für Compare und diese Oberfläche: Einstellungen (⚙).",
    "filters.buffer": "Puffer (Sekunden)",
    "filters.noise": "Rausch-Schwelle",
    "filters.pixel": "Pixel-Schwelle",
    "filters.pixel_max": "Pixel-Obergrenze (0=aus)",
    "filters.davinci_timeout": "DaVinci Timeout (s, 0=aus)",
    "filters.ffmpeg_on": "FFmpeg-Export aktiv",
    "filters.davinci_on": "DaVinci-Export aktiv",
    "filters.ffmpeg_renders": "FFmpeg rendert",
    "filters.export_unique": "Exporte nicht überschreiben (Suffix)",
    "filters.ff.both": "beide",
    "filters.ff.source": "Original",
    "filters.ff.deepfake": "Deepfake",
    "filters.br_group": "Bitrate — Regeln (kbps je Mindesthöhe)",
    "filters.preset": "Preset",
    "filters.apply_preset": "Preset laden",
    "filters.subfolders": "Unterordner einbeziehen",
    "filters.only_lower": "Nur wenn Zielbitrate unter Quelle",
    "filters.suffix_out": "Suffix für Ausgabe",
    "filters.mp4": "Immer .mp4 ausgeben",
    "filters.br_delete_source": "Nach erfolgreicher Bitrate-Konvertierung: Original im Eingangsordner löschen",
    "filters.codec": "Codec",
    "filters.audio": "Audio",
    "filters.tag_group": "Autotagger — Muster und Suffixe",
    "filters.keep": "Keep-Suffixe (Komma)",
    "filters.ignore": "Ignore-Suffixe",
    "filters.drop": "Drop-Suffixe",
    "filters.pattern": "Muster im Dateinamen",
    "settings.title": "Einstellungen",
    "settings.lang": "Sprache der Oberfläche und Compare-Meldungen",
    "settings.lang_de": "Deutsch",
    "settings.lang_en": "English",
    "settings.davinci_api": "DaVinci Python-API (Ordner „Modules“)",
    "settings.davinci_preset": "DaVinci Render-Preset (Name in Resolve)",
    "settings.davinci_exe": "Resolve.exe (optional, Auto-Start unter Windows)",
    "settings.davinci_startup_wait": "Wartezeit nach Resolve-Start (s, 0–600)",
    "settings.davinci_exe_browse": "Resolve.exe wählen",
    "settings.save": "Speichern",
    "settings.cancel": "Schließen",
    "settings.saved": "Einstellungen wurden gespeichert.",
    "settings.ini_write_warn": "settings.ini konnte nicht vollständig geschrieben werden.",
    "br.action.convert": "konvertieren",
    "br.action.skip": "überspringen",
    "br.reason.unreadable_resolution": "Auflösung nicht lesbar",
    "br.reason.bitrate_unknown": "Bitrate unbekannt",
    "br.reason.already_low_enough": "Schon niedrig genug",
    "br.reason.reduce": "Reduzieren",
    "br.reason.scan_error": "Scan-Fehler",
    "info.compare_busy": "Ein Vergleich läuft schon — bitte warten.",
    "info.convert_busy": "Eine Konvertierung läuft schon — bitte warten.",
    "info.note": "Hinweis",
    "info.tagger_same_as_bitrate_in": "Autotagger-Quelle und Bitrate-Eingang sind derselbe Ordner — Verschieben entfällt.",
    "info.compare_already_in_folder": "Datei(en) liegen bereits im Zielordner — nichts zu verschieben.",
    "info.compare_nothing_moved": "Keine Datei konnte verschoben werden.",
    "err.input": "Eingabe",
    "err.tool": "Werkzeug fehlt",
    "err.ffprobe": "ffprobe wurde nicht gefunden (PATH).",
    "err.ffmpeg": "ffmpeg wurde nicht gefunden (PATH).",
    "err.compare_missing": "Die Programmdateien sind unvollständig (Compare fehlt).",
    "err.ini_missing": "Die Datei settings.ini fehlt.\nKopiere settings.example.ini nach settings.ini und starte Oxco erneut.",
    "err.pick_orig": "Original-Video wählen.",
    "err.pick_df": "Deepfake-Video wählen.",
    "err.numbers": "Puffer / Schwellen / Timeout: gültige Zahlen eingeben.",
    "err.br_folder": "Bitrate: Zu prüfender Ordner ungültig (Tab Pfade).",
    "err.br_out": "Ausgabeordner setzen (Tab Pfade).",
    "err.br_scan_first": "Zuerst Ordner scannen.",
    "err.br_sel_invalid": "Markierung ungültig — bitte erneut scannen oder Zeilen in der Tabelle wählen.",
    "err.br_sel_no_convert": "Unter den markierten Zeilen ist keine zum Konvertieren vorgesehen (Spalte „konvertieren“).",
    "err.br_none_to_convert": "Im Scan ist keine Datei zum Konvertieren vorgesehen (Regeln / Spalte Aktion).",
    "err.tagger_folders": "Tagger: Quell- und Zielordner setzen (Tab Pfade).",
    "err.tagger_sel_invalid": "Ungültige Markierung in der Autotagger-Tabelle — „Liste laden“ klicken und Zeilen wählen.",
    "err.tagger_in_for_move": "Autotagger-Quellordner setzen (Tab Pfade), damit Dateien dorthin verschoben werden können.",
    "err.bitrate_in_for_move": "Bitrate-Eingangsordner setzen (Tab Pfade), damit Dateien dorthin verschoben werden können.",
    "err.recycle_bin_unsupported": "Papierkorb wird nur unter Windows unterstützt.",
    "err.recycle_bin_failed": "Datei(en) konnten nicht in den Papierkorb verschoben werden.",
    "err.file_in_use": "„{name}“ ist noch geöffnet (z. B. Vorschau-Tab). Oxco hat die Sperre gelöst — bitte erneut versuchen.",
    "err.br_rule": "Regel für ≥{h} px fehlt.",
    "err.br_rule_num": "Ungültige Zahl bei ≥{h}: {raw}",
    "err.br_rule_pos": "Wert muss > 0 sein (≥{h}).",
    "log.compare_start": "— Compare gestartet —",
    "log.compare_retry_export": "— Compare: nur Export (gleicher Schnitt, keine neue Analyse) —",
    "log.compare_stopped": "— Compare durch Benutzer gestoppt —",
    "log.compare_partial": "Export (FFmpeg/DaVinci) fehlgeschlagen — Filter anpassen und „Erneut“ (nur Export, keine neue Analyse).",
    "log.compare_end": "— Compare beendet (Code {rc}) —",
    "log.compare_err": "FEHLER: {err}",
    "log.br_scan": "Bitrate-Scan …",
    "log.scan_line": "  Scan {a}/{b}",
    "log.scan_done": "Scan fertig: {n} Dateien, {c} zum Konvertieren.",
    "log.br_conv": "— Bitrate-Konvertierung —",
    "log.br_conv_all": "Konvertieren: alle {n} Tabellenzeilen (nur Aktion „konvertieren“).",
    "log.br_conv_sel": "Konvertieren: {n} markierte Tabellenzeile(n) (nur Aktion „konvertieren“).",
    "log.br_prog": "Fortschritt: {cur}/{tot}",
    "log.br_done": "— Bitrate fertig —",
    "log.br_src_deleted": "Quelle gelöscht: {name}",
    "log.br_src_delete_fail": "Quelle konnte nicht gelöscht werden: {name} ({err})",
    "log.icon_missing": (
        "Hinweis: Taskleisten-Icon nicht geladen. Oxco.cmd oder Desktop-Verknüpfung nutzen "
        "(create_oxco_shortcut.ps1), oder dist\\Oxco\\Oxco.exe bauen."
    ),
    "log.tagger_start": "— Autotagger gestartet —",
    "log.tagger_done": "— Autotagger fertig: {ok} verschoben, {sk} übersprungen —",
    "log.tagger_list": "Autotagger-Liste: {n} .mp4 im Quellordner.",
    "log.tagger_sel": "Autotagger: nur {n} markierte Datei(en).",
    "log.br_move_tagger": "Nach Autotagger-Quelle verschoben: {name}",
    "log.compare_move_bitrate": "Nach Bitrate-Eingang verschoben: {name}",
    "log.compare_move_tagger": "Nach Autotagger-Quelle verschoben: {name}",
    "log.compare_recycle": "In Papierkorb: {name}",
    "log.tagger_no_sel_match": "Keine der markierten Dateien liegt (mehr) im Quellordner — „Liste laden“.",
    "help.thresholds.title": "Schwellen",
    "help.thresholds.body": (
        "Puffer (Sekunden): Kurz warten, ob ein Unterschied wirklich weg ist — damit der Schnitt "
        "nicht ständig hin und her springt.\n\n"
        "Rausch: Wie empfindlich kleine Bildunterschiede mitgezählt werden.\n\n"
        "Pixel: Ab wie vielen auffälligen Stellen im Bild Oxco „Unterschied“ meldet.\n\n"
        "Pixel-Obergrenze: Wenn **mehr** Pixel als diese Zahl abweichen, zählt der Frame **nicht** "
        "als Unterschied (0 = aus). Hilft z. B. bei fast komplett veränderten Bildern (Auflösung/KI); "
        "kleinere echte Unterschiede bleiben sichtbar, solange ihre Pixelanzahl unter dieser Obergrenze liegt.\n\n"
        "DaVinci-Zeit: Wie lange maximal auf den Export gewartet wird (0 = ohne Grenze)."
    ),
    "help.export.title": "Export",
    "help.export.body": (
        "Hier stellst du ein, ob nach der Auswertung neue Videodateien erzeugt werden — "
        "mit FFmpeg oder DaVinci, je nachdem was du eingeschaltet hast.\n\n"
        "Du kannst wählen, welches Video geschnitten wird (Original, Deepfake oder beides).\n\n"
        "„Nicht überschreiben“: Wenn schon eine Datei mit gleichem Namen da ist, bekommt die neue "
        "einen Zusatz im Namen.\n\n"
        "Tab „Ablauf“: Compare kann mit „Stoppen“ abgebrochen werden. Endet Compare mit Code 3 "
        "(Export-Problem), unter „Filter“ FFmpeg/DaVinci anpassen und „Erneut“ — das startet **nur den Export** "
        "(gleicher Schnitt wie zuletzt analysiert), keine erneute Pixelanalyse."
    ),
    "help.bitrate.title": "Bitrate",
    "help.bitrate.body": (
        "Je nach der kürzeren Bildkante (Minimum aus Breite und Höhe) nimmt Oxco die passende Zeile in der Tabelle. "
        "Hochkant zählt damit wie die gleiche Stufe im Querformat (z. B. 1080×1920 wie 1080p, nicht wie 1920 Pixel Höhe).\n\n"
        "Die neue Datei wird nicht stärker komprimiert als die Quelle es hergibt.\n\n"
        "„Nur wenn Ziel unter Quelle“: Dateien, die schon klein genug sind, werden übersprungen.\n\n"
        "Konvertieren: Ohne Markierung in der Tabelle werden alle Zeilen mit Aktion „konvertieren“ verarbeitet. "
        "Mit Strg- oder Umschalt-Klick mehrere Zeilen markieren — dann nur diese.\n\n"
        "Optional: Häkchen „Original löschen“ entfernt die Quelldatei nur nach erfolgreicher Umwandlung "
        "(Quell- und Ausgabedatei dürfen nicht derselbe Pfad sein)."
    ),
    "help.suffix.title": "Suffix",
    "help.suffix.body": "Wird an den Namen der neuen Datei gehängt (z. B. _bitrate), damit du sie vom Original unterscheidest.",
    "help.keep.title": "Keep-Suffixe",
    "help.keep.body": "Endungen mit Komma trennen (z. B. _hyb, _pro). Diese Teile bleiben am Dateinamen erhalten.",
    "help.ignore.title": "Ignore-Suffixe",
    "help.ignore.body": "Dateien mit solchem Namensende werden nicht bearbeitet — z. B. wenn du Rohmaterial auslassen willst.",
    "help.drop.title": "Drop-Suffixe",
    "help.drop.body": (
        "Zusätzliche Teile am Ende des Dateinamens (ohne .mp4), die du selbst einträgst — per Komma wie bei Keep.\n\n"
        "Automatisch (ohne Eintrag hier) entfernt Oxco beim Taggen u. a.:\n"
        "• Compare-Schwellen-Suffix aus Tab „Filter“ (_b…_n…_p…, optional _m…)\n"
        "• _DaVinci_Export\n"
        "• das Bitrate-Ausgabe-Suffix aus Tab „Filter“ (z. B. _bitrate)\n"
        "• andere _b/_n/_p-Kombinationen (auch ältere Schwellen wie n15, wenn du jetzt n19 nutzt)\n"
        "  — überall im Namen, nicht nur am Ende\n\n"
        "Regex: Eintrag mit r: am Anfang; nur am Namensende. Beispiel Auflösungen: r:_\\d{3,4}p"
    ),
    "help.pattern.title": "Muster im Dateinamen",
    "help.pattern.body": (
        "Ein Stück Text im Dateinamen, das Oxco findet — oft ein Datum oder eine Zeit (z. B. YYMMDDHHmmSS).\n"
        "Wenn das Muster nicht passt, wird die Datei übersprungen.\n\n"
        "Beispiel: Datei heißt Clip_260428193001_hyb.mp4 — das Muster trifft den mittleren Block; der Tag ersetzt "
        "genau diese Stelle im Namen (nicht: Muster löschen und Tag ans Ende setzen).\n\n"
        "Statt fester Zahlen kann man DIGITS eintragen (eine Ziffernfolge).\n\n"
        "Tag: Freier Text wie [Musik], der die gefundene Muster-Stelle ersetzt."
    ),
    "help.tag.title": "Tag",
    "help.tag.body": "Text, der die gefundene Muster-Stelle im Dateinamen ersetzt — z. B. [Musik] oder [Anna].\nFrei eintippen oder aus der Liste wählen (Tags aus „Tag-Verteilung“).\nLeer lassen, wenn nur das Muster entfernt werden soll (ohne Ersatz).",
    "help.profile.title": "Profilname",
    "help.profile.body": "Nur ein Ersatzname, falls nach dem Aufräumen fast nichts Sinnvolles vom alten Namen übrig bleibt.",
    "preview.files": "Dateien",
    "preview.video_a": "Video A (Original)",
    "preview.video_b": "Video B (Deepfake)",
    "preview.link_paths": "Pfade aus Tab „Ablauf“ mitführen (Original / Deepfake)",
    "preview.auto_load": "Neu laden, wenn sich Pfade ändern",
    "preview.path_hint": "Eigene Videos: Haken oben aus — oder hier tippen / „…“ wählen (dann wird die Verknüpfung ausgeschaltet).",
    "preview.try_diff": "Unterschied ausprobieren",
    "preview.sens_small": "Empfindlichkeit für kleine Unterschiede",
    "preview.diff_threshold": "Ab wie vielen Stellen im Bild „Unterschied“",
    "preview.overlay": "Differenz-Overlay auf Vorschau",
    "preview.hint_buffer": (
        "Hinweis: Die Wartezeit (Puffer) aus dem Tab „Filter“ wirkt erst beim echten Vergleich — "
        "in der Vorschau siehst du nur die beiden Regler oben.\n\n"
        "„Unterschied: … Stellen“ = abweichende Pixel im **ganzen** Bild (wie Compare). Im Tab „Filter“ zählt ein Frame "
        "als „Unterschied“, wenn diese Zahl **größer** als die **Pixel-Schwelle** ist und unter der **Pixel-Obergrenze** "
        "bleibt (falls eingeschaltet)."
    ),
    "preview.apply_filter_tab": "Schwellen in Tab „Filter“ übernehmen",
    "preview.apply_ini": "Schwellen in settings.ini schreiben",
    "preview.load": "Laden",
    "preview.play": "Abspielen",
    "preview.pause": "Pause",
    "preview.max_fps": "Max. FPS",
    "preview.side_by_side": "Nebeneinander (A | B)",
    "preview.picture": "Bild",
    "preview.no_video": "Kein Video geladen.",
    "preview.help_diff.title": "Unterschied",
    "preview.help_diff.body": (
        "Mit den beiden Reglern stellst du ein, wie streng Oxco zwei Bilder vergleicht.\n\n"
        "Wenn die Zahl unter „Unterschied“ zu hoch ist: Rausch höher drehen oder die zweite Schwelle erhöhen.\n\n"
        "„In Tab Filter übernehmen“ kopiert die Schwellen.\n"
        "„In settings.ini schreiben“ speichert die Schwellen für den nächsten Vergleich-Lauf."
    ),
    "preview.help_player.title": "Vorschau",
    "preview.help_player.body": (
        "Leertaste: abspielen oder pausieren.\n"
        "Pfeil links / rechts: ein Bild vor oder zurück.\n\n"
        "Mit zwei Videos siehst du, wo sie sich unterscheiden. Mit „Overlay“ werden die Stellen eingefärbt.\n\n"
        "Pfade: Standard ist die Verknüpfung mit Tab „Ablauf“. Zum Testen anderer Dateien Haken aus "
        "oder Pfad ändern / „…“ nutzen."
    ),
    "preview.done_filter": "Fertig",
    "preview.done_filter_msg": "Die Werte stehen jetzt im Tab „Filter“ (Schwellen).",
    "preview.done_ini_msg": "Gespeichert in der Einstellungsdatei (settings.ini).",
    "preview.err_ini_title": "settings.ini",
    "preview.err_ini_msg": "settings.ini nicht gefunden oder nicht beschreibbar.",
    "preview.warn_no_a_title": "Vorschau",
    "preview.warn_no_a": "Bitte Video A wählen (oder im Tab „Ablauf“ setzen).",
    "preview.warn_no_b": "Nebeneinander: Video B fehlt.",
    "preview.err_not_found": "Video A wurde nicht gefunden.",
    "preview.err_open_a": "Video A konnte nicht geöffnet werden.",
    "preview.warn_b_open": "Video B konnte nicht geöffnet werden — nur A.",
    "preview.diff.none_b": "Unterschied: — (zweites Video laden)",
    "preview.diff.places": "Unterschied: {n} Stellen",
    "preview.diff.over": "Über deiner Schwelle — Oxco würde hier „Unterschied“ sagen",
    "preview.diff.under": "Unter deiner Schwelle — Oxco würde hier eher „gleich“ sagen",
    "preview.frame_info": "Frame {i} / {last}",
    "preview.meta": "{name}  ·  {frames} Frames  ·  {w}×{h}",
    "preview.frames_word": "Frames",
}

EN: Dict[str, str] = {k: v for k, v in DE.items()}  # placeholder, overwritten below

EN.update(
    {
        "app.title": "Oxco — Compare, bitrate, autotagger",
        "btn.settings": "Settings",
        "tab.flow": "Workflow",
        "tab.preview": "Preview",
        "tab.paths": "Paths",
        "tab.filters": "Filters",
        "log.title": "Log",
        "paths.compare_export": "Compare — export folder",
        "paths.compare_export_hint": "Folder for exported videos",
        "paths.bitrate": "Video bitrate (input / output)",
        "paths.bitrate_in": "Folder to scan",
        "paths.bitrate_out": "Output folder",
        "paths.tagger": "Autotagger (one folder at a time)",
        "paths.tagger_in": "Source folder (.mp4)",
        "paths.tagger_out": "Destination folder",
        "dlg.folder": "Choose folder",
        "dlg.video_orig": "Original video",
        "dlg.video_df": "Deepfake video",
        "dlg.video_a": "Video A",
        "dlg.video_b": "Video B",
        "flow.step1": "1. Run Compare",
        "flow.original": "Original (source)",
        "flow.deepfake": "Deepfake",
        "flow.file_btn": "File…",
        "flow.run_compare": "Run Compare",
        "flow.compare_stop": "Stop",
        "flow.compare_retry": "Retry",
        "flow.compare_more_filters": "More thresholds: “Filter” tab.",
        "flow.compare_src_dir": "Original folder (scan)",
        "flow.compare_df_dir": "Deepfake folder (scan)",
        "flow.compare_load_lists": "Load lists",
        "flow.compare_recursive": "Include subfolders",
        "flow.compare_sort": "Sort",
        "flow.compare_group": "Group by",
        "flow.compare_sort.date_desc": "Date (newest first)",
        "flow.compare_sort.date_asc": "Date (oldest first)",
        "flow.compare_sort.size_desc": "Size (largest first)",
        "flow.compare_sort.size_asc": "Size (smallest first)",
        "flow.compare_sort.name_asc": "Name (A–Z)",
        "flow.compare_sort.name_desc": "Name (Z–A)",
        "flow.compare_sort.duration_desc": "Duration (longest first)",
        "flow.compare_sort.duration_asc": "Duration (shortest first)",
        "flow.compare_group.none": "None",
        "flow.compare_group.folder": "Subfolder",
        "flow.compare_group.date": "Date",
        "flow.compare_group.letter": "First letter",
        "flow.compare_group.duration": "Video duration",
        "flow.compare_tree_name": "File",
        "flow.compare_tree_rel": "Path",
        "flow.compare_tree_size": "Size",
        "flow.compare_tree_date": "Modified",
        "flow.compare_tree_duration": "Duration",
        "flow.compare_tree_res": "Resolution",
        "flow.compare_color_hint": "Same color = same duration and resolution (ffprobe, both lists).",
        "flow.compare_run_batch": "Compare (selection)",
        "flow.compare_batch_hint": "Exactly one original on the left, one or more deepfakes selected on the right (Ctrl+click) — Compare runs them sequentially. Deepfake list: right-click to move, Del = recycle bin.",
        "err.compare_scan_dirs": "Set valid original and deepfake scan folders.",
        "err.compare_pick_orig_tree": "Select exactly one file in the original list.",
        "err.compare_pick_df_tree": "Select at least one file in the deepfake list.",
        "log.compare_scan": "Compare lists: {no} original, {nd} deepfake.",
        "log.compare_probe_progress": "Compare metadata: {cur}/{tot} …",
        "log.compare_probe_done": "Compare metadata done — colors by duration/resolution.",
        "log.compare_probe_no_ffprobe": "ffprobe not found — no duration/resolution/colors in compare lists.",
        "log.compare_jump_many": "Deepfake(s) with same duration/resolution selected: {n}",
        "log.compare_jump_one": "Deepfake selected: {name}",
        "log.compare_jump_one_more": "Deepfake selected: {name} ({more} more with same duration/resolution)",
        "log.compare_jump_none": "No deepfake with same duration/resolution as “{name}”.",
        "log.compare_jump_none_detail": "No deepfake for “{name}” (key: {match_key}, {nd} DF total, {probed} with metadata).",
        "log.compare_jump_no_meta": "Original “{name}”: duration/resolution unknown (wait for metadata scan).",
        "log.compare_jump_entry": "Original “{name}” not in entry list (reload lists).",
        "log.compare_batch_start": "— Compare queue: {n} deepfake(s) for one original —",
        "log.compare_batch_job": "Compare {cur}/{tot}: {df}",
        "log.compare_batch_stopped": "— Queue stopped (error, stop, or code {rc}) —",
        "log.compare_batch_done": "— Compare queue finished —",
        "flow.step2": "2. Bitrate — scan folder and transcode",
        "flow.tree.file": "File",
        "flow.tree.res": "Resolution",
        "flow.tree.src_k": "Source kbps",
        "flow.tree.tgt_k": "Target kbps",
        "flow.tree.action": "Action",
        "flow.scan": "Scan folder",
        "flow.convert": "Start conversion",
        "flow.stop": "Stop",
        "flow.step3": "3. Autotagger — rename and move files",
        "flow.tag": "Tag in filename",
        "flow.profile": "Profile name (fallback)",
        "flow.process": "Process now",
        "flow.tagger_tree_file": "File (.mp4)",
        "flow.tagger_preview": "Preview",
        "flow.tagger_preview_hint": "Select a file — use the slider or play to see who is in the clip.",
        "flow.tagger_preview_no_file": "No file selected.",
        "flow.tagger_refresh": "Load list",
        "flow.tagger_hint": "No selection: every .mp4 in the source folder. With selection: only the highlighted rows.",
        "flow.ctx_move_to_tagger": "Move to autotagger source folder",
        "flow.ctx_move_to_bitrate": "Move to bitrate input folder",
        "flow.ctx_recycle_bin": "Move to recycle bin (Del)",
        "flow.tag_route_setup": "Tag routing…",
        "flow.tag_route_distribute": "Distribute",
        "flow.tag_route_auto": "Distribute automatically after tagging",
        "flow.tag_route_title": "Tag routing",
        "flow.tag_route_col_tag": "Tag in filename",
        "flow.tag_route_col_folder": "Destination folder",
        "flow.tag_route_add": "Add row",
        "flow.tag_route_save": "Save & close",
        "flow.tag_route_remove": "Remove",
        "err.tag_route_no_rules": "No tag routing rules — open “Tag routing…” first.",
        "err.tag_route_out_missing": "Invalid autotagger destination folder (Paths tab).",
        "log.tag_route_start": "— Tag routing started —",
        "log.tag_route_done": "— Tag routing finished: {moved} moved, {nomatch} no match, {err} errors —",
        "log.tag_route_moved": "Routed: {name} → {dest}",
        "log.tag_route_no_match": "No matching tag: {name}",
        "log.tag_route_no_rules": "Tag routing: no valid rules.",
        "log.tag_route_unstable": "Skipped (file not ready): {name}",
        "log.tag_route_error": "Error for {name}: {err}",
        "help.tag_route.title": "Tag routing",
        "help.tag_route.body": (
            "Source is always the autotagger destination folder (Paths tab). Each row: tag text and destination folder.\n\n"
            "With bracket tags (as after autotagger), the text inside the brackets must match **exactly** — "
            "[Julia] does not match [Julia Berens]. Longer tags are tried first.\n\n"
            "Without brackets in the filename, “Julia” does not match “Julia Berens” (word boundary).\n\n"
            "Files with no match stay in the autotagger destination folder."
        ),
        "filters.group_compare": "Compare — analysis and export",
        "filters.lang_note": "Language for Compare and this UI: Settings (⚙).",
        "filters.buffer": "Buffer (seconds)",
        "filters.noise": "Noise threshold",
        "filters.pixel": "Pixel threshold",
        "filters.pixel_max": "Pixel ceiling (0=off)",
        "filters.davinci_timeout": "DaVinci timeout (s, 0=off)",
        "filters.ffmpeg_on": "FFmpeg export enabled",
        "filters.davinci_on": "DaVinci export enabled",
        "filters.ffmpeg_renders": "FFmpeg renders",
        "filters.export_unique": "Do not overwrite exports (suffix)",
        "filters.ff.both": "both",
        "filters.ff.source": "original",
        "filters.ff.deepfake": "deepfake",
        "filters.br_group": "Bitrate — rules (kbps per minimum height)",
        "filters.preset": "Preset",
        "filters.apply_preset": "Load preset",
        "filters.subfolders": "Include subfolders",
        "filters.only_lower": "Only if target bitrate below source",
        "filters.suffix_out": "Output suffix",
        "filters.mp4": "Always output .mp4",
        "filters.br_delete_source": "After successful bitrate conversion: delete the original in the input folder",
        "filters.codec": "Codec",
        "filters.audio": "Audio",
        "filters.tag_group": "Autotagger — pattern and suffixes",
        "filters.keep": "Keep suffixes (comma)",
        "filters.ignore": "Ignore suffixes",
        "filters.drop": "Drop suffixes",
        "filters.pattern": "Filename pattern",
        "settings.title": "Settings",
        "settings.lang": "UI and Compare message language",
        "settings.lang_de": "German",
        "settings.lang_en": "English",
        "settings.davinci_api": "DaVinci Python API (\"Modules\" folder)",
        "settings.davinci_preset": "DaVinci render preset (name in Resolve)",
        "settings.davinci_exe": "Resolve.exe (optional; auto-start on Windows when DaVinci export runs)",
        "settings.davinci_startup_wait": "Wait after starting Resolve (seconds, 0–600)",
        "settings.davinci_exe_browse": "Choose Resolve.exe",
        "settings.save": "Save",
        "settings.cancel": "Close",
        "settings.saved": "Settings have been saved.",
        "settings.ini_write_warn": "Could not write settings.ini completely.",
        "br.action.convert": "convert",
        "br.action.skip": "skip",
        "br.reason.unreadable_resolution": "Resolution unreadable",
        "br.reason.bitrate_unknown": "Bitrate unknown",
        "br.reason.already_low_enough": "Already low enough",
        "br.reason.reduce": "Reduce",
        "br.reason.scan_error": "Scan error",
        "info.compare_busy": "A compare run is already in progress — please wait.",
        "info.convert_busy": "A conversion is already in progress — please wait.",
        "info.note": "Note",
        "info.tagger_same_as_bitrate_in": "Autotagger source and bitrate input are the same folder — nothing to move.",
        "info.compare_already_in_folder": "File(s) are already in the destination folder — nothing to move.",
        "info.compare_nothing_moved": "No file was moved.",
        "err.input": "Input",
        "err.tool": "Missing tool",
        "err.ffprobe": "ffprobe was not found (PATH).",
        "err.ffmpeg": "ffmpeg was not found (PATH).",
        "err.compare_missing": "Program files are incomplete (Compare is missing).",
        "err.ini_missing": "settings.ini is missing.\nCopy settings.example.ini to settings.ini and restart Oxco.",
        "err.pick_orig": "Choose the original video.",
        "err.pick_df": "Choose the deepfake video.",
        "err.numbers": "Enter valid numbers for buffer / thresholds / timeout.",
        "err.br_folder": "Bitrate: invalid scan folder (Paths tab).",
        "err.br_out": "Set an output folder (Paths tab).",
        "err.br_scan_first": "Scan the folder first.",
        "err.br_sel_invalid": "Invalid selection — scan again or pick rows in the table.",
        "err.br_sel_no_convert": "None of the selected rows are set to convert (check the Action column).",
        "err.br_none_to_convert": "No files in the scan are set to convert (rules / Action column).",
        "err.tagger_folders": "Tagger: set source and destination folders (Paths tab).",
        "err.tagger_sel_invalid": "Invalid selection in the autotagger table — click “Load list” and pick rows.",
        "err.tagger_in_for_move": "Set the autotagger source folder (Paths tab) before moving files there.",
        "err.bitrate_in_for_move": "Set the bitrate input folder (Paths tab) before moving files there.",
        "err.recycle_bin_unsupported": "Recycle bin is only supported on Windows.",
        "err.recycle_bin_failed": "Could not move file(s) to the recycle bin.",
        "err.file_in_use": "“{name}” is still open (e.g. Preview tab). Oxco released its lock — please try again.",
        "err.br_rule": "Rule for ≥{h} px is missing.",
        "err.br_rule_num": "Invalid number at ≥{h}: {raw}",
        "err.br_rule_pos": "Value must be > 0 (≥{h}).",
        "log.compare_start": "— Compare started —",
        "log.compare_retry_export": "— Compare: export only (same cut, no new analysis) —",
        "log.compare_stopped": "— Compare stopped by user —",
        "log.compare_partial": "Export (FFmpeg/DaVinci) failed — adjust Filters and Retry (export only, no new analysis).",
        "log.compare_end": "— Compare finished (code {rc}) —",
        "log.compare_err": "ERROR: {err}",
        "log.br_scan": "Bitrate scan …",
        "log.scan_line": "  Scan {a}/{b}",
        "log.scan_done": "Scan done: {n} files, {c} to convert.",
        "log.br_conv": "— Bitrate conversion —",
        "log.br_conv_all": "Converting: all {n} table rows (only “convert” action).",
        "log.br_conv_sel": "Converting: {n} selected table row(s) (only “convert” action).",
        "log.br_prog": "Progress: {cur}/{tot}",
        "log.br_done": "— Bitrate finished —",
        "log.br_src_deleted": "Source deleted: {name}",
        "log.br_src_delete_fail": "Could not delete source: {name} ({err})",
        "log.icon_missing": (
            "Note: taskbar icon not loaded. Use Oxco.cmd or a desktop shortcut "
            "(create_oxco_shortcut.ps1), or build dist\\Oxco\\Oxco.exe."
        ),
        "log.tagger_start": "— Autotagger started —",
        "log.tagger_done": "— Autotagger finished: {ok} moved, {sk} skipped —",
        "log.tagger_list": "Autotagger list: {n} .mp4 in the source folder.",
        "log.tagger_sel": "Autotagger: only {n} selected file(s).",
        "log.br_move_tagger": "Moved to autotagger source: {name}",
        "log.compare_move_bitrate": "Moved to bitrate input: {name}",
        "log.compare_move_tagger": "Moved to autotagger source: {name}",
        "log.compare_recycle": "Sent to recycle bin: {name}",
        "log.tagger_no_sel_match": "None of the selected files are in the source folder anymore — click “Load list”.",
        "help.thresholds.title": "Thresholds",
        "help.thresholds.body": (
            "Buffer (seconds): short wait to see if a difference really disappeared — so cuts do not flicker.\n\n"
            "Noise: how sensitive small image differences are counted.\n\n"
            "Pixels: from how many noticeable spots Oxco reports a “difference”.\n\n"
            "Pixel ceiling: if **more** pixels than this differ, the frame does **not** count as a difference "
            "(0 = disabled). Useful when almost the whole frame changes (resolution/KI); smaller real differences "
            "still count as long as their pixel count stays below this ceiling.\n\n"
            "DaVinci time: maximum time to wait for export (0 = no limit)."
        ),
        "help.export.title": "Export",
        "help.export.body": (
            "Choose whether new video files are created after analysis — with FFmpeg or DaVinci, depending on what you enable.\n\n"
            "You can choose which clip is rendered (original, deepfake, or both).\n\n"
            "“Do not overwrite”: if a file with the same name exists, the new one gets an extra suffix.\n\n"
            "Workflow tab: you can Stop Compare while it runs. If Compare exits with code 3 (export issue), "
            "adjust FFmpeg/DaVinci on the Filters tab and use Retry — that runs **export only** "
            "(same cut as the last analysis), not a new pixel pass."
        ),
        "help.bitrate.title": "Bitrate",
        "help.bitrate.body": (
            "Oxco picks the table row from the shorter frame side (min of width and height), so portrait clips use "
            "the same tier as the equivalent landscape size (e.g. 1080×1920 is treated like 1080p, not like a 1920-tall row).\n\n"
            "The new file is never compressed more aggressively than the source allows.\n\n"
            "“Only if target below source”: files that are already small enough are skipped.\n\n"
            "Convert: With no rows selected in the table, every row with action “convert” runs. "
            "Ctrl- or Shift-click to select multiple rows — only those are processed.\n\n"
            "Optional: “Delete original” removes the source file only after a successful conversion "
            "(source and output paths must not be the same file)."
        ),
        "help.suffix.title": "Suffix",
        "help.suffix.body": "Appended to the new filename (e.g. _bitrate) so you can tell it apart from the original.",
        "help.keep.title": "Keep suffixes",
        "help.keep.body": "Comma-separated endings (e.g. _hyb, _pro). These stay on the filename.",
        "help.ignore.title": "Ignore suffixes",
        "help.ignore.body": "Files whose names end like this are skipped — e.g. to exclude raw material.",
        "help.drop.title": "Drop suffixes",
        "help.drop.body": (
            "Extra trailing parts of the filename stem (before .mp4) that you list here — comma-separated like Keep.\n\n"
            "Removed automatically when tagging (no entry needed):\n"
            "• Compare threshold suffix from the Filter tab (_b…_n…_p…, optional _m…)\n"
            "• _DaVinci_Export\n"
            "• the bitrate output suffix from the Filter tab (e.g. _bitrate)\n"
            "• other _b/_n/_p combinations (older thresholds like n15 when you now use n19)\n"
            "  — anywhere in the name, not only at the end\n\n"
            "Regex: prefix r: ; end of stem only. Example resolutions: r:_\\d{3,4}p"
        ),
        "help.pattern.title": "Filename pattern",
        "help.pattern.body": (
            "Text in the filename Oxco should find — often a date or time (e.g. YYMMDDHHmmSS).\n"
            "If the pattern does not match, the file is skipped.\n\n"
            "Example: Clip_260428193001_hyb.mp4 — the pattern hits the middle block; the Tag replaces that spot "
            "(not: delete the token and append the tag at the end).\n\n"
            "Advanced: use DIGITS for any run of digits.\n\n"
            "Tag: free text like [Music] that replaces the matched segment."
        ),
        "help.tag.title": "Tag",
        "help.tag.body": "Text that replaces the matched pattern in the filename — e.g. [Music] or [Anna].\nType freely or pick from the list (tags from “Tag routing”).\nLeave empty to remove the pattern only (no replacement).",
        "help.profile.title": "Profile name",
        "help.profile.body": "Fallback name if almost nothing sensible is left of the old name after cleanup.",
        "preview.files": "Files",
        "preview.video_a": "Video A (original)",
        "preview.video_b": "Video B (deepfake)",
        "preview.link_paths": "Follow paths from “Workflow” tab (original / deepfake)",
        "preview.auto_load": "Reload when paths change",
        "preview.path_hint": "Own videos: turn off the checkbox above — or type a path / use “…” (link turns off).",
        "preview.try_diff": "Try difference settings",
        "preview.sens_small": "Sensitivity for small differences",
        "preview.diff_threshold": "From how many spots count as “difference”",
        "preview.overlay": "Difference overlay on preview",
        "preview.hint_buffer": (
            "Note: the wait time (buffer) from the “Filters” tab only applies to a real Compare run — "
            "the preview only uses the two sliders above.\n\n"
            "“Difference: … spots” counts differing pixels in the **full** frame (same as Compare). On the “Filters” tab, "
            "a frame counts as a “difference” only if that count is **greater** than the **pixel threshold** and stays "
            "below the **pixel ceiling** (when enabled)."
        ),
        "preview.apply_filter_tab": "Copy thresholds to “Filters” tab",
        "preview.apply_ini": "Write thresholds to settings.ini",
        "preview.load": "Load",
        "preview.play": "Play",
        "preview.pause": "Pause",
        "preview.max_fps": "Max FPS",
        "preview.side_by_side": "Side by side (A | B)",
        "preview.picture": "Picture",
        "preview.no_video": "No video loaded.",
        "preview.help_diff.title": "Difference",
        "preview.help_diff.body": (
            "The two sliders control how strictly Oxco compares two frames.\n\n"
            "If the number under “Difference” is too high: raise noise or raise the second threshold.\n\n"
            "“Copy to Filters tab” copies the thresholds.\n"
            "“Write to settings.ini” saves thresholds for the next Compare run."
        ),
        "preview.help_player.title": "Preview",
        "preview.help_player.body": (
            "Space: play or pause.\n"
            "Left / right arrow: one frame back or forward.\n\n"
            "With two videos you see where they differ. “Overlay” highlights those spots.\n\n"
            "Paths: by default they follow the “Workflow” tab. To test other files, turn off the checkbox "
            "or change the path / use “…”."
        ),
        "preview.done_filter": "Done",
        "preview.done_filter_msg": "Values are now on the “Filters” tab (thresholds).",
        "preview.done_ini_msg": "Saved to settings.ini.",
        "preview.err_ini_title": "settings.ini",
        "preview.err_ini_msg": "settings.ini not found or not writable.",
        "preview.warn_no_a_title": "Preview",
        "preview.warn_no_a": "Choose video A (or set it on the “Workflow” tab).",
        "preview.warn_no_b": "Side by side: video B is missing.",
        "preview.err_not_found": "Video A was not found.",
        "preview.err_open_a": "Video A could not be opened.",
        "preview.warn_b_open": "Video B could not be opened — showing A only.",
        "preview.diff.none_b": "Difference: — (load second video)",
        "preview.diff.places": "Difference: {n} spots",
        "preview.diff.over": "Above your threshold — Oxco would call this a “difference”",
        "preview.diff.under": "Below your threshold — Oxco would treat this as “same”",
        "preview.frame_info": "Frame {i} / {last}",
        "preview.meta": "{name}  ·  {frames} frames  ·  {w}×{h}",
        "preview.frames_word": "frames",
    }
)


BR_REASON_KEY = {
    "Auflösung nicht lesbar": "br.reason.unreadable_resolution",
    "Bitrate unbekannt": "br.reason.bitrate_unknown",
    "Schon niedrig genug": "br.reason.already_low_enough",
    "Reduzieren": "br.reason.reduce",
    "Scan-Fehler": "br.reason.scan_error",
}


def normalize_lang(code: str) -> str:
    c = (code or "de").strip().lower()
    return "en" if c.startswith("en") else "de"


def tr(lang: str, key: str, **kwargs: Any) -> str:
    lang = normalize_lang(lang)
    table = EN if lang == "en" else DE
    s = table.get(key) or DE.get(key) or key
    if kwargs:
        try:
            return s.format(**kwargs)
        except (KeyError, ValueError):
            return s
    return s


def tr_br_reason(lang: str, reason_de: str) -> str:
    rk = BR_REASON_KEY.get(reason_de)
    if rk:
        return tr(lang, rk)
    return reason_de
