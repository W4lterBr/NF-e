#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gera_danfe_local.py

Gera DANFE A4 retrato (folhas soltas) aplicando o XSLT oficial 4.00
a partir de um XSLT local e converte em PDF com wkhtmltopdf.

Pré-requisitos:
  pip install lxml pdfkit
  wkhtmltopdf instalado (defina WKHTMLTOPDF_PATH se necessário).

Passo obrigatório ANTES de rodar:
1. Abra no navegador e baixe o XSLT oficial (v4.00):
     https://www.portalfiscal.inf.br/nfe/NFe-Danfe-NFCe_v4.00.xsl
2. Salve como:
     C:\Users\Walter\Documents\Arquivo Walter\BOT - Busca NFE\xmls\DANFE_NFe_v4.00.xsl
"""
import os
import glob
from lxml import etree
import pdfkit

# —————————————————————————————————————————————————
# 1) Ajuste estes caminhos se for diferente
DIR_XML   = r"C:\Users\Walter\Documents\Arquivo Walter\BOT - Busca NFE\xmls"
XSLT_FILE = os.path.join(DIR_XML, "DANFE_NFe_v4.00.xsl")

# 2) Caminho do wkhtmltopdf (ou defina WKHTMLTOPDF_PATH no seu env)
WK_BIN     = os.environ.get(
    "WKHTMLTOPDF_PATH",
    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
)
PDFKIT_CFG = pdfkit.configuration(wkhtmltopdf=WK_BIN)

# 3) Opções para respeitar scripts e CSS do DANFE
PDF_OPTIONS = {
    'enable-javascript': None,
    'javascript-delay': '1500',
    'no-stop-slow-scripts': None,
    'viewport-size': '1280x1024',
    'zoom': '1.0',
}

def load_transformer():
    """Carrega o XSLT oficial de arquivo local."""
    if not os.path.isfile(XSLT_FILE):
        raise FileNotFoundError(
            f"Arquivo XSLT não encontrado: {XSLT_FILE}\n"
            "Baixe em https://www.portalfiscal.inf.br/nfe/NFe-Danfe-NFCe_v4.00.xsl\n"
            "e salve com este nome na pasta xmls."
        )
    xslt_doc = etree.parse(XSLT_FILE)
    return etree.XSLT(xslt_doc)

def xml_to_html(xml_path, transform):
    """Aplica o XSLT local ao XML e retorna o HTML."""
    doc = etree.parse(xml_path)
    result = transform(doc)
    return str(result)

def html_to_pdf(html_str, pdf_path):
    """Converte o HTML em PDF usando wkhtmltopdf."""
    pdfkit.from_string(html_str, pdf_path,
                       configuration=PDFKIT_CFG,
                       options=PDF_OPTIONS)

def main():
    try:
        transform = load_transformer()
    except Exception as e:
        print("❌ ERRO ao carregar XSLT:", e)
        return

    xml_files = glob.glob(os.path.join(DIR_XML, "*.xml"))
    if not xml_files:
        print("❌ Nenhum XML encontrado em", DIR_XML)
        return

    for xml in xml_files:
        base = os.path.splitext(os.path.basename(xml))[0]
        out_pdf = os.path.join(DIR_XML, f"DANFE_{base}.pdf")
        try:
            html = xml_to_html(xml, transform)
            html_to_pdf(html, out_pdf)
            print("✔ Gerado:", out_pdf)
        except Exception as e:
            print(f"❌ Erro ao processar {xml}: {e}")

if __name__ == "__main__":
    main()
