"""
Geração de DANFE/DACTE em PDF a partir do XML completo da nota.
Tenta usar bibliotecas especializadas para renderização fiel.

Preferências de backend:
1) brazilfiscalreport (DANFE/DACTE completos, multiplataforma)
2) PyNFe (para NF-e, se disponível)
3) erpbrasil.edoc.pdf (pode falhar no Windows)
4) Fallback simplificado (ReportLab)

Uso:
    path = generate_pdf_from_xml(xml_str, tipo='NFe', out_path='C:/temp/saida.pdf', logo_path=None)
"""
from __future__ import annotations

from typing import Optional


def generate_pdf_from_xml(xml_str: str, tipo: str = 'NFe', out_path: Optional[str] = None, logo_path: Optional[str] = None) -> str:
    """Gera PDF (DANFE/DACTE) a partir do XML fornecido.

    Args:
        xml_str: XML completo da nota (nfeProc/NFe ou procCTe/CTe)
        tipo: 'NFe' ou 'CTe'
        out_path: caminho final do PDF (obrigatório)
        logo_path: caminho de um logo opcional para o cabeçalho

    Returns:
        Caminho do arquivo PDF gerado.

    Raises:
        RuntimeError: se nenhuma biblioteca estiver disponível ou ocorrer erro na geração.
    """
    if not out_path:
        raise RuntimeError('Parâmetro out_path é obrigatório para salvar o PDF')

    # 1) NF-e: usar brazilfiscalreport como primário
    if tipo.upper().startswith('NFE'):
        # Tenta brazilfiscalreport (preferido, suporta Windows)
        try:
            from brazilfiscalreport.danfe.danfe import Danfe as BFRDanfe  # type: ignore
            from brazilfiscalreport.danfe.config import DanfeConfig  # type: ignore
            cfg = DanfeConfig(logo=logo_path) if logo_path else DanfeConfig()
            d = BFRDanfe(xml_str, cfg)
            d.output(out_path)
            return out_path
        except Exception as e_bfr:
            bfr_err = e_bfr
        # 2) Tenta PyNFe como alternativa (nem sempre possui gerador de PDF funcional)
        try:
            # Vários caminhos possíveis conforme versão do PyNFe
            danfe_cls = None
            method_name = None
            try:
                from pynfe.pdf.danfe import Danfe as _PN_DANFE  # type: ignore
                danfe_cls = _PN_DANFE
                method_name = 'export_pdf'
            except Exception:
                pass
            if danfe_cls is None:
                try:
                    from pynfe.pdf.danfe import DANFE as _PN_DANFE2  # type: ignore
                    danfe_cls = _PN_DANFE2
                    method_name = 'output'
                except Exception:
                    pass
            if danfe_cls is None:
                try:
                    from pynfe.processamento.danfe import DANFE as _PN_DANFE3  # type: ignore
                    danfe_cls = _PN_DANFE3
                    method_name = 'output'
                except Exception:
                    pass
            # Algumas versões expõem a classe como 'Danfe' (camel-case) em processamento.danfe
            if danfe_cls is None:
                try:
                    from pynfe.processamento.danfe import Danfe as _PN_DANFE4  # type: ignore
                    danfe_cls = _PN_DANFE4
                    method_name = 'output'
                except Exception:
                    pass

            if danfe_cls is None:
                raise RuntimeError(
                    "PyNFe não encontrado. Instale com: pip install PyNFe"
                )

            try:
                obj = danfe_cls(xml_str, logo=logo_path)  # type: ignore
            except TypeError:
                # Algumas versões aceitam nomeado xml
                obj = danfe_cls(xml=xml_str, logo=logo_path)  # type: ignore

            # Tenta métodos comuns
            for m in [method_name, 'export_pdf', 'gerar_pdf', 'output', 'save']:
                if not m:
                    continue
                if hasattr(obj, m):
                    getattr(obj, m)(out_path)  # type: ignore
                    return out_path
            # Algumas versões usam render() + write
            if hasattr(obj, 'render'):
                pdf_bytes = obj.render()  # type: ignore
                with open(out_path, 'wb') as f:
                    f.write(pdf_bytes)
                return out_path

            raise RuntimeError(
                "Não foi possível localizar método de exportação do PyNFe (tentados: export_pdf, gerar_pdf, output, save, render)."
            )
        except ImportError:
            last_err = f"brazilfiscalreport falhou ({bfr_err}); PyNFe não instalado."
        except Exception as e:
            # Se o PyNFe não possui suporte a PDF nesta versão, tenta fallback simplificado com ReportLab
            last_err = f"brazilfiscalreport falhou ({bfr_err}); falha PyNFe: {e}"
            try:
                from reportlab.pdfgen import canvas  # type: ignore
                from reportlab.lib.pagesizes import A4  # type: ignore
                import xml.etree.ElementTree as ET

                def extract_nf_fields(xml_txt: str) -> dict[str, str]:
                    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                    try:
                        root = ET.fromstring(xml_txt)
                    except Exception:
                        return {}
                    # Suporta nfeProc/NFe
                    ide = root.find('.//nfe:ide', ns)
                    emit = root.find('.//nfe:emit', ns)
                    dest = root.find('.//nfe:dest', ns)
                    tot = root.find('.//nfe:ICMSTot', ns)
                    inf = root.find('.//nfe:infNFe', ns)
                    chave = ''
                    if inf is not None:
                        cid = inf.get('Id') or ''
                        if cid.startswith('NFe'):
                            chave = cid[3:]
                    def txt(el, tag):
                        return el.findtext(f'nfe:{tag}', default='', namespaces=ns) if el is not None else ''
                    dh = txt(ide, 'dhEmi') or txt(ide, 'dEmi')
                    dh = dh[:19]
                    return {
                        'tipo': 'NF-e',
                        'numero': txt(ide, 'nNF'),
                        'serie': txt(ide, 'serie'),
                        'data': dh,
                        'emitente': txt(emit, 'xNome'),
                        'dest': txt(dest, 'xNome'),
                        'total': txt(tot, 'vNF'),
                        'chave': chave,
                    }

                info = extract_nf_fields(xml_str)
                c = canvas.Canvas(out_path, pagesize=A4)
                w, h = A4
                y = h - 50
                c.setFont("Helvetica-Bold", 14)
                c.drawString(40, y, f"{info.get('tipo','NF-e')} (PDF simplificado)")
                y -= 30
                c.setFont("Helvetica", 11)
                lines = [
                    f"Número: {info.get('numero','')}  Série: {info.get('serie','')}",
                    f"Data: {info.get('data','')}",
                    f"Emitente: {info.get('emitente','')}",
                    f"Destinatário: {info.get('dest','')}",
                    f"Valor Total: {info.get('total','')}",
                    f"Chave: {info.get('chave','')}",
                ]
                for line in lines:
                    c.drawString(40, y, line)
                    y -= 18
                y -= 10
                c.setFont("Helvetica-Oblique", 9)
                c.drawString(40, y, "Observação: usando fallback simples pois o backend principal falhou (brazilfiscalreport/PyNFe).")
                y -= 14
                c.setFont("Helvetica-Oblique", 8)
                c.drawString(40, y, last_err[:120])
                c.showPage()
                c.save()
                return out_path
            except ImportError:
                raise RuntimeError(last_err + " | Fallback também indisponível: instale reportlab (pip install reportlab)")
            except Exception as e2:
                raise RuntimeError(last_err + f" | Falha no fallback simplificado: {e2}")

    # 2) CT-e: usar brazilfiscalreport como primário
    last_cte_err = None
    try:
        if tipo.upper().startswith('CTE'):
            from brazilfiscalreport.dacte.dacte import Dacte  # type: ignore
            from brazilfiscalreport.dacte.config import DacteConfig  # type: ignore
            cfg = DacteConfig(logo=logo_path) if logo_path else DacteConfig()
            d = Dacte(xml_str, cfg)
            d.output(out_path)
            return out_path
    except Exception as e:
        last_cte_err = f"Falha ao gerar DACTE com brazilfiscalreport: {e}"
        # Tenta erpbrasil como alternativa (pode falhar no Windows)
        try:
            from erpbrasil.edoc.pdf.dacte import DACTE  # type: ignore
            dacte = DACTE(xml_str, logo=logo_path)
            dacte.output(out_path)
            return out_path
        except Exception as e2:
            last_cte_err += f" | Alternativa erpbrasil também falhou: {e2}"

    # 3) Fallback mínimo: gerar PDF simples com ReportLab (como último recurso, hoje focado em CT-e)
    try:
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.lib.pagesizes import A4  # type: ignore
        import xml.etree.ElementTree as ET

        # Extrai campos básicos do XML
        def extract_basic_fields(xml_txt: str, tipo_doc: str):
            ns_nfe = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            ns_cte = {'cte': 'http://www.portalfiscal.inf.br/cte'}
            try:
                tree = ET.fromstring(xml_txt)
            except Exception:
                return {}
            if not tipo_doc.upper().startswith('NFE'):
                ide = tree.find('.//cte:ide', ns_cte)
                emit = tree.find('.//cte:emit', ns_cte)
                return {
                    'tipo': 'CT-e',
                    'numero': ide.findtext('cte:nCT', default='', namespaces=ns_cte) if ide is not None else '',
                    'data': (ide.findtext('cte:dhEmi', default='', namespaces=ns_cte) or '')[:19],
                    'emitente': emit.findtext('cte:xNome', default='', namespaces=ns_cte) if emit is not None else '',
                    'chave': ''
                }
            return {}

        info = extract_basic_fields(xml_str, tipo)
        c = canvas.Canvas(out_path, pagesize=A4)
        w, h = A4
        y = h - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, f"{info.get('tipo','Documento Fiscal')} (PDF simplificado)")
        y -= 30
        c.setFont("Helvetica", 11)
        lines = [
            f"Número: {info.get('numero','')}",
            f"Data: {info.get('data','')}",
            f"Emitente: {info.get('emitente','')}",
            f"Chave: {info.get('chave','')}"
        ]
        for line in lines:
            c.drawString(40, y, line)
            y -= 18
        y -= 10
        c.setFont("Helvetica-Oblique", 9)
        note = "Observação: este é um PDF simplificado gerado sem layout oficial por falta de backends especializados."
        if last_cte_err:
            note += f"  Motivo: {last_cte_err[:120]}"
        c.drawString(40, y, note)
        c.showPage()
        c.save()
        return out_path
    except ImportError:
        pass
    except Exception as e:
        raise RuntimeError(f"Falha ao gerar PDF simplificado: {e}")

    # Sem backends disponíveis
    raise RuntimeError(
        "Nenhum backend de PDF disponível.\n"
        "Recomendado: pip install brazil-fiscal-report qrcode[pil]\n"
        "Alternativas: pip install PyNFe | pip install erpbrasil.edoc.pdf weasyprint cairosvg tinycss2 cssselect2\n"
    )
