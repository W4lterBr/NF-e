"""Simple PDF generator for NFe/CTe documents."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def generate_danfe_pdf(xml_text: str, out_path: str, tipo: str = "NFe") -> bool:
    """
    Generate DANFE PDF from XML.
    
    Args:
        xml_text: XML content
        out_path: Output PDF path
        tipo: Document type (NFe, CTe, NFS-e)
    
    Returns:
        True if successful
    """
    try:
        # Try using BrazilFiscalReport (recommended - full DANFE)
        try:
            from brazilfiscalreport.danfe import Danfe
            import sys
            print("[PDF] Tentando gerar DANFE com BrazilFiscalReport...", file=sys.stderr)
            
            # BrazilFiscalReport aceita tanto string quanto bytes
            if isinstance(xml_text, str):
                xml_bytes = xml_text.encode('utf-8')
            else:
                xml_bytes = xml_text
            
            danfe = Danfe(xml=xml_bytes)
            danfe.output(str(out_path))
            print(f"[PDF] DANFE completo gerado com sucesso: {out_path}", file=sys.stderr)
            return True
        except ImportError as e:
            import sys
            print(f"[PDF] BrazilFiscalReport não disponível: {e}", file=sys.stderr)
        except Exception as e:
            import sys
            print(f"[PDF] Erro ao usar BrazilFiscalReport: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        # Try using brazilnum-python (if available)
        try:
            from brazilnum.nfe import render_pdf_from_xml
            pdf_bytes = render_pdf_from_xml(xml_text)
            Path(out_path).write_bytes(pdf_bytes)
            return True
        except ImportError:
            pass
        
        # Fallback: try using reportlab for a simple text-based PDF
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from lxml import etree
            
            # Parse XML to extract basic info
            tree = etree.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)
            
            # Extract basic fields
            info = _extract_basic_info(tree, tipo)
            
            # Create simple PDF
            c = canvas.Canvas(str(out_path), pagesize=A4)
            width, height = A4
            
            y = height - 50
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, y, f"DANFE - {tipo}")
            y -= 30
            
            c.setFont("Helvetica", 10)
            for key, value in info.items():
                if y < 50:
                    c.showPage()
                    y = height - 50
                c.drawString(50, y, f"{key}: {value}")
                y -= 15
            
            c.save()
            return True
        except ImportError:
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
        if tipo.upper() == "NFE":
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
    
    except Exception:
        pass
    
    return info or {"Info": "Dados não extraídos"}
