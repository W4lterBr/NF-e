# Auto-gerado para baixar XML completo dos selecionados
import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHAVES = ['52251012676495000152550010000135461939886626']

def main():
    from nfe_search import NFeService, DatabaseManager, XMLProcessor
    from modules.database import DatabaseManager as UIData
    db_path = project_dir / 'notas.db'
    ui_db = UIData(db_path)
    core_db = DatabaseManager(db_path)
    core_db.criar_tabela_detalhada()
    proc = XMLProcessor()

    # Carrega certificados (legado)
    certs = core_db.get_certificados()
    cert_map = {str(c[0]): c for c in certs}  # cnpj -> tuple

    total = 0
    completos = 0
    for chave in CHAVES:
        total += 1
        nota = ui_db.get_note_by_chave(chave)
        if not nota:
            logger.warning(f'Nota não encontrada no banco: {chave}')
            continue
        informante = (nota.get('informante') or '').strip()
        if not informante or informante not in cert_map:
            logger.warning(f'Certificado não encontrado para informante={informante} (chave={chave})')
            continue
        cnpj, path, senha, inf, cuf = cert_map[informante]
        svc = NFeService(path, senha, cnpj, cuf)
        # Consulta por consChNFe
        xml = svc.fetch_by_chave(chave)
        if not xml:
            logger.warning(f'Sem resposta para chave {chave}')
            continue
        # Extrai documentos retornados (podem ser vários docZip)
        docs = proc.extract_docs(xml)
        encontrou_completo = False
        for nsu, xml_doc in docs:
            doc_type = proc.detect_doc_type(xml_doc)
            if doc_type in ('nfeProc', 'NFe'):
                # Salvar como COMPLETO
                dados = DatabaseManager.extrair_dados_nfe(xml_doc, core_db)
                if dados:
                    dados['xml_status'] = 'COMPLETO'
                    dados['informante'] = informante
                    dados['nsu'] = nsu
                    core_db.salvar_nota_detalhada(dados)
                    ui_db.update_xml_status(chave, 'COMPLETO')
                    completos += 1
                    encontrou_completo = True
                    break
        if not encontrou_completo:
            logger.info(f'Chave {chave} ainda em RESUMO')
    print(f'ATUALIZACAO_SELECIONADOS: total={total}, completos={completos}')

if __name__ == '__main__':
    main()
