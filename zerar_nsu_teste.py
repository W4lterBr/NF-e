"""
🔒 SCRIPT DE TESTE - ZERAR NSU E BUSCAR TUDO
==============================================

Este script permite zerar os NSUs de forma SEGURA para testar o sistema
de controle rigoroso em condições reais de busca completa.

⚠️ ATENÇÃO: Este script é apenas para TESTES!
Ao zerar os NSUs, o sistema irá:
1. Baixar TODOS os documentos desde o início (NSU 0)
2. Gravar o NSU de cada documento no banco
3. Permitir verificar se o controle rigoroso está funcionando

🔒 SEGURANÇA:
- Requer código de confirmação
- Cria backup antes de zerar
- Permite zerar apenas 1 informante (recomendado para teste)
- Logs detalhados de auditoria

Uso:
    python zerar_nsu_teste.py
"""

import sys
from pathlib import Path

# Adiciona diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from nfe_search import DatabaseManager

def print_header(title):
    """Imprime cabeçalho formatado"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def listar_informantes(db):
    """Lista todos os informantes e seus NSUs atuais"""
    print_header("INFORMANTES DISPONÍVEIS")
    
    import sqlite3
    conn = sqlite3.connect("notas.db")
    cursor = conn.cursor()
    
    informantes = cursor.execute("""
        SELECT n.informante, n.ult_nsu, COUNT(nd.chave) as total_docs
        FROM nsu n
        LEFT JOIN notas_detalhadas nd ON nd.informante = n.informante
        GROUP BY n.informante
        ORDER BY n.informante
    """).fetchall()
    
    if not informantes:
        print("\n⚠️ Nenhum informante encontrado!")
        conn.close()
        return []
    
    print(f"\nTotal de {len(informantes)} informantes:\n")
    
    for idx, (informante, nsu, total_docs) in enumerate(informantes, 1):
        print(f"{idx}. {informante}")
        print(f"   NSU atual: {nsu}")
        print(f"   Documentos: {total_docs}")
        print()
    
    conn.close()
    return informantes

def zerar_nsu_teste(db, informante=None):
    """Zera NSU para teste"""
    print_header("ZERANDO NSU PARA TESTE")
    
    if informante:
        print(f"\n⚠️ ATENÇÃO: Você está prestes a zerar o NSU do informante:")
        print(f"   {informante}")
    else:
        print(f"\n⚠️⚠️⚠️ ATENÇÃO: Você está prestes a zerar o NSU de TODOS os informantes!")
    
    print("\nISSO FARÁ COM QUE:")
    print("  1. O próximo ciclo de busca comece do NSU 0")
    print("  2. TODOS os documentos sejam baixados novamente")
    print("  3. Os NSUs sejam gravados no banco de dados")
    print("  4. Permita testar o controle rigoroso em condições reais")
    
    print("\n" + "="*80)
    print("Para confirmar, digite exatamente: CONFIRMO_RESET_NSU")
    print("Para cancelar, pressione Enter ou digite qualquer outra coisa")
    print("="*80)
    
    confirmacao = input("\nDigite aqui: ").strip()
    
    if confirmacao != "CONFIRMO_RESET_NSU":
        print("\n❌ Operação CANCELADA pelo usuário.")
        return False
    
    print("\n🔄 Executando reset do NSU...")
    
    resultado = db.reset_nsu_for_testing(informante, "CONFIRMO_RESET_NSU")
    
    if resultado['success']:
        print(f"\n✅ NSU zerado com sucesso!")
        print(f"   Informantes resetados: {len(resultado['informantes_zerados'])}")
        print(f"   Backup: {len(resultado['backup'])} registros salvos")
        
        print("\n📋 Backup dos NSUs anteriores:")
        for inf, nsu in resultado['backup'][:10]:  # Mostra primeiros 10
            print(f"   {inf}: {nsu}")
        if len(resultado['backup']) > 10:
            print(f"   ... e mais {len(resultado['backup']) - 10} informantes")
        
        print("\n" + "="*80)
        print("PRÓXIMOS PASSOS:")
        print("="*80)
        print("1. Execute o programa principal (Busca NF-e.py)")
        print("2. Clique no botão 'Buscar' para iniciar a busca")
        print("3. Acompanhe os logs - verá mensagens como:")
        print("   '✅ NSU XXX gravado para nota...'")
        print("4. Após a busca, execute: python test_controle_nsu.py")
        print("5. Verifique que os NSUs foram gravados corretamente")
        print("="*80)
        
        return True
    else:
        print(f"\n❌ Erro ao zerar NSU: {resultado.get('error', 'Desconhecido')}")
        return False

def main():
    """Menu principal"""
    print("\n" + "="*80)
    print("🔒 TESTE - ZERAR NSU E BUSCAR TUDO")
    print("="*80)
    print("\nEste script permite testar o controle rigoroso de NSU")
    print("zerando os NSUs e forçando uma busca completa.\n")
    
    # Inicializa o banco
    db_path = Path("notas.db")
    db = DatabaseManager(db_path)
    
    # Lista informantes
    informantes = listar_informantes(db)
    
    if not informantes:
        print("\n❌ Nenhum informante encontrado. Execute uma busca primeiro.")
        return 1
    
    print("\n" + "="*80)
    print("OPÇÕES:")
    print("="*80)
    print("1. Zerar NSU de UM informante (RECOMENDADO para teste)")
    print("2. Zerar NSU de TODOS os informantes (⚠️ CUIDADO!)")
    print("0. Cancelar")
    print("="*80)
    
    try:
        opcao = input("\nEscolha uma opção: ").strip()
        
        if opcao == "0":
            print("\n❌ Operação cancelada pelo usuário.")
            return 0
        
        elif opcao == "1":
            print("\n" + "="*80)
            print("Digite o número do informante que deseja zerar:")
            print("="*80)
            
            try:
                idx = int(input("\nNúmero: ").strip())
                if 1 <= idx <= len(informantes):
                    informante = informantes[idx - 1][0]
                    zerar_nsu_teste(db, informante)
                else:
                    print(f"\n❌ Número inválido. Escolha entre 1 e {len(informantes)}")
                    return 1
            except ValueError:
                print("\n❌ Digite um número válido!")
                return 1
        
        elif opcao == "2":
            print("\n⚠️⚠️⚠️ VOCÊ ESCOLHEU ZERAR TODOS OS INFORMANTES!")
            print("Isso fará o sistema baixar TODOS os documentos novamente.")
            print("Pode levar MUITO TEMPO dependendo da quantidade de documentos.")
            
            zerar_nsu_teste(db, None)
        
        else:
            print("\n❌ Opção inválida!")
            return 1
    
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário (Ctrl+C)")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
