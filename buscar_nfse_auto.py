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
from modules.nfse_service import NFSeService, consultar_nfse_incremental, consultar_danfse_oficial, extrair_chave_nfse
from lxml import etree

# Importa salvar_nfse_detalhada para salvar em notas_detalhadas (banco principal)
from nfe_search import salvar_nfse_detalhada

# FLUXO OBRIGATÓRIO DE PDF (igual em toda a base — buscar_nfse_auto.py, pdf_simple.py,
# "Gerar PDFs Pendentes"): 1) tenta o DANFSe OFICIAL via consultar_danfse_oficial()
# (Ambiente Nacional); 2) se indisponível, gera localmente com gerar_danfse_profissional
# (WeasyPrint -> ReportLab). Nunca pula direto para geração local sem tentar a API antes.


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
        resultado_local = salvar_xml_por_certificado(xml_content, cnpj, pasta_base="xmls")
        caminho_local = resultado_local[0] if isinstance(resultado_local, tuple) else resultado_local
        logger.info(f"   💾 XML salvo localmente (backup): {caminho_local}")
        
        # Salva em TODOS os perfis ativos (sistema multi-perfis)
        try:
            from nfe_search import get_data_dir
            _db_path = str(get_data_dir() / 'notas.db')
            db_main = DatabaseManager(_db_path)
            nome_cert = db_main.get_cert_nome_by_informante(cnpj)
            
            resultado_perfis = salvar_xml_por_certificado(xml_content, cnpj, pasta_base=None, nome_certificado=nome_cert)
            caminho_perfis = resultado_perfis[0] if isinstance(resultado_perfis, tuple) else resultado_perfis
            if caminho_perfis:
                logger.info(f"   💾 XML salvo nos perfis de armazenamento: {caminho_perfis}")
            return (caminho_local, caminho_perfis)
                
        except Exception as e:
            logger.warning(f"   ⚠️  Não foi possível salvar nos perfis: {e}")
            return (caminho_local, None)
        
    except Exception as e:
        logger.error(f"   ❌ Erro ao salvar XML: {e}")
        from modules.log_categorias import log_falha
        log_falha('storage', documento=f"salvar XML NFS-e numero={numero_nfse}", cnpj=cnpj, erro=e)
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
                    
                    # Baixa DANFSe (PDF) logo após salvar XML.
                    # FALLBACK OBRIGATÓRIO: PDF oficial (ADN) -> geração local (gerar_danfse_profissional).
                    # Nenhuma exceção aqui pode deixar a nota sem PDF nenhum (antes, se a API ADN
                    # falhasse — ex.: município não integrado, erro 502/503 — a nota ficava sem PDF
                    # até o usuário abrir manualmente na interface).
                    try:
                        chave_acesso, motivo_chave = extrair_chave_nfse(xml_content)
                        if not chave_acesso:
                            logger.warning(f"   ⚠️  NFS-e {numero_nfse}: {motivo_chave} - PDF não disponível")
                        elif not caminho_xml_local:
                            logger.warning(f"   ⚠️  NFS-e {numero_nfse} sem caminho de XML local - PDF não pode ser salvo")
                        else:
                            pdf_path_local = caminho_xml_local.replace('.xml', '.pdf')

                            logger.info(f"   📄 Baixando DANFSe OFICIAL (PDF) para {numero_nfse}...")
                            resultado_pdf = consultar_danfse_oficial(
                                chave_acesso, cert_path, senha, informante, cuf,
                                ambiente='producao', numero=numero_nfse, cnpj_prestador=cnpj, retry=1
                            )

                            pdf_tipo = None
                            if resultado_pdf['ok']:
                                with open(pdf_path_local, 'wb') as f:
                                    f.write(resultado_pdf['pdf_bytes'])
                                pdf_tipo = 'OFICIAL'
                                logger.info(f"   ✅ DANFSe OFICIAL salvo (local): {pdf_path_local}")

                                if caminho_xml_storage:
                                    pdf_path_storage = caminho_xml_storage.replace('.xml', '.pdf')
                                    with open(pdf_path_storage, 'wb') as f:
                                        f.write(resultado_pdf['pdf_bytes'])
                                    logger.info(f"   ✅ DANFSe OFICIAL salvo (storage): {pdf_path_storage}")
                            else:
                                # FALLBACK OBRIGATÓRIO: PDF oficial indisponível -> gera localmente.
                                logger.info(f"   ℹ️  PDF oficial indisponível ({resultado_pdf['motivo'][:100]}) — tentando geração local")
                                try:
                                    from gerar_danfse_profissional import gerar_danfse_profissional
                                    if gerar_danfse_profissional(xml_content, pdf_path_local):
                                        pdf_tipo = 'GENERICO'
                                        logger.info(f"   ✅ DANFSe gerado localmente (fallback): {pdf_path_local}")

                                        if caminho_xml_storage:
                                            pdf_path_storage = caminho_xml_storage.replace('.xml', '.pdf')
                                            import shutil as _shutil_pdf
                                            _shutil_pdf.copy2(pdf_path_local, pdf_path_storage)
                                            logger.info(f"   ✅ DANFSe (fallback) copiado para storage: {pdf_path_storage}")
                                    else:
                                        logger.warning(f"   ⚠️  Geração local do DANFSe também falhou para {numero_nfse}")
                                except Exception as e_local:
                                    logger.error(f"   ❌ Erro na geração local do DANFSe (fallback) para {numero_nfse}: {e_local}")

                            # 📝 Registra caminho + tipo do PDF no banco principal (notas_detalhadas).
                            # Sem isso, o PDF existe em disco mas o sistema não sabe e tenta de novo
                            # a cada "Gerar PDFs Pendentes", ou o usuário precisa abrir manualmente.
                            if pdf_tipo:
                                try:
                                    db.main_db.atualizar_pdf_path(chave_acesso, str(Path(pdf_path_local).resolve()), pdf_tipo)
                                except Exception as e_reg:
                                    logger.warning(f"   ⚠️  Erro ao registrar pdf_path no banco para {chave_acesso[:20]}…: {e_reg}")

                    except Exception as e_pdf:
                        logger.error(f"   ❌ Erro inesperado ao processar PDF de {numero_nfse}: {e_pdf}")
                        from modules.log_categorias import log_falha
                        log_falha('pdf', documento=f"NFS-e numero={numero_nfse}",
                                   chave=locals().get('chave_acesso'), cnpj=cnpj, erro=e_pdf)
                    
            except Exception as e:
                logger.error(f"   ❌ Erro ao processar NSU={nsu}: {e}")
                from modules.log_categorias import log_falha
                log_falha('nfse', documento=f"NSU={nsu} numero={locals().get('numero_nfse')}", cnpj=cnpj, erro=e)
                continue
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ BUSCA CONCLUIDA: {notas_salvas}/{len(documentos)} documento(s) salvo(s)")
        logger.info(f"{'='*70}\n")
        
        return documentos
        
    except Exception as e:
        logger.error(f"❌ Erro na busca via Ambiente Nacional: {e}")
        import traceback
        traceback.print_exc()
        from modules.log_categorias import log_falha
        log_falha('nfse', documento="busca via Ambiente Nacional", cnpj=cnpj, erro=e)
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

    # 🔒 Validação ANTES de qualquer tentativa de conexão com o ADN/município —
    # evita gastar chamadas de rede com um certificado vencido/inválido.
    from modules.certificate_manager import validar_certificado
    cert_info = validar_certificado(cert_path, senha)
    if cert_info["expirado"]:
        logger.error(f"🔴 [{cnpj}] Certificado VENCIDO ({cert_info['motivo']}) — pulando NFS-e deste certificado")
        return 0
    if not cert_info["valido"]:
        logger.error(f"🔴 [{cnpj}] Certificado inválido ({cert_info['motivo']}) — pulando NFS-e deste certificado")
        return 0
    if cert_info["motivo"]:
        logger.warning(f"🟡 [{cnpj}] {cert_info['motivo']}")

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
