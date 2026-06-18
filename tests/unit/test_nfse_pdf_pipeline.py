# -*- coding: utf-8 -*-
"""
Testes do pipeline de PDF/DANFSe de NFS-e.

Cobre:
  - extracao da chave de acesso (infNFSe Id, ChaveAcesso, XML municipal ABRASF)
  - consultar_danfse_oficial() / NFSeService.consultar_danfse() com a sessao HTTP
    mockada (sem rede real, sem certificado digital real)
  - geracao local do DANFSe (gerar_danfse_profissional): fallback WeasyPrint -> ReportLab

Nao depende de rede, certificado real ou banco de dados. Roda isolado.

Uso:
    python -m pytest tests/unit/test_nfse_pdf_pipeline.py -v
    python tests/unit/test_nfse_pdf_pipeline.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import requests

from modules.nfse_service import (
    extrair_chave_nfse,
    consultar_danfse_oficial,
    DANFSE_TAMANHO_MINIMO,
    NFSeService,
)


CHAVE_NACIONAL = "3" * 50

XML_NACIONAL = f"""<?xml version="1.0" encoding="UTF-8"?>
<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe Id="NFS{CHAVE_NACIONAL}">
    <nNFSe>1234</nNFSe>
    <emit><CNPJ>12345678000199</CNPJ><xNome>Empresa Teste</xNome></emit>
    <DPS><infDPS>
      <dhEmi>2026-06-01T10:00:00-03:00</dhEmi>
      <toma><CNPJ>98765432000111</CNPJ><xNome>Tomador Teste</xNome></toma>
      <serv><cServ><xDescServ>Servico Teste</xDescServ></cServ></serv>
      <valores><vServPrest><vServ>100.00</vServ></vServPrest></valores>
    </infDPS></DPS>
  </infNFSe>
</NFSe>"""

XML_CHAVE_ACESSO = """<?xml version="1.0" encoding="UTF-8"?>
<Nfse><ChaveAcesso>CHAVE-MUNICIPAL-XYZ-123</ChaveAcesso><Numero>55</Numero></Nfse>"""

XML_ABRASF_MUNICIPAL = """<?xml version="1.0" encoding="UTF-8"?>
<CompNfse xmlns="http://www.abrasf.org.br/nfse.xsd">
  <Nfse><InfNfse Id="NFS9988">
    <Numero>9988</Numero>
    <CodigoVerificacao>VERIF123</CodigoVerificacao>
    <DataEmissao>2026-05-10T14:30:00</DataEmissao>
    <PrestadorServico>
      <IdentificacaoPrestador><Cnpj>11122233000144</Cnpj></IdentificacaoPrestador>
      <RazaoSocial>Prestador ABRASF Ltda</RazaoSocial>
    </PrestadorServico>
    <TomadorServico>
      <IdentificacaoTomador><CpfCnpj><Cnpj>55566677000188</Cnpj></CpfCnpj></IdentificacaoTomador>
      <RazaoSocial>Tomador ABRASF SA</RazaoSocial>
    </TomadorServico>
    <Servico><Valores><ValorServicos>250.00</ValorServicos><ValorIss>12.50</ValorIss></Valores>
    <Discriminacao>Servico ABRASF</Discriminacao></Servico>
  </InfNfse></Nfse>
</CompNfse>"""


# ---------------------------------------------------------------------------
# extrair_chave_nfse()
# ---------------------------------------------------------------------------

class TestExtrairChaveNfse(unittest.TestCase):
    def test_xml_nacional_com_infnfse_id(self):
        chave, erro = extrair_chave_nfse(XML_NACIONAL)
        self.assertEqual(chave, CHAVE_NACIONAL)
        self.assertIsNone(erro)

    def test_xml_com_chaveacesso(self):
        chave, erro = extrair_chave_nfse(XML_CHAVE_ACESSO)
        self.assertEqual(chave, "CHAVE-MUNICIPAL-XYZ-123")
        self.assertIsNone(erro)

    def test_xml_municipal_abrasf_transcrito(self):
        chave, erro = extrair_chave_nfse(XML_ABRASF_MUNICIPAL)
        self.assertEqual(chave, "9988")
        # ABRASF nao usa o padrao nacional de 50 digitos -> sinalizado, mas a chave é retornada
        self.assertIsNotNone(erro)

    def test_xml_sem_chave_loga_erro(self):
        chave, erro = extrair_chave_nfse("<Nfse><Numero>1</Numero></Nfse>")
        self.assertIsNone(chave)
        self.assertIsNotNone(erro)

    def test_xml_invalido(self):
        chave, erro = extrair_chave_nfse("isto nao eh xml valido <<<")
        self.assertIsNone(chave)
        self.assertIsNotNone(erro)

    def test_xml_vazio(self):
        chave, erro = extrair_chave_nfse("")
        self.assertIsNone(chave)
        self.assertIsNotNone(erro)

    def test_id_sem_prefixo_nfs_nao_corrompe_chave(self):
        # Regressao: Id sem prefixo "NFS" nao deve ter os 3 primeiros chars cortados
        xml = XML_NACIONAL.replace(f"NFS{CHAVE_NACIONAL}", CHAVE_NACIONAL)
        chave, erro = extrair_chave_nfse(xml)
        self.assertEqual(chave, CHAVE_NACIONAL)


# ---------------------------------------------------------------------------
# NFSeService.consultar_danfse() — sessao HTTP mockada
# ---------------------------------------------------------------------------

def _build_service(ambiente="producao"):
    """Constroi um NFSeService sem ler certificado real (bypassa __init__)."""
    svc = NFSeService.__new__(NFSeService)
    svc.cert_path = "/fake/cert.pfx"
    svc.senha = "senha"
    svc.informante = "12345678000199"
    svc.cuf = "35"
    svc.ambiente = ambiente
    svc.url_base = (
        "https://adn.nfse.gov.br" if ambiente == "producao"
        else "https://adn.producaorestrita.nfse.gov.br"
    )
    svc.session = MagicMock()
    return svc


class TestConsultarDanfseHttp(unittest.TestCase):
    def test_api_retornando_pdf_valido(self):
        pdf_bytes = b"%PDF-1.4" + b"0" * 2000  # > DANFSE_TAMANHO_MINIMO, magic bytes ok
        svc = _build_service()
        svc.session.get.return_value = MagicMock(
            status_code=200, content=pdf_bytes, headers={"Content-Type": "application/pdf"}
        )
        resultado = svc.consultar_danfse(CHAVE_NACIONAL, retry=1)
        self.assertEqual(resultado, pdf_bytes)

    def test_api_retornando_404(self):
        svc = _build_service()
        resp = MagicMock(status_code=404, headers={}, content=b"")
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
        svc.session.get.return_value = resp
        with self.assertRaises(Exception):
            svc.consultar_danfse(CHAVE_NACIONAL, retry=1)

    def test_api_retornando_html_de_erro(self):
        # HTTP 200 mas corpo é HTML (pagina de erro/manutencao) — nao deve ser aceito como PDF
        svc = _build_service()
        html = b"<html><body>Servico temporariamente indisponivel</body></html>"
        svc.session.get.return_value = MagicMock(
            status_code=200, content=html, headers={"Content-Type": "text/html"}
        )
        with self.assertRaises(Exception):
            svc.consultar_danfse(CHAVE_NACIONAL, retry=1)

    def test_pdf_menor_que_tamanho_minimo_e_rejeitado(self):
        svc = _build_service()
        pdf_pequeno = b"%PDF-1.4" + b"x" * 10  # menor que DANFSE_TAMANHO_MINIMO
        self.assertLess(len(pdf_pequeno), DANFSE_TAMANHO_MINIMO)
        svc.session.get.return_value = MagicMock(
            status_code=200, content=pdf_pequeno, headers={"Content-Type": "application/pdf"}
        )
        with self.assertRaises(Exception):
            svc.consultar_danfse(CHAVE_NACIONAL, retry=1)

    def test_servidor_indisponivel_502_propaga_erro(self):
        svc = _build_service()
        resp = MagicMock(status_code=502, headers={}, content=b"")
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
        svc.session.get.return_value = resp
        with self.assertRaises(Exception):
            svc.consultar_danfse(CHAVE_NACIONAL, retry=1)


# ---------------------------------------------------------------------------
# consultar_danfse_oficial() — função única/canônica
# ---------------------------------------------------------------------------

class TestConsultarDanfseOficial(unittest.TestCase):
    def test_chave_vazia_falha_graciosamente(self):
        r = consultar_danfse_oficial("", "/fake/cert.pfx", "senha", "123", "35")
        self.assertFalse(r["ok"])
        self.assertIsNone(r["pdf_bytes"])

    def test_sucesso_retorna_oficial(self):
        fake_svc = MagicMock()
        fake_svc.consultar_danfse.return_value = b"%PDF-1.4" + b"0" * 2000
        with patch("modules.nfse_service.NFSeService", return_value=fake_svc):
            r = consultar_danfse_oficial(CHAVE_NACIONAL, "/fake/cert.pfx", "senha", "123", "35")
        self.assertTrue(r["ok"])
        self.assertEqual(r["pdf_tipo"], "OFICIAL")
        self.assertTrue(r["pdf_bytes"].startswith(b"%PDF"))

    def test_falha_da_api_retorna_ok_false_sem_excecao(self):
        fake_svc = MagicMock()
        fake_svc.consultar_danfse.side_effect = Exception("404 Not Found")
        with patch("modules.nfse_service.NFSeService", return_value=fake_svc):
            r = consultar_danfse_oficial(CHAVE_NACIONAL, "/fake/cert.pfx", "senha", "123", "35")
        self.assertFalse(r["ok"])
        self.assertIn("404", r["motivo"])

    def test_falha_ao_inicializar_certificado(self):
        with patch("modules.nfse_service.NFSeService", side_effect=FileNotFoundError("cert nao encontrado")):
            r = consultar_danfse_oficial(CHAVE_NACIONAL, "/cert/inexistente.pfx", "senha", "123", "35")
        self.assertFalse(r["ok"])


# ---------------------------------------------------------------------------
# Geração local do DANFSe (WeasyPrint -> ReportLab)
# ---------------------------------------------------------------------------

class TestGeracaoLocalDanfse(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.pdf_path = str(Path(self._tmpdir.name) / "teste.pdf")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_weasyprint_falhando_cai_para_reportlab(self):
        import gerar_danfse_profissional as gdp
        with patch.object(gdp, "_gerar_com_weasyprint", side_effect=ImportError("WeasyPrint indisponível (simulado)")):
            ok = gdp.gerar_danfse_profissional(XML_NACIONAL, self.pdf_path)
        self.assertTrue(ok)
        self.assertTrue(Path(self.pdf_path).exists())
        self.assertGreater(Path(self.pdf_path).stat().st_size, 0)

    def test_reportlab_funcionando_isoladamente(self):
        import gerar_danfse_profissional as gdp
        dados = gdp._extrair_dados_xml(XML_NACIONAL)
        dados["qr_base64"] = ""
        ok = gdp._gerar_com_reportlab(dados, self.pdf_path)
        self.assertTrue(ok)
        self.assertTrue(Path(self.pdf_path).exists())

    def test_ambos_fallbacks_falhando_retorna_false_sem_excecao(self):
        import gerar_danfse_profissional as gdp
        with patch.object(gdp, "_gerar_com_weasyprint", side_effect=ImportError("simulado")), \
             patch.object(gdp, "_gerar_com_reportlab", side_effect=Exception("simulado")):
            ok = gdp.gerar_danfse_profissional(XML_NACIONAL, self.pdf_path)
        self.assertFalse(ok)

    def test_extracao_campos_nacional_completa(self):
        import gerar_danfse_profissional as gdp
        dados = gdp._extrair_dados_xml(XML_NACIONAL)
        self.assertEqual(dados["chave"], CHAVE_NACIONAL)
        self.assertEqual(dados["numero"], "1234")
        self.assertEqual(dados["prest_cnpj"], "12345678000199")
        self.assertEqual(dados["toma_cnpj"], "98765432000111")
        self.assertEqual(dados["desc_serv"], "Servico Teste")

    def test_extracao_campos_abrasf_completa(self):
        import gerar_danfse_profissional as gdp
        dados = gdp._extrair_dados_xml(XML_ABRASF_MUNICIPAL)
        self.assertEqual(dados["numero"], "9988")
        self.assertEqual(dados["prest_cnpj"], "11122233000144")
        self.assertEqual(dados["toma_cnpj"], "55566677000188")
        self.assertEqual(dados["cod_verificacao"], "VERIF123")
        self.assertEqual(dados["v_issqn"], "12.50")


if __name__ == "__main__":
    unittest.main(verbosity=2)
