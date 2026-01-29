"""
Teste de processamento de evento de manifestação (simula o código real do nfe_search.py).
"""
import sys
from pathlib import Path
from lxml import etree

# Adiciona o diretório raiz ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import DatabaseManager

def test_evento_processing():
    """Testa o processamento de evento como no código real"""
    
    print("=" * 60)
    print("TESTE DE PROCESSAMENTO DE EVENTO")
    print("=" * 60)
    
    # XML de exemplo de evento tipo 210210 (Ciência da Operação)
    xml_evento = '''<?xml version="1.0" encoding="UTF-8"?>
<procEventoNFe versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe">
    <evento versao="1.00">
        <infEvento Id="ID2102105026012950648000014955001000149851100276746001">
            <cOrgao>50</cOrgao>
            <tpAmb>1</tpAmb>
            <CNPJ>33251845000109</CNPJ>
            <chNFe>50260129506480000149550010001498511002767460</chNFe>
            <dhEvento>2026-01-07T15:30:00-03:00</dhEvento>
            <tpEvento>210210</tpEvento>
            <nSeqEvento>1</nSeqEvento>
            <verEvento>1.00</verEvento>
            <detEvento versao="1.00">
                <descEvento>Ciencia da Operacao</descEvento>
            </detEvento>
        </infEvento>
    </evento>
    <retEvento versao="1.00">
        <infEvento Id="ID1351234567890">
            <tpAmb>1</tpAmb>
            <verAplic>MS_PL_000001</verAplic>
            <cOrgao>50</cOrgao>
            <cStat>135</cStat>
            <xMotivo>Evento registrado e vinculado a NF-e</xMotivo>
            <chNFe>50260129506480000149550010001498511002767460</chNFe>
            <tpEvento>210210</tpEvento>
            <xEvento>Ciencia da Operacao</xEvento>
            <nSeqEvento>1</nSeqEvento>
            <CNPJDest>33251845000109</CNPJDest>
            <dhRegEvento>2026-01-07T15:30:05-03:00</dhRegEvento>
            <nProt>150260000123456</nProt>
        </infEvento>
    </retEvento>
</procEventoNFe>'''
    
    # Inicializa banco
    db_path = BASE_DIR / "notas_test.db"
    print(f"\n📂 Usando banco: {db_path}")
    
    db = DatabaseManager(db_path)
    print("✅ DatabaseManager inicializado")
    
    # Simula o processamento do evento (código do nfe_search.py linhas 2610-2625)
    print("\n🔄 Processando evento XML...")
    
    tree = etree.fromstring(xml_evento.encode('utf-8'))
    ns = "{http://www.portalfiscal.inf.br/nfe}"
    
    # Extrai informações do evento
    chave = tree.findtext(f'.//{ns}chNFe')
    tpEvento = tree.findtext(f'.//{ns}tpEvento')
    cnpj = tree.findtext(f'.//{ns}CNPJ') or tree.findtext(f'.//{ns}CNPJDest')
    cStat_evento = tree.findtext(f'.//{ns}cStat')
    protocolo = tree.findtext(f'.//{ns}nProt')
    
    print(f"\n📋 Dados extraídos:")
    print(f"   Chave: {chave}")
    print(f"   Tipo Evento: {tpEvento}")
    print(f"   CNPJ: {cnpj}")
    print(f"   cStat: {cStat_evento}")
    print(f"   Protocolo: {protocolo}")
    
    # Simula o código real de processamento
    print(f"\n🔍 Verificando se é manifestação (tpEvento.startswith('2102')): {tpEvento.startswith('2102')}")
    print(f"🔍 Verificando cStat == '135': {cStat_evento == '135'}")
    
    if tpEvento and tpEvento.startswith('2102'):
        print(f"✅ É uma manifestação do destinatário")
        
        if cStat_evento == '135':
            print(f"✅ Evento registrado com sucesso (cStat=135)")
            
            # Verifica se já existe
            print(f"\n🔍 Verificando se manifestação já existe...")
            existe = db.check_manifestacao_exists(chave, tpEvento, cnpj)
            print(f"   Resultado: {existe}")
            
            if not existe:
                print(f"\n📝 Registrando manifestação...")
                sucesso = db.register_manifestacao(chave, tpEvento, cnpj, 'REGISTRADA', protocolo)
                
                if sucesso:
                    print(f"✅ Manifestação {tpEvento} registrada para chave {chave}")
                else:
                    print(f"⚠️ Falha ao registrar manifestação")
            else:
                print(f"ℹ️ Manifestação já estava registrada")
    
    # Verifica no banco
    print(f"\n🔍 Consultando banco de dados...")
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT COUNT(*) FROM manifestacoes WHERE chave = ?",
        (chave,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"   Total de manifestações para esta chave: {count}")
    
    if count > 0:
        print("\n" + "=" * 60)
        print("✅ TESTE BEM-SUCEDIDO!")
        print("   - Evento processado corretamente")
        print("   - Manifestação registrada no banco")
        print("   - Nenhum erro de 'check_manifestacao_exists'")
        print("=" * 60)
        return True
    else:
        print("\n❌ ERRO: Manifestação não foi registrada")
        return False

if __name__ == "__main__":
    try:
        success = test_evento_processing()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERRO DURANTE TESTE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
