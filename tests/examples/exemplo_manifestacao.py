"""
Exemplo de uso do sistema de controle de manifestações automáticas.

Este script demonstra como evitar duplicatas ao enviar Ciência da Operação (210210).
"""

from modules.database import DatabaseManager
from datetime import datetime
from pathlib import Path


# Caminho do banco de dados
DB_PATH = Path(__file__).parent / "notas.db"


def exemplo_verificar_manifestacao():
    """Exemplo 1: Verificar se manifestação já foi enviada."""
    print("=" * 60)
    print("EXEMPLO 1: Verificando se manifestação já foi enviada")
    print("=" * 60)
    
    db = DatabaseManager(DB_PATH)
    
    # Dados de exemplo
    chave_exemplo = "35241234567890123456789012345678901234567890"
    tipo_evento = "210210"  # Ciência da Operação
    cnpj_informante = "12345678000190"
    
    # Verifica se já foi manifestada
    ja_manifestada = db.check_manifestacao_exists(
        chave=chave_exemplo,
        tipo_evento=tipo_evento,
        informante=cnpj_informante
    )
    
    if ja_manifestada:
        print(f"⏭️  Manifestação JÁ ENVIADA anteriormente")
        print(f"    Chave: {chave_exemplo[:10]}...")
        print(f"    Tipo: {tipo_evento} (Ciência)")
        print(f"    Informante: {cnpj_informante}")
    else:
        print(f"✅ Manifestação PODE SER ENVIADA")
        print(f"    Chave: {chave_exemplo[:10]}...")
        print(f"    Tipo: {tipo_evento} (Ciência)")
        print(f"    Informante: {cnpj_informante}")
    
    print()


def exemplo_registrar_manifestacao():
    """Exemplo 2: Registrar uma nova manifestação."""
    print("=" * 60)
    print("EXEMPLO 2: Registrando nova manifestação")
    print("=" * 60)
    
    db = DatabaseManager(DB_PATH)
    
    # Dados de exemplo
    chave_exemplo = "35241234567890123456789012345678901234567890"
    tipo_evento = "210210"
    cnpj_informante = "12345678000190"
    protocolo_sefaz = "135240123456789"
    
    # Tenta registrar
    sucesso = db.register_manifestacao(
        chave=chave_exemplo,
        tipo_evento=tipo_evento,
        informante=cnpj_informante,
        status="ENVIADA",
        protocolo=protocolo_sefaz
    )
    
    if sucesso:
        print(f"✅ Manifestação REGISTRADA com sucesso!")
        print(f"    Chave: {chave_exemplo[:10]}...")
        print(f"    Protocolo: {protocolo_sefaz}")
        print(f"    Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"⚠️  Manifestação JÁ ESTAVA REGISTRADA")
        print(f"    Chave: {chave_exemplo[:10]}...")
        print(f"    (Constraint UNIQUE impediu duplicata)")
    
    print()


def exemplo_fluxo_completo():
    """Exemplo 3: Fluxo completo de manifestação com proteção anti-duplicata."""
    print("=" * 60)
    print("EXEMPLO 3: Fluxo completo com proteção anti-duplicata")
    print("=" * 60)
    
    db = DatabaseManager(DB_PATH)
    
    # Lista de NF-es recebidas (simulação)
    nfes_recebidas = [
        {
            'chave': '35241234567890123456789012345678901234567890',
            'numero': '000123',
            'emitente': 'FORNECEDOR A LTDA'
        },
        {
            'chave': '35241234567890123456789012345678901234567891',
            'numero': '000124',
            'emitente': 'FORNECEDOR B LTDA'
        },
        {
            'chave': '35241234567890123456789012345678901234567890',  # DUPLICATA!
            'numero': '000123',
            'emitente': 'FORNECEDOR A LTDA'
        }
    ]
    
    cnpj_destinatario = "12345678000190"
    tipo_evento = "210210"
    
    print(f"Processando {len(nfes_recebidas)} NF-es recebidas...\n")
    
    manifestadas = 0
    duplicadas = 0
    
    for i, nfe in enumerate(nfes_recebidas, 1):
        chave = nfe['chave']
        numero = nfe['numero']
        emitente = nfe['emitente']
        
        print(f"[{i}] NF-e {numero} - {emitente}")
        print(f"    Chave: {chave[:10]}...{chave[-4:]}")
        
        # 1. Verifica se já manifestou
        if db.check_manifestacao_exists(chave, tipo_evento, cnpj_destinatario):
            print(f"    ⏭️  PULANDO - Ciência já manifestada anteriormente")
            duplicadas += 1
        else:
            # 2. Simula envio para SEFAZ
            print(f"    📤 Enviando ciência para SEFAZ...")
            
            # Aqui seria o código real de envio:
            # resultado = nfe_service.enviar_evento(...)
            
            # Simulação de sucesso
            protocolo = f"135240{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            print(f"    ✅ SEFAZ retornou: cStat=135 (Evento registrado)")
            print(f"    📝 Protocolo: {protocolo}")
            
            # 3. Registra no banco
            db.register_manifestacao(
                chave=chave,
                tipo_evento=tipo_evento,
                informante=cnpj_destinatario,
                status="ENVIADA",
                protocolo=protocolo
            )
            
            print(f"    💾 Manifestação registrada no banco")
            manifestadas += 1
        
        print()
    
    print("=" * 60)
    print(f"RESULTADO:")
    print(f"  ✅ Manifestações enviadas: {manifestadas}")
    print(f"  ⏭️  Duplicatas evitadas: {duplicadas}")
    print(f"  📊 Total processado: {len(nfes_recebidas)}")
    print("=" * 60)
    print()


def exemplo_consultar_manifestacoes():
    """Exemplo 4: Consultar manifestações registradas."""
    print("=" * 60)
    print("EXEMPLO 4: Consultando manifestações registradas")
    print("=" * 60)
    
    import sqlite3
    
    try:
        conn = sqlite3.connect('notas.db')
        cursor = conn.execute('''
            SELECT chave, tipo_evento, data_manifestacao, status, protocolo
            FROM manifestacoes
            ORDER BY data_manifestacao DESC
            LIMIT 10
        ''')
        
        rows = cursor.fetchall()
        
        if not rows:
            print("ℹ️  Nenhuma manifestação registrada ainda")
        else:
            print(f"📋 Últimas {len(rows)} manifestações:\n")
            
            eventos = {
                '210210': 'Ciência',
                '210200': 'Confirmação',
                '210220': 'Desconhecimento',
                '210240': 'Não Realizada'
            }
            
            for i, row in enumerate(rows, 1):
                chave = row[0]
                tipo = eventos.get(row[1], row[1])
                data = row[2]
                status = row[3]
                protocolo = row[4] or 'N/A'
                
                print(f"[{i}] {chave[:10]}...{chave[-4:]}")
                print(f"    Tipo: {tipo} ({row[1]})")
                print(f"    Data: {data}")
                print(f"    Status: {status}")
                print(f"    Protocolo: {protocolo}")
                print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao consultar banco: {e}")
    
    print()


def main():
    """Executa todos os exemplos."""
    print("\n")
    print("🔄 SISTEMA DE CONTROLE DE MANIFESTAÇÕES AUTOMÁTICAS")
    print("   Evitando duplicatas de Ciência da Operação (210210)")
    print("\n")
    
    # Exemplo 1: Verificar
    exemplo_verificar_manifestacao()
    
    # Exemplo 2: Registrar
    exemplo_registrar_manifestacao()
    
    # Exemplo 3: Fluxo completo
    exemplo_fluxo_completo()
    
    # Exemplo 4: Consultar
    exemplo_consultar_manifestacoes()
    
    print("=" * 60)
    print("✅ Exemplos concluídos!")
    print()
    print("📖 Para mais informações, consulte:")
    print("   - MANIFESTACAO_AUTOMATICA.md")
    print("   - modules/database.py (métodos check_manifestacao_exists e register_manifestacao)")
    print("=" * 60)


if __name__ == "__main__":
    main()
