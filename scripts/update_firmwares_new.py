#!/usr/bin/env python3
"""
Firmware Downloader für KM271-Projekte

Usage:
  update_firmwares.py [--sources=<yaml>] [--fetchdir=<dir>] [--no-progress] [--quiet]
  update_firmwares.py (-h | --help)
  update_firmwares.py --version

Options:
  --sources=<yaml>   YAML-Datei mit Quellen [default: sources.yaml]
  --fetchdir=<dir>   Zielverzeichnis für Downloads [default: ./tmpfw]
  --no-progress      Zeige keinen Fortschrittsbalken
  --quiet            Zeige nur Fehlermeldungen und Zusammenfassung
  -h --help          Zeige diese Hilfe
  --version          Zeige Version

Examples:
  update_firmwares.py
  update_firmwares.py --sources=sources.yaml --fetchdir=./firmware
  update_firmwares.py --quiet
"""

from docopt import docopt


def main():
    """Hauptfunktion des Firmware-Downloaders."""
    args = docopt(__doc__, version="Firmware Downloader 1.0.0")

    # Argumente extrahieren
    sources_file = args["--sources"]
    fetch_dir = args["--fetchdir"]
    show_progress = not args["--no-progress"]
    quiet = args["--quiet"]

    # Debug-Ausgabe der Argumente
    if not quiet:
        print("🚀 Firmware Downloader gestartet")
        print(f"📁 Quellen-Datei: {sources_file}")
        print(f"📂 Zielverzeichnis: {fetch_dir}")
        print(f"📊 Fortschrittsbalken: {'Ein' if show_progress else 'Aus'}")
        print(f"🔇 Ruhig-Modus: {'Ein' if quiet else 'Aus'}")

    print("\n✅ Script erfolgreich gestartet!")


if __name__ == "__main__":
    main()
