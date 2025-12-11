"""
Script para testar a extração e atualização de status dos XMLs existentes.
"""

from pathlib import Path
from nfe_search import DatabaseManager, XMLProcessor
import logging

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    BASE = Path(__file__).parent
    XML_DIR = BASE / "xmls"
    db = DatabaseManager(BASE / "notas.db")
    parser = XMLProcessor()
    
    logger.info("Iniciando atualização de status dos XMLs existentes...")
    
    xml_files = list(XML_DIR.rglob("*.xml"))
    total = len(xml_files)
    processados = 0
    atualizados = 0
    erros = 0
    
    for xml_file in xml_files:
        try:
            xml_txt = xml_file.read_text(encoding="utf-8")
            
            # Extrai chave
            from lxml import etree
            tree = etree.fromstring(xml_txt.encode('utf-8'))
            
            chave = None
            infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
            if infnfe is not None:
                chave = infnfe.attrib.get('Id', '')[-44:]
            else:
                infcte = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
                if infcte is not None:
                    chave = infcte.attrib.get('Id', '')[-44:]
            
            if not chave:
                continue
            
            # Extrai status
            cStat, xMotivo = parser.extract_status_from_xml(xml_txt)
            
            if cStat and xMotivo:
                db.set_nf_status(chave, cStat, xMotivo)
                atualizados += 1
                logger.info(f"✓ {xml_file.name}: {cStat} - {xMotivo}")
            else:
                logger.debug(f"⚠ {xml_file.name}: Sem status no XML")
            
            processados += 1
            
            if processados % 100 == 0:
                logger.info(f"Progresso: {processados}/{total} ({atualizados} atualizados)")
                
        except Exception as e:
            erros += 1
            logger.error(f"✗ Erro em {xml_file.name}: {e}")
    
    logger.info("="*60)
    logger.info(f"RESUMO:")
    logger.info(f"  Total de XMLs: {total}")
    logger.info(f"  Processados: {processados}")
    logger.info(f"  Status atualizados: {atualizados}")
    logger.info(f"  Erros: {erros}")
    logger.info("="*60)

if __name__ == "__main__":
    main()
