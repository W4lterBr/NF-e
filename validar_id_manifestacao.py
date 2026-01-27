"""
Validador simples de ID de evento de manifestação.
"""

def validar_id_evento(id_evento, tipo_evento, chave, nseq_evento):
    """
    Valida se o ID do evento está no formato correto.
    
    XSD exige: ID[0-9]{52}
    Estrutura: ID + tpEvento(6) + chave(44) + nSeqEvento(2) = 54 chars total
    """
    print(f"📋 Validando ID do evento...")
    print(f"   ID completo: {id_evento}")
    print(f"   Tamanho: {len(id_evento)} caracteres")
    print()
    
    # Verifica comprimento total
    if len(id_evento) != 54:
        print(f"❌ ERRO: ID deve ter 54 caracteres (ID + 52 dígitos)")
        print(f"   Encontrado: {len(id_evento)} caracteres")
        return False
    
    # Verifica prefixo "ID"
    if not id_evento.startswith("ID"):
        print(f"❌ ERRO: ID deve começar com 'ID'")
        return False
    
    # Extrai componentes
    id_sem_prefixo = id_evento[2:]  # Remove "ID"
    
    if len(id_sem_prefixo) != 52:
        print(f"❌ ERRO: Após 'ID', deve ter 52 dígitos")
        print(f"   Encontrado: {len(id_sem_prefixo)} dígitos")
        return False
    
    # Verifica se tudo após "ID" são dígitos
    if not id_sem_prefixo.isdigit():
        print(f"❌ ERRO: Após 'ID', deve conter apenas dígitos")
        return False
    
    # Decompõe
    tp_evento_extraido = id_sem_prefixo[0:6]
    chave_extraida = id_sem_prefixo[6:50]  # 44 dígitos
    nseq_extraido = id_sem_prefixo[50:52]  # 2 dígitos
    
    print(f"✅ Estrutura do ID válida!")
    print(f"   Prefixo: ID")
    print(f"   tpEvento: {tp_evento_extraido} (esperado: {tipo_evento})")
    print(f"   Chave: {chave_extraida} (esperado: {chave})")
    print(f"   nSeqEvento: {nseq_extraido} (esperado: {str(nseq_evento).zfill(2)})")
    print()
    
    # Valida componentes
    erros = []
    
    if tp_evento_extraido != tipo_evento:
        erros.append(f"tpEvento não corresponde: {tp_evento_extraido} != {tipo_evento}")
    
    if chave_extraida != chave:
        erros.append(f"Chave não corresponde")
    
    if nseq_extraido != str(nseq_evento).zfill(2):
        erros.append(f"nSeqEvento não corresponde: {nseq_extraido} != {str(nseq_evento).zfill(2)}")
    
    if erros:
        print("❌ Erros de validação:")
        for erro in erros:
            print(f"   - {erro}")
        return False
    
    print("✅ ID do evento VÁLIDO!")
    return True

if __name__ == "__main__":
    # Teste com ID do log anterior (ERRADO - com 3 dígitos no nSeqEvento)
    print("="*80)
    print("TESTE 1: ID ERRADO (com .zfill(3))")
    print("="*80)
    id_errado = "ID21021035260172381189001001550010083154761637954119001"
    validar_id_evento(
        id_evento=id_errado,
        tipo_evento="210210",
        chave="35260172381189001001550010083154761637954119",
        nseq_evento=1
    )
    
    print("\n" + "="*80)
    print("TESTE 2: ID CORRETO (com .zfill(2))")
    print("="*80)
    # ID correto (52 dígitos após "ID")
    id_correto = "ID21021035260172381189001001550010083154761637954119" + "01"
    validar_id_evento(
        id_evento=id_correto,
        tipo_evento="210210",
        chave="35260172381189001001550010083154761637954119",
        nseq_evento=1
    )
