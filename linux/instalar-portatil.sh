#!/bin/sh
# RASGO Suite — installs every instrument for the current user, without root,
# for any distribution: the AppImages go to ~/.local/opt/rasgo, with a
# launcher in ~/.local/bin and an entry in the applications menu.
# ./uninstall.sh removes exactly what this script installed.
# Instala cada instrumento para o usuário atual, sem root.
set -eu
cd "$(dirname "$0")"
OPT="$HOME/.local/opt/rasgo"
BIN="$HOME/.local/bin"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONES="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
SVG="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
mkdir -p "$OPT" "$BIN" "$APPS" "$ICONES" "$SVG"
: > "$OPT/.instalado-pela-suite"

while IFS='|' read -r tipo arquivo id nome wmclass binario; do
    [ -n "$id" ] || continue
    echo "-> $nome"
    # nome do atalho e do ícone: rasgo-<id>, sem repetir o prefixo
    case "$id" in rasgo-*) nome_arq=$id ;; *) nome_arq=rasgo-$id ;; esac
    case "$tipo" in
        appimage)
            cp -f "apps/$arquivo" "$OPT/$id.AppImage"
            chmod 755 "$OPT/$id.AppImage"
            exe="$OPT/$id.AppImage"
            # o ícone que o próprio AppImage leva (.DirIcon, em geral um link
            # para o .svg ou .png da raiz), extraído sem precisar de FUSE
            tmp=$(mktemp -d)
            (
                cd "$tmp" && "$exe" --appimage-extract .DirIcon >/dev/null 2>&1 || exit 0
                # segue a cadeia de links (.DirIcon -> x.svg -> usr/share/icons/…)
                rel=.DirIcon; n=0
                while [ -L "squashfs-root/$rel" ] && [ "$n" -lt 6 ]; do
                    alvo=$(readlink "squashfs-root/$rel")
                    case "$alvo" in /*) exit 0 ;; esac
                    dir=$(dirname "$rel")
                    [ "$dir" = . ] && rel=$alvo || rel="$dir/$alvo"
                    "$exe" --appimage-extract "$rel" >/dev/null 2>&1 || exit 0
                    n=$((n + 1))
                done
                origem="squashfs-root/$rel"
                [ -f "$origem" ] || exit 0
                case "$origem" in
                    *.svg) cp -f "$origem" "$SVG/$nome_arq.svg" ;;
                    *) cp -f "$origem" "$ICONES/$nome_arq.png" ;;
                esac
            )
            rm -rf "$tmp" ;;
        tar)
            rm -rf "$OPT/$id"
            mkdir -p "$OPT/$id"
            tar -xzf "apps/$arquivo" -C "$OPT/$id" --strip-components=1
            exe="$OPT/$id/$binario"
            icone=$(ls "$OPT/$id"/usr/share/icons/hicolor/256x256/apps/*.png 2>/dev/null | head -n 1 || true)
            [ -n "$icone" ] && cp -f "$icone" "$ICONES/$nome_arq.png" ;;
        *) echo "   unknown type: $tipo"; continue ;;
    esac
    ln -sf "$exe" "$BIN/$id"
    cat > "$APPS/$nome_arq.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$nome
Exec="$exe"
Icon=$nome_arq
Categories=AudioVideo;Audio;Music;
Terminal=false
StartupWMClass=$wmclass
DESKTOP
    echo "$id $nome_arq" >> "$OPT/.instalado-pela-suite"
done < apps/apps.txt

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" 2>/dev/null || true
echo
echo "Done: the instruments are in the applications menu and in $BIN."
echo "Pronto: os instrumentos estão no menu de aplicativos e em $BIN."
