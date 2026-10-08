#!/bin/bash
# Doble clic para instalar lo necesario en Mac (Homebrew, Python, FFmpeg).
cd "$(dirname "$0")" || exit 1
echo ""
echo "  Instalando lo necesario para Basetoque Studio. Tarda unos minutos."
echo "  Si te pide la contraseña de tu Mac, escríbela (no se ve mientras escribes) y Enter."
echo ""
if ! command -v brew >/dev/null 2>&1; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi
command -v python3 >/dev/null 2>&1 || brew install python
command -v ffmpeg >/dev/null 2>&1 || brew install ffmpeg
echo ""
echo "  Instalando el asistente de Claude (opcional)…"
python3 -m pip install --user --upgrade anthropic 2>/dev/null || python3 -m pip install --user --break-system-packages --upgrade anthropic
chmod +x "Abrir Basetoque.command"
echo ""
echo "  ¡Listo! Cierra esta ventana y abre 'Abrir Basetoque.command'."
read -r -p "Presiona Enter para cerrar…"
