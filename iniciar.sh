#!/usr/bin/env bash
# Script de inicialização automática da versão simplificada de Reconhecimento Facial
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  Inicializando Reconhecimento Facial Simplificado..."
echo "========================================================"

# 1. Cria o ambiente virtual (.venv) caso ainda não exista
if [ ! -d ".venv" ]; then
    echo "[1/3] Criando ambiente virtual Python (.venv)..."
    python3 -m venv .venv
else
    echo "[1/3] Ambiente virtual (.venv) encontrado."
fi

# 2. Ativa o ambiente virtual e instala as dependências leves
echo "[2/3] Verificando e instalando dependências (Flask, OpenCV, NumPy)..."
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# 3. Inicia o servidor Flask (o banco SQLite é criado automaticamente)
echo "[3/3] Iniciando servidor web em http://localhost:8000 ..."
python3 app.py
