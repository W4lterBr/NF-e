#!/usr/bin/env python3
"""
Consulta eventos de um CT-e específico na SEFAZ.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import NFeService, DatabaseManager

CHAVE_CTE = "50251203232675000154570010056290311009581385"

def main():
    print(f"\n{'='*80}")
    print(f"CONSULTA DE EVENTOS DO CT-e NA SEFAZ")
    print(f"{'='*80}\n")
    print(f"Chave: {CHAVE_CTE}\n")
    
    # Conecta ao banco
    db_path = BASE_DIR / "notas_test.db"
    db = DatabaseManager(db_path)
    
    # Carrega certificados
    certificados = db.get_certificados()
    if not certificados:
        print("❌ Nenhum certificado cadastrado!")
        return
    
    print(f"Certificados: {len(certificados)}\n")
    
    # Tenta com cada certificado
    for idx, (cnpj, path, senha, inf, cuf) in enumerate(certificados):
        print(f"{'='*80}")
        print(f"TENTATIVA {idx+1}/{len(certificados)}: {inf} (UF={cuf})")
        print(f"{'='*80}\n")
        
        try:
            svc = NFeService(path, senha, cnpj, cuf)
            
            # Consulta eventos
            print("Consultando eventos na SEFAZ...")
            resp_xml = svc.consultar_eventos_chave(CHAVE_CTE)
            
            if resp_xml:
                print(f"\n✅ Resposta recebida ({len(resp_xml)} caracteres)\n")
                
                # Verifica se tem evento de cancelamento
                if 'tpEvento>110111' in resp_xml or 'tpEvento="110111"' in resp_xml:
                    print("🚫 CANCELAMENTO ENCONTRADO!")
                    
                    # Salva para análise
                    output_file = BASE_DIR / f"{CHAVE_CTE}_eventos.xml"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(resp_xml)
                    print(f"\n📄 XML de eventos salvo em: {output_file}\n")
                    
                    # Extrai informações do cancelamento
                    from lxml import etree
                    tree = etree.fromstring(resp_xml.encode('utf-8'))
                    ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
                    
                    eventos = tree.findall('.//cte:infEvento', namespaces=ns)
                    if eventos:
                        print(f"\n{'='*60}")
                        print(f"EVENTOS ENCONTRADOS: {len(eventos)}")
                        print(f"{'='*60}\n")
                        
                        for i, evento in enumerate(eventos, 1):
                            tp_evento = evento.findtext('cte:tpEvento', namespaces=ns)
                            desc = evento.findtext('cte:descEvento', namespaces=ns) or evento.findtext('cte:xEvento', namespaces=ns)
                            cstat = evento.findtext('cte:cStat', namespaces=ns)
                            xmotivo = evento.findtext('cte:xMotivo', namespaces=ns)
                            dh_evento = evento.findtext('cte:dhRegEvento', namespaces=ns)
                            nseq = evento.findtext('cte:nSeqEvento', namespaces=ns)
                            
                            print(f"Evento #{i}:")
                            print(f"  Tipo: {tp_evento} ({desc})")
                            print(f"  Status: {cstat} - {xmotivo}")
                            print(f"  Data/Hora: {dh_evento}")
                            print(f"  Sequência: {nseq}")
                            
                            if tp_evento == '110111':
                                print(f"  → 🚫 CANCELAMENTO")
                                if cstat == '135':
                                    print(f"  → ✅ HOMOLOGADO")
                            print()
                    
                    return
                    
                elif 'cStat>217' in resp_xml or 'cStat="217"' in resp_xml:
                    print("ℹ️  Nenhum evento registrado para esta chave")
                elif 'cStat>226' in resp_xml:
                    print("⚠️  UF divergente")
                else:
                    # Mostra primeiros 1000 caracteres
                    print("Resposta:")
                    print(resp_xml[:1000])
                    print("\n...")
            else:
                print("❌ Nenhuma resposta recebida")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print(f"{'='*80}")
    print("❌ Nenhum evento de cancelamento encontrado em nenhum certificado")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
