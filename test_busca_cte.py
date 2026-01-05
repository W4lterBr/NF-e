#!/usr/bin/env python3
"""
Script de teste para buscar CT-e por chave de acesso.
"""

import sys
from pathlib import Path

# Adiciona o diretório base ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import NFeService, DatabaseManager

# Chave do CT-e problemático
CHAVE_CTE = "50251203232675000154570010056290311009581385"

def main():
    print(f"\n{'='*80}")
    print(f"TESTE DE BUSCA CT-e POR CHAVE")
    print(f"{'='*80}\n")
    print(f"Chave: {CHAVE_CTE}")
    
    # Detecta tipo
    modelo = CHAVE_CTE[20:22]
    tipo = "CT-e" if modelo == "57" else "NF-e"
    print(f"Modelo: {modelo} ({tipo})")
    print(f"UF: {CHAVE_CTE[:2]}")
    print()
    
    # Conecta ao banco
    db_path = BASE_DIR / "notas_test.db"
    db = DatabaseManager(db_path)
    
    # Carrega certificados
    certificados = db.get_certificados()
    print(f"Certificados cadastrados: {len(certificados)}")
    
    if not certificados:
        print("❌ Nenhum certificado cadastrado!")
        return
    
    # Tenta buscar com cada certificado
    for idx, (cnpj, path, senha, inf, cuf) in enumerate(certificados):
        print(f"\n{'='*80}")
        print(f"TENTATIVA {idx+1}/{len(certificados)}")
        print(f"{'='*80}")
        print(f"Certificado: {cnpj}")
        print(f"Informante: {inf}")
        print(f"UF: {cuf}")
        print()
        
        try:
            svc = NFeService(path, senha, cnpj, cuf)
            
            # Busca CT-e
            print("Buscando CT-e na SEFAZ...")
            resp_xml = svc.fetch_prot_cte(CHAVE_CTE)
            
            if resp_xml:
                print(f"✅ Resposta recebida ({len(resp_xml)} caracteres)")
                print(f"\nPrimeiros 500 caracteres:")
                print(resp_xml[:500])
                
                # Verifica cStat
                if '<cStat>100</cStat>' in resp_xml:
                    print("\n✅ CT-e AUTORIZADO (cStat=100)!")
                    
                    # Salva XML para análise
                    output_file = BASE_DIR / f"{CHAVE_CTE}_resposta.xml"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(resp_xml)
                    print(f"\n📄 XML salvo em: {output_file}")
                    
                    print("\n🎉 SUCESSO! CT-e encontrado!")
                    return
                elif '<cStat>217</cStat>' in resp_xml:
                    print("\n⚠️ CT-e não consta na base deste certificado (217)")
                elif '<cStat>226</cStat>' in resp_xml:
                    print("\n⚠️ UF divergente (226)")
                else:
                    import re
                    cstat_match = re.search(r'<cStat>(\d+)</cStat>', resp_xml)
                    xmotivo_match = re.search(r'<xMotivo>([^<]+)</xMotivo>', resp_xml)
                    cstat = cstat_match.group(1) if cstat_match else "?"
                    xmotivo = xmotivo_match.group(1) if xmotivo_match else "?"
                    print(f"\n⚠️ Código: {cstat} - {xmotivo}")
            else:
                print("❌ Nenhuma resposta recebida")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("❌ CT-e não encontrado em nenhum certificado")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
