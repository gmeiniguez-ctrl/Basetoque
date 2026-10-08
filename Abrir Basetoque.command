#!/bin/bash
# Doble clic para abrir Basetoque Studio en Mac.
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "No encontré Python. Abre primero 'Instalar (Mac).command'."
  read -r -p "Presiona Enter para cerrar…"
  exit 1
fi
python3 app/server.py
