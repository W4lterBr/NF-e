# -*- coding: utf-8 -*-
"""
Gerador de DANFSe (Documento Auxiliar da NFS-e) profissional.
Layout baseado no padrão Ambiente Nacional de NFS-e.

Método principal : WeasyPrint + Jinja2 (HTML → PDF)
Fallback         : reportlab canvas (caso WeasyPrint não esteja disponível)

NOTA: Esta função só é chamada quando o PDF oficial do ADN
      (GET /danfse/{chave}) NÃO está disponível.
"""

from lxml import etree
from datetime import datetime
from typing import Optional

# Cache de disponibilidade do WeasyPrint (None=não testado, True=OK, False=indisponível)
_weasyprint_available: Optional[bool] = None


# ---------------------------------------------------------------------------
# Template HTML/CSS do DANFSe (Jinja2)
# ---------------------------------------------------------------------------
_DANFSE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 8.5pt;
    color: #111;
    padding: 8mm;
    background: white;
  }
  /* ---- Cabeçalho ---- */
  .header {
    border: 2px solid #1a3a5c;
    padding: 4mm 5mm;
    margin-bottom: 3mm;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .header-center { flex: 1; text-align: center; }
  .header-title {
    font-size: 18pt;
    font-weight: bold;
    color: #1a3a5c;
    letter-spacing: 2px;
  }
  .header-subtitle { font-size: 9pt; color: #555; margin-top: 1mm; }
  .header-number {
    text-align: right;
    min-width: 45mm;
  }
  .header-number .num-label { font-size: 7.5pt; color: #666; }
  .header-number .num-value {
    font-size: 14pt;
    font-weight: bold;
    color: #1a3a5c;
  }
  .header-number .num-emit { font-size: 7.5pt; color: #555; margin-top: 1mm; }
  /* ---- Seções ---- */
  .section {
    border: 1px solid #bbb;
    margin-bottom: 3mm;
  }
  .section-header {
    background: #1a3a5c;
    color: white;
    font-size: 8pt;
    font-weight: bold;
    padding: 1.5mm 3mm;
    letter-spacing: 0.5px;
  }
  .section-body { padding: 2.5mm 3mm; }
  /* ---- Campos ---- */
  .field-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0 5mm;
    margin-bottom: 1.5mm;
  }
  .field { flex: 1; min-width: 60mm; }
  .field-label {
    font-size: 7pt;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .field-value { font-size: 8.5pt; font-weight: bold; }
  .field-value-normal { font-size: 8.5pt; }
  /* ---- Discriminação ---- */
  .disc-text {
    font-size: 8pt;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }
  /* ---- Tabela de valores ---- */
  .valores-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2mm 5mm;
  }
  .valor-item { border-bottom: 1px solid #e0e0e0; padding-bottom: 1.5mm; }
  .valor-item .field-value { font-size: 10pt; color: #1a3a5c; }
  .valor-destaque {
    background: #f0f4f8;
    border: 1px solid #1a3a5c;
    padding: 2mm 3mm;
    margin-top: 2mm;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .valor-destaque .label { font-size: 9pt; font-weight: bold; color: #1a3a5c; }
  .valor-destaque .value { font-size: 13pt; font-weight: bold; color: #1a3a5c; }
  /* ---- QR e chave ---- */
  .footer-row {
    display: flex;
    gap: 5mm;
    align-items: flex-start;
    margin-top: 3mm;
    border: 1px solid #bbb;
    padding: 2.5mm 3mm;
  }
  .qr-img { width: 22mm; height: 22mm; flex-shrink: 0; }
  .footer-text { flex: 1; }
  .chave-label { font-size: 7pt; color: #666; margin-bottom: 1mm; }
  .chave-value {
    font-family: 'Courier New', monospace;
    font-size: 7.5pt;
    word-break: break-all;
    color: #333;
  }
  .footer-note { font-size: 7pt; color: #888; margin-top: 2mm; }
  /* ---- Gerado localmente ---- */
  .aviso-local {
    margin-top: 2mm;
    padding: 1.5mm 3mm;
    background: #fffbe6;
    border: 1px solid #f5c518;
    font-size: 7pt;
    color: #7a6000;
    text-align: center;
  }
</style>
</head>
<body>

<!-- ==================== CABEÇALHO ==================== -->
<div class="header">
  <div class="header-center">
    <div class="header-title">DANFSe</div>
    <div class="header-subtitle">Documento Auxiliar da Nota Fiscal de Serviços Eletrônica</div>
    <div class="header-subtitle" style="margin-top:1mm; font-size:7.5pt; color:#888;">
      Gerado localmente a partir do XML — PDF oficial disponível em
      <em>adn.nfse.gov.br</em>
    </div>
  </div>
  <div class="header-number">
    <div class="num-label">NÚMERO DA NFS-e</div>
    <div class="num-value">{{ numero }}</div>
    <div class="num-emit">Emissão: {{ dh_emissao }}</div>
    {% if competencia %}
    <div class="num-emit">Competência: {{ competencia }}</div>
    {% endif %}
  </div>
</div>

<!-- ==================== PRESTADOR ==================== -->
<div class="section">
  <div class="section-header">PRESTADOR DE SERVIÇOS</div>
  <div class="section-body">
    <div class="field-row">
      <div class="field" style="flex:2">
        <div class="field-label">Razão Social / Nome</div>
        <div class="field-value">{{ prest_nome }}</div>
      </div>
      <div class="field">
        <div class="field-label">CNPJ / CPF</div>
        <div class="field-value">{{ prest_cnpj | cnpj_fmt }}</div>
      </div>
      {% if prest_im %}
      <div class="field">
        <div class="field-label">Inscrição Municipal</div>
        <div class="field-value-normal">{{ prest_im }}</div>
      </div>
      {% endif %}
    </div>
    {% if prest_end %}
    <div class="field-row">
      <div class="field" style="flex:3">
        <div class="field-label">Endereço</div>
        <div class="field-value-normal">{{ prest_end }}</div>
      </div>
      {% if prest_cep %}
      <div class="field">
        <div class="field-label">CEP</div>
        <div class="field-value-normal">{{ prest_cep }}</div>
      </div>
      {% endif %}
      {% if prest_mun %}
      <div class="field">
        <div class="field-label">Município / UF</div>
        <div class="field-value-normal">{{ prest_mun }}{% if prest_uf %} / {{ prest_uf }}{% endif %}</div>
      </div>
      {% endif %}
    </div>
    {% endif %}
  </div>
</div>

<!-- ==================== TOMADOR ==================== -->
<div class="section">
  <div class="section-header">TOMADOR DE SERVIÇOS</div>
  <div class="section-body">
    <div class="field-row">
      <div class="field" style="flex:2">
        <div class="field-label">Razão Social / Nome</div>
        <div class="field-value">{{ toma_nome }}</div>
      </div>
      <div class="field">
        <div class="field-label">CNPJ / CPF</div>
        <div class="field-value">{{ toma_cnpj | cnpj_fmt }}</div>
      </div>
      {% if toma_im %}
      <div class="field">
        <div class="field-label">Inscrição Municipal</div>
        <div class="field-value-normal">{{ toma_im }}</div>
      </div>
      {% endif %}
    </div>
    {% if toma_end %}
    <div class="field-row">
      <div class="field" style="flex: 3">
        <div class="field-label">Endereço</div>
        <div class="field-value-normal">{{ toma_end }}</div>
      </div>
      {% if toma_mun %}
      <div class="field">
        <div class="field-label">Município / UF</div>
        <div class="field-value-normal">{{ toma_mun }}{% if toma_uf %} / {{ toma_uf }}{% endif %}</div>
      </div>
      {% endif %}
    </div>
    {% endif %}
  </div>
</div>

<!-- ==================== DISCRIMINAÇÃO ==================== -->
<div class="section">
  <div class="section-header">DISCRIMINAÇÃO DOS SERVIÇOS</div>
  <div class="section-body">
    {% if cod_serv or item_lista %}
    <div class="field-row" style="margin-bottom:2mm">
      {% if cod_serv %}
      <div class="field">
        <div class="field-label">Código do Serviço / CNAE</div>
        <div class="field-value-normal">{{ cod_serv }}</div>
      </div>
      {% endif %}
      {% if item_lista %}
      <div class="field">
        <div class="field-label">Item Lista de Serviços</div>
        <div class="field-value-normal">{{ item_lista }}</div>
      </div>
      {% endif %}
    </div>
    {% endif %}
    <div class="disc-text">{{ desc_serv }}</div>
  </div>
</div>

<!-- ==================== VALORES ==================== -->
<div class="section">
  <div class="section-header">VALORES E TRIBUTAÇÃO</div>
  <div class="section-body">
    <div class="valores-grid">
      <div class="valor-item">
        <div class="field-label">Valor dos Serviços</div>
        <div class="field-value">R$ {{ v_serv | brl }}</div>
      </div>
      <div class="valor-item">
        <div class="field-label">Base de Cálculo do ISS</div>
        <div class="field-value">R$ {{ v_bc | brl }}</div>
      </div>
      <div class="valor-item">
        <div class="field-label">Alíquota ISS</div>
        <div class="field-value">{{ p_aliq }}%</div>
      </div>
      <div class="valor-item">
        <div class="field-label">Valor do ISS</div>
        <div class="field-value">R$ {{ v_issqn | brl }}</div>
      </div>
      {% if v_desc and v_desc != '0.00' %}
      <div class="valor-item">
        <div class="field-label">Descontos</div>
        <div class="field-value">R$ {{ v_desc | brl }}</div>
      </div>
      {% endif %}
      {% if v_ret and v_ret != '0.00' %}
      <div class="valor-item">
        <div class="field-label">ISS Retido pelo Tomador</div>
        <div class="field-value">{{ 'Sim' if iss_retido == '1' else ('Não' if iss_retido else '—') }}</div>
      </div>
      {% endif %}
    </div>
    <div class="valor-destaque">
      <div class="label">VALOR LÍQUIDO DA NFS-e</div>
      <div class="value">R$ {{ v_liq | brl }}</div>
    </div>
  </div>
</div>

<!-- ==================== CHAVE / QR CODE ==================== -->
<div class="footer-row">
  {% if qr_base64 %}
  <img class="qr-img" src="data:image/png;base64,{{ qr_base64 }}" alt="QR Code">
  {% endif %}
  <div class="footer-text">
    <div class="chave-label">CHAVE DE ACESSO ({{ chave | length }} dígitos)</div>
    <div class="chave-value">{{ chave }}</div>
    <div class="footer-note">
      Para verificar a autenticidade desta NFS-e acesse:
      <strong>https://adn.nfse.gov.br</strong>
    </div>
  </div>
</div>

<div class="aviso-local">
  ⚠️ PDF gerado localmente a partir do XML — este não é o DANFSe oficial.
  O documento oficial está disponível em <strong>adn.nfse.gov.br</strong>.
</div>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _debug_prof(msg):
    """Registra mensagem de debug no log de PDF de NFS-e."""
    import os
    from pathlib import Path
    log_dir = Path(os.environ.get('APPDATA', '.')) / 'Busca XML' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'nfse_pdf_debug.log'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [DANFSE_PROF] {msg}\n")
    except Exception:
        pass


def _fmt_brl(value):
    """Formata número como moeda brasileira (ex: 1.234,56)."""
    try:
        return f"{float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return '0,00'


def _fmt_cnpj(value):
    """Formata CNPJ (14 dígitos) ou CPF (11 dígitos)."""
    v = str(value or '').strip().replace('.', '').replace('/', '').replace('-', '')
    if len(v) == 14:
        return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:14]}"
    if len(v) == 11:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:11]}"
    return value or ''


def _extrair_dados_abrasf(tree):
    """Extrai campos DANFSe de XML no formato ABRASF (DominioWeb / municipal)."""
    ns_ab = {'ab': 'http:/www.abrasf.org.br/nfse.xsd'}

    def tab(parent, *tags):
        """Busca texto em parent com ns ABRASF e, em seguida, sem namespace."""
        for tag in tags:
            el = parent.find(f'ab:{tag}', ns_ab)
            if el is None:
                el = parent.find(tag)
            if el is not None and el.text:
                return el.text.strip()
        return ''

    def elab(parent, tag):
        el = parent.find(f'ab:{tag}', ns_ab)
        if el is None:
            el = parent.find(tag)
        return el

    # Primeiro InfNfse do documento
    inf = tree.find('.//ab:InfNfse', ns_ab)
    if inf is None:
        inf = tree.find('.//InfNfse')
    if inf is None:
        inf = tree  # fallback

    numero = tab(inf, 'Numero') or 'N/A'
    chave_id = inf.get('Id', '') if inf is not None else ''

    dh_raw = tab(inf, 'DataEmissao')
    dh_emissao = dh_raw
    if dh_raw:
        try:
            dt = datetime.fromisoformat(dh_raw.replace('Z', '+00:00'))
            dh_emissao = dt.strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            pass

    competencia_raw = tab(inf, 'Competencia') or ''
    competencia = competencia_raw[:10] if competencia_raw else ''

    _p = elab(inf, 'PrestadorServico'); prest = _p if _p is not None else etree.Element('_')
    _ip = elab(prest, 'IdentificacaoPrestador'); id_prest = _ip if _ip is not None else etree.Element('_')
    _ep = elab(prest, 'Endereco'); end_prest = _ep if _ep is not None else etree.Element('_')
    _cp = elab(prest, 'Contato'); cont_prest = _cp if _cp is not None else etree.Element('_')

    prest_cnpj = tab(id_prest, 'Cnpj')
    prest_im   = tab(id_prest, 'InscricaoMunicipal')
    prest_nome = tab(prest, 'RazaoSocial', 'NomeFantasia')
    prest_lgr  = tab(end_prest, 'Endereco', 'Logradouro')
    prest_nro  = tab(end_prest, 'Numero')
    prest_bai  = tab(end_prest, 'Bairro')
    prest_mun  = tab(end_prest, 'CodigoMunicipio')
    prest_uf   = tab(end_prest, 'Uf', 'UF')
    prest_cep  = tab(end_prest, 'Cep', 'CEP')
    prest_end  = ', '.join(p for p in [prest_lgr, prest_nro, prest_bai] if p)

    _t2 = elab(inf, 'TomadorServico'); toma = _t2 if _t2 is not None else etree.Element('_')
    _it = elab(toma, 'IdentificacaoTomador'); id_toma = _it if _it is not None else etree.Element('_')
    _cc = elab(id_toma, 'CpfCnpj'); cpfcnpj = _cc if _cc is not None else etree.Element('_')
    _et = elab(toma, 'Endereco'); end_toma = _et if _et is not None else etree.Element('_')

    toma_cnpj = tab(cpfcnpj, 'Cnpj') or tab(cpfcnpj, 'Cpf')
    toma_nome = tab(toma, 'RazaoSocial', 'NomeFantasia')
    toma_lgr  = tab(end_toma, 'Endereco', 'Logradouro')
    toma_nro  = tab(end_toma, 'Numero')
    toma_bai  = tab(end_toma, 'Bairro')
    toma_mun  = tab(end_toma, 'CodigoMunicipio')
    toma_uf   = tab(end_toma, 'Uf', 'UF')
    toma_end  = ', '.join(p for p in [toma_lgr, toma_nro, toma_bai] if p)

    _sv = elab(inf, 'Servico'); serv = _sv if _sv is not None else etree.Element('_')
    _vl = elab(serv, 'Valores'); vals = _vl if _vl is not None else etree.Element('_')

    cod_serv  = tab(serv, 'ItemListaServico', 'CodigoTributacaoMunicipio')
    desc_serv = tab(serv, 'Discriminacao') or 'Prestação de Serviços'
    v_serv    = tab(vals, 'ValorServicos') or '0.00'
    v_bc      = tab(vals, 'BaseCalculo') or v_serv
    p_aliq    = tab(vals, 'Aliquota') or '0.00'
    v_issqn   = tab(vals, 'ValorIss') or '0.00'
    v_desc    = tab(vals, 'ValorDescondicionado', 'ValorDesconto') or '0.00'
    v_ret     = tab(vals, 'ValorIssRetido') or '0.00'
    v_liq     = tab(vals, 'ValorLiquidoNfse') or v_serv

    iss_ret_raw = tab(vals, 'IssRetido')
    iss_retido = '1' if iss_ret_raw in ('true', '1', 'S', 'Sim') else '2'

    return dict(
        numero=numero, chave=chave_id,
        dh_emissao=dh_emissao, competencia=competencia,
        prest_cnpj=prest_cnpj, prest_nome=prest_nome, prest_im=prest_im,
        prest_end=prest_end, prest_mun=prest_mun, prest_uf=prest_uf, prest_cep=prest_cep,
        toma_cnpj=toma_cnpj, toma_nome=toma_nome, toma_im='',
        toma_end=toma_end, toma_mun=toma_mun, toma_uf=toma_uf,
        cod_serv=cod_serv, item_lista='', desc_serv=desc_serv,
        v_serv=v_serv, v_bc=v_bc, p_aliq=p_aliq,
        v_issqn=v_issqn, v_desc=v_desc, v_ret=v_ret,
        iss_retido=iss_retido, v_liq=v_liq,
        qr_base64='',
    )


def _extrair_dados_xml(xml_content):
    """
    Extrai todos os dados necessários para o DANFSe do XML da NFS-e.
    Suporta dois formatos:
      - SPED/ADN  (namespace http://www.sped.fazenda.gov.br/nfse)
      - ABRASF    (namespace http:/www.abrasf.org.br/nfse.xsd  — DominioWeb / municipal)
    Retorna dict com os campos.
    """
    ns = {'n': 'http://www.sped.fazenda.gov.br/nfse'}

    def t(*xpaths):
        """Tenta múltiplos xpaths (com e sem namespace) e retorna o primeiro resultado."""
        for xpath in xpaths:
            # com namespace
            v = tree.findtext(xpath, namespaces=ns)
            if v:
                return v.strip()
            # sem namespace (tenta substituindo 'n:' por nada)
            v = tree.findtext(xpath.replace('n:', ''))
            if v:
                return v.strip()
        return ''

    tree = etree.fromstring(
        xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content
    )

    # ----------------------------------------------------------------
    # Detecta formato ABRASF pelo namespace da tag raiz ou conteúdo
    # ----------------------------------------------------------------
    raw_tag = tree.tag or ''
    is_abrasf = 'abrasf.org.br' in raw_tag or tree.find('.//InfNfse') is not None
    if not is_abrasf:
        # Tenta namespace ABRASF explícito
        ns_ab = {'ab': 'http:/www.abrasf.org.br/nfse.xsd'}
        is_abrasf = tree.find('.//ab:InfNfse', ns_ab) is not None

    if is_abrasf:
        return _extrair_dados_abrasf(tree)

    # --- SPED/ADN — lógica original ---

    # --- Número e chave ---
    numero = (t('.//n:nNFSe', './/n:nDFSe') or
              tree.findtext('./nNFSe') or
              tree.findtext('./nDFSe') or 'N/A')

    inf_nfse = tree.find('.//n:infNFSe', namespaces=ns)
    if inf_nfse is None:
        inf_nfse = tree.find('.//infNFSe')
    chave = inf_nfse.get('Id', '')[3:] if inf_nfse is not None else ''

    # --- Datas ---
    dh_raw = t('.//n:DPS/n:infDPS/n:dhEmi', './/n:DPS/n:infDPS/n:dCompet')
    dh_emissao = dh_raw
    if dh_raw:
        try:
            dt = datetime.fromisoformat(dh_raw.replace('Z', '+00:00'))
            dh_emissao = dt.strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            pass

    competencia = t('.//n:DPS/n:infDPS/n:dCompet')

    # --- Prestador ---
    prest_cnpj = t('.//n:emit//n:CNPJ')
    prest_nome = t('.//n:emit//n:xNome')
    prest_im   = t('.//n:emit//n:IM')
    prest_lgr  = t('.//n:emit//n:enderNac//n:xLgr')
    prest_nro  = t('.//n:emit//n:enderNac//n:nro')
    prest_bai  = t('.//n:emit//n:enderNac//n:xBairro')
    prest_mun  = t('.//n:emit//n:enderNac//n:cMun')
    prest_uf   = t('.//n:emit//n:enderNac//n:UF')
    prest_cep  = t('.//n:emit//n:enderNac//n:CEP')
    prest_end  = ', '.join(p for p in [prest_lgr, prest_nro, prest_bai] if p)

    # --- Tomador ---
    toma_cnpj = (t('.//n:DPS/n:infDPS/n:toma/n:CNPJ') or
                 t('.//n:DPS/n:infDPS/n:toma/n:CPF'))
    toma_nome  = t('.//n:DPS/n:infDPS/n:toma/n:xNome')
    toma_im    = t('.//n:DPS/n:infDPS/n:toma/n:IM')
    toma_lgr   = t('.//n:DPS/n:infDPS/n:toma/n:end/n:endNac/n:xLgr')
    toma_nro   = t('.//n:DPS/n:infDPS/n:toma/n:end/n:endNac/n:nro')
    toma_bai   = t('.//n:DPS/n:infDPS/n:toma/n:end/n:endNac/n:xBairro')
    toma_mun   = t('.//n:DPS/n:infDPS/n:toma/n:end/n:endNac/n:cMun')
    toma_uf    = t('.//n:DPS/n:infDPS/n:toma/n:end/n:endNac/n:UF')
    toma_end   = ', '.join(p for p in [toma_lgr, toma_nro, toma_bai] if p)

    # --- Serviços ---
    cod_serv   = t('.//n:DPS/n:infDPS/n:serv/n:cServ/n:cTribNac',
                   './/n:DPS/n:infDPS/n:serv/n:cServ/n:cTribMun')
    item_lista = t('.//n:DPS/n:infDPS/n:serv/n:cServ/n:CNAE')
    desc_serv  = (t('.//n:DPS/n:infDPS/n:serv/n:cServ/n:xDescServ',
                    './/n:DPS/n:infDPS/n:serv/n:xDescServ',
                    './/n:xTribMun') or 'Serviços')

    # --- Valores ---
    v_serv  = (t('.//n:DPS/n:infDPS/n:valores/n:vtNF') or
               t('.//n:DPS/n:infDPS/n:valores/n:vServPrest/n:vServ') or
               t('.//n:valores//n:vLiq') or '0.00')
    v_bc    = (t('.//n:DPS/n:infDPS/n:valores/n:vBC') or
               t('.//n:valores//n:vBC') or v_serv)
    p_aliq  = (t('.//n:DPS/n:infDPS/n:valores/n:trib/n:tribMun/n:tribISSQN/n:pAliq') or
               t('.//n:valores//n:pAliqAplic') or '0.00')
    v_issqn = (t('.//n:DPS/n:infDPS/n:valores/n:vtLiq') or
               t('.//n:valores//n:vISSQN') or '0.00')
    v_desc  = t('.//n:DPS/n:infDPS/n:valores/n:vDesc') or '0.00'
    v_ret   = t('.//n:DPS/n:infDPS/n:valores/n:vServPrest/n:vRedBC') or '0.00'
    iss_retido = t('.//n:DPS/n:infDPS/n:valores/n:trib/n:tribMun/n:tribISSQN/n:tpRetISSQN')

    # Valor líquido = valor serviços − ISS retido (quando retido)
    try:
        v_liq_f = float(v_serv)
        if iss_retido == '1':
            v_liq_f -= float(v_issqn)
        v_liq = f"{v_liq_f:.2f}"
    except Exception:
        v_liq = v_serv

    return dict(
        numero=numero, chave=chave,
        dh_emissao=dh_emissao, competencia=competencia,
        prest_cnpj=prest_cnpj, prest_nome=prest_nome, prest_im=prest_im,
        prest_end=prest_end, prest_mun=prest_mun, prest_uf=prest_uf, prest_cep=prest_cep,
        toma_cnpj=toma_cnpj, toma_nome=toma_nome, toma_im=toma_im,
        toma_end=toma_end, toma_mun=toma_mun, toma_uf=toma_uf,
        cod_serv=cod_serv, item_lista=item_lista, desc_serv=desc_serv,
        v_serv=v_serv, v_bc=v_bc, p_aliq=p_aliq,
        v_issqn=v_issqn, v_desc=v_desc, v_ret=v_ret,
        iss_retido=iss_retido, v_liq=v_liq,
        qr_base64='',  # preenchido depois se possível
    )


def _gerar_qr_base64(chave):
    """Gera QR Code como string base64 PNG. Retorna '' se falhar."""
    try:
        import qrcode
        from io import BytesIO
        import base64
        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data(f"https://adn.nfse.gov.br/validacao?chave={chave}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception:
        return ''


def _gerar_com_weasyprint(dados, pdf_path):
    """
    Renderiza o DANFSe em HTML via Jinja2 e converte para PDF com WeasyPrint.
    Retorna True em caso de sucesso, False caso contrário.
    """
    global _weasyprint_available
    # Pula imediatamente se já sabemos que WeasyPrint não está disponível
    if _weasyprint_available is False:
        raise ImportError("WeasyPrint indisponível (GTK ausente — verificação anterior)")
    try:
        import weasyprint
        _weasyprint_available = True
    except (ImportError, OSError) as _wp_err:
        _weasyprint_available = False
        raise ImportError(f"WeasyPrint não importável: {_wp_err}") from _wp_err
    from jinja2 import Environment

    # Filtros Jinja2 personalizados
    env = Environment()
    env.filters['brl']      = lambda v: _fmt_brl(v)
    env.filters['cnpj_fmt'] = lambda v: _fmt_cnpj(v)

    html_str = env.from_string(_DANFSE_HTML_TEMPLATE).render(**dados)
    weasyprint.HTML(string=html_str, base_url=None).write_pdf(str(pdf_path))
    return True


def _gerar_com_reportlab(dados, pdf_path):
    """
    Gera DANFSe com reportlab canvas (fallback quando WeasyPrint não está disponível).
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader

    numero    = dados['numero']
    chave     = dados['chave']
    dh_emissao = dados['dh_emissao']
    prest_nome = dados['prest_nome']
    prest_cnpj = dados['prest_cnpj']
    prest_im   = dados['prest_im']
    prest_end  = dados['prest_end']
    prest_mun  = dados['prest_mun']
    prest_uf   = dados['prest_uf']
    prest_cep  = dados['prest_cep']
    toma_nome  = dados['toma_nome']
    toma_cnpj  = dados['toma_cnpj']
    toma_end   = dados['toma_end']
    desc_serv  = dados['desc_serv']
    v_serv     = dados['v_serv']
    v_bc       = dados['v_bc']
    p_aliq     = dados['p_aliq']
    v_issqn    = dados['v_issqn']

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    mx, my = 15 * mm, 15 * mm

    y = height - my

    # Cabeçalho
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "DANFSE")
    y -= 5 * mm
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, y, "Documento Auxiliar da Nota Fiscal de Serviços Eletrônica")
    y -= 7 * mm

    # Caixa número
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(mx, y - 15 * mm, width - 2 * mx, 15 * mm)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(mx + 3 * mm, y - 7 * mm, f"Nº {numero}")
    c.setFont("Helvetica", 8)
    c.drawString(mx + 3 * mm, y - 12 * mm, f"Emissão: {dh_emissao}")

    # QR Code
    if chave and len(chave) >= 44:
        try:
            import qrcode
            from io import BytesIO
            qr = qrcode.QRCode(version=1, box_size=2, border=1)
            qr.add_data(f"https://adn.nfse.gov.br/validacao?chave={chave}")
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img_qr.save(buf, format='PNG')
            buf.seek(0)
            c.drawImage(ImageReader(buf), width - mx - 25 * mm, y - 15 * mm, 22 * mm, 22 * mm)
        except Exception:
            pass

    y -= 18 * mm

    # Prestador
    c.setFont("Helvetica-Bold", 9)
    c.drawString(mx, y, "PRESTADOR DE SERVIÇOS")
    y -= 5 * mm
    c.setStrokeColor(colors.grey)
    c.setLineWidth(0.5)
    c.rect(mx, y - 25 * mm, width - 2 * mx, 25 * mm)
    c.setFont("Helvetica", 8)
    c.drawString(mx + 2 * mm, y - 4 * mm, f"Razão Social: {prest_nome}")
    c.drawString(mx + 2 * mm, y - 9 * mm, f"CNPJ: {_fmt_cnpj(prest_cnpj)}")
    c.drawString(mx + 2 * mm, y - 14 * mm, f"Inscrição Municipal: {prest_im}")
    if prest_end:
        c.drawString(mx + 2 * mm, y - 19 * mm, f"Endereço: {prest_end[:80]}")
        c.drawString(mx + 2 * mm, y - 23 * mm,
                     f"CEP: {prest_cep}  Município/UF: {prest_mun}/{prest_uf}")
    y -= 28 * mm

    # Tomador
    c.setFont("Helvetica-Bold", 9)
    c.drawString(mx, y, "TOMADOR DE SERVIÇOS")
    y -= 5 * mm
    c.rect(mx, y - 20 * mm, width - 2 * mx, 20 * mm)
    c.setFont("Helvetica", 8)
    c.drawString(mx + 2 * mm, y - 4 * mm, f"Razão Social: {toma_nome}")
    c.drawString(mx + 2 * mm, y - 9 * mm, f"CNPJ/CPF: {_fmt_cnpj(toma_cnpj)}")
    if toma_end:
        c.drawString(mx + 2 * mm, y - 14 * mm, f"Endereço: {toma_end[:80]}")
    y -= 23 * mm

    # Discriminação
    c.setFont("Helvetica-Bold", 9)
    c.drawString(mx, y, "DISCRIMINAÇÃO DOS SERVIÇOS")
    y -= 5 * mm
    h_serv = 30 * mm
    c.rect(mx, y - h_serv, width - 2 * mx, h_serv)
    c.setFont("Helvetica", 8)
    y_txt = y - 4 * mm
    for i in range(0, len(desc_serv), 95):
        c.drawString(mx + 2 * mm, y_txt, desc_serv[i:i + 95])
        y_txt -= 4 * mm
        if y_txt < y - h_serv + 2 * mm:
            break
    y -= h_serv + 3 * mm

    # Valores
    c.setFont("Helvetica-Bold", 9)
    c.drawString(mx, y, "VALORES")
    y -= 5 * mm
    for label, val in [
        ("Valor dos Serviços", f"R$ {_fmt_brl(v_serv)}"),
        ("Base de Cálculo",    f"R$ {_fmt_brl(v_bc)}"),
        ("Alíquota ISS",       f"{_fmt_brl(p_aliq)}%"),
        ("Valor do ISS",       f"R$ {_fmt_brl(v_issqn)}"),
    ]:
        c.setFont("Helvetica", 8)
        c.drawString(mx + 2 * mm, y, label)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(width / 2, y, val)
        y -= 5 * mm

    # Rodapé
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.grey)
    ry = my + 10 * mm
    c.drawCentredString(width / 2, ry,
        "PDF gerado localmente — para o documento oficial acesse adn.nfse.gov.br")
    if chave:
        c.setFont("Helvetica", 6)
        c.drawCentredString(width / 2, ry - 4 * mm, f"Chave: {chave}")

    c.save()
    return True


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------

def gerar_danfse_profissional(xml_content, pdf_path):
    """
    Gera DANFSe localmente a partir do XML da NFS-e.

    Método 1 (preferido): WeasyPrint + Jinja2  → PDF moderno com CSS
    Método 2 (fallback) : reportlab canvas     → compatível com PyInstaller

    Esta função só deve ser chamada quando o PDF oficial da API
    (GET /danfse/{chave}) não estiver disponível.

    Args:
        xml_content: Conteúdo XML da NFS-e (str ou bytes)
        pdf_path   : Caminho de destino do PDF (str ou Path)

    Returns:
        bool: True se o PDF foi gerado com sucesso.
    """
    _debug_prof("=" * 60)
    _debug_prof("INÍCIO gerar_danfse_profissional()")

    try:
        dados = _extrair_dados_xml(xml_content)
        _debug_prof(f"XML extraído — nNFSe={dados['numero']}, chave={dados['chave'][:15]}…")
    except Exception as exc:
        import traceback
        _debug_prof(f"❌ Falha ao extrair dados do XML: {exc}\n{traceback.format_exc()}")
        return False

    # Tenta gerar QR Code (não é crítico)
    if dados['chave']:
        dados['qr_base64'] = _gerar_qr_base64(dados['chave'])

    # ---- Método 1: WeasyPrint + Jinja2 ----
    try:
        _debug_prof("Tentando WeasyPrint + Jinja2…")
        _gerar_com_weasyprint(dados, pdf_path)
        from pathlib import Path
        tamanho = Path(pdf_path).stat().st_size if Path(pdf_path).exists() else 0
        _debug_prof(f"✅ WeasyPrint OK — {tamanho:,} bytes")
        return True
    except ImportError as ie:
        _debug_prof(f"WeasyPrint/Jinja2 não disponível ({ie}), usando reportlab…")
    except Exception as exc:
        import traceback
        _debug_prof(f"⚠️ WeasyPrint falhou ({exc}), usando reportlab…\n{traceback.format_exc()}")

    # ---- Método 2: reportlab (fallback) ----
    try:
        _debug_prof("Tentando reportlab canvas…")
        _gerar_com_reportlab(dados, pdf_path)
        from pathlib import Path
        tamanho = Path(pdf_path).stat().st_size if Path(pdf_path).exists() else 0
        _debug_prof(f"✅ reportlab OK — {tamanho:,} bytes")
        return True
    except Exception as exc:
        import traceback
        _debug_prof(f"❌ reportlab também falhou: {exc}\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    from pathlib import Path

    xmls = list(Path('xmls').rglob('NFSe_*.xml'))
    if not xmls:
        print("Nenhum XML de NFS-e encontrado em xmls/")
    else:
        xml_path = xmls[0]
        print(f"Testando com: {xml_path}")
        xml_content = xml_path.read_text(encoding='utf-8')
        pdf_path = 'teste_danfse_profissional.pdf'
        if gerar_danfse_profissional(xml_content, pdf_path):
            print(f"✅ DANFSe gerado: {pdf_path}")
        else:
            print("❌ Falha ao gerar")

