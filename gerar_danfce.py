"""
Gerador de DANFE NFC-e (Documento Auxiliar da Nota Fiscal de Consumidor Eletrônica).

Gera cupom térmico em formato PDF (largura ~80 mm) compatível com o padrão NFC-e
(modelo 65).  Usa reportlab como motor principal e tenta WeasyPrint como fallback
dentro do processo sandbox (onde as libs GTK estão disponíveis).

Ponto de entrada público:
    gerar_danfce(xml_content: str | bytes, pdf_path: str) -> bool
"""
from __future__ import annotations

import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

_FORMAS_PAG = {
    "01": "Dinheiro",
    "02": "Cheque",
    "03": "Cartão de Crédito",
    "04": "Cartão de Débito",
    "05": "Créd. Loja",
    "10": "Vale Alimentação",
    "11": "Vale Refeição",
    "12": "Vale Presente",
    "13": "Vale Combustível",
    "15": "Boleto Bancário",
    "90": "Sem Pagamento",
    "99": "Outros",
}


def _fmt_cnpj(v: str) -> str:
    v = re.sub(r"\D", "", v)
    if len(v) == 14:
        return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
    return v


def _fmt_cpf(v: str) -> str:
    v = re.sub(r"\D", "", v)
    if len(v) == 11:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
    return v


def _fmt_chave(v: str) -> str:
    v = re.sub(r"\D", "", v)
    return " ".join(v[i:i+4] for i in range(0, len(v), 4))


def _fmt_data(v: str) -> str:
    """Formats ISO datetime or date to dd/mm/aaaa HH:MM:SS."""
    if not v:
        return ""
    v = v[:19]
    try:
        dt = datetime.fromisoformat(v)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return v


def _fmt_valor(v: str) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return v or "R$ 0,00"


# ---------------------------------------------------------------------------
# Extração de dados
# ---------------------------------------------------------------------------

def _extrair_dados(xml_content: str | bytes) -> dict:
    """Parse NFC-e XML e retorna dicionário com todos os campos necessários."""
    try:
        from lxml import etree
    except ImportError:
        from xml.etree import ElementTree as etree

    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    root = etree.fromstring(xml_content)

    def _t(el, path):
        if el is None:
            return ""
        found = el.find(path, _NS)
        return (found.text or "").strip() if found is not None else ""

    inf = root.find(".//nfe:infNFe", _NS)
    if inf is None:
        return {}

    ide = inf.find("nfe:ide", _NS)
    emit = inf.find("nfe:emit", _NS)
    ender_emit = emit.find("nfe:enderEmit", _NS) if emit is not None else None
    dest = inf.find("nfe:dest", _NS)
    total = inf.find("nfe:total", _NS)
    icms_tot = total.find("nfe:ICMSTot", _NS) if total is not None else None
    pag = inf.find("nfe:pag", _NS)
    supl = root.find(".//nfe:infNFeSupl", _NS)
    inf_prot = root.find(".//nfe:infProt", _NS)

    # Produtos
    produtos = []
    for det in inf.findall("nfe:det", _NS):
        prod = det.find("nfe:prod", _NS)
        if prod is None:
            continue
        produtos.append({
            "seq":    det.get("nItem", ""),
            "codigo": _t(prod, "nfe:cProd"),
            "nome":   _t(prod, "nfe:xProd"),
            "ncm":    _t(prod, "nfe:NCM"),
            "cfop":   _t(prod, "nfe:CFOP"),
            "un":     _t(prod, "nfe:uCom"),
            "qtd":    _t(prod, "nfe:qCom"),
            "vUnit":  _t(prod, "nfe:vUnCom"),
            "vProd":  _t(prod, "nfe:vProd"),
            "vDesc":  _t(prod, "nfe:vDesc"),
        })

    # Pagamentos
    pagamentos = []
    v_troco = ""
    if pag is not None:
        for dp in pag.findall("nfe:detPag", _NS):
            tp = _t(dp, "nfe:tPag")
            vp = _t(dp, "nfe:vPag")
            pagamentos.append({
                "forma": _FORMAS_PAG.get(tp, tp),
                "valor": vp,
            })
        v_troco = _t(pag, "nfe:vTroco")

    # QR Code
    qr_code_url = _t(supl, "nfe:qrCode") if supl is not None else ""
    url_chave = _t(supl, "nfe:urlChave") if supl is not None else ""

    chave = (inf.get("Id") or "").replace("NFe", "")
    n_nf = _t(ide, "nfe:nNF")
    serie = _t(ide, "nfe:serie")
    dh_emi = _fmt_data(_t(ide, "nfe:dhEmi"))

    # Emitente
    emit_nome = _t(emit, "nfe:xNome")
    emit_fant = _t(emit, "nfe:xFant")
    emit_cnpj = _fmt_cnpj(_t(emit, "nfe:CNPJ") or _t(emit, "nfe:CPF"))
    emit_ie = _t(emit, "nfe:IE")
    emit_end = ", ".join(filter(None, [
        _t(ender_emit, "nfe:xLgr"),
        _t(ender_emit, "nfe:nro"),
        _t(ender_emit, "nfe:xBairro"),
    ]))
    emit_mun = _t(ender_emit, "nfe:xMun")
    emit_uf = _t(ender_emit, "nfe:UF")
    emit_cep = _t(ender_emit, "nfe:CEP")

    # Destinatário
    dest_cnpj = ""
    dest_nome = ""
    if dest is not None:
        raw = (_t(dest, "nfe:CNPJ") or _t(dest, "nfe:CPF"))
        if len(re.sub(r"\D", "", raw)) == 14:
            dest_cnpj = _fmt_cnpj(raw)
        else:
            dest_cnpj = _fmt_cpf(raw)
        dest_nome = _t(dest, "nfe:xNome")

    # Protocolo
    n_prot = _t(inf_prot, "nfe:nProt") if inf_prot is not None else ""
    dh_rec = _fmt_data(_t(inf_prot, "nfe:dhRecbto")) if inf_prot is not None else ""
    c_stat = _t(inf_prot, "nfe:cStat") if inf_prot is not None else ""
    x_motivo = _t(inf_prot, "nfe:xMotivo") if inf_prot is not None else ""

    return {
        "chave": chave,
        "chave_fmt": _fmt_chave(chave),
        "n_nf": n_nf,
        "serie": serie,
        "dh_emi": dh_emi,
        "emit_nome": emit_nome,
        "emit_fant": emit_fant,
        "emit_cnpj": emit_cnpj,
        "emit_ie": emit_ie,
        "emit_end": emit_end,
        "emit_mun": emit_mun,
        "emit_uf": emit_uf,
        "emit_cep": emit_cep,
        "dest_cnpj": dest_cnpj,
        "dest_nome": dest_nome,
        "produtos": produtos,
        "pagamentos": pagamentos,
        "v_troco": v_troco,
        "v_prod": _t(icms_tot, "nfe:vProd"),
        "v_desc": _t(icms_tot, "nfe:vDesc"),
        "v_nf": _t(icms_tot, "nfe:vNF"),
        "v_icms": _t(icms_tot, "nfe:vICMS"),
        "qr_code_url": qr_code_url,
        "url_chave": url_chave,
        "n_prot": n_prot,
        "dh_rec": dh_rec,
        "c_stat": c_stat,
        "x_motivo": x_motivo,
    }


# ---------------------------------------------------------------------------
# Geração via ReportLab (primário)
# ---------------------------------------------------------------------------

def _gerar_com_reportlab(dados: dict, pdf_path: str) -> bool:
    """Gera o cupom NFC-e usando ReportLab."""
    from reportlab.lib.pagesizes import mm
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
        Image as RLImage,
    )
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    # Largura do cupom: 80 mm
    PAGE_WIDTH = 80 * mm
    MARGINS = 4 * mm
    CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGINS

    # Estilos base
    styles = getSampleStyleSheet()

    def _style(name, **kw):
        base = kw.pop("parent", "Normal")
        s = ParagraphStyle(name, parent=styles[base], **kw)
        return s

    bold_center = _style("bold_center", fontName="Helvetica-Bold", fontSize=8, alignment=TA_CENTER, leading=10)
    normal_center = _style("norm_center", fontName="Helvetica", fontSize=7, alignment=TA_CENTER, leading=9)
    normal_left = _style("norm_left", fontName="Helvetica", fontSize=7, alignment=TA_LEFT, leading=9)
    tiny_center = _style("tiny_center", fontName="Helvetica", fontSize=6, alignment=TA_CENTER, leading=8)
    tiny_left = _style("tiny_left", fontName="Helvetica", fontSize=6, alignment=TA_LEFT, leading=8)
    title_style = _style("title", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER, leading=11)
    small_bold = _style("small_bold", fontName="Helvetica-Bold", fontSize=7, alignment=TA_CENTER, leading=9)

    story = []

    def hr():
        story.append(HRFlowable(width=CONTENT_WIDTH, thickness=0.5, color=colors.black, spaceAfter=2, spaceBefore=2))

    def sp(h=2):
        story.append(Spacer(1, h * mm))

    # --- Cabeçalho ---
    emit_nome = dados.get("emit_fant") or dados.get("emit_nome") or ""
    story.append(Paragraph(emit_nome, title_style))
    story.append(Paragraph(f"CNPJ: {dados.get('emit_cnpj', '')}", normal_center))
    if dados.get("emit_ie"):
        story.append(Paragraph(f"IE: {dados.get('emit_ie', '')}", normal_center))
    endereco = dados.get("emit_end", "")
    if endereco:
        story.append(Paragraph(endereco, tiny_center))
    mun_uf = " - ".join(filter(None, [dados.get("emit_mun", ""), dados.get("emit_uf", "")]))
    if mun_uf:
        story.append(Paragraph(mun_uf, tiny_center))
    sp(1)
    hr()

    story.append(Paragraph("NFC-e — Nota Fiscal de Consumidor Eletrônica", bold_center))
    story.append(Paragraph(f"Nº {dados.get('n_nf', '')}  Série {dados.get('serie', '')}  {dados.get('dh_emi', '')}", normal_center))
    hr()

    # --- Produtos ---
    story.append(Paragraph("ITEM  DESCRIÇÃO                   QTD     UN     V.UNIT       V.TOTAL", tiny_left))
    hr()

    for p in dados.get("produtos", []):
        desc = p.get("nome", "")[:38]
        seq = p.get("seq", "")
        qtd = p.get("qtd", "")
        un = p.get("un", "")
        try:
            v_unit = f"{float(p.get('vUnit','0')):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            v_unit = p.get("vUnit", "")
        try:
            v_prod_item = f"{float(p.get('vProd','0')):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            v_prod_item = p.get("vProd", "")

        v_desc_raw = p.get("vDesc", "")
        try:
            v_desc_f = float(v_desc_raw) if v_desc_raw else 0.0
        except Exception:
            v_desc_f = 0.0

        linha1 = f"{seq:>3}  {desc}"
        linha2 = f"     {qtd} {un}  x  {v_unit}  =  {v_prod_item}"
        story.append(Paragraph(linha1, tiny_left))
        story.append(Paragraph(linha2, tiny_left))
        if v_desc_f > 0:
            story.append(Paragraph(f"     Desconto: -{v_desc_raw}", tiny_left))
        sp(0.5)

    hr()

    # --- Totais ---
    tot_data = []
    if dados.get("v_prod"):
        try:
            tot_data.append(["Subtotal:", _fmt_valor(dados["v_prod"])])
        except Exception:
            pass
    v_desc_total = dados.get("v_desc", "")
    if v_desc_total:
        try:
            if float(v_desc_total) > 0:
                tot_data.append(["Desconto:", f"- {_fmt_valor(v_desc_total)}"])
        except Exception:
            pass
    if dados.get("v_nf"):
        tot_data.append(["TOTAL:", _fmt_valor(dados["v_nf"])])

    if tot_data:
        tbl = Table(tot_data, colWidths=[CONTENT_WIDTH * 0.55, CONTENT_WIDTH * 0.45])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -2), 7),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 8),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(tbl)
    hr()

    # --- Pagamento ---
    story.append(Paragraph("FORMA DE PAGAMENTO", small_bold))
    for pg in dados.get("pagamentos", []):
        story.append(Paragraph(
            f"{pg.get('forma', '')}:  {_fmt_valor(pg.get('valor', '0'))}",
            normal_left
        ))
    if dados.get("v_troco"):
        try:
            if float(dados["v_troco"]) > 0:
                story.append(Paragraph(f"Troco:  {_fmt_valor(dados['v_troco'])}", normal_left))
        except Exception:
            pass
    hr()

    # --- Destinatário (se informado) ---
    if dados.get("dest_cnpj") or dados.get("dest_nome"):
        story.append(Paragraph("CONSUMIDOR", small_bold))
        if dados.get("dest_nome"):
            story.append(Paragraph(dados["dest_nome"], normal_center))
        if dados.get("dest_cnpj"):
            story.append(Paragraph(f"CPF/CNPJ: {dados['dest_cnpj']}", normal_center))
        hr()

    # --- QR Code ---
    qr_url = dados.get("qr_code_url", "")
    if qr_url:
        try:
            import qrcode as _qrcode
            qr = _qrcode.QRCode(
                version=None,
                error_correction=_qrcode.constants.ERROR_CORRECT_M,
                box_size=2,
                border=2,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            img_pil = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img_pil.save(buf, format="PNG")
            buf.seek(0)
            qr_size = min(CONTENT_WIDTH, 50 * mm)
            rl_img = RLImage(buf, width=qr_size, height=qr_size)
            rl_img.hAlign = "CENTER"
            story.append(rl_img)
            sp(1)
        except Exception as e:
            story.append(Paragraph(f"[QR Code indisponível: {e}]", tiny_center))

    # --- Chave de acesso ---
    story.append(Paragraph("Consulte pela chave de acesso em:", tiny_center))
    url = dados.get("url_chave") or "www.nfce.fazenda.sp.gov.br/consulta"
    story.append(Paragraph(url, tiny_center))
    sp(0.5)
    chave_fmt = dados.get("chave_fmt", "")
    if chave_fmt:
        # Quebra em linhas de ~44 chars para caber no cupom
        partes = chave_fmt.split(" ")
        grupos = []
        linha_atual = []
        for p in partes:
            linha_atual.append(p)
            if len(" ".join(linha_atual)) >= 43:
                grupos.append(" ".join(linha_atual))
                linha_atual = []
        if linha_atual:
            grupos.append(" ".join(linha_atual))
        for g in grupos:
            story.append(Paragraph(g, tiny_center))
    hr()

    # --- Protocolo de autorização ---
    if dados.get("n_prot"):
        story.append(Paragraph("Protocolo de Autorização de Uso", small_bold))
        story.append(Paragraph(dados.get("n_prot", ""), normal_center))
        story.append(Paragraph(dados.get("dh_rec", ""), normal_center))
        if dados.get("c_stat"):
            story.append(Paragraph(f"cStat: {dados['c_stat']} - {dados.get('x_motivo', '')}", tiny_center))
    else:
        story.append(Paragraph("NFC-e sem autorização registrada neste XML", tiny_center))
    sp(2)

    # --- Rodapé ---
    story.append(Paragraph("Gerado por Busca XML", tiny_center))

    # --- Build ---
    # Height is auto (will extend as needed)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=(PAGE_WIDTH, 600 * mm),
        leftMargin=MARGINS,
        rightMargin=MARGINS,
        topMargin=MARGINS,
        bottomMargin=MARGINS,
    )
    doc.build(story)
    return True


# ---------------------------------------------------------------------------
# Tentativa via WeasyPrint + Jinja2 (sandbox subprocess only)
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; font-family: monospace; }
body { width: 80mm; font-size: 8pt; padding: 3mm; }
h1 { font-size: 10pt; text-align: center; }
.center { text-align: center; }
.small { font-size: 7pt; }
.tiny { font-size: 6pt; }
.bold { font-weight: bold; }
hr { border: none; border-top: 1px dashed #000; margin: 2mm 0; }
table.produtos { width: 100%; border-collapse: collapse; font-size: 7pt; }
table.produtos td { padding: 0.5mm 0; vertical-align: top; }
table.totais { width: 100%; font-size: 8pt; }
table.totais td { padding: 0.5mm; }
table.totais tr:last-child td { font-weight: bold; font-size: 9pt; }
table.totais td:last-child { text-align: right; }
img.qr { display: block; margin: 2mm auto; width: 50mm; height: 50mm; }
</style>
</head><body>
<h1>{{ emit_fant or emit_nome }}</h1>
<p class="center small">CNPJ: {{ emit_cnpj }}</p>
{% if emit_ie %}<p class="center small">IE: {{ emit_ie }}</p>{% endif %}
<p class="center tiny">{{ emit_end }}</p>
<p class="center tiny">{{ emit_mun }} - {{ emit_uf }}</p>
<hr>
<p class="center bold small">NFC-e — Nota Fiscal de Consumidor Eletrônica</p>
<p class="center small">Nº {{ n_nf }}  Série {{ serie }}  {{ dh_emi }}</p>
<hr>
<table class="produtos">
  <tr><th>#</th><th>Produto</th><th>Qtd</th><th>V.Unit</th><th>Total</th></tr>
  {% for p in produtos %}
  <tr>
    <td>{{ p.seq }}</td>
    <td>{{ p.nome }}</td>
    <td>{{ p.qtd }} {{ p.un }}</td>
    <td>{{ p.vUnit }}</td>
    <td>{{ p.vProd }}</td>
  </tr>
  {% endfor %}
</table>
<hr>
<table class="totais">
  {% if v_prod %}<tr><td>Subtotal:</td><td>{{ v_prod_fmt }}</td></tr>{% endif %}
  {% if v_desc_show %}<tr><td>Desconto:</td><td>- {{ v_desc_fmt }}</td></tr>{% endif %}
  <tr><td>TOTAL:</td><td>{{ v_nf_fmt }}</td></tr>
</table>
<hr>
<p class="center bold small">FORMA DE PAGAMENTO</p>
{% for pg in pagamentos %}
<p class="small">{{ pg.forma }}: {{ pg.valor_fmt }}</p>
{% endfor %}
{% if v_troco_show %}<p class="small">Troco: {{ v_troco_fmt }}</p>{% endif %}
<hr>
{% if dest_cnpj or dest_nome %}
<p class="center bold small">CONSUMIDOR</p>
{% if dest_nome %}<p class="center small">{{ dest_nome }}</p>{% endif %}
{% if dest_cnpj %}<p class="center small">CPF/CNPJ: {{ dest_cnpj }}</p>{% endif %}
<hr>
{% endif %}
{% if qr_img_b64 %}
<img class="qr" src="data:image/png;base64,{{ qr_img_b64 }}" alt="QR Code NFC-e">
{% endif %}
<p class="center tiny">Consulte em: {{ url_chave or 'www.nfe.fazenda.gov.br/portal' }}</p>
<p class="center tiny">{{ chave_fmt }}</p>
<hr>
{% if n_prot %}
<p class="center bold small">Protocolo de Autorização</p>
<p class="center small">{{ n_prot }}</p>
<p class="center small">{{ dh_rec }}</p>
{% else %}
<p class="center tiny">NFC-e sem autorização neste XML</p>
{% endif %}
<p class="center tiny" style="margin-top:3mm">Gerado por Busca XML</p>
</body></html>
"""


def _gerar_com_weasyprint(dados: dict, pdf_path: str) -> bool:
    """Tenta gerar o DANFE NFC-e via WeasyPrint + Jinja2."""
    import base64

    from jinja2 import Template
    from weasyprint import HTML

    # QR Code como base64
    qr_img_b64 = ""
    qr_url = dados.get("qr_code_url", "")
    if qr_url:
        import qrcode as _qrcode
        qr = _qrcode.QRCode(error_correction=_qrcode.constants.ERROR_CORRECT_M, box_size=3, border=2)
        qr.add_data(qr_url)
        qr.make(fit=True)
        pil_img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        qr_img_b64 = base64.b64encode(buf.getvalue()).decode()

    ctx = dict(dados)
    ctx["qr_img_b64"] = qr_img_b64
    ctx["v_prod_fmt"] = _fmt_valor(dados.get("v_prod", ""))
    ctx["v_nf_fmt"] = _fmt_valor(dados.get("v_nf", ""))
    v_desc_raw = dados.get("v_desc", "")
    try:
        ctx["v_desc_show"] = float(v_desc_raw) > 0
    except Exception:
        ctx["v_desc_show"] = False
    ctx["v_desc_fmt"] = _fmt_valor(v_desc_raw)
    v_troco_raw = dados.get("v_troco", "")
    try:
        ctx["v_troco_show"] = float(v_troco_raw) > 0
    except Exception:
        ctx["v_troco_show"] = False
    ctx["v_troco_fmt"] = _fmt_valor(v_troco_raw)

    for pg in ctx.get("pagamentos", []):
        pg["valor_fmt"] = _fmt_valor(pg.get("valor", "0"))

    tmpl = Template(_HTML_TEMPLATE)
    html_str = tmpl.render(**ctx)

    HTML(string=html_str).write_pdf(pdf_path)
    return True


# ---------------------------------------------------------------------------
# Ponto de entrada público
# ---------------------------------------------------------------------------

def gerar_danfce(xml_content: str | bytes, pdf_path: str) -> bool:
    """
    Gera o DANFE NFC-e em formato PDF (cupom térmico ~80 mm).

    Tenta WeasyPrint primeiro (melhor qualidade tipográfica); se falhar,
    usa ReportLab.  Retorna True em caso de sucesso.
    """
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode("utf-8", errors="replace")

    try:
        dados = _extrair_dados(xml_content)
    except Exception as e:
        print(f"[DANFCE] Erro ao extrair dados XML: {e}", file=sys.stderr)
        return False

    if not dados.get("chave") and not dados.get("emit_cnpj"):
        print("[DANFCE] XML não parece ser uma NFC-e válida.", file=sys.stderr)
        return False

    # 1. Tenta WeasyPrint
    try:
        ok = _gerar_com_weasyprint(dados, pdf_path)
        if ok and Path(pdf_path).stat().st_size > 500:
            print("[DANFCE] PDF gerado via WeasyPrint.", file=sys.stderr)
            return True
    except Exception as e_wp:
        print(f"[DANFCE] WeasyPrint falhou ({e_wp}), tentando ReportLab...", file=sys.stderr)

    # 2. Fallback ReportLab
    try:
        ok = _gerar_com_reportlab(dados, pdf_path)
        if ok:
            print("[DANFCE] PDF gerado via ReportLab.", file=sys.stderr)
            return True
    except Exception as e_rl:
        print(f"[DANFCE] ReportLab também falhou: {e_rl}", file=sys.stderr)
        try:
            from modules.log_categorias import log_falha
            log_falha('pdf', documento=f"DANFCE numero={dados.get('n_nf')}",
                       chave=dados.get('chave'), cnpj=dados.get('emit_cnpj'), erro=e_rl)
        except Exception:
            pass

    return False
