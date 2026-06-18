# -*- coding: utf-8 -*-
"""
Teste de regressão: nfe_search.py processar_nfse() não avançava o NSU quando
a API do Ambiente Nacional (GET /contribuintes/DFe/{NSU}) retornava
ultNSU="000000000000000" no envelope, mesmo quando o lote trazia documentos
reais com NSU próprio cada um. O sintoma real era: NFS-e novas paravam de
aparecer, porque cada execução reprocessava sempre o mesmo lote antigo sem
nunca persistir um NSU mais alto.

Uso:
    python -m unittest tests.unit.test_processar_nfse_nsu -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import unittest

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import nfe_search

XML_NFSE_VALIDO = (
    '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">'
    '<infNFSe Id="NFS' + '1' * 50 + '">'
    '<emit><CNPJ>12345678000199</CNPJ><xNome>Teste</xNome></emit>'
    '</infNFSe></NFSe>'
)


def _docs(faixa):
    return [(str(n).zfill(15), XML_NFSE_VALIDO, 'NFS-e') for n in faixa]


class TestProcessarNfseNsuWatermark(unittest.TestCase):
    def _rodar(self, fake_svc, nsu_inicial='000000000000102'):
        fake_db = MagicMock()
        fake_db.get_last_nsu_nfse.return_value = nsu_inicial
        nsu_salvos = []
        fake_db.set_last_nsu_nfse.side_effect = lambda inf, nsu: nsu_salvos.append(nsu)

        with patch('modules.nfse_service.NFSeService', return_value=fake_svc), \
             patch.object(nfe_search, 'salvar_nfse_detalhada', return_value=True):
            nfe_search.processar_nfse(
                ('12345678000199', '/fake/cert.pfx', 'senha', '12345678000199', '35'), fake_db
            )
        return nsu_salvos

    def test_avanca_nsu_via_maior_documento_quando_ultnsu_zerado(self):
        """Reproduz o bug real: ultNSU sempre '0' no envelope, mas 45 docs reais (NSU 103-147)."""
        fake_svc = MagicMock()
        fake_svc.consultar_nsu.side_effect = [{'p': 1}, {'p': 2}]
        fake_svc.extrair_cstat_nsu.side_effect = [
            ('', '000000000000000', '000000000000000'),
            ('137', '000000000000000', '000000000000000'),
        ]
        fake_svc.extrair_documentos.side_effect = [_docs(range(103, 148)), []]
        fake_svc.validar_xml.return_value = True

        nsu_salvos = self._rodar(fake_svc)

        self.assertTrue(nsu_salvos, "set_last_nsu_nfse nunca foi chamado — bug não corrigido")
        self.assertEqual(nsu_salvos[-1], '000000000000147')

    def test_usa_ultnsu_do_envelope_quando_disponivel(self):
        """Quando a API preenche ultNSU corretamente, continua usando esse valor (comportamento original preservado)."""
        fake_svc = MagicMock()
        fake_svc.consultar_nsu.side_effect = [{'p': 1}, {'p': 2}]
        fake_svc.extrair_cstat_nsu.side_effect = [
            ('', '000000000000200', '000000000000200'),
            ('137', '000000000000000', '000000000000000'),
        ]
        fake_svc.extrair_documentos.side_effect = [_docs(range(103, 108)), []]
        fake_svc.validar_xml.return_value = True

        nsu_salvos = self._rodar(fake_svc)

        self.assertEqual(nsu_salvos[-1], '000000000000200')

    def test_sem_documentos_e_sem_ultnsu_nao_avanca_e_nao_quebra(self):
        """Resposta vazia (sem docs, sem ultNSU) não deve travar nem avançar incorretamente."""
        fake_svc = MagicMock()
        fake_svc.consultar_nsu.return_value = {'p': 1}
        fake_svc.extrair_cstat_nsu.return_value = ('', '000000000000000', '000000000000000')
        fake_svc.extrair_documentos.return_value = []
        fake_svc.validar_xml.return_value = True

        nsu_salvos = self._rodar(fake_svc)

        self.assertEqual(nsu_salvos, [])

    def test_cstat_137_finaliza_sem_avancar(self):
        fake_svc = MagicMock()
        fake_svc.consultar_nsu.return_value = {'p': 1}
        fake_svc.extrair_cstat_nsu.return_value = ('137', '000000000000000', '000000000000000')
        fake_svc.extrair_documentos.return_value = []

        nsu_salvos = self._rodar(fake_svc)

        self.assertEqual(nsu_salvos, [])
        fake_svc.extrair_documentos.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
