# -*- coding: utf-8 -*-
"""
Testes de modules/certificate_manager.py: validação de certificado (arquivo,
senha, expiração) e decisão de verificação do certificado do servidor.

Gera certificados PKCS#12 sintéticos (autoassinados) com datas de expiração
controladas — não depende de certificados reais nem de senha real.

Uso:
    python -m unittest tests.unit.test_certificate_manager -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import requests

from modules.certificate_manager import (
    validar_certificado,
    determinar_verify_para_host,
    classificar_erro_https_certificado,
    _verify_cache,
)


def _gerar_pfx_sintetico(caminho: str, senha: str, dias_para_vencer: int):
    """Gera um .pfx autoassinado com expiração em `dias_para_vencer` dias
    (negativo = já vencido) e grava no `caminho` informado."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    chave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TESTE SINTETICO")])
    agora = datetime.now(timezone.utc)

    cert = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave_privada.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=365))
        .not_valid_after(agora + timedelta(days=dias_para_vencer))
        .sign(chave_privada, hashes.SHA256())
    )

    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=b"teste",
        key=chave_privada,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(senha.encode("utf-8")),
    )
    Path(caminho).write_bytes(pfx_bytes)


class TestValidarCertificado(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.senha = "senha-teste-123"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _caminho(self, nome):
        return str(Path(self._tmpdir.name) / nome)

    def test_arquivo_inexistente(self):
        r = validar_certificado(self._caminho("nao_existe.pfx"), self.senha)
        self.assertFalse(r["valido"])
        self.assertIn("não encontrado", r["motivo"])

    def test_caminho_vazio(self):
        r = validar_certificado("", self.senha)
        self.assertFalse(r["valido"])

    def test_certificado_valido_dentro_do_prazo(self):
        caminho = self._caminho("valido.pfx")
        _gerar_pfx_sintetico(caminho, self.senha, dias_para_vencer=200)
        r = validar_certificado(caminho, self.senha)
        self.assertTrue(r["valido"])
        self.assertFalse(r["expirado"])
        self.assertIsNone(r["motivo"])
        self.assertGreater(r["dias_restantes"], 190)

    def test_certificado_vencido(self):
        caminho = self._caminho("vencido.pfx")
        _gerar_pfx_sintetico(caminho, self.senha, dias_para_vencer=-10)
        r = validar_certificado(caminho, self.senha)
        self.assertFalse(r["valido"])
        self.assertTrue(r["expirado"])
        self.assertIn("VENCIDO", r["motivo"])

    def test_certificado_vencendo_em_breve_avisa_mas_e_valido(self):
        caminho = self._caminho("vencendo.pfx")
        _gerar_pfx_sintetico(caminho, self.senha, dias_para_vencer=5)
        r = validar_certificado(caminho, self.senha)
        self.assertTrue(r["valido"])
        self.assertFalse(r["expirado"])
        self.assertIsNotNone(r["motivo"])  # avisa, mas continua usável

    def test_senha_incorreta(self):
        caminho = self._caminho("senha_errada.pfx")
        _gerar_pfx_sintetico(caminho, self.senha, dias_para_vencer=200)
        r = validar_certificado(caminho, "senha-totalmente-errada")
        self.assertFalse(r["valido"])
        self.assertIn("senha incorreta", r["motivo"].lower())


class TestDeterminarVerifyParaHost(unittest.TestCase):
    def setUp(self):
        _verify_cache.clear()

    def test_host_com_cadeia_ok(self):
        with patch("requests.get", return_value=MagicMock()):
            v = determinar_verify_para_host("https://exemplo-bom.gov.br/ws")
        self.assertTrue(v)

    def test_host_com_cadeia_mal_configurada_cai_para_false_e_loga(self):
        with patch("requests.get", side_effect=requests.exceptions.SSLError("self-signed certificate")):
            v = determinar_verify_para_host("https://exemplo-ruim.gov.br/ws")
        self.assertFalse(v)

    def test_resultado_e_cacheado_por_host(self):
        with patch("requests.get", side_effect=requests.exceptions.SSLError("erro")) as mock_get:
            v1 = determinar_verify_para_host("https://exemplo-cache.gov.br/ws")
            v2 = determinar_verify_para_host("https://exemplo-cache.gov.br/ws")
        self.assertFalse(v1)
        self.assertFalse(v2)
        mock_get.assert_called_once()  # segunda chamada não bateu na rede de novo

    def test_erro_de_rede_nao_relacionado_a_ssl_assume_seguro(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectTimeout("timeout")):
            v = determinar_verify_para_host("https://exemplo-timeout.gov.br/ws")
        self.assertTrue(v)


class TestClassificarErroHttpsCertificado(unittest.TestCase):
    def test_certificado_vencido(self):
        self.assertIsNotNone(classificar_erro_https_certificado(Exception("certificate has expired")))

    def test_certificado_revogado(self):
        self.assertIsNotNone(classificar_erro_https_certificado(Exception("certificate revoked")))

    def test_senha_incorreta(self):
        self.assertIsNotNone(classificar_erro_https_certificado(Exception("bad decrypt")))

    def test_erro_desconhecido_retorna_none(self):
        self.assertIsNone(classificar_erro_https_certificado(Exception("connection reset by peer")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
