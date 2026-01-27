# -*- coding: utf-8 -*-
"""
Busca automatica de NFS-e via consulta propria com certificado digital.
Similar ao processo de NF-e e CT-e.
"""

import sys
import io
from pathlib import Path
from datetime import datetime, timedelta

# Força UTF-8 no Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

from nfse_search import NFSeDatabase, logger, URLS_MUNICIPIOS, consultar_cnpj
from modules.nfse_service import NFSeService, consultar_nfse_incremental
from lxml import etree

# Importa gerador profissional de DANFSe
try:
    from gerar_danfse_profissional import gerar_danfse_profissional
    GERADOR_PDF_DISPONIVEL = True
except ImportError:
    GERADOR_PDF_DISPONIVEL = False
    logger.warning("⚠️  Gerador de DANFSe profissional não disponível")


def gerar_pdf_nfse(xml_content, pdf_path):
    """
    Gera DANFSe profissional a partir do XML.
    Wrapper para a função gerar_danfse_profissional().
    
    Args:
        xml_content: Conteúdo XML da NFS-e
        pdf_path: Caminho onde salvar o PDF
        
    Returns:
        bool: True se PDF foi gerado com sucesso
    """
    if not GERADOR_PDF_DISPONIVEL:
        logger.warning("   ⚠️  Gerador de PDF não disponível")
        return False
    
    try:
        return gerar_danfse_profissional(xml_content, pdf_path)
    except Exception as e:
        logger.error(f"   ❌ Erro ao gerar DANFSe: {e}")
        return False


def salvar_xml_nfse(cnpj, xml_content, numero_nfse, data_emissao):
    """
    Salva XML da NFS-e em arquivo local.
    
    Args:
        cnpj: CNPJ do prestador
        xml_content: Conteudo XML completo
        numero_nfse: Numero da NFS-e
        data_emissao: Data de emissao (formato ISO ou datetime)
    
    Returns:
        Caminho do arquivo salvo ou None se erro
    """
    try:
        # Parse da data
        if isinstance(data_emissao, str):
            # Tenta varios formatos
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(data_emissao.split('T')[0] if 'T' in data_emissao else data_emissao, fmt)
                    break
                except:
                    continue
            else:
                dt = datetime.now()
        else:
            dt = data_emissao
        
        # Define estrutura de pastas: xmls/{CNPJ}/{MES-ANO}/NFSe/
        pasta_base = Path(__file__).parent / "xmls" / cnpj / dt.strftime('%m-%Y') / "NFSe"
        pasta_base.mkdir(parents=True, exist_ok=True)
        
        # Nome do arquivo
        nome_arquivo = f"NFSe_{numero_nfse}.xml"
        caminho_completo = pasta_base / nome_arquivo
        
        # Salva XML
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logger.info(f"   💾 XML salvo: {caminho_completo}")
        return str(caminho_completo)
        
    except Exception as e:
        logger.error(f"   ❌ Erro ao salvar XML: {e}")
        return None


def buscar_nfse_ambiente_nacional(db, cert_data, config_nfse, busca_completa=False):
    """
    Busca NFS-e via Ambiente Nacional (consulta propria com certificado).
    Similar ao processo de NF-e e CT-e.
    
    Args:
        db: Instancia do banco de dados
        cert_data: Tupla com dados do certificado (cnpj, path, senha, informante, cuf)
        config_nfse: Tupla com config (provedor, cod_municipio, inscricao, url)
        busca_completa: Se True, busca todos documentos (NSU=0), senão busca incremental
    
    Returns:
        Lista de NFS-e encontradas
    """
    cnpj, cert_path, senha, informante, cuf = cert_data
    provedor, cod_municipio, inscricao_municipal, url = config_nfse
    
    logger.info(f"\n{'='*70}")
    logger.info(f"BUSCANDO NFS-e VIA AMBIENTE NACIONAL")
    logger.info(f"{'='*70}")
    logger.info(f"CNPJ: {cnpj}")
    logger.info(f"Informante: {informante}")
    logger.info(f"Municipio: {cod_municipio}")
    logger.info(f"Certificado: {cert_path}")
    
    try:
        # Inicializa servico NFS-e (similar ao CTe e NFe)
        nfse_service = NFSeService(
            cert_path=cert_path,
            senha=senha,
            informante=informante,
            cuf=cuf,
            ambiente='producao'
        )
        
        logger.info("✅ Servico NFS-e inicializado com sucesso")
        
        # Consulta incremental ou completa via NSU
        if busca_completa:
            logger.info("🔄 Modo: BUSCA COMPLETA (NSU=0)")
        else:
            logger.info("📍 Modo: BUSCA INCREMENTAL (últimos documentos)")
            
        documentos = consultar_nfse_incremental(
            db=db,
            cert_path=cert_path,
            senha=senha,
            informante=informante,
            cuf=cuf,
            ambiente='producao',
            busca_completa=busca_completa
        )
        
        if not documentos:
            logger.info("📭 Nenhum documento novo encontrado")
            return []
        
        logger.info(f"✅ {len(documentos)} documento(s) encontrado(s)")
        
        # Processa cada documento
        notas_salvas = 0
        for nsu, xml_content, tipo_doc in documentos:
            try:
                # Valida XML
                if not nfse_service.validar_xml(xml_content):
                    logger.warning(f"⚠️  Documento NSU={nsu} invalido, pulando")
                    continue
                
                # Extrai informacoes basicas
                tree = etree.fromstring(xml_content.encode('utf-8'))
                
                # Sistema Nacional NFS-e - namespace
                ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
                
                # Tenta extrair chave/numero da NFS-e
                # (estrutura pode variar por municipio)
                numero_nfse = (
                    tree.findtext('.//nfse:nNFSe', namespaces=ns) or
                    tree.findtext('.//nNFSe') or
                    tree.findtext('.//Numero') or
                    tree.findtext('.//NumeroNfse') or
                    f"NSU_{nsu}"
                )
                
                data_emissao = (
                    tree.findtext('.//nfse:dhEmi', namespaces=ns) or
                    tree.findtext('.//dhEmi') or
                    tree.findtext('.//DataEmissao') or
                    datetime.now().isoformat()
                )
                
                valor_servicos = (
                    tree.findtext('.//nfse:vServ', namespaces=ns) or
                    tree.findtext('.//vServ') or
                    tree.findtext('.//ValorServicos') or
                    "0"
                )
                
                cnpj_tomador = (
                    tree.findtext('.//nfse:toma//nfse:CNPJ', namespaces=ns) or
                    tree.findtext('.//toma//CNPJ') or
                    tree.findtext('.//Tomador//IdentificacaoTomador//CpfCnpj//Cnpj') or
                    ""
                )
                
                # Salva XML
                caminho_xml = salvar_xml_nfse(
                    cnpj=cnpj,
                    xml_content=xml_content,
                    numero_nfse=numero_nfse,
                    data_emissao=data_emissao
                )
                
                if caminho_xml:
                    # Salva no banco
                    db.salvar_nfse(
                        numero=numero_nfse,
                        cnpj_prestador=cnpj,
                        cnpj_tomador=cnpj_tomador,
                        data_emissao=data_emissao,
                        valor=float(valor_servicos.replace(',', '.')),
                        xml=xml_content
                    )
                    
                    notas_salvas += 1
                    logger.info(f"   ✅ NFS-e {numero_nfse}: R$ {valor_servicos} salva")
                    
                    # Tenta baixar DANFSE (PDF) logo após salvar XML
                    try:
                        # A chave de acesso da NFS-e está no atributo Id da tag infNFSe
                        # Formato: "NFS31062001213891738000138250000000157825012270096818"
                        # Precisamos remover o prefixo "NFS" para obter a chave de 50 dígitos
                        inf_nfse = tree.find('.//nfse:infNFSe', namespaces=ns)
                        chave_acesso = None
                        
                        if inf_nfse is not None:
                            chave_id = inf_nfse.get('Id', '')
                            if chave_id and chave_id.startswith('NFS'):
                                chave_acesso = chave_id[3:]  # Remove prefixo "NFS"
                        
                        if chave_acesso:
                            logger.info(f"   📄 Baixando DANFSe OFICIAL (PDF) para {numero_nfse}...")
                            
                            # Usa o mesmo serviço NFS-e para baixar o PDF OFICIAL
                            # O DANFSe é o PDF oficial gerado pelo Ambiente Nacional
                            # Similar ao DANFE da NF-e, com layout padronizado
                            nfse_service = NFSeService(
                                cert_path=cert_path,
                                senha=senha,
                                informante=informante,
                                cuf=cuf,
                                ambiente='producao'
                            )
                            
                            # Tenta baixar com retry (3 tentativas)
                            pdf_content = nfse_service.consultar_danfse(chave_acesso, retry=3)
                            
                            if pdf_content:
                                # Salva PDF OFICIAL na mesma pasta do XML
                                pdf_path = caminho_xml.replace('.xml', '.pdf')
                                with open(pdf_path, 'wb') as f:
                                    f.write(pdf_content)
                                
                                logger.info(f"   ✅ DANFSe OFICIAL salvo: {pdf_path}")
                        else:
                            logger.warning(f"   ⚠️  NFS-e {numero_nfse} sem ChaveAcesso - PDF não disponível")
                    
                    except Exception as e_pdf:
                        logger.warning(f"   ⚠️  API indisponível: {str(e_pdf)[:100]}")
                        
                        # FALLBACK: Gera PDF local genérico
                        logger.info(f"   🔄 Gerando PDF genérico local (API indisponível)...")
                        pdf_path = caminho_xml.replace('.xml', '.pdf')
                        if gerar_pdf_nfse(xml_content, pdf_path):
                            logger.info(f"   ✅ PDF genérico salvo: {pdf_path}")
                            logger.info(f"   💡 Dica: Execute gerar_pdfs_nfse.py para tentar baixar PDFs oficiais")
                        else:
                            logger.warning(f"   ⚠️  Não foi possível gerar PDF")
                    
            except Exception as e:
                logger.error(f"   ❌ Erro ao processar NSU={nsu}: {e}")
                continue
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ BUSCA CONCLUIDA: {notas_salvas}/{len(documentos)} documento(s) salvo(s)")
        logger.info(f"{'='*70}\n")
        
        return documentos
        
    except Exception as e:
        logger.error(f"❌ Erro na busca via Ambiente Nacional: {e}")
        import traceback
        traceback.print_exc()
        return []


def processar_certificado(db, cert_data, busca_completa=False):
    """
    Processa um certificado: busca configuracoes NFS-e e executa consultas.
    
    Args:
        db: Instancia do banco de dados
        cert_data: Tupla com dados do certificado (cnpj, path, senha, informante, cuf)
        busca_completa: Se True, busca todos documentos (NSU=0)
    
    Returns:
        int: Numero de notas encontradas
    """
    cnpj, cert_path, senha, informante, cuf = cert_data
    
    logger.info(f"\n{'='*70}")
    logger.info(f"PROCESSANDO CERTIFICADO: {cnpj}")
    logger.info(f"{'='*70}")
    logger.info(f"Informante: {informante}")
    logger.info(f"UF: {cuf}")
    logger.info(f"Certificado: {cert_path}")
    
    # Busca configuracoes NFS-e para este CNPJ
    configs = db.get_config_nfse(cnpj)
    
    if not configs:
        logger.info("⚠️  Nenhuma configuracao NFS-e encontrada para este certificado")
        logger.info("   Use test_nfse_module.py para configurar")
        return 0
    
    logger.info(f"✅ {len(configs)} configuracao(oes) NFS-e encontrada(s)")
    
    total_notas = 0
    
    # Processa cada configuracao (um CNPJ pode ter multiplos municipios)
    for config in configs:
        provedor, cod_municipio, inscricao_municipal, url = config
        
        logger.info(f"\n--- Configuracao ---")
        logger.info(f"   Provedor: {provedor}")
        logger.info(f"   Municipio: {cod_municipio}")
        logger.info(f"   Inscricao: {inscricao_municipal}")
        
        # Usa consulta propria via Ambiente Nacional
        # Similar ao que fazemos com NF-e e CT-e
        logger.info("   Metodo: Consulta propria via certificado digital")
        notas = buscar_nfse_ambiente_nacional(db, cert_data, config, busca_completa=busca_completa)
        total_notas += len(notas)
        
    return total_notas


def buscar_todos_certificados(busca_completa=False):
    """
    Funcao principal: busca NFS-e para todos os certificados cadastrados.
    
    Args:
        busca_completa: Se True, busca todos documentos (NSU=0), senão busca incremental
    """
    logger.info("\n" + "="*70)
    if busca_completa:
        logger.info("BUSCA COMPLETA DE NFS-e - TODOS OS CERTIFICADOS")
    else:
        logger.info("BUSCA INCREMENTAL DE NFS-e - TODOS OS CERTIFICADOS")
    logger.info("="*70)
    logger.info("Metodo: Consulta propria via Ambiente Nacional")
    logger.info("Similar ao processo de NF-e e CT-e")
    logger.info("="*70 + "\n")
    
    # Inicializa banco
    db = NFSeDatabase()
    
    # Busca todos os certificados do banco principal
    try:
        certificados = db.get_certificados()
        
        if not certificados:
            logger.warning("⚠️  Nenhum certificado encontrado no banco de dados")
            return
        
        logger.info(f"✅ {len(certificados)} certificado(s) encontrado(s)\n")
        
        # Estatisticas
        total_processados = 0
        total_com_config = 0
        total_notas = 0
        
        # Processa cada certificado
        for cert in certificados:
            try:
                cnpj = cert[0]  # CNPJ do certificado
                notas_encontradas = processar_certificado(db, cert, busca_completa=busca_completa)
                total_processados += 1
                
                # Verifica se tem configuração NFS-e (independente de ter notas)
                configs = db.get_config_nfse(cnpj)
                if configs:
                    total_com_config += 1
                
                if notas_encontradas > 0:
                    total_notas += notas_encontradas
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar certificado: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Resumo final
        logger.info(f"\n{'='*70}")
        logger.info(f"RESUMO FINAL")
        logger.info(f"{'='*70}")
        logger.info(f"Certificados processados: {total_processados}")
        logger.info(f"Com configuracao NFS-e: {total_com_config}")
        logger.info(f"Total de notas encontradas: {total_notas}")
        logger.info(f"{'='*70}\n")
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar certificados: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    # Verifica se foi passado argumento --completa ou --all
    busca_completa = '--completa' in sys.argv or '--all' in sys.argv
    
    if busca_completa:
        logger.info("🔄 Modo: BUSCA COMPLETA (resetando NSU para 0)")
    else:
        logger.info("📍 Modo: BUSCA INCREMENTAL (continuando do último NSU)")
    
    try:
        buscar_todos_certificados(busca_completa=busca_completa)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Busca interrompida pelo usuario")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
