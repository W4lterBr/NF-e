# -*- coding: utf-8 -*-
"""
Testes de modules/log_categorias.py: logs separados por categoria
(nfe, cte, nfse, nfce, pdf, storage, database) — Problema crítico 7.

Uso:
    python -m unittest tests.unit.test_log_categorias -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import modules.log_categorias as log_categorias
from modules.log_categorias import log_falha, get_logger_categoria, CATEGORIAS_VALIDAS


class TestLogCategorias(unittest.TestCase):
    def _fechar_handlers(self):
        import logging
        for cat in CATEGORIAS_VALIDAS:
            logger = logging.getLogger(f"categoria.{cat}")
            for h in list(logger.handlers):
                h.close()
                logger.removeHandler(h)

    def setUp(self):
        # Isola em diretório temporário e zera o cache de loggers entre testes
        self._fechar_handlers()
        log_categorias._loggers_categoria.clear()
        self._tmpdir = tempfile.TemporaryDirectory()
        self._patcher = patch.object(log_categorias, "_get_log_dir", return_value=Path(self._tmpdir.name))
        self._patcher.start()

    def tearDown(self):
        self._fechar_handlers()
        log_categorias._loggers_categoria.clear()
        self._patcher.stop()
        self._tmpdir.cleanup()

    def _ler_log(self, categoria):
        caminho = Path(self._tmpdir.name) / f"{categoria}.log"
        return caminho.read_text(encoding="utf-8") if caminho.exists() else ""

    def test_todas_as_7_categorias_existem(self):
        self.assertEqual(set(CATEGORIAS_VALIDAS), {"nfe", "cte", "nfse", "nfce", "pdf", "storage", "database"})

    def test_categoria_invalida_levanta_erro(self):
        with self.assertRaises(ValueError):
            get_logger_categoria("categoria_que_nao_existe")

    def test_cada_categoria_grava_no_proprio_arquivo(self):
        for cat in CATEGORIAS_VALIDAS:
            log_falha(cat, documento=f"doc-{cat}", chave="X" * 10, cnpj="12345678000199", erro=f"erro-{cat}")
        for cat in CATEGORIAS_VALIDAS:
            conteudo = self._ler_log(cat)
            self.assertIn(f"doc-{cat}", conteudo)
            self.assertIn(f"erro-{cat}", conteudo)
            # não deve aparecer nos arquivos de outras categorias
            for outra in CATEGORIAS_VALIDAS:
                if outra != cat:
                    self.assertNotIn(f"doc-{cat}", self._ler_log(outra))

    def test_campos_obrigatorios_no_log(self):
        log_falha("nfe", documento="NF 123", chave="1" * 44, cnpj="99887766000155", erro="falha simulada")
        conteudo = self._ler_log("nfe")
        self.assertIn("documento=NF 123", conteudo)
        self.assertIn("chave=" + "1" * 44, conteudo)
        self.assertIn("cnpj=99887766000155", conteudo)
        self.assertIn("erro=falha simulada", conteudo)

    def test_traceback_incluido_quando_ha_excecao_ativa(self):
        try:
            raise RuntimeError("erro proposital")
        except RuntimeError as e:
            log_falha("pdf", documento="teste", erro=e)
        conteudo = self._ler_log("pdf")
        self.assertIn("Traceback", conteudo)
        self.assertIn("RuntimeError", conteudo)

    def test_sem_excecao_ativa_nao_inclui_traceback(self):
        log_falha("storage", documento="teste", erro="erro manual sem exception")
        conteudo = self._ler_log("storage")
        self.assertNotIn("Traceback", conteudo)

    def test_campos_extras_aparecem_no_log(self):
        log_falha("database", documento="teste", erro="erro", nsu="000000000012345", status_http=500)
        conteudo = self._ler_log("database")
        self.assertIn("nsu=000000000012345", conteudo)
        self.assertIn("status_http=500", conteudo)

    def test_nivel_warning_nao_aparece_como_error(self):
        log_falha("cte", documento="teste-warning", erro="aviso", nivel="WARNING")
        conteudo = self._ler_log("cte")
        self.assertIn("[WARNING]", conteudo)
        self.assertNotIn("[ERROR]", conteudo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
