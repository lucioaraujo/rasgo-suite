# RASGO Suite

**English** · [Português](#português) · [Français](#français) · [Español](#español)

Every instrument of the [RASGO](https://rasgoinstruments.arquiviagem.net/)
family by Lúcio de Araújo in one download per system. The suite is a
snapshot of the family: it gathers the **latest official release** of each
instrument, byte for byte as its own repository published it, checked
against the size and SHA-256 GitHub reports. Each instrument keeps its own
repository, versions, site and licence, and also downloads on its own.

**Version:** by date (`2026.11`) · **Licence of these scripts:** GNU
AGPL-3.0-or-later ([`LICENSE`](LICENSE)); each instrument keeps its own
licence, listed in `SUITE.txt` and in the release notes.

## What comes in

Antitotem, Aquorbium, Batruc, Maestruc, Navalha 2, Rasgo Modular, Rasgo
Synth Asterismus, Rasgo Synth Studio and Trioio. The list, with each
instrument's repository and file patterns, is [`suite.json`](suite.json).

## The packages

| System | File | How it installs |
|---|---|---|
| Windows | `rasgo-suite-<version>-windows-x64.exe` | one installer with a box per instrument, all ticked; it runs each official installer, so each instrument lands where it would on its own, with its own shortcut and uninstaller |
| macOS | `rasgo-suite-<version>-macos-universal.dmg` | the official `.app` of each instrument (Universal 2); drag them onto Applications at once; `READ ME.txt` explains the first launch |
| Ubuntu, Debian, Mint | `rasgo-suite-<version>-linux-x86_64.tar.gz` | the official `.deb` packages and `./install.sh` (`sudo apt install`) |
| Other Linux | `rasgo-suite-<version>-linux-x86_64-appimage.tar.gz` | the official AppImages and `./install.sh` for the current user, no root, with menu entries; `./uninstall.sh` removes exactly that |

Every package carries `SUITE.txt`: the version of each instrument, the
release it came from and the SHA-256 of each file.

## How it is built

[`.github/workflows/suite.yml`](.github/workflows/suite.yml), by hand or on a
`vYYYY.MM` tag:

1. `tools/suite.py resolver` asks GitHub for the latest release (not a
   pre-release) of each instrument and picks one file per system. A missing
   or doubled file stops the suite: a suite with half the instruments looks
   complete and is not.
2. `tools/suite.py baixar` downloads and checks size and SHA-256.
3. The four packages are assembled, nothing recompiled.
4. Tests: the Windows installer runs silently on a Windows runner and every
   instrument must be in Program Files; the `.dmg` is mounted on a macOS
   runner and every app's signature verified; on Debian 12, Ubuntu 24.04,
   Fedora and Arch the Linux packages are installed and every instrument is
   opened on a virtual screen.
5. On a tag, the release with the packages and `SUITE.txt`. A tag with a
   hyphen (`v2026.11-rc1`) is a pre-release, for testing before the final one.

Locally: `python3 -m unittest discover -s tests`.

Contact: **rasgo.instruments@gmail.com**

---

## Português

Todos os instrumentos da família [RASGO](https://rasgoinstruments.arquiviagem.net/),
de Lúcio de Araújo, num download por sistema. A suíte é uma foto da
família: reúne a **última release oficial** de cada instrumento, byte a
byte como o repositório dele publicou, conferida pelo tamanho e pelo
SHA-256 que o GitHub informa. Cada instrumento segue com repositório,
versões, site e licença próprios, e também se baixa sozinho.

- **Windows:** um instalador com uma caixa por instrumento, todas marcadas.
  Ele roda o instalador oficial de cada um: cada instrumento fica onde
  ficaria instalado sozinho, com atalho e desinstalador próprios.
- **macOS:** os `.app` oficiais (Universal 2), para arrastar de uma vez para
  Aplicativos; o `READ ME.txt` explica a primeira abertura.
- **Ubuntu, Debian e Mint:** os `.deb` oficiais e o `./install.sh`.
- **Outras distribuições:** os AppImages oficiais e o `./install.sh` para o
  usuário atual, sem root, com atalhos no menu; o `./uninstall.sh` remove
  exatamente isso.

Cada pacote leva o `SUITE.txt`, com a versão de cada instrumento, a release
de origem e o SHA-256 de cada arquivo. Os scripts são AGPL-3.0-or-later;
cada instrumento mantém a licença dele.

## Français

Tous les instruments de la famille [RASGO](https://rasgoinstruments.arquiviagem.net/),
de Lúcio de Araújo, en un seul téléchargement par système. La suite est un
instantané de la famille : elle réunit la **dernière version officielle** de
chaque instrument, octet pour octet telle que son dépôt l'a publiée,
vérifiée par la taille et le SHA-256 indiqués par GitHub. Chaque instrument
garde son dépôt, ses versions, son site et sa licence, et se télécharge
aussi seul. Windows : un installeur qui lance l'installeur officiel de
chaque instrument. macOS : les `.app` officiels à glisser dans Applications.
Linux : les `.deb` officiels ou les AppImages, chacun avec `./install.sh`.
`SUITE.txt` donne la version, l'origine et le SHA-256 de chaque fichier.

## Español

Todos los instrumentos de la familia [RASGO](https://rasgoinstruments.arquiviagem.net/),
de Lúcio de Araújo, en una descarga por sistema. La suite es una foto de la
familia: reúne la **última versión oficial** de cada instrumento, byte a
byte como la publicó su repositorio, comprobada por el tamaño y el SHA-256
que informa GitHub. Cada instrumento mantiene su repositorio, versiones,
sitio y licencia, y también se descarga solo. Windows: un instalador que
ejecuta el instalador oficial de cada instrumento. macOS: los `.app`
oficiales para arrastrar a Aplicaciones. Linux: los `.deb` oficiales o los
AppImages, cada uno con `./install.sh`. `SUITE.txt` indica la versión, el
origen y el SHA-256 de cada archivo.
