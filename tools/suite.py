#!/usr/bin/env python3
"""Monta a RASGO Suite a partir das últimas releases oficiais de cada instrumento.

A suíte é uma foto do conjunto: não recompila nada. Cada arquivo que entra é
byte a byte o que o repositório do instrumento publicou, conferido pelo
tamanho e pelo SHA-256 que o GitHub informa. Se um arquivo falta ou não
confere, nada sai: uma suíte com metade dos instrumentos parece completa.

Só biblioteca padrão do Python. Etapas (cada uma lê o que a anterior deixou):

  suite.py resolver --saida build/lock.json
      lê suite.json, pergunta ao GitHub a última release (não pré-release)
      de cada instrumento, escolhe o arquivo de cada sistema e a licença.
  suite.py baixar  --lock build/lock.json --sistema linux --pasta build/dl
      baixa e confere os arquivos de um sistema (windows, macos, deb,
      portatil ou todos).
  suite.py deb      --lock … --pasta build/dl --versao 2026.11 --saida dist
  suite.py portatil --lock … --pasta build/dl --versao 2026.11 --saida dist
  suite.py windows  --lock … --pasta build/dl --versao 2026.11 --saida dist
      (gera o .nsi e chama o makensis; roda em Linux)
  suite.py macos    --lock … --pasta build/dl --versao 2026.11 --saida dist
      (usa hdiutil; só em macOS)
  suite.py suite-txt --lock … --versao 2026.11 --saida dist

O token do GitHub (GH_TOKEN ou GITHUB_TOKEN), quando existe, só evita o
limite de chamadas anônimas.
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.github.com"
SISTEMAS = ("windows", "macos", "deb", "portatil")
NOME_PACOTE = "rasgo-suite-{versao}-{sufixo}"
SUFIXOS = {
    "windows": "windows-x64.exe",
    "macos": "macos-universal.dmg",
    "deb": "linux-x86_64.tar.gz",
    "portatil": "linux-x86_64-appimage.tar.gz",
}


class Falha(Exception):
    pass


# ---- GitHub ---------------------------------------------------------------

def _pedido(url, aceitar="application/vnd.github+json"):
    cab = {"Accept": aceitar, "User-Agent": "rasgo-suite"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(API):
        cab["Authorization"] = "Bearer " + token
    return urllib.request.Request(url, headers=cab)


def api(caminho):
    with urllib.request.urlopen(_pedido(API + caminho), timeout=60) as r:
        return json.load(r)


# ---- resolver -------------------------------------------------------------

def carregar_suite(caminho=None):
    return json.loads(pathlib.Path(caminho or RAIZ / "suite.json").read_text(encoding="utf-8"))


def escolher(assets, padrao, onde):
    """O único arquivo da release que casa com o padrão. Zero ou mais de um é falha.

    `padrao` pode ser uma lista, em ordem de preferência: vale o primeiro
    padrão que encontra arquivo (o Asterismus, por exemplo, ainda não tem
    AppImage e entra no pacote portátil pelo .tar.gz).
    """
    padroes = padrao if isinstance(padrao, list) else [padrao]
    achados = []
    for pad in padroes:
        rx = re.compile(pad)
        achados = [a for a in assets if rx.search(a["name"])]
        if achados:
            break
    if len(achados) != 1:
        nomes = ", ".join(a["name"] for a in assets) or "(release sem arquivos)"
        raise Falha("%s: %d arquivos casam com %s (há: %s)" % (onde, len(achados), " ou ".join(padroes), nomes))
    a = achados[0]
    digest = a.get("digest") or ""
    if not digest.startswith("sha256:"):
        raise Falha("%s: o GitHub não informa o SHA-256 de %s" % (onde, a["name"]))
    return {"nome": a["name"], "tamanho": a["size"], "sha256": digest[len("sha256:"):],
            "url": a["browser_download_url"]}


def resolver_instrumento(inst, release, licenca):
    if release.get("prerelease") or release.get("draft"):
        raise Falha("%s: a última release (%s) é pré-release" % (inst["id"], release.get("tag_name")))
    item = {"id": inst["id"], "nome": inst["nome"], "repo": inst["repo"], "site": inst["site"],
            "tag": release["tag_name"], "versao": release["tag_name"].lstrip("v"),
            "licenca": licenca, "arquivos": {}}
    for sis in SISTEMAS:
        cfg = inst[sis]
        arq = escolher(release["assets"], cfg["arquivo"], "%s/%s" % (inst["id"], sis))
        arq.update({k: v for k, v in cfg.items() if k != "arquivo"})
        if sis == "portatil" and cfg.get("tipo") == "auto":
            arq["tipo"] = "appimage" if arq["nome"].endswith(".AppImage") else "tar"
        item["arquivos"][sis] = arq
    return item


def cmd_resolver(a):
    suite = carregar_suite(a.suite)
    lock = {"nome": suite["nome"], "instrumentos": []}
    erros = []
    for inst in suite["instrumentos"]:
        try:
            release = api("/repos/%s/releases/latest" % inst["repo"])
            lic = (api("/repos/%s/license" % inst["repo"]).get("license") or {}).get("spdx_id") or "?"
            lock["instrumentos"].append(resolver_instrumento(inst, release, lic))
            print("%-24s %-8s %s" % (inst["id"], release["tag_name"], lic))
        except Falha as e:
            erros.append(str(e))
    if erros:
        raise Falha("a suíte não sai:\n  " + "\n  ".join(erros))
    saida = pathlib.Path(a.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("lock: %s (%d instrumentos)" % (saida, len(lock["instrumentos"])))


# ---- baixar e conferir ----------------------------------------------------

def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def conferir(caminho, arq):
    tam = caminho.stat().st_size
    if tam != arq["tamanho"]:
        raise Falha("%s: %d bytes, a release diz %d" % (arq["nome"], tam, arq["tamanho"]))
    soma = sha256(caminho)
    if soma != arq["sha256"]:
        raise Falha("%s: SHA-256 %s, a release diz %s" % (arq["nome"], soma, arq["sha256"]))


def sistemas_de(nome):
    return SISTEMAS if nome == "todos" else (nome,)


def cmd_baixar(a):
    lock = json.loads(pathlib.Path(a.lock).read_text(encoding="utf-8"))
    pasta = pathlib.Path(a.pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for inst in lock["instrumentos"]:
        for sis in sistemas_de(a.sistema):
            arq = inst["arquivos"][sis]
            destino = pasta / arq["nome"]
            if destino.exists():
                try:
                    conferir(destino, arq)
                    print("já está  %s" % arq["nome"])
                    continue
                except Falha:
                    destino.unlink()
            parcial = destino.with_name(destino.name + ".parcial")
            with urllib.request.urlopen(_pedido(arq["url"], "application/octet-stream"), timeout=300) as r, \
                    open(parcial, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            conferir(parcial, arq)
            parcial.rename(destino)
            print("conferido %s" % arq["nome"])


# ---- pacotes --------------------------------------------------------------

def nome_pacote(sis, versao):
    return NOME_PACOTE.format(versao=versao, sufixo=SUFIXOS[sis])


def texto_suite(lock, versao):
    linhas = ["%s %s" % (lock["nome"], versao), "",
              "Each instrument exactly as its own repository published it.",
              "Cada instrumento exatamente como o repositório dele publicou.", ""]
    for inst in lock["instrumentos"]:
        linhas.append("%s %s  (%s)" % (inst["nome"], inst["versao"], inst["licenca"]))
        linhas.append("  https://github.com/%s/releases/tag/%s" % (inst["repo"], inst["tag"]))
        linhas.append("  %s" % inst["site"])
        for sis in SISTEMAS:
            arq = inst["arquivos"][sis]
            linhas.append("  %s  %s" % (arq["sha256"], arq["nome"]))
        linhas.append("")
    return "\n".join(linhas)


def _tar(saida, raiz_nome, entradas):
    """tar.gz com uma pasta raiz; entradas = [(caminho_no_disco, nome_dentro, modo)]."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(saida, "w:gz") as t:
        pasta = tarfile.TarInfo(raiz_nome)
        pasta.type, pasta.mode = tarfile.DIRTYPE, 0o755
        t.addfile(pasta)
        for origem, nome, modo in entradas:
            info = t.gettarinfo(str(origem), arcname="%s/%s" % (raiz_nome, nome))
            info.mode, info.uid, info.gid, info.uname, info.gname = modo, 0, 0, "", ""
            with open(origem, "rb") as f:
                t.addfile(info, f)


def _escrever_temp(pasta, nome, texto):
    p = pathlib.Path(pasta) / nome
    p.write_text(texto, encoding="utf-8")
    return p


def cmd_deb(a):
    lock, versao, dl, saida = _comum(a)
    raiz = "rasgo-suite-%s-linux" % versao
    with tempfile.TemporaryDirectory() as tmp:
        entradas = [(dl / i["arquivos"]["deb"]["nome"], "debs/" + i["arquivos"]["deb"]["nome"], 0o644)
                    for i in lock["instrumentos"]]
        entradas.append((RAIZ / "linux" / "instalar-deb.sh", "install.sh", 0o755))
        entradas.append((_escrever_temp(tmp, "SUITE.txt", texto_suite(lock, versao)), "SUITE.txt", 0o644))
        destino = saida / nome_pacote("deb", versao)
        _tar(destino, raiz, entradas)
    print(destino)


def cmd_portatil(a):
    lock, versao, dl, saida = _comum(a)
    raiz = "rasgo-suite-%s-linux-appimage" % versao
    with tempfile.TemporaryDirectory() as tmp:
        entradas, lista = [], []
        for i in lock["instrumentos"]:
            arq = i["arquivos"]["portatil"]
            modo = 0o755 if arq["tipo"] == "appimage" else 0o644
            entradas.append((dl / arq["nome"], "apps/" + arq["nome"], modo))
            # uma linha por instrumento para o install.sh: tipo|arquivo|id|nome|wmclass|binário do tar
            lista.append("|".join([arq["tipo"], arq["nome"], i["id"], i["nome"],
                                   arq.get("wmclass", i["nome"]), arq.get("binario_tar", "")]))
        entradas.append((_escrever_temp(tmp, "apps.txt", "\n".join(lista) + "\n"), "apps/apps.txt", 0o644))
        entradas.append((RAIZ / "linux" / "instalar-portatil.sh", "install.sh", 0o755))
        entradas.append((RAIZ / "linux" / "remover-portatil.sh", "uninstall.sh", 0o755))
        entradas.append((_escrever_temp(tmp, "SUITE.txt", texto_suite(lock, versao)), "SUITE.txt", 0o644))
        destino = saida / nome_pacote("portatil", versao)
        _tar(destino, raiz, entradas)
    print(destino)


def nsi(lock, versao, dl, destino):
    """O instalador do Windows: uma seção por instrumento, todas marcadas.

    Cada seção roda o instalador oficial em modo silencioso (/S): o
    instrumento fica onde ficaria instalado sozinho, com atalhos e
    desinstalador próprios.
    """
    def q(s):
        return str(s).replace("$", "$$").replace('"', '$\\"')

    secoes, descricoes = [], []
    for n, i in enumerate(lock["instrumentos"]):
        arq = i["arquivos"]["windows"]
        secoes.append('''Section "{nome} {versao}" SEC{n}
  SetOutPath "$PLUGINSDIR"
  File "{origem}"
  DetailPrint "$(instalando) {nome} {versao}"
  ExecWait '"$PLUGINSDIR\\{arquivo}" /S' $0
  Delete "$PLUGINSDIR\\{arquivo}"
  StrCmp $0 "0" pronto{n}
    StrCpy $Falhas "$Falhas$\\r$\\n{nome} ($0)"
    DetailPrint "$(falhou) {nome}: $0"
  pronto{n}:
SectionEnd'''.format(nome=q(i["nome"]), versao=q(i["versao"]), n=n,
                     origem=q(dl.resolve() / arq["nome"]), arquivo=q(arq["nome"])))
        descricoes.append('  !insertmacro MUI_DESCRIPTION_TEXT ${SEC%d} "%s %s · %s"'
                          % (n, q(i["nome"]), q(i["versao"]), q(i["licenca"])))
    modelo = (RAIZ / "windows" / "suite.nsi.in").read_text(encoding="utf-8")
    texto = (modelo.replace("@VERSAO@", q(versao))
             .replace("@SAIDA@", q(destino.resolve()))
             .replace("@SECOES@", "\n\n".join(secoes))
             .replace("@DESCRICOES@", "\n".join(descricoes)))
    return texto


def cmd_windows(a):
    lock, versao, dl, saida = _comum(a)
    destino = saida / nome_pacote("windows", versao)
    saida.mkdir(parents=True, exist_ok=True)
    script = saida / "rasgo-suite.nsi"
    script.write_text(nsi(lock, versao, dl, destino), encoding="utf-8")
    if a.so_script:
        print(script)
        return
    subprocess.run(["makensis", "-V2", "-INPUTCHARSET", "UTF8", str(script)], check=True)
    script.unlink()
    print(destino)


def cmd_macos(a):
    lock, versao, dl, saida = _comum(a)
    destino = saida / nome_pacote("macos", versao)
    saida.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        palco = pathlib.Path(tmp) / "RASGO Suite"
        palco.mkdir()
        for i in lock["instrumentos"]:
            arq = i["arquivos"]["macos"]
            ponto = pathlib.Path(tmp) / ("vol-" + i["id"])
            # Os .dmg do CPack trazem a licença como contrato (SLA): sem
            # terminal, o hdiutil cancela. O "Y" na entrada aceita o contrato,
            # que é a licença livre do próprio instrumento.
            subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-noautoopen",
                            "-mountpoint", str(ponto), str(dl / arq["nome"])], check=True,
                           input=b"Y\n" * 4, stdout=subprocess.DEVNULL,
                           env=dict(os.environ, PAGER="true"))
            try:
                app = ponto / arq["app"]
                if not app.is_dir():
                    raise Falha("%s: %s não está no .dmg" % (arq["nome"], arq["app"]))
                # ditto preserva a assinatura, os atributos e os links do bundle
                subprocess.run(["ditto", str(app), str(palco / arq["app"])], check=True)
            finally:
                subprocess.run(["hdiutil", "detach", str(ponto)], check=True, stdout=subprocess.DEVNULL)
        (palco / "Applications").symlink_to("/Applications")
        (palco / "SUITE.txt").write_text(texto_suite(lock, versao), encoding="utf-8")
        shutil.copy(RAIZ / "macos" / "LEIA-ME.txt", palco / "READ ME.txt")
        if destino.exists():
            destino.unlink()
        subprocess.run(["hdiutil", "create", "-volname", "RASGO Suite %s" % versao, "-srcfolder",
                        str(palco), "-format", "UDZO", "-imagekey", "zlib-level=9", "-ov",
                        str(destino)], check=True)
    print(destino)


def cmd_suite_txt(a):
    lock = json.loads(pathlib.Path(a.lock).read_text(encoding="utf-8"))
    saida = pathlib.Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "SUITE.txt").write_text(texto_suite(lock, a.versao), encoding="utf-8")
    print(saida / "SUITE.txt")


def cmd_listar(a):
    """Uma linha por instrumento com um campo do lock (para os testes do workflow)."""
    lock = json.loads(pathlib.Path(a.lock).read_text(encoding="utf-8"))
    for inst in lock["instrumentos"]:
        valor = inst
        for parte in a.campo.split("."):
            valor = valor[parte]
        print(valor)


def _comum(a):
    lock = json.loads(pathlib.Path(a.lock).read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d{4}\.\d{2}(-rc\d+)?", a.versao):
        raise Falha("versão %r fora do padrão AAAA.MM (ou AAAA.MM-rcN)" % a.versao)
    return lock, a.versao, pathlib.Path(a.pasta), pathlib.Path(a.saida)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolver")
    r.add_argument("--suite")
    r.add_argument("--saida", default="build/lock.json")
    r.set_defaults(f=cmd_resolver)
    b = sub.add_parser("baixar")
    b.add_argument("--lock", default="build/lock.json")
    b.add_argument("--sistema", choices=SISTEMAS + ("todos",), required=True)
    b.add_argument("--pasta", default="build/dl")
    b.set_defaults(f=cmd_baixar)
    for nome, f in (("deb", cmd_deb), ("portatil", cmd_portatil), ("windows", cmd_windows),
                    ("macos", cmd_macos)):
        s = sub.add_parser(nome)
        s.add_argument("--lock", default="build/lock.json")
        s.add_argument("--pasta", default="build/dl")
        s.add_argument("--versao", required=True)
        s.add_argument("--saida", default="dist")
        if nome == "windows":
            s.add_argument("--so-script", action="store_true", help="só gera o .nsi")
        s.set_defaults(f=f)
    t = sub.add_parser("suite-txt")
    t.add_argument("--lock", default="build/lock.json")
    t.add_argument("--versao", required=True)
    t.add_argument("--saida", default="dist")
    t.set_defaults(f=cmd_suite_txt)
    li = sub.add_parser("listar")
    li.add_argument("--lock", default="build/lock.json")
    li.add_argument("--campo", required=True, help="ex.: arquivos.deb.comando")
    li.set_defaults(f=cmd_listar)
    a = p.parse_args(argv)
    try:
        a.f(a)
    except Falha as e:
        print("ERRO: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
