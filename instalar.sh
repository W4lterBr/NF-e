#!/bin/bash

# ===================================================================
# BOT - Busca NFE - Instalador Automático Linux
# ===================================================================

echo ""
echo "==================================================================="
echo "  BOT - BUSCA NFE - INSTALADOR AUTOMÁTICO"
echo "==================================================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERRO]${NC} Python 3 não encontrado!"
    echo ""
    echo "Instale Python 3.10+:"
    echo "  sudo apt update"
    echo "  sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Python encontrado"
python3 --version

# Verificar versão do Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo -e "${RED}[ERRO]${NC} Python 3.10+ necessário"
    echo "Versão atual: $PYTHON_VERSION"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Versão do Python compatível"
echo ""

# Instalar dependências do sistema
echo "[0/4] Verificando dependências do sistema..."
DEPS_NEEDED=false

for pkg in python3-dev libxml2-dev libxslt1-dev; do
    if ! dpkg -l | grep -q "^ii  $pkg"; then
        DEPS_NEEDED=true
        break
    fi
done

if [ "$DEPS_NEEDED" = true ]; then
    echo -e "${YELLOW}[AVISO]${NC} Instalando dependências do sistema..."
    echo "  Pode ser necessário senha de sudo"
    sudo apt update
    sudo apt install -y python3-dev libxml2-dev libxslt1-dev python3-venv
fi

# Criar ambiente virtual
if [ ! -d ".venv" ]; then
    echo ""
    echo "[1/4] Criando ambiente virtual..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO]${NC} Falha ao criar ambiente virtual"
        exit 1
    fi
    echo -e "${GREEN}[OK]${NC} Ambiente virtual criado"
else
    echo "[1/4] Ambiente virtual já existe"
fi

# Ativar ambiente virtual
echo ""
echo "[2/4] Ativando ambiente virtual..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO]${NC} Falha ao ativar ambiente virtual"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Ambiente virtual ativado"

# Atualizar pip
echo ""
echo "[3/4] Atualizando pip..."
python -m pip install --upgrade pip --quiet
echo -e "${GREEN}[OK]${NC} pip atualizado"

# Instalar dependências
echo ""
echo "[4/4] Instalando dependências..."
echo "(Isso pode levar 5-10 minutos...)"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO]${NC} Falha ao instalar dependências"
    echo ""
    echo "Tente instalar manualmente:"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo ""
echo "==================================================================="
echo "  INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "==================================================================="
echo ""
echo "Próximos passos:"
echo "  1. Execute: python verificar_instalacao.py"
echo "  2. Configure certificados digitais"
echo "  3. Inicie o sistema: python interface_pyqt5.py"
echo ""
echo "==================================================================="
echo ""
