"""
🧪 TESTE DE INSTALAÇÃO LIMPA
Simula o que um usuário novo verá ao clonar o repositório
"""

import sys
from pathlib import Path

print("=" * 80)
print("🧪 TESTE DE INSTALAÇÃO LIMPA - BOT Busca NFE")
print("=" * 80)

# 1. Verifica arquivos principais
print("\n📋 1. VERIFICANDO ARQUIVOS PRINCIPAIS")
print("-" * 80)

arquivos_essenciais = [
    "Busca NF-e.py",
    "nfe_search.py",
    "requirements.txt",
    "README.md",
]

faltando = []
for arquivo in arquivos_essenciais:
    path = Path(arquivo)
    if path.exists():
        print(f"  ✅ {arquivo}")
    else:
        print(f"  ❌ {arquivo} - FALTANDO!")
        faltando.append(arquivo)

# 2. Verifica módulos essenciais
print("\n📦 2. VERIFICANDO MÓDULOS (modules/)")
print("-" * 80)

modulos_essenciais = [
    "modules/__init__.py",
    "modules/database.py",
    "modules/crypto_portable.py",
    "modules/sefaz_integration.py",
    "modules/cte_service.py",
    "modules/pdf_generator.py",
    "modules/manifestacao_service.py",
    "modules/xsd_validator.py",
]

for modulo in modulos_essenciais:
    path = Path(modulo)
    if path.exists():
        print(f"  ✅ {modulo}")
    else:
        print(f"  ❌ {modulo} - FALTANDO!")
        faltando.append(modulo)

# 3. Testa imports
print("\n🔧 3. TESTANDO IMPORTS PRINCIPAIS")
print("-" * 80)

erros_import = []

# Adiciona diretório ao path
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from modules.database import DatabaseManager
    print("  ✅ DatabaseManager")
except Exception as e:
    print(f"  ❌ DatabaseManager - ERRO: {e}")
    erros_import.append(("DatabaseManager", str(e)))

try:
    from modules.crypto_portable import PortableCryptoManager
    print("  ✅ PortableCryptoManager")
except Exception as e:
    print(f"  ❌ PortableCryptoManager - ERRO: {e}")
    erros_import.append(("PortableCryptoManager", str(e)))

try:
    # NFeService está em nfe_search.py, não em modules
    import importlib.util
    spec = importlib.util.spec_from_file_location("nfe_search", BASE_DIR / "nfe_search.py")
    if spec and spec.loader:
        nfe_search = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nfe_search)
        # Verifica se a classe existe
        if hasattr(nfe_search, 'NFeService'):
            print("  ✅ NFeService")
        else:
            print("  ❌ NFeService - classe não encontrada em nfe_search.py")
            erros_import.append(("NFeService", "Classe não encontrada"))
    else:
        print("  ❌ NFeService - não foi possível carregar nfe_search.py")
        erros_import.append(("NFeService", "Arquivo não carregado"))
except Exception as e:
    print(f"  ❌ NFeService - ERRO: {e}")
    erros_import.append(("NFeService", str(e)))

try:
    from modules.manifestacao_service import ManifestacaoService
    print("  ✅ ManifestacaoService")
except Exception as e:
    print(f"  ❌ ManifestacaoService - ERRO: {e}")
    erros_import.append(("ManifestacaoService", str(e)))

# 4. Verifica dependências do requirements.txt
print("\n📚 4. VERIFICANDO DEPENDÊNCIAS")
print("-" * 80)

dependencias = [
    ("PyQt5", "Interface gráfica"),
    ("lxml", "Processamento XML"),
    ("requests", "Requisições HTTP"),
    ("zeep", "Cliente SOAP"),
    ("cryptography", "Criptografia"),
    ("reportlab", "Geração de PDF"),
]

deps_faltando = []
for modulo, descricao in dependencias:
    try:
        __import__(modulo)
        print(f"  ✅ {modulo:<20} - {descricao}")
    except ImportError:
        print(f"  ⚠️  {modulo:<20} - {descricao} (instalar: pip install {modulo})")
        deps_faltando.append(modulo)

# 5. Verifica estrutura de diretórios
print("\n📁 5. VERIFICANDO ESTRUTURA DE DIRETÓRIOS")
print("-" * 80)

diretorios = [
    "modules",
    "Arquivo_xsd",
    "Icone",
    "config",
]

for diretorio in diretorios:
    path = Path(diretorio)
    if path.exists() and path.is_dir():
        arquivos = list(path.iterdir())
        print(f"  ✅ {diretorio}/ ({len(arquivos)} arquivos)")
    else:
        print(f"  ℹ️  {diretorio}/ (será criado na primeira execução)")

# 6. Conclusão
print("\n" + "=" * 80)
print("📊 RESULTADO DO TESTE")
print("=" * 80)

problemas = len(faltando) + len(erros_import)

if problemas == 0 and len(deps_faltando) == 0:
    print("""
✅ SISTEMA PRONTO PARA USO!

O repositório está completo e um usuário novo conseguirá:
1. Clonar o repositório
2. Criar ambiente virtual: python -m venv .venv
3. Instalar dependências: pip install -r requirements.txt
4. Executar o sistema: python "Busca NF-e.py"

📝 PRÓXIMOS PASSOS PARA O USUÁRIO:
• Adicionar certificado digital (.pfx)
• Configurar pasta de armazenamento
• Executar primeira busca na SEFAZ
""")
elif len(deps_faltando) > 0 and problemas == 0:
    print(f"""
⚠️  DEPENDÊNCIAS FALTANDO ({len(deps_faltando)})

Instale as dependências com:
    pip install -r requirements.txt

Dependências faltando: {', '.join(deps_faltando)}

✅ Estrutura de arquivos está correta!
""")
else:
    print(f"""
❌ PROBLEMAS ENCONTRADOS ({problemas})

Arquivos faltando: {len(faltando)}
{chr(10).join(f"  • {f}" for f in faltando) if faltando else "  Nenhum"}

Erros de import: {len(erros_import)}
{chr(10).join(f"  • {m}: {e}" for m, e in erros_import) if erros_import else "  Nenhum"}

Dependências faltando: {len(deps_faltando)}
{chr(10).join(f"  • {d}" for d in deps_faltando) if deps_faltando else "  Nenhum"}

⚠️  O sistema NÃO está pronto para distribuição!
""")

print("=" * 80)
