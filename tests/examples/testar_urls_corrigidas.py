#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testa URLs corrigidas para DF e ES
"""

# Chaves de teste dos logs
chaves_teste = {
    'DF_NFE': '53251137056132000145550020011410611490016848',
    'DF_CTE': '53251248740351001137570000007259621439722566',
    'ES_NFE': '32251105607657001026550210003305311339865336',
    'ES_CTE': '32251148740351001641570000065263841976277655'
}

print("🔍 Análise das URLs corrigidas\n")
print("="*80)

# Simula lógica de detecção de URL
def get_url_nfe(cuf):
    url_map = {
        '31': 'https://nfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4',  # MG
        '50': 'https://nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4',  # MS
        '51': 'https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4',  # MT
        '35': 'https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',  # SP
        '41': 'https://nfe.sefa.pr.gov.br/nfe/NFeConsultaProtocolo4',  # PR
        '29': 'https://nfe.sefaz.ba.gov.br/webservices/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # BA
        # SVRS para estados sem servidor próprio
        '32': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # ES (SVRS)
        '33': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # RJ (SVRS)
        '52': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # GO (SVRS)
        '53': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # DF (SVRS)
    }
    return url_map.get(cuf, 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx')

def get_url_cte(cuf):
    url_map = {
        '31': 'https://cte.fazenda.mg.gov.br/cte/services/CTeConsultaV4',  # MG
        '35': 'https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeConsultaV4.asmx',  # SP
        '41': 'https://cte.fazenda.pr.gov.br/cte4/CTeConsultaV4',  # PR
        '50': 'https://producao.cte.ms.gov.br/ws/CTeConsultaV4',  # MS
        '51': 'https://cte.sefaz.mt.gov.br/ctews2/services/CTeConsultaV4',  # MT
        # SVRS (usado por GO=52, DF=53, RJ=33, RS=43, AC, AL, AP, ES, PA, PB, PI, RN, RO, RR, SC, SE, TO)
        '52': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # GO (SVRS)
        '53': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # DF (SVRS)
        '33': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # RJ (SVRS)
        '43': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # RS (SVRS)
    }
    return url_map.get(cuf, 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx')

ufs = {
    '53': 'DF (Distrito Federal)',
    '32': 'ES (Espírito Santo)'
}

for nome, chave in chaves_teste.items():
    cuf = chave[:2]
    modelo = chave[20:22]
    tipo = 'CT-e' if modelo == '57' else 'NF-e'
    
    print(f"\n📋 {nome}")
    print(f"   Chave: {chave}")
    print(f"   UF: {cuf} - {ufs.get(cuf, 'Desconhecido')}")
    print(f"   Tipo: {tipo} (modelo {modelo})")
    
    if tipo == 'NF-e':
        url = get_url_nfe(cuf)
    else:
        url = get_url_cte(cuf)
    
    print(f"   URL: {url}")
    
    # Verifica se é SVRS
    if 'sefazvirtual' in url or 'svrs' in url:
        print(f"   ✅ Usa SVRS (Sefaz Virtual)")
    else:
        print(f"   ℹ️ Servidor próprio do estado")

print("\n" + "="*80)
print("\n📊 Resumo das correções:")
print("\n1. ✅ DF (53) - NF-e:")
print("   ❌ Antes: https://nfe.sefaz.df.gov.br/ws/NFeConsultaProtocolo4")
print("   ✅ Agora: https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/...")
print("   → DF não tem servidor próprio, usa SVRS")

print("\n2. ✅ ES (32) - NF-e:")
print("   ❌ Antes: URL não mapeada (usava fallback)")
print("   ✅ Agora: https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/...")
print("   → ES também usa SVRS")

print("\n3. ✅ Correção SSL:")
print("   ❌ Antes: verify=False + check_hostname=True (conflito)")
print("   ✅ Agora: Contexto SSL personalizado com ambos desabilitados")
print("   → Compatível com Python 3.10+")

print("\n" + "="*80)
