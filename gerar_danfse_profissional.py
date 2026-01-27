# -*- coding: utf-8 -*-
"""
Gerador de DANFSe (Documento Auxiliar da NFS-e) profissional.
Layout baseado no padrão Ambiente Nacional de NFS-e.
Usa reportlab para gerar PDF com aparência oficial.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from lxml import etree
from datetime import datetime
import qrcode
from io import BytesIO


def gerar_danfse_profissional(xml_content, pdf_path):
    """
    Gera DANFSe profissional com layout similar ao oficial.
    
    Layout inclui:
    - Cabeçalho com título e dados fiscais
    - QR Code para consulta
    - Caixas organizadas com informações
    - Tabela de serviços
    - Valores destacados
    
    Args:
        xml_content: XML da NFS-e (string)
        pdf_path: Caminho para salvar o PDF
        
    Returns:
        bool: True se gerado com sucesso
    """
    try:
        # Parse do XML
        ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
        tree = etree.fromstring(xml_content.encode('utf-8'))
        
        # ========== EXTRAÇÃO DE DADOS ==========
        
        # Número e chave
        numero = tree.findtext('.//nfse:nNFSe', namespaces=ns) or tree.findtext('.//nfse:nDFSe', namespaces=ns) or 'N/A'
        
        # Chave de acesso
        inf_nfse = tree.find('.//nfse:infNFSe', namespaces=ns)
        chave = inf_nfse.get('Id', '')[3:] if inf_nfse is not None else ''
        
        # Datas
        dh_emissao = tree.findtext('.//nfse:DPS//nfse:dhEmi', namespaces=ns) or \
                     tree.findtext('.//nfse:DPS//nfse:dCompet', namespaces=ns) or 'N/A'
        if dh_emissao != 'N/A':
            try:
                dt = datetime.fromisoformat(dh_emissao.replace('Z', '+00:00'))
                dh_emissao = dt.strftime('%d/%m/%Y %H:%M:%S')
            except:
                pass
        
        # Prestador
        prest_cnpj = tree.findtext('.//nfse:emit//nfse:CNPJ', namespaces=ns) or 'N/A'
        prest_nome = tree.findtext('.//nfse:emit//nfse:xNome', namespaces=ns) or 'N/A'
        prest_im = tree.findtext('.//nfse:emit//nfse:IM', namespaces=ns) or 'N/A'
        prest_end = tree.findtext('.//nfse:emit//nfse:enderNac//nfse:xLgr', namespaces=ns) or ''
        prest_num = tree.findtext('.//nfse:emit//nfse:enderNac//nfse:nro', namespaces=ns) or ''
        prest_bairro = tree.findtext('.//nfse:emit//nfse:enderNac//nfse:xBairro', namespaces=ns) or ''
        prest_mun = tree.findtext('.//nfse:emit//nfse:enderNac//nfse:cMun', namespaces=ns) or ''
        prest_uf = tree.findtext('.//nfse:emit//nfse:enderNac//nfse:UF', namespaces=ns) or ''
        prest_cep = tree.findtext('.//nfse:emit//nfse:enderNac//nfse:CEP', namespaces=ns) or ''
        
        # Tomador
        toma_cnpj = tree.findtext('.//nfse:DPS//nfse:toma//nfse:CNPJ', namespaces=ns) or \
                    tree.findtext('.//nfse:DPS//nfse:toma//nfse:CPF', namespaces=ns) or 'N/A'
        toma_nome = tree.findtext('.//nfse:DPS//nfse:toma//nfse:xNome', namespaces=ns) or 'N/A'
        toma_end = tree.findtext('.//nfse:DPS//nfse:toma//nfse:end//nfse:xLgr', namespaces=ns) or ''
        toma_num = tree.findtext('.//nfse:DPS//nfse:toma//nfse:end//nfse:nro', namespaces=ns) or ''
        toma_bairro = tree.findtext('.//nfse:DPS//nfse:toma//nfse:end//nfse:xBairro', namespaces=ns) or ''
        
        # Serviços
        desc_serv = tree.findtext('.//nfse:DPS//nfse:serv//nfse:cServ//nfse:xDescServ', namespaces=ns) or \
                    tree.findtext('.//nfse:xTribMun', namespaces=ns) or 'Serviços'
        
        # Valores
        v_serv = tree.findtext('.//nfse:valores//nfse:vLiq', namespaces=ns) or \
                 tree.findtext('.//nfse:DPS//nfse:valores//nfse:vServPrest//nfse:vServ', namespaces=ns) or '0.00'
        v_issqn = tree.findtext('.//nfse:valores//nfse:vISSQN', namespaces=ns) or '0.00'
        v_bc = tree.findtext('.//nfse:valores//nfse:vBC', namespaces=ns) or v_serv
        p_aliq = tree.findtext('.//nfse:valores//nfse:pAliqAplic', namespaces=ns) or \
                 tree.findtext('.//nfse:DPS//nfse:valores//nfse:trib//nfse:tribMun//nfse:tribISSQN//nfse:pAliq', namespaces=ns) or '0.00'
        
        # ========== CRIAÇÃO DO PDF ==========
        
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4
        
        # Margens
        margin_x = 15*mm
        margin_y = 15*mm
        
        # ========== CABEÇALHO ==========
        y = height - margin_y
        
        # Título principal
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, y, "DANFSE")
        y -= 5*mm
        
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, y, "Documento Auxiliar da Nota Fiscal de Serviços Eletrônica")
        y -= 7*mm
        
        # Caixa do número
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(margin_x, y - 15*mm, width - 2*margin_x, 15*mm)
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_x + 3*mm, y - 7*mm, f"Nº {numero}")
        
        c.setFont("Helvetica", 8)
        c.drawString(margin_x + 3*mm, y - 12*mm, f"Emissão: {dh_emissao}")
        
        # QR Code (se tiver chave)
        if chave and len(chave) >= 44:
            try:
                qr = qrcode.QRCode(version=1, box_size=2, border=1)
                qr.add_data(f"https://adn.nfse.gov.br/validacao?chave={chave}")
                qr.make(fit=True)
                img_qr = qr.make_image(fill_color="black", back_color="white")
                
                # Salva QR em buffer
                buf = BytesIO()
                img_qr.save(buf, format='PNG')
                buf.seek(0)
                
                # Desenha QR Code
                c.drawImage(buf, width - margin_x - 25*mm, y - 15*mm, 22*mm, 22*mm)
            except:
                pass
        
        y -= 18*mm
        
        # ========== PRESTADOR ==========
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin_x, y, "PRESTADOR DE SERVIÇOS")
        y -= 5*mm
        
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.5)
        c.rect(margin_x, y - 25*mm, width - 2*margin_x, 25*mm)
        
        c.setFont("Helvetica", 8)
        c.drawString(margin_x + 2*mm, y - 4*mm, f"Razão Social: {prest_nome}")
        c.drawString(margin_x + 2*mm, y - 9*mm, f"CNPJ: {prest_cnpj}")
        c.drawString(margin_x + 2*mm, y - 14*mm, f"Inscrição Municipal: {prest_im}")
        
        if prest_end:
            end_completo = f"{prest_end}, {prest_num} - {prest_bairro}"
            c.drawString(margin_x + 2*mm, y - 19*mm, f"Endereço: {end_completo[:80]}")
            c.drawString(margin_x + 2*mm, y - 23*mm, f"CEP: {prest_cep}  Município/UF: {prest_mun}/{prest_uf}")
        
        y -= 28*mm
        
        # ========== TOMADOR ==========
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin_x, y, "TOMADOR DE SERVIÇOS")
        y -= 5*mm
        
        c.rect(margin_x, y - 20*mm, width - 2*margin_x, 20*mm)
        
        c.setFont("Helvetica", 8)
        c.drawString(margin_x + 2*mm, y - 4*mm, f"Razão Social: {toma_nome}")
        c.drawString(margin_x + 2*mm, y - 9*mm, f"CNPJ/CPF: {toma_cnpj}")
        
        if toma_end:
            end_completo = f"{toma_end}, {toma_num} - {toma_bairro}"
            c.drawString(margin_x + 2*mm, y - 14*mm, f"Endereço: {end_completo[:80]}")
        
        y -= 23*mm
        
        # ========== DISCRIMINAÇÃO DOS SERVIÇOS ==========
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin_x, y, "DISCRIMINAÇÃO DOS SERVIÇOS")
        y -= 5*mm
        
        # Altura da caixa de serviços
        altura_serv = 30*mm
        c.rect(margin_x, y - altura_serv, width - 2*margin_x, altura_serv)
        
        # Quebra texto em linhas
        c.setFont("Helvetica", 8)
        max_chars = 95
        y_texto = y - 4*mm
        for i in range(0, len(desc_serv), max_chars):
            linha = desc_serv[i:i+max_chars]
            c.drawString(margin_x + 2*mm, y_texto, linha)
            y_texto -= 4*mm
            if y_texto < y - altura_serv + 2*mm:
                break
        
        y -= altura_serv + 3*mm
        
        # ========== VALORES ==========
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin_x, y, "VALORES")
        y -= 5*mm
        
        # Tabela de valores
        dados_valores = [
            ['Valor dos Serviços', f'R$ {float(v_serv):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Base de Cálculo', f'R$ {float(v_bc):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Alíquota', f'{float(p_aliq):.2f}%'],
            ['Valor do ISSQN', f'R$ {float(v_issqn):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')],
        ]
        
        y_val = y
        for label, valor in dados_valores:
            c.setFont("Helvetica", 8)
            c.drawString(margin_x + 2*mm, y_val, label)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(width/2, y_val, valor)
            y_val -= 5*mm
        
        # Linha separadora
        c.line(margin_x, y - 21*mm, width - margin_x, y - 21*mm)
        
        y -= 24*mm
        
        # ========== RODAPÉ ==========
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.grey)
        
        rodape_y = margin_y + 15*mm
        c.drawCentredString(width/2, rodape_y, "Este documento foi gerado automaticamente a partir do XML da NFS-e")
        c.drawCentredString(width/2, rodape_y - 3*mm, "Para validar a autenticidade, consulte: https://adn.nfse.gov.br")
        
        if chave:
            c.setFont("Helvetica", 6)
            c.drawCentredString(width/2, rodape_y - 7*mm, f"Chave de Acesso: {chave}")
        
        c.save()
        return True
        
    except Exception as e:
        print(f"Erro ao gerar DANFSe profissional: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Teste
    from pathlib import Path
    
    xmls = list(Path('xmls/33251845000109').rglob('NFSe/*.xml'))
    if xmls:
        xml_path = xmls[0]
        xml_content = xml_path.read_text(encoding='utf-8')
        
        pdf_path = 'teste_danfse_profissional.pdf'
        if gerar_danfse_profissional(xml_content, pdf_path):
            print(f"✅ DANFSe profissional gerado: {pdf_path}")
        else:
            print("❌ Falha ao gerar")
