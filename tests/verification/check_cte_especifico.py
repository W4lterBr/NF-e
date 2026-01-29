#!/usr/bin/env python3
"""Verifica status do CT-e específico no banco de dados."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "notas_test.db"
CHAVE = "50251203232675000154570010056290311009581385"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    
    # Verifica se a chave existe
    print(f"\n{'='*80}")
    print(f"VERIFICANDO CHAVE: {CHAVE}")
    print(f"{'='*80}\n")
    
    cursor = conn.execute(
        "SELECT chave, tipo, status, numero, nome_emitente, data_emissao FROM notas_detalhadas WHERE chave = ?",
        (CHAVE,)
    )
    row = cursor.fetchone()
    
    if row:
        print("✅ CHAVE ENCONTRADA NO BANCO:")
        print(f"   Tipo: {row[1]}")
        print(f"   Status: {row[2]}")
        print(f"   Número: {row[3]}")
        print(f"   Emitente: {row[4]}")
        print(f"   Data Emissão: {row[5]}")
    else:
        print("❌ CHAVE NÃO ENCONTRADA NO BANCO")
    
    print(f"\n{'='*80}")
    
    # Busca CTes similares (mesmo CNPJ emitente)
    cnpj_prefix = CHAVE[6:20]  # Extrai CNPJ da chave
    print(f"\nBuscando CT-es do mesmo CNPJ ({cnpj_prefix}):")
    cursor = conn.execute(
        "SELECT chave, status, numero FROM notas_detalhadas WHERE tipo = 'CTe' AND chave LIKE ? LIMIT 10",
        (f"______{cnpj_prefix}%",)
    )
    rows = cursor.fetchall()
    
    if rows:
        for r in rows:
            print(f"  {r[0]} - Status: {r[1]} - Num: {r[2]}")
    else:
        print("  Nenhum CT-e encontrado com esse CNPJ")
    
    # Total de CTes
    cursor = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo = 'CTe'")
    total_ctes = cursor.fetchone()[0]
    print(f"\n📊 Total de CT-es no banco: {total_ctes}")
    
    # Verifica XMLs baixados
    print(f"\n{'='*80}")
    print("VERIFICANDO ARQUIVOS XML:")
    print(f"{'='*80}\n")
    
    xml_dir = Path(__file__).parent / "xml_extraidos"
    xml_file = xml_dir / f"{CHAVE}-cte.xml"
    
    if xml_file.exists():
        print(f"✅ XML completo encontrado: {xml_file}")
        # Verifica conteúdo
        try:
            content = xml_file.read_text(encoding='utf-8')
            if 'procEventoCTe' in content:
                print("   📄 Arquivo contém evento (procEventoCTe)")
            elif 'cteProc' in content:
                print("   📄 Arquivo é CT-e completo (cteProc)")
            elif 'resCTe' in content:
                print("   📄 Arquivo é resumo (resCTe)")
        except Exception as e:
            print(f"   ⚠️ Erro ao ler arquivo: {e}")
    else:
        print(f"❌ XML completo não encontrado: {xml_file}")
    
    # Verifica eventos
    eventos_dir = xml_dir / "eventos"
    if eventos_dir.exists():
        eventos = list(eventos_dir.glob(f"{CHAVE}*.xml"))
        if eventos:
            print(f"\n✅ {len(eventos)} evento(s) encontrado(s):")
            for evento in eventos:
                print(f"   - {evento.name}")
                try:
                    content = evento.read_text(encoding='utf-8')
                    if '110111' in content:
                        print("     → Tipo: CANCELAMENTO (110111)")
                    if 'cStat>135' in content:
                        print("     → Status: HOMOLOGADO (135)")
                except:
                    pass
        else:
            print(f"\n❌ Nenhum evento encontrado para essa chave")
    
    conn.close()
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
