"""Offline-Vorbau; keine Abhängigkeiten und kein konkreter PVS-Adapter."""

import sys

# Auch die direkte Skriptausführung erzeugt keine Bytecode-Dateien.
sys.dont_write_bytecode = True
