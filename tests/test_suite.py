"""Testes da montagem da suíte, sem rede: python3 -m unittest discover -s tests"""

import json
import pathlib
import sys
import tarfile
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import suite  # noqa: E402

# Os nomes das releases de 17-19/11/2026 (nomes antigos e do padrão novo
# misturados, como estão) e os nomes que cada uma terá no padrão de 18/11.
RELEASES = {
    "antitotem": ["antitotem-0.3.1-Darwin.dmg", "antitotem-0.3.1-linux-x86_64.AppImage",
                  "antitotem-0.3.1-linux-x86_64.tar.gz", "antitotem-0.3.1-Linux.deb",
                  "antitotem-0.3.1-win64.exe", "antitotem-0.3.1-win64.zip"],
    "batruc": ["batruc-0.1.5-linux-x86_64.AppImage", "batruc-0.1.5-linux-x86_64.deb",
               "batruc-0.1.5-linux-x86_64.tar.gz", "batruc-0.1.5-macos-universal.dmg",
               "batruc-0.1.5-windows-x64.exe", "batruc-0.1.5-windows-x64.zip"],
    "navalha2": ["navalha2-0.2.2-Darwin.dmg", "navalha2-0.2.2-linux-x86_64.AppImage",
                 "navalha2-0.2.2-linux-x86_64.tar.gz", "navalha2-0.2.2-win64.exe",
                 "navalha2-0.2.2-win64.zip", "navalha2_0.2.2_x86_64.deb"],
    "rasgo-synth-asterismus": ["rasgo-synth-asterismus-0.5.2-Darwin.dmg",
                               "rasgo-synth-asterismus-0.5.2-Linux.deb",
                               "rasgo-synth-asterismus-0.5.2-Linux.tar.gz",
                               "rasgo-synth-asterismus-0.5.2-win64.exe",
                               "rasgo-synth-asterismus-0.5.2-win64.zip"],
    "rasgo-synth-studio": ["rasgo-synth-studio-0.2.1-linux-x86_64.AppImage",
                           "rasgo-synth-studio-0.2.1-linux-x86_64.deb",
                           "rasgo-synth-studio-0.2.1-linux-x86_64.tar.gz",
                           "rasgo-synth-studio-0.2.1-macos-universal.dmg",
                           "rasgo-synth-studio-0.2.1-windows-x64.exe",
                           "rasgo-synth-studio-0.2.1-windows-x64.zip", "SHA256SUMS"],
}


def padrao_novo(id_, versao):
    return ["%s-%s-%s" % (id_, versao, s) for s in
            ("linux-x86_64.AppImage", "linux-x86_64.deb", "linux-x86_64.tar.gz",
             "macos-universal.dmg", "windows-x64.exe", "windows-x64.zip")]


def assets(nomes):
    return [{"name": n, "size": 10 + k, "digest": "sha256:" + "%064x" % k,
             "browser_download_url": "https://example.invalid/" + n} for k, n in enumerate(nomes)]


def release(nomes, tag="v1.0.0", pre=False):
    return {"tag_name": tag, "prerelease": pre, "draft": False, "assets": assets(nomes)}


class Padroes(unittest.TestCase):
    def setUp(self):
        self.suite = {i["id"]: i for i in suite.carregar_suite()["instrumentos"]}

    def test_lista_tem_os_nove(self):
        self.assertEqual(len(self.suite), 9)
        for i in self.suite.values():
            for sis in suite.SISTEMAS:
                self.assertIn(sis, i, i["id"])

    def test_releases_de_hoje(self):
        for id_, nomes in RELEASES.items():
            item = suite.resolver_instrumento(self.suite[id_], release(nomes), "AGPL-3.0")
            self.assertEqual(set(item["arquivos"]), set(suite.SISTEMAS))
        ast = suite.resolver_instrumento(self.suite["rasgo-synth-asterismus"],
                                         release(RELEASES["rasgo-synth-asterismus"]), "GPL-3.0")
        self.assertEqual(ast["arquivos"]["portatil"]["tipo"], "tar")

    def test_padrao_novo_de_cada_instrumento(self):
        # quando cada instrumento trocar para o padrão de 18/11, a suíte segue
        for id_, inst in self.suite.items():
            base = inst["repo"].split("/")[1].replace("-juce", "")
            item = suite.resolver_instrumento(inst, release(padrao_novo(base, "9.9.9")), "AGPL-3.0")
            self.assertEqual(item["arquivos"]["windows"]["nome"], "%s-9.9.9-windows-x64.exe" % base)
            self.assertEqual(item["arquivos"]["portatil"]["tipo"], "appimage", id_)

    def test_asterismus_prefere_appimage_quando_houver(self):
        nomes = RELEASES["rasgo-synth-asterismus"] + ["rasgo-synth-asterismus-0.6.0-linux-x86_64.AppImage"]
        item = suite.resolver_instrumento(self.suite["rasgo-synth-asterismus"], release(nomes), "GPL-3.0")
        self.assertEqual(item["arquivos"]["portatil"]["tipo"], "appimage")


class Falhas(unittest.TestCase):
    def setUp(self):
        self.inst = {i["id"]: i for i in suite.carregar_suite()["instrumentos"]}["batruc"]

    def test_arquivo_faltando(self):
        nomes = [n for n in RELEASES["batruc"] if not n.endswith(".dmg")]
        with self.assertRaises(suite.Falha):
            suite.resolver_instrumento(self.inst, release(nomes), "AGPL-3.0")

    def test_dois_arquivos_para_um_sistema(self):
        nomes = RELEASES["batruc"] + ["batruc-0.1.5-win64.exe"]
        with self.assertRaises(suite.Falha):
            suite.resolver_instrumento(self.inst, release(nomes), "AGPL-3.0")

    def test_pre_release(self):
        with self.assertRaises(suite.Falha):
            suite.resolver_instrumento(self.inst, release(RELEASES["batruc"], pre=True), "AGPL-3.0")

    def test_sem_sha256(self):
        a = assets(RELEASES["batruc"])
        for x in a:
            x.pop("digest")
        with self.assertRaises(suite.Falha):
            suite.escolher(a, self.inst["deb"]["arquivo"], "batruc/deb")

    def test_conferir_tamanho_e_soma(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "x.deb"
            p.write_bytes(b"rasgo")
            arq = {"nome": "x.deb", "tamanho": 5, "sha256": suite.sha256(p)}
            suite.conferir(p, arq)
            with self.assertRaises(suite.Falha):
                suite.conferir(p, dict(arq, tamanho=6))
            with self.assertRaises(suite.Falha):
                suite.conferir(p, dict(arq, sha256="0" * 64))


class Pacotes(unittest.TestCase):
    """Monta os pacotes Linux e o .nsi com arquivos falsos."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.tmp.name)
        self.dl, self.dist = base / "dl", base / "dist"
        self.dl.mkdir()
        lock = {"nome": "RASGO Suite", "instrumentos": []}
        for inst in suite.carregar_suite()["instrumentos"]:
            base_nome = inst["repo"].split("/")[1].replace("-juce", "")
            item = suite.resolver_instrumento(inst, release(padrao_novo(base_nome, "1.2.3"), "v1.2.3"),
                                              "AGPL-3.0")
            for arq in item["arquivos"].values():
                (self.dl / arq["nome"]).write_bytes(b"x")
            lock["instrumentos"].append(item)
        self.lock = base / "lock.json"
        self.lock.write_text(json.dumps(lock), encoding="utf-8")
        self.args = ["--lock", str(self.lock), "--pasta", str(self.dl), "--versao", "2026.11",
                     "--saida", str(self.dist)]

    def tearDown(self):
        self.tmp.cleanup()

    def test_deb(self):
        self.assertEqual(suite.main(["deb"] + self.args), 0)
        with tarfile.open(self.dist / "rasgo-suite-2026.11-linux-x86_64.tar.gz") as t:
            nomes = t.getnames()
            self.assertEqual(len([n for n in nomes if n.endswith(".deb")]), 9)
            self.assertIn("rasgo-suite-2026.11-linux/install.sh", nomes)
            self.assertEqual(t.getmember("rasgo-suite-2026.11-linux/install.sh").mode, 0o755)
            texto = t.extractfile("rasgo-suite-2026.11-linux/SUITE.txt").read().decode()
            self.assertIn("Maestruc 1.2.3", texto)

    def test_portatil(self):
        self.assertEqual(suite.main(["portatil"] + self.args), 0)
        raiz = "rasgo-suite-2026.11-linux-appimage"
        with tarfile.open(self.dist / "rasgo-suite-2026.11-linux-x86_64-appimage.tar.gz") as t:
            lista = t.extractfile(raiz + "/apps/apps.txt").read().decode().split("\n")
            self.assertEqual(len([l for l in lista if l]), 9)
            self.assertIn(raiz + "/uninstall.sh", t.getnames())
            self.assertIn("appimage|navalha2-1.2.3-linux-x86_64.AppImage|navalha2|Navalha 2|Navalha 2|",
                          lista)

    def test_nsi(self):
        self.assertEqual(suite.main(["windows", "--so-script"] + self.args), 0)
        nsi = (self.dist / "rasgo-suite.nsi").read_text(encoding="utf-8")
        self.assertEqual(nsi.count("ExecWait"), 9)
        for campo in ("@VERSAO@", "@SAIDA@", "@SECOES@", "@DESCRICOES@"):
            self.assertNotIn(campo, nsi)
        self.assertIn('Section "Navalha 2 1.2.3" SEC4', nsi)
        self.assertIn('/S\' $0', nsi)

    def test_versao_fora_do_padrao(self):
        args = list(self.args)
        args[args.index("2026.11")] = "1.0"
        self.assertEqual(suite.main(["deb"] + args), 1)


if __name__ == "__main__":
    unittest.main()
