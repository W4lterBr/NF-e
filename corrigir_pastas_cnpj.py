# -*- coding: utf-8 -*-
"""
Move XMLs de pastas com nome incorreto para pastas com CNPJ correto
"""
import shutil
from pathlib import Path
import sqlite3

print("="*80)
print("🔧 CORREÇÃO AUTOMÁTICA: Movendo XMLs para pastas corretas")
print("="*80)
print()

# Carrega mapeamento de certificados
db_path = 'notas.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT informante, nome_certificado
    FROM certificados
    WHERE nome_certificado IS NOT NULL
    ORDER BY informante
""")

certificados = cursor.fetchall()
conn.close()

# Cria mapeamento reverso: nome_certificado -> CNPJ
nome_para_cnpj = {}
for cnpj, nome_cert in certificados:
    if nome_cert and cnpj:
        nome_para_cnpj[nome_cert] = cnpj

print(f"📋 Mapeamento certificados:")
for nome, cnpj in nome_para_cnpj.items():
    print(f"   {nome} → {cnpj}")
print()

# Pastas problemáticas detectadas
pastas_problema = [
    "6-NEXUS TECNOLOGIA",
    "61-MATPARCG",
    "75-PARTNESS FUTURA DIST",
    "79-ALFA COMPUTADORES",
    "80-LUZ COMERCIO ALIMENT",
    "99-JL COMERCIO"
]

xmls_folder = Path('xmls')

print("="*80)
print("🔄 Iniciando correção...")
print("="*80)
print()

total_movidos = 0
total_erros = 0

for pasta_nome in pastas_problema:
    pasta_origem = xmls_folder / pasta_nome
    
    if not pasta_origem.exists():
        print(f"⚠️  Pasta não encontrada: {pasta_nome}")
        continue
    
    # Busca CNPJ correto
    cnpj_correto = nome_para_cnpj.get(pasta_nome)
    
    if not cnpj_correto:
        print(f"❌ CNPJ não encontrado para: {pasta_nome}")
        continue
    
    pasta_destino = xmls_folder / cnpj_correto
    
    print(f"📁 {pasta_nome}")
    print(f"   Origem: {pasta_origem}")
    print(f"   Destino: {pasta_destino}")
    
    # Lista arquivos XML
    arquivos = list(pasta_origem.rglob('*.xml'))
    print(f"   XMLs encontrados: {len(arquivos)}")
    
    if not arquivos:
        print("   ⚠️  Nenhum XML encontrado, pulando...")
        continue
    
    # Move arquivos mantendo estrutura
    movidos_pasta = 0
    erros_pasta = 0
    
    for arquivo in arquivos:
        try:
            # Mantém estrutura relativa
            relativo = arquivo.relative_to(pasta_origem)
            destino_arquivo = pasta_destino / relativo
            
            # Cria diretórios de destino
            destino_arquivo.parent.mkdir(parents=True, exist_ok=True)
            
            # Move arquivo
            shutil.move(str(arquivo), str(destino_arquivo))
            movidos_pasta += 1
            
        except Exception as e:
            print(f"   ❌ Erro ao mover {arquivo.name}: {e}")
            erros_pasta += 1
    
    print(f"   ✅ Movidos: {movidos_pasta}")
    if erros_pasta > 0:
        print(f"   ❌ Erros: {erros_pasta}")
    
    # Remove pasta antiga se vazia
    try:
        if not list(pasta_origem.rglob('*.xml')):  # Sem mais XMLs
            # Remove diretórios vazios
            for dirpath in sorted(pasta_origem.rglob('*'), key=lambda p: -len(str(p))):
                if dirpath.is_dir() and not list(dirpath.iterdir()):
                    dirpath.rmdir()
            
            # Remove pasta raiz se estiver vazia
            if not list(pasta_origem.iterdir()):
                pasta_origem.rmdir()
                print(f"   🗑️  Pasta antiga removida: {pasta_nome}")
    except Exception as e:
        print(f"   ⚠️  Erro ao remover pasta: {e}")
    
    print()
    
    total_movidos += movidos_pasta
    total_erros += erros_pasta

print("="*80)
print("✅ CORREÇÃO CONCLUÍDA")
print("="*80)
print()
print(f"📊 Resultados:")
print(f"   ✅ XMLs movidos: {total_movidos}")
print(f"   ❌ Erros: {total_erros}")
print()

if total_movidos > 0:
    print("💡 Próximos passos:")
    print("   1. Verifique as pastas corrigidas em xmls/")
    print("   2. Agora você pode usar 'Aplicar Perfil' sem erros")
    print("   3. Execute: .\.venv\Scripts\python.exe diagnosticar_cnpjs_sem_nome.py")
    print("      para confirmar que tudo está correto")
    print()

print("="*80)
