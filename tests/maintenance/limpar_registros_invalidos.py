"""
Script para limpar registros inválidos do banco de dados
Remove registros sem número ou que vieram de respostas de erro da SEFAZ
"""
from modules.database import DatabaseManager
from pathlib import Path

db = DatabaseManager(Path('notas.db'))

with db._connect() as conn:
    # Remove registros sem número válido
    result = conn.execute("""
        DELETE FROM notas_detalhadas 
        WHERE numero IS NULL 
        OR numero = '' 
        OR numero = 'N/A' 
        OR numero = 'SEM_NUMERO'
        OR nome_emitente = 'SEM_NOME'
    """)
    
    print(f"✓ {result.rowcount} registros inválidos removidos do banco")
    
    # Verifica estatísticas atualizadas
    result = conn.execute("SELECT COUNT(*), xml_status FROM notas_detalhadas GROUP BY xml_status").fetchall()
    print("\nEstatísticas atualizadas:")
    for count, status in result:
        print(f"  {status}: {count}")
