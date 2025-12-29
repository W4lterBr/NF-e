"""
Script de Verificação de Instalação
BOT - Busca NFE

Verifica se todos os arquivos e dependências necessários estão presentes.
Execute este script após copiar o sistema para um novo PC.
"""

import sys
import os
from pathlib import Path

print("=" * 70)
print("  BOT - BUSCA NFE - VERIFICADOR DE INSTALAÇÃO")
print("=" * 70)
print()

# Cores para terminal (Windows/Linux)
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    OK = Fore.GREEN + "✓" + Style.RESET_ALL
    ERRO = Fore.RED + "✗" + Style.RESET_ALL
    AVISO = Fore.YELLOW + "⚠" + Style.RESET_ALL
except ImportError:
    OK = "[OK]"
    ERRO = "[ERRO]"
    AVISO = "[AVISO]"

erros = []
avisos = []

# 1. Verificar Python
print("[1/8] Verificando Python...")
versao_python = sys.version_info
if versao_python.major >= 3 and versao_python.minor >= 10:
    print(f"  {OK} Python {versao_python.major}.{versao_python.minor}.{versao_python.micro}")
else:
    print(f"  {ERRO} Python {versao_python.major}.{versao_python.minor} (requer 3.10+)")
    erros.append("Versão do Python incompatível")

# 2. Verificar arquivos principais
print("\n[2/8] Verificando arquivos principais...")
arquivos_principais = [
    "interface_pyqt5.py",
    "nfe_search.py",
    "nfse_search.py",
    "nuvem_fiscal_api.py",
    "requirements.txt"
]

for arquivo in arquivos_principais:
    if Path(arquivo).exists():
        print(f"  {OK} {arquivo}")
    else:
        print(f"  {ERRO} {arquivo} NÃO ENCONTRADO")
        erros.append(f"Arquivo {arquivo} não encontrado")

# 3. Verificar pasta modules
print("\n[3/8] Verificando pasta modules/...")
modules_obrigatorios = [
    "__init__.py",
    "database.py",
    "sandbox_worker.py",
    "sandbox_task_runner.py",
    "pdf_generator.py",
    "pdf_simple.py"
]

if not Path("modules").exists():
    print(f"  {ERRO} Pasta modules/ não encontrada!")
    erros.append("Pasta modules/ não existe")
else:
    for mod in modules_obrigatorios:
        mod_path = Path("modules") / mod
        if mod_path.exists():
            print(f"  {OK} modules/{mod}")
        else:
            print(f"  {ERRO} modules/{mod} NÃO ENCONTRADO")
            erros.append(f"Módulo {mod} não encontrado")

# 4. Verificar schemas XSD
print("\n[4/8] Verificando schemas XSD...")
xsd_obrigatorios = [
    "retDistDFeInt_v1.01.xsd",
    "resNFe_v1.01.xsd",
    "procNFe_v4.00.xsd",
    "nfe_v4.00.xsd"
]

if not Path("Arquivo_xsd").exists():
    print(f"  {ERRO} Pasta Arquivo_xsd/ não encontrada!")
    erros.append("Pasta Arquivo_xsd/ não existe")
else:
    for xsd in xsd_obrigatorios:
        xsd_path = Path("Arquivo_xsd") / xsd
        if xsd_path.exists():
            print(f"  {OK} {xsd}")
        else:
            print(f"  {ERRO} {xsd} NÃO ENCONTRADO")
            erros.append(f"Schema {xsd} não encontrado")
    
    # Conta total de XSDs
    total_xsd = len(list(Path("Arquivo_xsd").glob("*.xsd")))
    if total_xsd >= 40:
        print(f"  {OK} Total: {total_xsd} schemas XSD")
    else:
        print(f"  {AVISO} Total: {total_xsd} schemas (esperado ~56)")
        avisos.append(f"Apenas {total_xsd} schemas encontrados (esperado ~56)")

# 5. Verificar ícones
print("\n[5/8] Verificando ícones...")
if not Path("Icone").exists():
    print(f"  {ERRO} Pasta Icone/ não encontrada!")
    erros.append("Pasta Icone/ não existe")
else:
    if Path("Icone/xml.png").exists():
        print(f"  {OK} Icone/xml.png")
    else:
        print(f"  {ERRO} Icone/xml.png NÃO ENCONTRADO")
        erros.append("Ícone xml.png não encontrado")

# 6. Verificar dependências Python
print("\n[6/8] Verificando dependências Python...")
dependencias = {
    "PyQt5": "Interface gráfica",
    "lxml": "Processamento XML",
    "requests": "Requisições HTTP",
    "requests_pkcs12": "Certificados digitais",
    "cryptography": "Criptografia",
    "zeep": "SOAP/WSDL",
    "reportlab": "Geração PDF"
}

for lib, desc in dependencias.items():
    try:
        __import__(lib)
        print(f"  {OK} {lib} ({desc})")
    except ImportError:
        print(f"  {ERRO} {lib} NÃO INSTALADO ({desc})")
        erros.append(f"Biblioteca {lib} não instalada")

# 7. Verificar pastas de dados
print("\n[7/8] Verificando estrutura de pastas...")
pastas_opcionais = {
    "xmls": "XMLs baixados (criado automaticamente)",
    "logs": "Logs do sistema (criado automaticamente)",
    ".venv": "Ambiente virtual Python"
}

for pasta, desc in pastas_opcionais.items():
    if Path(pasta).exists():
        print(f"  {OK} {pasta}/ ({desc})")
    else:
        print(f"  {AVISO} {pasta}/ não encontrada ({desc})")
        if pasta == ".venv":
            avisos.append("Ambiente virtual não criado - execute: python -m venv .venv")

# 8. Verificar banco de dados
print("\n[8/8] Verificando banco de dados...")
if Path("notas.db").exists():
    print(f"  {OK} notas.db (banco existente)")
else:
    print(f"  {AVISO} notas.db não encontrado (será criado na primeira execução)")

# Verificar API credentials
if Path("api_credentials.csv").exists():
    print(f"  {OK} api_credentials.csv (Nuvem Fiscal)")
else:
    print(f"  {AVISO} api_credentials.csv não encontrado (opcional - apenas para NFS-e)")

# Resumo final
print("\n" + "=" * 70)
print("  RESUMO DA VERIFICAÇÃO")
print("=" * 70)

if not erros and not avisos:
    print(f"\n{OK} INSTALAÇÃO COMPLETA!")
    print("\nTodos os arquivos e dependências estão presentes.")
    print("\nPróximos passos:")
    print("  1. Configure um certificado digital (Menu Certificados)")
    print("  2. Execute a primeira busca (Botão Buscar)")
    print("\nPara iniciar o sistema:")
    print("  python interface_pyqt5.py")
elif not erros:
    print(f"\n{OK} INSTALAÇÃO OK COM AVISOS")
    print(f"\n{AVISO} {len(avisos)} aviso(s) encontrado(s):")
    for aviso in avisos:
        print(f"  • {aviso}")
    print("\nO sistema pode funcionar, mas recomenda-se resolver os avisos.")
else:
    print(f"\n{ERRO} INSTALAÇÃO INCOMPLETA")
    print(f"\n{len(erros)} erro(s) crítico(s) encontrado(s):")
    for erro in erros:
        print(f"  • {erro}")
    
    if avisos:
        print(f"\n{len(avisos)} aviso(s):")
        for aviso in avisos:
            print(f"  • {aviso}")
    
    print("\n🔧 SOLUÇÃO:")
    print("  1. Copie todos os arquivos necessários")
    print("  2. Instale dependências: pip install -r requirements.txt")
    print("  3. Execute este script novamente")

print("\n" + "=" * 70)
print()

# Exit code
sys.exit(0 if not erros else 1)
