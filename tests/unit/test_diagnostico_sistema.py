# -*- coding: utf-8 -*-
"""
Testes de modules/diagnostico_sistema.py (Problema crítico 8 — Diagnóstico do Sistema).

Usa um banco SQLite temporário com o schema mínimo necessário e mocks de rede
(_testar_conexao) — não depende de rede real nem do notas.db de produção.

Uso:
    python -m unittest tests.unit.test_diagnostico_sistema -v
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import modules.diagnostico_sistema as diag


def _criar_db_minimo(caminho: Path):
    conn = sqlite3.connect(str(caminho))
    conn.executescript("""
        CREATE TABLE notas_detalhadas (chave TEXT PRIMARY KEY, pdf_path TEXT, atualizado_em TEXT);
        CREATE TABLE certificados (cnpj_cpf TEXT, caminho TEXT, senha TEXT, informante TEXT);
        CREATE TABLE perfis_armazenamento (nome TEXT, pasta_base TEXT, ativo INTEGER);
        CREATE TABLE xmls_baixados (chave TEXT PRIMARY KEY, caminho_arquivo TEXT, baixado_em TEXT);
        CREATE TABLE nfse_config (provedor TEXT, url_customizada TEXT, ativo INTEGER);
    """)
    conn.commit()
    conn.close()


class DiagnosticoTestBase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "notas.db"
        _criar_db_minimo(self.db_path)
        self._patcher = patch.object(diag, "_db_path", return_value=self.db_path)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def _conn(self):
        return sqlite3.connect(str(self.db_path))


class TestCheckBancoIntegro(DiagnosticoTestBase):
    def test_banco_vazio_mas_integro_e_ok(self):
        r = diag.checar_banco_integro()
        self.assertEqual(r["status"], diag.OK)

    def test_banco_inexistente_retorna_erro_sem_quebrar(self):
        with patch.object(diag, "_db_path", return_value=Path("/caminho/inexistente/notas.db")):
            r = diag.checar_banco_integro()
        self.assertEqual(r["status"], diag.ERRO)


class TestCheckCertificados(DiagnosticoTestBase):
    def test_sem_certificados_e_atencao(self):
        r = diag.checar_certificados()
        self.assertEqual(r["status"], diag.ATENCAO)

    def test_certificado_com_caminho_inexistente_e_erro(self):
        conn = self._conn()
        conn.execute("INSERT INTO certificados VALUES ('123', '/nao/existe.pfx', '', '123')")
        conn.commit()
        conn.close()
        r = diag.checar_certificados()
        self.assertEqual(r["status"], diag.ERRO)
        self.assertIn("inválido", r["detalhe"])

    def test_certificado_vencido_sintetico_e_erro(self):
        from tests.unit.test_certificate_manager import _gerar_pfx_sintetico
        caminho = Path(self._tmpdir.name) / "vencido.pfx"
        _gerar_pfx_sintetico(str(caminho), "senha123", dias_para_vencer=-5)
        conn = self._conn()
        conn.execute("INSERT INTO certificados VALUES ('999', ?, 'senha123', '999')", (str(caminho),))
        conn.commit()
        conn.close()
        r = diag.checar_certificados()
        self.assertEqual(r["status"], diag.ERRO)
        self.assertIn("vencido", r["detalhe"].lower())

    def test_certificado_valido_sintetico_e_ok(self):
        from tests.unit.test_certificate_manager import _gerar_pfx_sintetico
        caminho = Path(self._tmpdir.name) / "valido.pfx"
        _gerar_pfx_sintetico(str(caminho), "senha123", dias_para_vencer=300)
        conn = self._conn()
        conn.execute("INSERT INTO certificados VALUES ('111', ?, 'senha123', '111')", (str(caminho),))
        conn.commit()
        conn.close()
        r = diag.checar_certificados()
        self.assertEqual(r["status"], diag.OK)


class TestCheckCaminhosEPdfs(DiagnosticoTestBase):
    def test_sem_xmls_registrados_e_atencao(self):
        r = diag.checar_caminhos_xml()
        self.assertEqual(r["status"], diag.ATENCAO)

    def test_xml_existente_e_ok(self):
        xml_real = Path(self._tmpdir.name) / "teste.xml"
        xml_real.write_text("<a/>", encoding="utf-8")
        conn = self._conn()
        conn.execute("INSERT INTO xmls_baixados VALUES ('chave1', ?, '2026-01-01')", (str(xml_real),))
        conn.commit()
        conn.close()
        r = diag.checar_caminhos_xml()
        self.assertEqual(r["status"], diag.OK)

    def test_xml_ausente_e_erro(self):
        conn = self._conn()
        conn.execute("INSERT INTO xmls_baixados VALUES ('chave1', '/nao/existe.xml', '2026-01-01')")
        conn.commit()
        conn.close()
        r = diag.checar_caminhos_xml()
        self.assertIn(r["status"], (diag.ATENCAO, diag.ERRO))

    def test_pdf_valido_e_ok(self):
        pdf_real = Path(self._tmpdir.name) / "teste.pdf"
        pdf_real.write_bytes(b"%PDF-1.4" + b"0" * 200)
        conn = self._conn()
        conn.execute("INSERT INTO notas_detalhadas VALUES ('chave1', ?, '2026-01-01')", (str(pdf_real),))
        conn.commit()
        conn.close()
        r = diag.checar_pdfs()
        self.assertEqual(r["status"], diag.OK)

    def test_pdf_sem_magic_bytes_e_invalido(self):
        pdf_falso = Path(self._tmpdir.name) / "falso.pdf"
        pdf_falso.write_bytes(b"NAO E UM PDF" * 20)
        conn = self._conn()
        conn.execute("INSERT INTO notas_detalhadas VALUES ('chave1', ?, '2026-01-01')", (str(pdf_falso),))
        conn.commit()
        conn.close()
        r = diag.checar_pdfs()
        self.assertIn(r["status"], (diag.ATENCAO, diag.ERRO))


class TestCheckStorage(DiagnosticoTestBase):
    def test_pasta_gravavel_e_ok(self):
        r = diag.checar_storage()
        self.assertEqual(r["status"], diag.OK)


class TestChecagensDeRede(unittest.TestCase):
    def test_internet_ok_quando_conexao_funciona(self):
        with patch.object(diag, "_testar_conexao", return_value=None):
            r = diag.checar_internet()
        self.assertEqual(r["status"], diag.OK)

    def test_internet_erro_quando_conexao_falha(self):
        with patch.object(diag, "_testar_conexao", return_value="timeout simulado"):
            r = diag.checar_internet()
        self.assertEqual(r["status"], diag.ERRO)

    def test_sefaz_ok(self):
        with patch.object(diag, "_testar_conexao", return_value=None):
            r = diag.checar_sefaz()
        self.assertEqual(r["status"], diag.OK)

    def test_sefaz_erro(self):
        with patch.object(diag, "_testar_conexao", return_value="recusado"):
            r = diag.checar_sefaz()
        self.assertEqual(r["status"], diag.ERRO)

    def test_adn_ok(self):
        with patch.object(diag, "_testar_conexao", return_value=None):
            r = diag.checar_adn_nfse()
        self.assertEqual(r["status"], diag.OK)


class TestStatusGeral(unittest.TestCase):
    def test_todos_ok_resulta_ok(self):
        resultados = [diag._item("a", diag.OK, "-"), diag._item("b", diag.OK, "-")]
        self.assertEqual(diag.status_geral(resultados), diag.OK)

    def test_um_atencao_resulta_atencao(self):
        resultados = [diag._item("a", diag.OK, "-"), diag._item("b", diag.ATENCAO, "-")]
        self.assertEqual(diag.status_geral(resultados), diag.ATENCAO)

    def test_um_erro_prevalece_sobre_atencao(self):
        resultados = [diag._item("a", diag.ATENCAO, "-"), diag._item("b", diag.ERRO, "-")]
        self.assertEqual(diag.status_geral(resultados), diag.ERRO)


class TestExecutarDiagnostico(DiagnosticoTestBase):
    def test_executa_todas_as_checagens_sem_quebrar(self):
        with patch.object(diag, "_testar_conexao", return_value=None):
            resultados = diag.executar_diagnostico()
        self.assertEqual(len(resultados), len(diag._CHECAGENS))
        for r in resultados:
            self.assertIn(r["status"], (diag.OK, diag.ATENCAO, diag.ERRO))

    def test_callback_de_progresso_e_chamado_para_cada_checagem(self):
        chamadas = []
        with patch.object(diag, "_testar_conexao", return_value=None):
            diag.executar_diagnostico(progresso=lambda i, t, n: chamadas.append((i, t, n)))
        self.assertEqual(len(chamadas), len(diag._CHECAGENS))
        self.assertEqual(chamadas[0][0], 1)
        self.assertEqual(chamadas[-1][0], len(diag._CHECAGENS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
