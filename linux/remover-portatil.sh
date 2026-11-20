#!/bin/sh
# RASGO Suite — removes what install.sh installed for this user.
# The music, recordings and settings in ~/Music/RASGO and ~/.config stay.
# Remove o que o install.sh instalou; músicas, gravações e ajustes ficam.
set -eu
OPT="$HOME/.local/opt/rasgo"
BIN="$HOME/.local/bin"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONES="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
SVG="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
[ -f "$OPT/.instalado-pela-suite" ] || { echo "Nothing to remove / nada a remover."; exit 0; }
while read -r id nome_arq; do
    [ -n "$id" ] || continue
    rm -rf "$OPT/$id.AppImage" "$OPT/$id"
    rm -f "$BIN/$id" "$APPS/$nome_arq.desktop" "$ICONES/$nome_arq.png" "$SVG/$nome_arq.svg"
    echo "-> $id"
done < "$OPT/.instalado-pela-suite"
rm -f "$OPT/.instalado-pela-suite"
rmdir "$OPT" 2>/dev/null || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" 2>/dev/null || true
echo "Done / pronto."
