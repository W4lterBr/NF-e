# -*- coding: utf-8 -*-
"""
Testa salvamento em múltiplos perfis ativos
"""
import sys
sys.path.insert(0, '.')

from nfe_search import salvar_xml_por_certificado
from datetime import datetime

print("="*80)
print("🧪 TESTE: SALVAMENTO EM MÚLTIPLOS PERFIS")
print("="*80)
print()

# XML de teste
xml_teste = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
    <NFe>
        <infNFe Id="NFe52260115045348000172570010014777191002562584">
            <ide>
                <cUF>52</cUF>
                <cNF>00256258</cNF>
                <natOp>VENDA</natOp>
                <mod>55</mod>
                <serie>1</serie>
                <nNF>000200</nNF>
                <dhEmi>2026-02-18T10:00:00-03:00</dhEmi>
                <tpNF>1</tpNF>
                <idDest>1</idDest>
                <cMunFG>5208707</cMunFG>
                <tpImp>1</tpImp>
                <tpEmis>1</tpEmis>
                <cDV>4</cDV>
                <tpAmb>1</tpAmb>
                <finNFe>1</finNFe>
                <indFinal>0</indFinal>
                <indPres>1</indPres>
                <procEmi>0</procEmi>
                <verProc>1.0</verProc>
            </ide>
            <emit>
                <CNPJ>15045348000172</CNPJ>
                <xNome>EMPRESA TESTE MULTIPERFIS LTDA</xNome>
                <xFant>TESTE MULTI</xFant>
                <enderEmit>
                    <xLgr>RUA TESTE</xLgr>
                    <nro>100</nro>
                    <xBairro>CENTRO</xBairro>
                    <cMun>5208707</cMun>
                    <xMun>GOIANIA</xMun>
                    <UF>GO</UF>
                    <CEP>74000000</CEP>
                    <cPais>1058</cPais>
                    <xPais>BRASIL</xPais>
                </enderEmit>
                <IE>123456789</IE>
                <CRT>3</CRT>
            </emit>
            <dest>
                <CNPJ>12345678000199</CNPJ>
                <xNome>CLIENTE TESTE</xNome>
                <enderDest>
                    <xLgr>AV TESTE</xLgr>
                    <nro>200</nro>
                    <xBairro>CENTRO</xBairro>
                    <cMun>5208707</cMun>
                    <xMun>GOIANIA</xMun>
                    <UF>GO</UF>
                    <CEP>74000000</CEP>
                    <cPais>1058</cPais>
                    <xPais>BRASIL</xPais>
                </enderDest>
                <indIEDest>1</indIEDest>
                <IE>987654321</IE>
            </dest>
            <det nItem="1">
                <prod>
                    <cProd>001</cProd>
                    <cEAN></cEAN>
                    <xProd>PRODUTO TESTE</xProd>
                    <NCM>12345678</NCM>
                    <CFOP>5102</CFOP>
                    <uCom>UN</uCom>
                    <qCom>1.0000</qCom>
                    <vUnCom>100.00</vUnCom>
                    <vProd>100.00</vProd>
                    <cEANTrib></cEANTrib>
                    <uTrib>UN</uTrib>
                    <qTrib>1.0000</qTrib>
                    <vUnTrib>100.00</vUnTrib>
                    <indTot>1</indTot>
                </prod>
                <imposto>
                    <ICMS>
                        <ICMS00>
                            <orig>0</orig>
                            <CST>00</CST>
                            <modBC>0</modBC>
                            <vBC>100.00</vBC>
                            <pICMS>18.00</pICMS>
                            <vICMS>18.00</vICMS>
                        </ICMS00>
                    </ICMS>
                </imposto>
            </det>
            <total>
                <ICMSTot>
                    <vBC>100.00</vBC>
                    <vICMS>18.00</vICMS>
                    <vICMSDeson>0.00</vICMSDeson>
                    <vFCP>0.00</vFCP>
                    <vBCST>0.00</vBCST>
                    <vST>0.00</vST>
                    <vFCPST>0.00</vFCPST>
                    <vFCPSTRet>0.00</vFCPSTRet>
                    <vProd>100.00</vProd>
                    <vFrete>0.00</vFrete>
                    <vSeg>0.00</vSeg>
                    <vDesc>0.00</vDesc>
                    <vII>0.00</vII>
                    <vIPI>0.00</vIPI>
                    <vIPIDevol>0.00</vIPIDevol>
                    <vPIS>0.00</vPIS>
                    <vCOFINS>0.00</vCOFINS>
                    <vOutro>0.00</vOutro>
                    <vNF>100.00</vNF>
                </ICMSTot>
            </total>
            <transp>
                <modFrete>9</modFrete>
            </transp>
            <pag>
                <detPag>
                    <indPag>0</indPag>
                    <tPag>01</tPag>
                    <vPag>100.00</vPag>
                </detPag>
            </pag>
        </infNFe>
    </NFe>
    <protNFe versao="4.00">
        <infProt>
            <tpAmb>1</tpAmb>
            <verAplic>SVRS202402011515</verAplic>
            <chNFe>52260115045348000172570010014777191002562584</chNFe>
            <dhRecbto>2026-02-18T10:01:00-03:00</dhRecbto>
            <nProt>152260000000001</nProt>
            <digVal>abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx=</digVal>
            <cStat>100</cStat>
            <xMotivo>Autorizado o uso da NF-e</xMotivo>
        </infProt>
    </protNFe>
</nfeProc>"""

print("📋 Dados do teste:")
print("   CNPJ: 15045348000172")
print("   NF-e: 000200")
print("   Emitente: EMPRESA TESTE MULTIPERFIS LTDA")
print()

print("💾 Salvando XML com pasta_base=None (todos os perfis ativos)...")
print()

try:
    # Salva em TODOS os perfis ativos
    resultado = salvar_xml_por_certificado(
        xml=xml_teste,
        cnpj_cpf="15045348000172",
        pasta_base=None,  # ⚠️ None = salva em TODOS os perfis ativos
        nome_certificado="TESTE_MULTIPERFIS",
        formato_mes="MMAAAA"
    )
    
    print()
    print("="*80)
    print("✅ RESULTADO")
    print("="*80)
    print()
    print("📁 Arquivo salvo com sucesso nos perfis ativos!")
    print()
    print("🔍 Verifique os arquivos em:")
    print("   1. C:\\Arquivo Walter - Empresas\\Notas\\DominioWeb\\TESTE_MULTIPERFIS\\022026\\NFe\\")
    print("   2. C:\\Arquivo Walter - Empresas\\Notas\\NFs\\TESTE_MULTIPERFIS\\022026\\NFe\\")
    print()
    print("💡 CONCLUSÃO:")
    print("   • Quando você BUSCAR XMLs, eles serão salvos automaticamente nos 2 perfis")
    print("   • Você pode criar quantos perfis quiser (5, 10, 20...)")
    print("   • Todos os perfis ATIVOS receberão os arquivos")
    print()
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("="*80)
