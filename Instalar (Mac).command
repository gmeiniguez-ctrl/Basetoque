#!/bin/bash
# Doble clic para instalar lo necesario en Mac (Homebrew, Python, FFmpeg).
cd "$(dirname "$0")" || exit 1
echo ""
echo "  Instalando lo necesario para Basetoque Studio. Tarda unos minutos."
echo "  Si te pide la contraseña de tu Mac, escríbela (no se ve mientras escribes) y Enter."
echo ""
for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && eval "$("$b" shellenv)"; done
if ! command -v brew >/dev/null 2>&1; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && eval "$("$b" shellenv)"; done
fi
# Que Homebrew quede disponible en futuras ventanas de Terminal
BREW_BIN="$(command -v brew)"
if [ -n "$BREW_BIN" ] && ! grep -q "brew shellenv" "$HOME/.zprofile" 2>/dev/null; then
  echo "eval \"\$($BREW_BIN shellenv)\"" >> "$HOME/.zprofile"
fi
command -v python3 >/dev/null 2>&1 || brew install python
command -v ffmpeg >/dev/null 2>&1 || brew install ffmpeg
echo ""
echo "  Instalando el asistente de Claude (opcional)…"
python3 -m pip install --user --upgrade anthropic 2>/dev/null || python3 -m pip install --user --break-system-packages --upgrade anthropic
chmod +x "Abrir Basetoque.command"
# Acceso directo en el Escritorio
CARPETA="$(pwd)"
ATAJO="$HOME/Desktop/Basetoque Studio.command"
cat > "$ATAJO" <<ATAJO_FIN
#!/bin/bash
cd "$CARPETA" && exec ./"Abrir Basetoque.command"
ATAJO_FIN
chmod +x "$ATAJO"
echo ""
echo "  ¡Listo! Ya tienes 'Basetoque Studio' en tu Escritorio. Ábrelo con doble clic."
echo "  (No borres ni muevas la carpeta Basetoque: el acceso directo la usa.)"
read -r -p "Presiona Enter para cerrar…"
