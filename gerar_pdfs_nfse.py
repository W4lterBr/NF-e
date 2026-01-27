# -*- coding: utf-8 -*-
"""
Script para gerar PDFs de NFS-e existentes que ainda não possuem PDF.
Processa todos os XMLs de NFS-e e tenta:
1. Baixar PDF da API (DANFSE)
2. Se falhar, gerar PDF local
"""

import sys
import io
from pathlib import Path
from time import sleep

sys.path.insert(0, str(Path(__file__).parent))

from buscar_nfse_auto import gerar_pdf_nfse, logger
from gerar_danfse_profissional import gerar_danfse_profissional
from modules.nfse_service import NFSeService
from lxml import etree
from nfse_search import NFSeDatabase


def processar_nfse_sem_pdf():
    """
    Processa todas as NFS-e que possuem XML mas não possuem PDF.
    """
    print("=" * 70)
    print("GERADOR DE PDFs PARA NFS-e EXISTENTES")
    print("=" * 70)
    
    # Busca todos os XMLs de NFS-e
    xmls_path = Path("xmls")
    xml_files = list(xmls_path.rglob("NFSe/*.xml"))
    
    print(f"\n📋 Encontrados {len(xml_files)} arquivo(s) XML de NFS-e")
    
    # Filtra apenas os que não têm PDF
    sem_pdf = []
    for xml_file in xml_files:
        pdf_file = xml_file.with_suffix('.pdf')
        if not pdf_file.exists():
            sem_pdf.append(xml_file)
    
    print(f"📄 {len(sem_pdf)} NFS-e sem PDF")
    
    if not sem_pdf:
        print("\n✅ Todas as NFS-e já possuem PDF!")
        return
    
    print(f"\n⚙️  Gerando {len(sem_pdf)} PDFs...\n")
    
    # Obtém credenciais do primeiro certificado configurado
    db = NFSeDatabase()
    certificados = db.get_certificados()
    
    nfse_service = None
    if certificados:
        # get_certificados retorna: (cnpj, caminho, senha, informante, cuf)
        cnpj, cert_path, senha, informante, cuf = certificados[0]
        
        try:
            nfse_service = NFSeService(cert_path, senha, informante, cuf, 'producao')
            print("✅ Serviço NFS-e inicializado - tentará baixar da API")
        except Exception as e:
            print(f"⚠️  Serviço NFS-e indisponível: {e}")
            print("   Apenas PDFs locais serão gerados")
    else:
        print("⚠️  Nenhum certificado encontrado - apenas PDFs locais serão gerados")
    
    # Processa cada XML
    sucesso = 0
    falha = 0
    api_sucesso = 0
    local_sucesso = 0
    
    print("\n" + "=" * 70)
    print("PROCESSANDO NFS-e")
    print("=" * 70 + "\n")
    
    for i, xml_file in enumerate(sem_pdf, 1):
        print(f"[{i}/{len(sem_pdf)}] {xml_file.name}...", end=" ")
        
        try:
            # Lê o XML
            xml_content = xml_file.read_text(encoding='utf-8')
            pdf_path = xml_file.with_suffix('.pdf')
            
            # Extrai chave de acesso
            ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
            tree = etree.fromstring(xml_content.encode('utf-8'))
            inf_nfse = tree.find('.//nfse:infNFSe', namespaces=ns)
            chave_acesso = None
            
            if inf_nfse is not None:
                chave_id = inf_nfse.get('Id', '')
                if chave_id and chave_id.startswith('NFS'):
                    chave_acesso = chave_id[3:]
            
            # Tenta baixar da API primeiro (PDF OFICIAL)
            pdf_gerado = False
            if nfse_service and chave_acesso:
                try:
                    # Usa retry=3 para tentar 3 vezes se servidor estiver instável
                    pdf_content = nfse_service.consultar_danfse(chave_acesso, retry=3)
                    if pdf_content:
                        pdf_path.write_bytes(pdf_content)
                        print("✅ API (OFICIAL)")
                        sucesso += 1
                        api_sucesso += 1
                        pdf_gerado = True
                        sleep(2)  # Rate limiting entre requisições
                except Exception as e:
                    # API falhou, tenta gerar local
                    pass
            
            # Se API falhou ou não tem serviço, gera DANFSe profissional local
            if not pdf_gerado:
                if gerar_danfse_profissional(xml_content, str(pdf_path)):
                    print("✅ Local (profissional)")
                    sucesso += 1
                    local_sucesso += 1
                else:
                    print("❌ Falhou")
                    falha += 1
        
        except Exception as e:
            print(f"❌ Erro: {e}")
            falha += 1
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"✅ Sucesso: {sucesso}")
    print(f"   - Via API (PDF OFICIAL do governo): {api_sucesso}")
    print(f"   - Gerados localmente (profissional): {local_sucesso}")
    print(f"❌ Falhas: {falha}")
    print("=" * 70)
    
    if api_sucesso > 0:
        print("\n🎉 PDFs da API são OFICIAIS (DANFSe do governo)!")
    if local_sucesso > 0:
        print("\n💡 PDFs locais têm layout profissional com QR Code")
        print("   Para obter PDFs oficiais, execute novamente quando API estabilizar")


if __name__ == "__main__":
    try:
        processar_nfse_sem_pdf()
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
