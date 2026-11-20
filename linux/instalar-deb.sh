#!/bin/sh
# RASGO Suite — installs every instrument from its official .deb
# (Ubuntu, Debian, Mint). Each one then uninstalls on its own:
#   sudo apt remove <name>
# Instala cada instrumento pelo .deb oficial dele.
set -eu
cd "$(dirname "$0")"
echo "RASGO Suite: $(ls debs/*.deb | wc -l) instruments / instrumentos"
if [ "$(id -u)" = 0 ]; then SUDO=; else SUDO=sudo; fi
$SUDO apt-get install -y ./debs/*.deb
echo
echo "Done. The instruments are in the applications menu."
echo "Pronto. Os instrumentos estão no menu de aplicativos."
