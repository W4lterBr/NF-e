# -*- coding: utf-8 -*-
"""
Busca automatica de NFS-e via consulta propria com certificado digital.
Similar ao processo de NF-e e CT-e.
"""

import sys
import io
from pathlib import Path
from datetime import datetime, timedelta

# Força UTF-8 no Windows SOMENTE ao executar diretamente como script.
# Quando importado como módulo pela GUI (.exe frozen), NÃO substituímos
# sys.stdout/stderr pois isso quebraria o stdout do processo principal.
if __name__ == "__main__" and sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Em modo dev (não-frozen), garante que o diretório-pai está no path.
# Em modo frozen (PyInstaller), os módulos já estão disponíveis sem isso.
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).parent))

from nfse_search import NFSeDatabase, logger, URLS_MUNICIPIOS, consultar_cnpj
from modules.nfse_service import NFSeService, consultar_nfse_incremental
from lxml import etree

# Importa salvar_nfse_detalhada para salvar em notas_detalhadas (banco principal)
from nfe_search import salvar_nfse_detalhada

# PDF da NFS-e é baixado APENAS via API oficial do Ambiente Nacional (ADN).
# Não há geração local de PDF — município não integrado = mensagem informativa.


def salvar_xml_nfse(db, cnpj, xml_content, numero_nfse, data_emissao):
    """
    Salva XML da NFS-e usando a mesma lógica de NF-e e CT-e.
    
    🔧 CORREÇÃO (2026-02-05): Usa salvar_xml_por_certificado() para garantir:
    1. Salvamento local em xmls/ (backup)
    2. Salvamento no storage configurado (se existir)
    3. Nome do certificado usado nas pastas do storage
    
    Args:
        db: Instância do banco de dados (NFSeDatabase)
        cnpj: CNPJ do prestador
        xml_content: Conteudo XML completo
        numero_nfse: Numero da NFS-e
        data_emissao: Data de emissao (formato ISO ou datetime)
    
    Returns:
        Tupla (caminho_local, caminho_storage) com os caminhos onde o XML foi salvo
        Retorna (caminho_local, None) se storage não configurado
        Retorna (None, None) em caso de erro
    """
    try:
        from nfe_search import salvar_xml_por_certificado
        from modules.database import DatabaseManager
        
        # Salva localmente (backup) usando função padrão
        resultado_local = salvar_xml_por_certificado(xml_content, cnpj)
        caminho_local = resultado_local[0] if isinstance(resultado_local, tuple) else resultado_local
        logger.info(f"   💾 XML salvo localmente (backup): {caminho_local}")
        
        # Verifica se há storage configurado
        try:
            from nfe_search import get_data_dir
            _db_path = str(get_data_dir() / 'notas.db')
            db_main = DatabaseManager(_db_path)
            pasta_storage = db_main.get_config('storage_pasta_base', 'xmls')
            
            if pasta_storage and pasta_storage != 'xmls':
                # Busca nome amigável do certificado
                nome_cert = db_main.get_cert_nome_by_informante(cnpj)
                
                # Salva também no storage
                resultado_storage = salvar_xml_por_certificado(xml_content, cnpj, pasta_base=pasta_storage, nome_certificado=nome_cert)
                caminho_storage = resultado_storage[0] if isinstance(resultado_storage, tuple) else resultado_storage
                logger.info(f"   💾 XML salvo no armazenamento: {caminho_storage}")
                return (caminho_local, caminho_storage)
            else:
                return (caminho_local, None)
                
        except Exception as e:
            logger.warning(f"   ⚠️  Não foi possível salvar no storage: {e}")
            return (caminho_local, None)
        
    except Exception as e:
        logger.error(f"   ❌ Erro ao salvar XML: {e}")
        return (None, None)


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
                caminhos = salvar_xml_nfse(
                    db=db,
                    cnpj=cnpj,
                    xml_content=xml_content,
                    numero_nfse=numero_nfse,
                    data_emissao=data_emissao
                )
                
                caminho_xml_local, caminho_xml_storage = caminhos if caminhos else (None, None)
                
                if caminho_xml_local:
                    # Salva no banco local (nfse_baixadas)
                    db.salvar_nfse(
                        numero=numero_nfse,
                        cnpj_prestador=cnpj,
                        cnpj_tomador=cnpj_tomador,
                        data_emissao=data_emissao,
                        valor=float(valor_servicos.replace(',', '.')),
                        xml=xml_content
                    )
                    
                    # 🔧 CORREÇÃO: Salva TAMBÉM em notas_detalhadas (banco principal)
                    # Esta é a tabela que a interface busca!
                    try:
                        salvar_nfse_detalhada(xml_content, nsu, informante)
                        logger.info(f"   ✅ NFS-e {numero_nfse}: R$ {valor_servicos} salva em notas_detalhadas")
                    except Exception as e_det:
                        logger.warning(f"   ⚠️  Erro ao salvar detalhes: {e_det}")
                    
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
                            pdf_content = nfse_service.consultar_danfse(chave_acesso, retry=1)
                            
                            if pdf_content:
                                # Salva PDF OFICIAL no mesmo local do XML (LOCAL)
                                if caminho_xml_local:
                                    pdf_path_local = caminho_xml_local.replace('.xml', '.pdf')
                                    with open(pdf_path_local, 'wb') as f:
                                        f.write(pdf_content)
                                    logger.info(f"   ✅ DANFSe OFICIAL salvo (local): {pdf_path_local}")
                                
                                # Salva PDF OFICIAL no mesmo local do XML (STORAGE)
                                if caminho_xml_storage:
                                    pdf_path_storage = caminho_xml_storage.replace('.xml', '.pdf')
                                    with open(pdf_path_storage, 'wb') as f:
                                        f.write(pdf_content)
                                    logger.info(f"   ✅ DANFSe OFICIAL salvo (storage): {pdf_path_storage}")

                            else:
                                # PDF não disponível — município não integrado ao ADN ou nota cancelada
                                logger.info(f"   ℹ️  PDF não retornado pela API ADN (sem conteúdo)")
                                logger.info(f"   ℹ️  Município possivelmente não integrado ao Padrão Nacional ADN")

                        else:
                            logger.warning(f"   ⚠️  NFS-e {numero_nfse} sem ChaveAcesso - PDF não disponível")
                    
                    except Exception as e_pdf:
                        _e_str = str(e_pdf)
                        logger.info(f"   ℹ️  PDF indisponível via API: {_e_str[:120]}")
                        if '502' in _e_str or '503' in _e_str or '504' in _e_str or 'Bad Gateway' in _e_str or 'Gateway' in _e_str:
                            logger.info(f"   ℹ️  Erro {('502' if '502' in _e_str else '503' if '503' in _e_str else '504')} (servidor ADN instável) — PDF pode ser baixado depois via Atualizar PDFs")
                        else:
                            logger.info(f"   ℹ️  Município não integrado ao Padrão Nacional ADN — PDF indisponível")
                            logger.info(f"   ℹ️  Isso NÃO é um bug! Acontece quando:")
                            logger.info(f"   ℹ️    • Município não integrado ao Padrão Nacional ADN")
                            logger.info(f"   ℹ️    • Em breve o município irá aderir ao Padrão!")
                    
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
    
    # Busca configuracoes NFS-e para este CNPJ (provedores municipais)
    configs = db.get_config_nfse(cnpj)
    
    if not configs:
        # Sem configuração municipal — tenta Ambiente Nacional diretamente.
        # O Ambiente Nacional (Receita Federal) não exige configuração de provedor/município.
        logger.info("ℹ️  Sem config municipal — tentando Ambiente Nacional (Receita Federal)")
        # Usa config padrão: provedor vazio, município vazio (não usado em buscar_nfse_ambiente_nacional)
        configs = [('AMBIENTE_NACIONAL', '', '', None)]
        logger.info(f"✅ Usando Ambiente Nacional como padrão")
    else:
        logger.info(f"✅ {len(configs)} configuracao(oes) municipal(ais) encontrada(s)")
    
    total_notas = 0
    
    # Processa cada configuracao (um CNPJ pode ter multiplos municipios)
    for config in configs:
        provedor, cod_municipio, inscricao_municipal, url = config
        
        if provedor == 'AMBIENTE_NACIONAL':
            logger.info(f"\n--- Ambiente Nacional (Receita Federal) ---")
            logger.info(f"   Metodo: Consulta propria via certificado digital (NSU)")
        else:
            logger.info(f"\n--- Configuracao Municipal ---")
            logger.info(f"   Provedor: {provedor}")
            logger.info(f"   Municipio: {cod_municipio}")
            logger.info(f"   Inscricao: {inscricao_municipal}")
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
