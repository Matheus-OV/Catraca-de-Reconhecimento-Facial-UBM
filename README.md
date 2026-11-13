# Reconhecimento Facial Simplificado

Versão enxuta, autocontida e de inicialização imediata baseada no
projeto original `Reconhecimento_Facial-main`. Esta versão elimina a
necessidade de instalar servidores externos de banco de dados
(PostgreSQL), compiladores C++ (`dlib`) ou modelos pesados de áudio/LLM,
concentrando-se nas funcionalidades essenciais de **Detecção Facial**,
**Cadastro de Pessoas** e **Reconhecimento Facial (por Imagem e Webcam
ao vivo)** através de uma **Interface Web moderna em Flask** e **banco
de dados local SQLite**.

------------------------------------------------------------------------

## 1. Requisitos Mínimos

-   **Sistema Operacional:** Windows 10/11, Linux ou macOS
- **Python:** [Baixar Python 3.10 ou superior](https://www.python.org/downloads/)
-   **Pacotes Python:**
    -   `flask`
    -   `opencv-python`
    -   `numpy`

------------------------------------------------------------------------

## 2. Inicialização no Windows (PowerShell)

No Windows, acesse a pasta do projeto pelo PowerShell e execute os
seguintes comandos:

``` powershell
# 1. Criar e ativar o ambiente virtual...
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Iniciar a aplicação Web
python app.py
```

Em seguida, abra o navegador em **<http://localhost:8000>**.

**Observação:** Caso o PowerShell bloqueie a execução do ambiente
virtual, execute:

``` powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Depois, execute novamente o comando de ativação do ambiente virtual.

------------------------------------------------------------------------

## 3. Inicialização Rápida (1 Comando) --- Linux/macOS

No terminal, acesse a pasta do projeto e execute o script de
inicialização automática:

``` bash
chmod +x iniciar.sh
./iniciar.sh
```

O script `iniciar.sh` realiza automaticamente todas as etapas:

1.  Cria o ambiente virtual isolado (`.venv`), caso ainda não exista.
2.  Instala as dependências leves (`flask`, `opencv-python`, `numpy`).
3.  Inicializa automaticamente o banco de dados local SQLite
    (`reconhecimento.db`) e a pasta `photos/`.
4.  Inicia o servidor web em **<http://localhost:8000>**.

------------------------------------------------------------------------

## 4. Inicialização Manual (Passo a Passo Alternativo) --- Linux/macOS

Caso prefira executar cada comando manualmente:

``` bash
# 1. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Iniciar a aplicação Web
python3 app.py
```

Em seguida, abra o navegador em `http://localhost:8000..`.

------------------------------------------------------------------------

## 5. Funcionalidades Disponíveis na Interface Web

1.  **Detectar & Reconhecer Foto (`/`):**
    -   Envie qualquer imagem (`.jpg`, `.png`, `.webp`) para localizar
        todos os rostos presentes, identificar pessoas já cadastradas
        com percentual de similaridade e visualizar a imagem anotada.
    -   Inclui opção de **Desfocar rostos detectados** (modo
        privacidade).
2.  **Webcam ao Vivo (`/webcam`):**
    -   Monitoramento em tempo real diretamente no navegador, desenhando
        caixas delimitadoras (verdes para pessoas reconhecidas e
        laranjas para desconhecidos) sobre o vídeo da câmera.
3.  **Cadastrar Pessoa (`/register`):**
    -   Permite cadastrar uma nova pessoa enviando uma foto ou
        capturando um quadro diretamente pela webcam do navegador.
    -   Recorta automaticamente o rosto principal, gera o descritor
        facial de 128 dimensões e salva no SQLite local.
4.  **Pessoas & Histórico (`/people`):**
    -   Exibe todas as pessoas cadastradas com miniatura da foto facial,
        permite excluir cadastros com um clique e lista o histórico
        recente de detecções.

------------------------------------------------------------------------

## 6. Estrutura de Arquivos

``` text
reconhecimento_facial_simplificado/
├── iniciar.sh                   # Script de inicialização automática em 1 comando (Linux/macOS)
├── requirements.txt             # Lista enxuta de dependências (Flask, OpenCV, NumPy)
├── app.py                       # Servidor Web Flask e rotas da API REST
├── vision.py                    # Motor de detecção, extração de embeddings e reconhecimento
├── db.py                        # Camada de persistência local em SQLite3
├── README.md                    # Instruções de instalação e uso
├── MANUAL_TECNICO_PARCIAL.md    # Manual técnico parcial (Seções 1 e 2)
├── examples/                    # Imagens de exemplo para testes imediatos
├── photos/                      # Rostos recortados no momento do cadastro
└── templates/                   # Páginas HTML da interface web
    ├── base.html
    ├── index.html
    ├── webcam.html
    ├── register.html
    └── people.html
```

------------------------------------------------------------------------

## 7. Variáveis de Ambiente Opcionais

Nenhuma configuração é obrigatória para rodar o projeto. Se desejar
personalizar parâmetros, você pode definir:

  -----------------------------------------------------------------------
  Variável                Valor Padrão            Descrição
  ----------------------- ----------------------- -----------------------
  `PORT`                  `8000`                  Porta HTTP onde o
                                                  servidor Flask será
                                                  iniciado

  `RF_THRESHOLD`          `0.45`                  Limiar máximo de
                                                  distância euclidiana
                                                  para reconhecimento
                                                  facial

  `RF_DB_PATH`            `./reconhecimento.db`   Caminho do arquivo de
                                                  banco de dados SQLite

  `PHOTOS_DIR`            `./photos`              Pasta para
                                                  armazenamento dos
                                                  recortes faciais
  -----------------------------------------------------------------------
