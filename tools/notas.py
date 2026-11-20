#!/usr/bin/env python3
"""As notas da release da suíte, lidas do lock: uso  notas.py build/lock.json"""

import json
import sys


def notas(lock):
    linhas = ["Every RASGO instrument in one download per system, each one byte for byte "
              "as its own release published it. Each instrument keeps its own site, versions "
              "and licence, and also downloads on its own.", "",
              "| Instrument | Version | Licence |", "|---|---|---|"]
    for i in lock["instrumentos"]:
        linhas.append("| [%s](%s) | [%s](https://github.com/%s/releases/tag/%s) | %s |"
                      % (i["nome"], i["site"], i["versao"], i["repo"], i["tag"], i["licenca"]))
    linhas += ["",
               "**Windows:** `rasgo-suite-…-windows-x64.exe` runs each official installer; "
               "each instrument keeps its own uninstaller in Settings → Apps.",
               "**macOS:** `rasgo-suite-…-macos-universal.dmg`, drag the instruments onto "
               "Applications; `READ ME.txt` inside explains the first launch.",
               "**Linux:** `rasgo-suite-…-linux-x86_64.tar.gz` (the `.deb` packages, for "
               "Ubuntu, Debian and Mint: `./install.sh`) or "
               "`rasgo-suite-…-linux-x86_64-appimage.tar.gz` (any distribution, no root: "
               "`./install.sh`, `./uninstall.sh`).",
               "`SUITE.txt` lists the SHA-256 of every file that went in.", "", "---", "",
               "Todos os instrumentos RASGO num download por sistema, cada um byte a byte "
               "como a release dele publicou. Cada instrumento segue com site, versões e "
               "licença próprios, e também se baixa sozinho.", "",
               "**Windows:** o `.exe` roda o instalador oficial de cada instrumento; cada um "
               "tem o próprio desinstalador em Configurações → Aplicativos. "
               "**macOS:** arraste os instrumentos para Aplicativos; o `READ ME.txt` explica "
               "a primeira abertura. **Linux:** o `.tar.gz` com os `.deb` (Ubuntu, Debian e "
               "Mint) ou o `-appimage.tar.gz` (qualquer distribuição, sem root), ambos com "
               "`./install.sh`.",
               "O `SUITE.txt` lista o SHA-256 de cada arquivo que entrou."]
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        sys.stdout.write(notas(json.load(f)))
