"""Simple PDF generator for NFe/CTe documents."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def generate_danfe_pdf(xml_text: str, out_path: str, tipo: str = "NFe",
                       xml_source_path: Optional[str] = None) -> bool:
    """
    Generate DANFE/DACTE PDF from XML.
    
    Args:
        xml_text: XML content
        out_path: Output PDF path
        tipo: Document type (NFe, CTe, NFS-e)
    
    Returns:
        True if successful
    """
    import sys
    from datetime import datetime
    
    # 🔍 DEBUG: Log detalhado para NFS-e
    def debug_log(msg):
        """Salva log de debug em AppData/Roaming/Busca XML/logs"""
        try:
            import os
            # AppData\Roaming\Busca XML\logs
            appdata = os.getenv('APPDATA')
            if appdata:
                debug_dir = Path(appdata) / "Busca XML" / "logs"
            else:
                # Fallback se APPDATA não estiver disponível
                debug_dir = Path.home() / "AppData" / "Roaming" / "Busca XML" / "logs"
            
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            debug_file = debug_dir / "nfse_pdf_debug.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {msg}\n")
            
            print(f"[PDF DEBUG] {msg}", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG ERROR] {e}", file=sys.stderr)
    
    try:
        # 🔥 NFS-e: Tenta baixar PDF OFICIAL da API, depois gera local
        if "NFS" in tipo.upper():
            debug_log("=" * 80)
            debug_log(f"INÍCIO GERAÇÃO PDF NFS-e")
            debug_log(f"Arquivo destino: {out_path}")
            
            # ========== ETAPA 1: VERIFICA SE PDF OFICIAL JÁ EXISTE (busca automática) ==========
            debug_log("ETAPA 1: Verificando se PDF oficial já foi baixado automaticamente...")
            pdf_ja_existe = False
            
            try:
                from lxml import etree
                import os, shutil
                
                ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
                tree = etree.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)
                numero_nfse = tree.findtext('.//nfse:nNFSe', namespaces=ns) or tree.findtext('.//nNFSe') or \
                             tree.findtext('.//nfse:nDFSe', namespaces=ns) or tree.findtext('.//nDFSe')
                
                if numero_nfse:
                    debug_log(f"   Número NFS-e: {numero_nfse}")
                    
                    # Determina raiz de busca: prefere o diretório do XML de origem;
                    # fallback para parents[2] do out_path (funciona quando out_path
                    # é o próprio caminho de saída definitivo, não um arquivo temporário).
                    if xml_source_path:
                        xml_path_obj = Path(xml_source_path)
                        # parents[2] = pasta do informante (ex: xmls/11893620000113)
                        try:
                            informante_dir = xml_path_obj.parents[2]
                            roots = [informante_dir] if informante_dir.is_dir() else [xml_path_obj.parent]
                        except (IndexError, Exception):
                            roots = [xml_path_obj.parent]
                    else:
                        out_path_obj = Path(out_path)
                        try:
                            informante_dir = out_path_obj.parents[2]
                            roots = [informante_dir] if informante_dir.is_dir() else [out_path_obj.parent]
                        except (IndexError, Exception):
                            roots = [out_path_obj.parent]
                    patterns = [f"{numero_nfse}-*.pdf", f"NFSe_{numero_nfse}.pdf", f"DANFSe_{numero_nfse}.pdf"]
                    
                    for root in roots:
                        if not root.exists():
                            continue
                        for pattern in patterns:
                            matches = list(root.rglob(pattern))
                            if matches:
                                pdf_oficial = max(matches, key=lambda p: p.stat().st_mtime if p.exists() else 0)
                                if pdf_oficial.exists() and pdf_oficial.stat().st_size > 10000:  # > 10 KB = provavelmente oficial
                                    debug_log(f"   ✅✅✅ PDF OFICIAL ENCONTRADO: {pdf_oficial.name}")
                                    debug_log(f"   Tamanho: {pdf_oficial.stat().st_size:,} bytes")
                                    shutil.copy2(pdf_oficial, out_path)
                                    debug_log(f"   ✅ PDF oficial copiado para: {out_path}")
                                    debug_log("=" * 80)
                                    print(f"[PDF] ✅ PDF OFICIAL reutilizado (busca automática)", file=sys.stderr)
                                    pdf_ja_existe = True
                                    return {"ok": True, "pdf_tipo": "OFICIAL"}
                    
                    if not pdf_ja_existe:
                        debug_log("   ⚠️ PDF oficial não encontrado - tentando baixar da API...")
            except Exception as e:
                debug_log(f"   ⚠️ Erro ao buscar PDF: {e}")
            
            if pdf_ja_existe:
                return {"ok": True, "pdf_tipo": "OFICIAL"}
            
            # ========== ETAPA 2: TENTA BAIXAR DA API ADN (PDF OFICIAL) ==========
            # Tenta o PDF oficial primeiro. Se a API não estiver disponível (404, timeout, ABRASF),
            # cai no ETAPA 3 (geração local) como fallback.
            debug_log("ETAPA 2: Tentando baixar PDF oficial da API ADN...")
            
            # Extrai chave de acesso do XML
            try:
                debug_log("Extraindo chave de acesso do XML...")
                from lxml import etree
                ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
                tree = etree.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)
                inf_nfse = tree.find('.//nfse:infNFSe', namespaces=ns)
                chave_acesso = None
                
                if inf_nfse is not None:
                    chave_id = inf_nfse.get('Id', '')
                    debug_log(f"Atributo Id encontrado: {chave_id}")
                    if chave_id and chave_id.startswith('NFS'):
                        chave_acesso = chave_id[3:]
                        debug_log(f"✅ Chave extraída: {chave_acesso[:10]}...{chave_acesso[-10:]} (len={len(chave_acesso)})")
                    else:
                        debug_log(f"❌ Id não começa com 'NFS': {chave_id}")
                else:
                    debug_log("❌ Elemento infNFSe não encontrado no XML")
                
                # Tenta obter PDF oficial da API (timeout curto: 1 tentativa de 10s)
                if chave_acesso and len(chave_acesso) >= 44:
                    debug_log(f"Chave válida ({len(chave_acesso)} dígitos) - buscando certificado...")
                    try:
                        # Obtém credenciais do certificado configurado
                        from nfse_search import NFSeDatabase
                        db = NFSeDatabase()
                        certificados = db.get_certificados()
                        
                        if certificados:
                            cnpj, cert_path, senha, informante, cuf = certificados[0]
                            debug_log(f"✅ Certificado encontrado: {cnpj}")
                            
                            # Cria serviço NFS-e e tenta baixar PDF oficial
                            debug_log("Criando NFSeService...")
                            from modules.nfse_service import NFSeService
                            nfse_service = NFSeService(cert_path, senha, informante, cuf, 'producao')
                            debug_log("✅ NFSeService criado com sucesso")
                            
                            debug_log(f"Chamando consultar_danfse(chave={chave_acesso[:10]}..., retry=1)...")
                            pdf_content = nfse_service.consultar_danfse(chave_acesso, retry=1)
                            
                            if pdf_content:
                                Path(out_path).write_bytes(pdf_content)
                                debug_log(f"✅✅✅ PDF OFICIAL SALVO DA API ({len(pdf_content):,} bytes)")
                                debug_log(f"Arquivo: {out_path}")
                                debug_log("=" * 80)
                                print(f"[PDF] ✅ PDF OFICIAL obtido da API do governo ({len(pdf_content):,} bytes)", file=sys.stderr)
                                return {"ok": True, "pdf_tipo": "OFICIAL"}
                            else:
                                debug_log("❌ API retornou None (sem conteúdo)")
                        else:
                            debug_log("❌ Nenhum certificado configurado no banco")
                    except Exception as e:
                        debug_log(f"❌ ERRO na API: {type(e).__name__}: {str(e)}")
                        import traceback
                        debug_log(f"Stack trace:\n{traceback.format_exc()}")
                        
                        # Explicação sobre erro 404
                        if '404' in str(e):
                            debug_log("=" * 80)
                            debug_log("ℹ️  ERRO 404 = NFS-e NÃO DISPONÍVEL na API do Ambiente Nacional")
                            debug_log("    Isso NÃO é um bug! Acontece quando:")
                            debug_log("    • Município não integrado ao Padrão Nacional ADN")
                            debug_log("    • Nota emitida por sistema legado (pré-2024)")
                            debug_log("    • Sistema municipal independente")
                            debug_log("    • Nota em processamento ou cancelada")
                            debug_log("=" * 80)
                        
                        print(f"[PDF] API indisponível: {e}", file=sys.stderr)
                        # Continua para geração local
                else:
                    if not chave_acesso:
                        debug_log("❌ Chave de acesso não foi extraída do XML")
                    else:
                        debug_log(f"❌ Chave muito curta ({len(chave_acesso)} < 44 dígitos)")
            except Exception as e:
                debug_log(f"❌ ERRO ao extrair chave: {type(e).__name__}: {str(e)}")
                import traceback
                debug_log(f"Stack trace:\n{traceback.format_exc()}")
                print(f"[PDF] Erro ao extrair chave: {e}", file=sys.stderr)

            # ========== ETAPA 2.5: TENTA LinkNFSe DO ABRASF MUNICIPAL ==========
            # Muitos provedores ABRASF (BH, Ginfes, Betha, etc.) incluem no campo
            # LinkNFSe do XML a URL pública do DANFSe no portal municipal.
            # Tentamos baixar esse PDF antes de gerar localmente.
            debug_log("ETAPA 2.5: Verificando LinkNFSe (padrão ABRASF municipal)...")
            try:
                from lxml import etree
                import re as _re

                tree_ab = etree.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)

                xml_str_check = xml_text if isinstance(xml_text, str) else xml_text.decode('utf-8', errors='replace')
                is_abrasf = ('abrasf.org.br' in xml_str_check) or ('ListaNotaFiscal' in xml_str_check)

                link_nfse = None
                if is_abrasf:
                    debug_log("   ✅ Formato ABRASF detectado — buscando campo LinkNFSe...")
                    # Namespace ABRASF usa barra simples (padrão do DominioWeb / outros)
                    ns_ab = {"ab": "http:/www.abrasf.org.br/nfse.xsd"}
                    el = tree_ab.find('.//ab:LinkNFSe', ns_ab)
                    if el is None:
                        el = tree_ab.find('.//LinkNFSe')
                    if el is not None and el.text:
                        link_nfse = el.text.strip()
                        debug_log(f"   LinkNFSe encontrado: {link_nfse}")

                    # Fallback: extrai URL de OutrasInformacoes (campo de texto livre)
                    if not link_nfse:
                        outras = tree_ab.find('.//ab:OutrasInformacoes', ns_ab)
                        if outras is None:
                            outras = tree_ab.find('.//OutrasInformacoes')
                        if outras is not None and outras.text:
                            urls = _re.findall(r'https?://\S+', outras.text)
                            if urls:
                                link_nfse = urls[0].rstrip('.,;)')
                                debug_log(f"   URL extraída de OutrasInformacoes: {link_nfse}")

                if link_nfse:
                    try:
                        import requests as _req
                        resp = _req.get(
                            link_nfse, timeout=15, allow_redirects=True,
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                        )
                        if resp.status_code == 200 and len(resp.content) > 10000:
                            if resp.content[:4] == b'%PDF':
                                Path(out_path).write_bytes(resp.content)
                                debug_log(f"✅ PDF OFICIAL baixado via LinkNFSe ({len(resp.content):,} bytes)")
                                debug_log("=" * 80)
                                print(f"[PDF] ✅ PDF OFICIAL via LinkNFSe ABRASF ({len(resp.content):,} bytes)", file=sys.stderr)
                                return {"ok": True, "pdf_tipo": "OFICIAL"}
                            else:
                                debug_log(f"❌ Conteúdo baixado não é PDF (magic: {resp.content[:8]})")
                        else:
                            debug_log(f"❌ LinkNFSe HTTP {resp.status_code} ou conteúdo pequeno ({len(resp.content)} bytes)")
                    except Exception as e_link:
                        debug_log(f"❌ Erro ao baixar LinkNFSe: {type(e_link).__name__}: {e_link}")
                        print(f"[PDF] LinkNFSe indisponível: {e_link}", file=sys.stderr)
                else:
                    if is_abrasf:
                        debug_log("   ⚠️ ABRASF sem campo LinkNFSe — seguindo para geração local")
                    else:
                        debug_log("   ℹ️ XML não é ABRASF — pulando ETAPA 2.5")
            except Exception as e:
                debug_log(f"❌ ERRO na ETAPA 2.5: {type(e).__name__}: {e}")

            # ========== ETAPA 3: GERA PDF LOCALMENTE (FALLBACK) ==========
            # Chega aqui se: API não disponível, chave inválida, município não aderiu ao ADN, etc.
            debug_log("ETAPA 3: Gerando DANFSe profissional localmente (fallback)...")
            print("[PDF] Gerando DANFSe profissional localmente...", file=sys.stderr)
            try:
                from gerar_danfse_profissional import gerar_danfse_profissional
                success = gerar_danfse_profissional(xml_text, out_path)
                if success:
                    debug_log(f"✅ DANFSe profissional gerado localmente: {out_path}")
                    debug_log("=" * 80)
                    print(f"[PDF] DANFSe profissional gerado localmente: {out_path}", file=sys.stderr)
                    return {"ok": True, "pdf_tipo": "GENERICO"}
                else:
                    debug_log("❌ gerar_danfse_profissional retornou False")
            except ImportError as e:
                debug_log(f"❌ ImportError gerar_danfse_profissional: {e}")
            except Exception as e:
                debug_log(f"❌ ERRO gerar_danfse_profissional: {type(e).__name__}: {str(e)}")
                import traceback
                debug_log(f"Stack trace:\n{traceback.format_exc()}")

            # API e geração local falharam
            debug_log("⚠️ NFS-e: Todas as tentativas falharam - retornando False")
            debug_log("=" * 80)
            print(f"[PDF] ❌ Não foi possível gerar PDF para NFS-e", file=sys.stderr)
            return {"ok": False, "pdf_tipo": None}

        # NFC-e (modelo 65): usa gerador próprio de cupom térmico
        if "NFC" in tipo.upper():
            print("[PDF] Gerando DANFE NFC-e (cupom térmico)...", file=sys.stderr)
            try:
                from gerar_danfce import gerar_danfce
                success = gerar_danfce(xml_text, out_path)
                if success:
                    print(f"[PDF] DANFE NFC-e gerado: {out_path}", file=sys.stderr)
                    return True
                else:
                    print("[PDF] ❌ Falha ao gerar DANFE NFC-e", file=sys.stderr)
                    return False
            except ImportError as e:
                print(f"[PDF] ❌ gerar_danfce não disponível: {e}", file=sys.stderr)
                return False
            except Exception as e:
                print(f"[PDF] ❌ Erro ao gerar DANFE NFC-e: {e}", file=sys.stderr)
                return False

        # Try using BrazilFiscalReport (recommended - full DANFE/DACTE)
        try:
            # Prepare XML
            if isinstance(xml_text, str):
                xml_bytes = xml_text.encode('utf-8')
            else:
                xml_bytes = xml_text
            
            # Select correct class based on document type
            if tipo.upper() == "CTE":
                from brazilfiscalreport.dacte import Dacte
                print("[PDF] Tentando gerar DACTE com BrazilFiscalReport...", file=sys.stderr)
                try:
                    doc = Dacte(xml=xml_bytes)
                    doc.output(str(out_path))
                    print(f"[PDF] DACTE completo gerado com sucesso: {out_path}", file=sys.stderr)
                    return True
                except TypeError as te:
                    if "'NoneType' object is not iterable" in str(te):
                        print(f"[PDF] CT-e sem infCarga detectado - tentando métodos alternativos", file=sys.stderr)
                        # Não faz raise, permite continuar para os métodos de fallback
                    else:
                        raise
                except NotImplementedError as nie:
                    if "Transcoding multiple strips" in str(nie):
                        print(f"[PDF] Problema com QR Code do CT-e (múltiplas strips) - tentando métodos alternativos", file=sys.stderr)
                        # Não faz raise, permite continuar para os métodos de fallback
                    else:
                        raise
                except (OSError, IOError) as io_err:
                    if "image" in str(io_err).lower() or "qr" in str(io_err).lower():
                        print(f"[PDF] Problema ao processar imagem/QR Code do CT-e - tentando métodos alternativos", file=sys.stderr)
                        # Não faz raise, permite continuar para os métodos de fallback
                    else:
                        raise
            else:  # NFe or default
                from brazilfiscalreport.danfe import Danfe
                print("[PDF] Tentando gerar DANFE com BrazilFiscalReport...", file=sys.stderr)
                doc = Danfe(xml=xml_bytes)
                doc.output(str(out_path))
                print(f"[PDF] DANFE completo gerado com sucesso: {out_path}", file=sys.stderr)
                return True
            
        except ImportError as e:
            print(f"[PDF] BrazilFiscalReport não disponível: {e}", file=sys.stderr)
        except Exception as e:
            # Suprime stack trace para erros conhecidos
            erro_conhecido = (
                (isinstance(e, TypeError) and "'NoneType' object is not iterable" in str(e)) or
                (isinstance(e, NotImplementedError) and "Transcoding multiple strips" in str(e)) or
                ((isinstance(e, OSError) or isinstance(e, IOError)) and ("image" in str(e).lower() or "qr" in str(e).lower()))
            )
            
            if not erro_conhecido:
                print(f"[PDF] Erro ao usar BrazilFiscalReport: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
        
        # Try using brazilnum-python (if available)
        print(f"[PDF] Tentando métodos alternativos para {tipo}...", file=sys.stderr)
        try:
            from brazilnum.nfe import render_pdf_from_xml
            pdf_bytes = render_pdf_from_xml(xml_text)
            Path(out_path).write_bytes(pdf_bytes)
            return True
        except ImportError:
            pass
        
        # Fallback: try using reportlab for a simple text-based PDF
        try:
            if "NFS" in tipo.upper():
                debug_log("⚠️ USANDO FALLBACK REPORTLAB SIMPLES (todos os métodos anteriores falharam)")
            
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from lxml import etree
            
            # Parse XML to extract basic info
            tree = etree.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)
            
            # Extract basic fields
            info = _extract_basic_info(tree, tipo)
            
            if "NFS" in tipo.upper():
                debug_log(f"Informações extraídas: {list(info.keys())}")
            
            # Create simple PDF
            c = canvas.Canvas(str(out_path), pagesize=A4)
            width, height = A4
            
            y = height - 50
            c.setFont("Helvetica-Bold", 16)
            title = "DACTE SIMPLIFICADO" if tipo.upper() == "CTE" else f"DANFE SIMPLIFICADO - {tipo}"
            c.drawString(50, y, title)
            y -= 20
            
            c.setFont("Helvetica", 8)
            c.drawString(50, y, "(PDF gerado em formato simplificado - Para DACTE completo, instale brazilfiscalreport)")
            y -= 30
            
            c.setFont("Helvetica", 10)
            for key, value in info.items():
                if y < 50:
                    c.showPage()
                    y = height - 50
                c.drawString(50, y, f"{key}: {value}")
                y -= 15
            
            c.save()
            
            if "NFS" in tipo.upper():
                debug_log(f"⚠️ PDF SIMPLES salvo (reportlab): {out_path}")
                debug_log("=" * 80)
            
            print(f"[PDF] {tipo} simplificado gerado com sucesso: {out_path}", file=sys.stderr)
            return True
        except ImportError:
            if "NFS" in tipo.upper():
                debug_log("❌ Reportlab não disponível")
            print(f"[PDF] Reportlab não disponível", file=sys.stderr)
            pass
        
        # Last resort: save XML as text file with .pdf extension (better than nothing)
        Path(out_path).write_text(
            f"DOCUMENTO FISCAL ELETRÔNICO\\n\\n"
            f"Tipo: {tipo}\\n\\n"
            f"[PDF completo requer pacote 'brazilnum-python' ou 'reportlab']\\n\\n"
            f"XML Content:\\n{xml_text[:1000]}...",
            encoding='utf-8'
        )
        return True
    
    except Exception as e:
        import sys
        print(f"[PDF Error] {e}", file=sys.stderr)
        return False


def _extract_basic_info(tree, tipo: str) -> dict:
    """Extract basic information from XML for PDF."""
    info = {}
    try:
        # 🆕 Suporte para NFS-e (Padrão Nacional ABRASF)
        if "NFS" in tipo.upper():
            # NFS-e pode ter vários namespaces ou nenhum
            # Tenta múltiplos padrões (Padrão Nacional ADN, ABRASF 2.0, sem namespace)
            namespaces = [
                "{http://www.sped.fazenda.gov.br/nfse}",  # ✅ Padrão Nacional ADN (Receita Federal)
                "{http://www.abrasf.org.br/nfse}",
                "{http://www.sistema.com.br/Nfse/arquivos/nfse_3.xsd}",
                ""  # Sem namespace
            ]
            
            for ns in namespaces:
                # 🔍 Padrão Nacional ADN: A estrutura é diferente!
                # Caminho: <retNFSe><NFSe><infNFSe> (não usa CompNfse)
                
                # Tenta encontrar NFSe raiz
                nfse_root = None
                if ns:
                    nfse_root = tree.find(f'.//{ns}NFSe')
                    if not nfse_root:
                        nfse_root = tree.find(f'.//{ns}CompNfse')
                    if not nfse_root:
                        nfse_root = tree.find(f'.//{ns}Nfse')
                else:
                    nfse_root = tree.find('.//NFSe')
                    if not nfse_root:
                        nfse_root = tree.find('.//CompNfse')
                    if not nfse_root:
                        nfse_root = tree.find('.//Nfse')
                
                if nfse_root is None:
                    continue  # Tenta próximo namespace
                
                # Tenta extrair infNFSe
                inf_nfse = None
                if ns:
                    inf_nfse = nfse_root.find(f'{ns}infNFSe')
                    if not inf_nfse:
                        inf_nfse = nfse_root.find(f'.//{ns}infNFSe')
                else:
                    inf_nfse = nfse_root.find('infNFSe')
                    if not inf_nfse:
                        inf_nfse = nfse_root.find('.//infNFSe')
                
                if inf_nfse is not None:
                    # Número da NFS-e (nNFSe)
                    numero_elem = inf_nfse.find(f'{ns}nNFSe' if ns else 'nNFSe')
                    if numero_elem is not None and numero_elem.text:
                        info['Número'] = numero_elem.text
                    
                    # Data de Processamento (dhProc)
                    data_elem = inf_nfse.find(f'{ns}dhProc' if ns else 'dhProc')
                    if data_elem is not None and data_elem.text:
                        info['Data Processamento'] = data_elem.text[:10] if 'T' in data_elem.text else data_elem.text
                    
                    # Prestador/Emitente (emit)
                    emit = inf_nfse.find(f'{ns}emit' if ns else 'emit')
                    if emit is not None:
                        razao = emit.find(f'{ns}xNome' if ns else 'xNome')
                        if razao is not None and razao.text:
                            info['Prestador'] = razao.text
                        cnpj = emit.find(f'{ns}CNPJ' if ns else 'CNPJ')
                        if cnpj is not None and cnpj.text:
                            info['CNPJ Prestador'] = cnpj.text
                    
                    # Tomador/Dest (dest ou DPS/infDPS/toma)
                    dest = inf_nfse.find(f'{ns}dest' if ns else 'dest')
                    if dest is None:
                        # Tenta estrutura alternativa: DPS/infDPS/toma
                        dps = inf_nfse.find(f'{ns}DPS' if ns else 'DPS')
                        if dps is not None:
                            inf_dps = dps.find(f'{ns}infDPS' if ns else 'infDPS')
                            if inf_dps is not None:
                                dest = inf_dps.find(f'{ns}toma' if ns else 'toma')
                    
                    if dest is not None:
                        razao = dest.find(f'{ns}xNome' if ns else 'xNome')
                        if razao is not None and razao.text:
                            info['Tomador'] = razao.text
                        cnpj = dest.find(f'{ns}CNPJ' if ns else 'CNPJ')
                        if cnpj is not None and cnpj.text:
                            info['CNPJ Tomador'] = cnpj.text
                    
                    # Valores (valores/vLiq)
                    valores = inf_nfse.find(f'{ns}valores' if ns else 'valores')
                    if valores is not None:
                        val_liq = valores.find(f'{ns}vLiq' if ns else 'vLiq')
                        if val_liq is not None and val_liq.text:
                            info['Valor Líquido'] = f"R$ {val_liq.text}"
                        
                        val_serv = valores.find(f'{ns}vServ' if ns else 'vServ')
                        if val_serv is not None and val_serv.text:
                            info['Valor Serviços'] = f"R$ {val_serv.text}"
                    
                    # Discriminação dos Serviços (xInfComp)
                    discr = inf_nfse.find(f'{ns}xInfComp' if ns else 'xInfComp')
                    if discr is not None and discr.text:
                        texto = discr.text[:200]  # Limita a 200 caracteres
                        info['Serviços'] = texto
                    
                    break  # Encontrou dados, para de procurar
            
            # Se não encontrou nada, tenta extrair campos gerais
            if not info:
                # Busca genérica por campos comuns (sem namespace)
                for campo in ['nNFSe', 'NumeroNfse', 'Numero', 'numero']:
                    elem = tree.find(f'.//{campo}')
                    if elem is not None and elem.text:
                        info['Número'] = elem.text
                        break
                
                # Se ainda não encontrou nada, adiciona mensagem
                if not info:
                    info['Status'] = 'Estrutura XML não reconhecida'
        
        elif tipo.upper() == "NFE":
            ns = "{http://www.portalfiscal.inf.br/nfe}"
            inf = tree.find(f'.//{ns}infNFe')
            if inf is not None:
                chave = inf.attrib.get('Id', '')[-44:]
                info['Chave'] = chave
                
                ide = inf.find(f'{ns}ide')
                if ide is not None:
                    info['Número'] = ide.findtext(f'{ns}nNF', '')
                    info['Data Emissão'] = ide.findtext(f'{ns}dhEmi', ide.findtext(f'{ns}dEmi', ''))
                
                emit = inf.find(f'{ns}emit')
                if emit is not None:
                    info['Emitente'] = emit.findtext(f'{ns}xNome', '')
                    info['CNPJ Emitente'] = emit.findtext(f'{ns}CNPJ', '')
                
                tot = tree.find(f'.//{ns}ICMSTot')
                if tot is not None:
                    info['Valor Total'] = tot.findtext(f'{ns}vNF', '')
        
        elif tipo.upper() == "CTE":
            ns = "{http://www.portalfiscal.inf.br/cte}"
            inf = tree.find(f'.//{ns}infCte')
            if inf is not None:
                chave = inf.attrib.get('Id', '')[-44:]
                info['Chave'] = chave
                
                ide = inf.find(f'{ns}ide')
                if ide is not None:
                    info['Número'] = ide.findtext(f'{ns}nCT', '')
                    info['Data Emissão'] = ide.findtext(f'{ns}dhEmi', '')
                
                emit = inf.find(f'{ns}emit')
                if emit is not None:
                    info['Emitente'] = emit.findtext(f'{ns}xNome', '')
                    info['CNPJ Emitente'] = emit.findtext(f'{ns}CNPJ', '')
                
                # Tenta extrair valor da prestação
                vPrest = tree.find(f'.//{ns}vPrest')
                if vPrest is not None:
                    info['Valor Total'] = vPrest.findtext(f'{ns}vTPrest', '')
    
    except Exception:
        pass
    
    return info or {"Info": "Dados não extraídos"}
