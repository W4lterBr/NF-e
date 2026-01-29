"""
Script de teste para demonstrar o comportamento do loop NF-e
Simula diferentes cenários de ultNSU vs maxNSU
"""

def simular_loop_nfe():
    """Simula o comportamento do loop NF-e"""
    
    print("=" * 80)
    print("SIMULAÇÃO DO LOOP NF-e")
    print("=" * 80)
    
    # Cenário 1: Há documentos (ultNSU < maxNSU)
    print("\n📋 CENÁRIO 1: Há documentos para buscar")
    print("-" * 80)
    ult_nsu = 59025
    max_nsu = 61722
    iteration = 0
    max_iterations = 100
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 Iteração {iteration}/{max_iterations}")
        print(f"   NSU atual: {ult_nsu:015d}")
        print(f"   maxNSU: {max_nsu:015d}")
        
        # Simula resposta SEFAZ (50 docs por vez)
        docs_processados = min(50, max_nsu - ult_nsu)
        ult_nsu += docs_processados
        
        print(f"   📥 Processados: {docs_processados} documentos")
        print(f"   📊 Novo ultNSU: {ult_nsu:015d}")
        
        # Verifica se sincronizou
        if ult_nsu == max_nsu:
            print(f"\n✅ SINCRONIZADO! ultNSU ({ult_nsu:015d}) == maxNSU ({max_nsu:015d})")
            print(f"   ⏰ Aguardar 1 hora conforme NT 2014.002")
            break
        else:
            docs_restantes = max_nsu - ult_nsu
            print(f"   🔄 Ainda há ~{docs_restantes} documentos - continuando IMEDIATAMENTE")
    
    print(f"\n📊 Total de iterações: {iteration}")
    print(f"📊 Total de documentos processados: {ult_nsu - 59025}")
    
    # Cenário 2: Sistema sincronizado (ultNSU == maxNSU)
    print("\n\n📋 CENÁRIO 2: Sistema já sincronizado")
    print("-" * 80)
    ult_nsu = 61722
    max_nsu = 61722
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 Iteração {iteration}/{max_iterations}")
        print(f"   NSU atual: {ult_nsu:015d}")
        print(f"   maxNSU: {max_nsu:015d}")
        
        # Verifica ANTES de processar
        if ult_nsu == max_nsu:
            print(f"\n✅ SINCRONIZADO! ultNSU ({ult_nsu:015d}) == maxNSU ({max_nsu:015d})")
            print(f"   ⏰ Aguardar 1 hora conforme NT 2014.002")
            print(f"   🚫 NÃO FAZ REQUISIÇÃO à SEFAZ (economiza quota)")
            break
    
    print(f"\n📊 Total de iterações: {iteration}")
    print(f"📊 Total de documentos processados: 0")
    
    # Cenário 3: Erro 656
    print("\n\n📋 CENÁRIO 3: Erro 656 (Consumo Indevido)")
    print("-" * 80)
    print(f"   🚫 cStat=656 detectado")
    print(f"   🔒 Bloquear por 65 minutos")
    print(f"   ⏭️ Sair do loop e ir para CT-e")
    print(f"   ⏰ Próxima consulta possível em 65 minutos")
    
    # Cenário 4: cStat 137
    print("\n\n📋 CENÁRIO 4: cStat=137 (Nenhum documento)")
    print("-" * 80)
    print(f"   📭 Nenhum documento localizado")
    print(f"   🔒 Bloquear por 1 hora")
    print(f"   ⏭️ Sair do loop e ir para CT-e")
    print(f"   ⏰ Próxima consulta possível em 1 hora")
    
    print("\n" + "=" * 80)
    print("RESUMO DAS REGRAS")
    print("=" * 80)
    print("\n✅ ultNSU < maxNSU:")
    print("   → HÁ DOCUMENTOS")
    print("   → CONTINUAR LOOP IMEDIATAMENTE (sem esperar)")
    print("   → Processar até 50 docs por iteração")
    print("\n🔄 ultNSU == maxNSU:")
    print("   → SINCRONIZADO")
    print("   → AGUARDAR 1 HORA (NT 2014.002)")
    print("   → Sair do loop e ir para CT-e")
    print("\n🚫 cStat=656:")
    print("   → CONSUMO INDEVIDO")
    print("   → AGUARDAR 65 MINUTOS")
    print("   → Sair do loop e ir para CT-e")
    print("\n📭 cStat=137:")
    print("   → NENHUM DOCUMENTO")
    print("   → AGUARDAR 1 HORA")
    print("   → Sair do loop e ir para CT-e")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    simular_loop_nfe()
