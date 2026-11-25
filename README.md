# Catraca de Reconhecimento Facial UBM

Sistema web para detectar rostos em imagens e na webcam, cadastrar pessoas e reconhecer pessoas previamente cadastradas.

## Sobre o projeto

O projeto surgiu da necessidade de melhorar a segurança e a praticidade no controle de acesso ao ambiente universitário. A proposta busca reduzir problemas do uso de carteirinhas, como esquecimentos, atrasos na entrega e dificuldades na liberação de acesso. O sistema permite cadastrar pessoas e detectar e reconhecer rostos por imagem ou webcam, como alternativa tecnológica de identificação. O público-alvo é a comunidade acadêmica: alunos, funcionários e demais pessoas que frequentam o campus.

**Parceiro extensionista:** UBM

## Tecnologias

As versões exatas estão no arquivo `requirements.txt`.

| Tecnologia | Versão | Para que serve no projeto |
| --- | --- | --- |
| Python | 3.10 | Linguagem principal da aplicação |
| Flask | 3.0.0 | Interface web e servidor da aplicação |
| OpenCV (`opencv-python`) | 4.13.0.92 | Detecção de rostos (Haar Cascade) e processamento de imagens |
| NumPy | 1.26.0 | Operações numéricas dos vetores faciais |
| SQLite | Integrado ao Python (`sqlite3`) | Armazenamento local dos cadastros e do histórico |

## Pré-requisitos

- **Python 3.10 ou superior** ([download oficial](https://www.python.org/downloads/)). Para conferir, abra o terminal e digite `python --version` (no Linux/macOS, `python3 --version`).
- **Git** ([download oficial](https://git-scm.com/downloads)). Para conferir: `git --version`.

No Windows, use o PowerShell. No Linux/macOS, use o terminal.

## Instalação

1. Clone o repositório e entre na pasta do projeto:

   ```bash
   git clone https://github.com/Matheus-OV/Catraca-de-Reconhecimento-Facial-UBM.git
   cd Catraca-de-Reconhecimento-Facial-UBM
   ```

2. Crie e ative um ambiente virtual.

   Windows (PowerShell):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   Linux/macOS:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

4. No Linux/macOS, se preferir o script de inicialização automática, dê permissão de execução:

   ```bash
   chmod +x iniciar.sh
   ```

## Configuração

Nenhuma variável de ambiente é obrigatória para iniciar o projeto. Para personalizar, use as variáveis abaixo:

| Variável | Obrigatória? | Valor padrão | Descrição |
| --- | --- | --- | --- |
| `PORT` | Não | `8000` | Porta HTTP usada pelo servidor Flask |
| `RF_THRESHOLD` | Não | `0.45` | Distância euclidiana máxima aceita no reconhecimento. Valores maiores aumentam o risco de confundir pessoas |
| `RF_DB_PATH` | Não | `./reconhecimento.db` (na Vercel: `/tmp/reconhecimento.db`) | Caminho do arquivo do banco SQLite |
| `PHOTOS_DIR` | Não | `./photos` | Pasta onde ficam os recortes de rosto dos cadastros |

Não é necessário criar um arquivo `.env` para a execução padrão. Se você criar um, não publique senhas, chaves ou tokens reais no repositório.

> **Atenção (dado biométrico):** o banco `reconhecimento.db` e a pasta `photos/` guardam rostos de pessoas e **não devem ser enviados ao Git**. Confirme que o arquivo `.gitignore` (com o ponto no início do nome) lista os dois.

## Como executar

**Windows (PowerShell).** Com o ambiente virtual ativado e as dependências instaladas:

```powershell
python app.py
```

Se o PowerShell bloquear a ativação do ambiente virtual, execute o comando abaixo e tente ativar de novo:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**Linux/macOS, inicialização automática:**

```bash
./iniciar.sh
```

O script cria o ambiente virtual `.venv` (se ainda não existir), instala as dependências do `requirements.txt` e inicia o servidor. O banco `reconhecimento.db` e a pasta `photos/` são criados automaticamente na primeira execução.

**Linux/macOS, inicialização manual:**

```bash
python3 app.py
```

### O que aparece no terminal quando dá certo

O servidor mostra a mensagem abaixo, seguida das linhas do próprio Flask (o texto exato pode variar conforme a versão):

```text
========================================================
 Reconhecimento Facial Simplificado iniciado com sucesso!
 Acesse no navegador: http://localhost:8000
========================================================

 * Serving Flask app 'app'
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8000
```

Se `./iniciar.sh` foi usado, antes disso aparecem as etapas `[1/3]`, `[2/3]` e `[3/3]` do script. Quando a mensagem de sucesso aparecer, abra o navegador em **http://localhost:8000** (ou na porta definida em `PORT`) e deixe o terminal aberto: fechá-lo encerra o servidor. Para parar, pressione `Ctrl+C`.

## Exemplo de uso

1. **Detectar e reconhecer uma foto (`/`):** envie uma imagem `.jpg`, `.png` ou `.webp`. O sistema localiza os rostos, compara com as pessoas cadastradas, mostra a similaridade e exibe a imagem processada. Há também a opção de desfocar os rostos (modo privacidade).
2. **Webcam ao vivo (`/webcam`):** detecção em tempo real no navegador. As marcações diferenciam pessoas reconhecidas de rostos ainda não identificados.
3. **Cadastrar uma pessoa (`/register`):** envie uma foto ou capture pela webcam. O sistema recorta o rosto principal e guarda os dados necessários ao reconhecimento.
4. **Pessoas e histórico (`/people`):** veja as pessoas cadastradas, exclua cadastros e consulte as detecções recentes.

<!-- TODO: adicionar capturas de tela em docs/img/ e referenciá-las aqui, por exemplo: ![Tela inicial](docs/img/tela-inicial.png) -->

## Publicação na Vercel

O repositório inclui um `vercel.json` que publica o `app.py` com o runtime `@vercel/python`. Antes de usar, saiba das limitações:

- **Os dados não são permanentes.** Na Vercel o disco é somente leitura, exceto `/tmp`. Por isso o banco fica em `/tmp/reconhecimento.db`, que é apagado quando a instância reinicia ou é recriada. **Os cadastros se perdem** e o reconhecimento volta a não identificar ninguém.
- **A pasta de fotos precisa ir para `/tmp`.** O código tenta criar a pasta `photos/` ao iniciar, o que falha em disco somente leitura. Nas variáveis de ambiente do projeto na Vercel, defina `PHOTOS_DIR=/tmp/photos`.
- **Uso recomendado:** apenas demonstração. Para o uso real na catraca, execute o sistema em um servidor com disco persistente (veja "Como executar") ou troque o SQLite por um banco externo.
- A webcam só funciona em páginas HTTPS ou `localhost`; a Vercel fornece HTTPS automaticamente.

## Testes

O projeto **não possui testes automatizados**. A validação é manual, pelos fluxos principais:

1. Inicie a aplicação e acesse `http://localhost:8000`.
2. Envie uma imagem na página inicial e verifique se os rostos são detectados.
3. Cadastre uma pessoa em `/register`.
4. Envie uma imagem dessa pessoa e verifique se ela é reconhecida.
5. Abra `/webcam` e confira a detecção pela câmera.
6. Abra `/people` e verifique se o cadastro e o histórico aparecem.

Se forem adicionados testes automatizados, documente aqui o comando e o resultado esperado.

## Estrutura do projeto

```text
Catraca-de-Reconhecimento-Facial-UBM/
├── iniciar.sh                    # Inicialização automática (Linux/macOS)
├── requirements.txt              # Dependências Python
├── vercel.json                   # Configuração de publicação na Vercel
├── app.py                        # Servidor Flask e rotas
├── vision.py                     # Detecção e reconhecimento facial
├── db.py                         # Persistência local com SQLite
├── examples/                     # Imagens de exemplo
├── photos/                       # Recortes de rosto gerados (não vai para o Git)
├── templates/                    # Páginas HTML
│   ├── base.html
│   ├── index.html
│   ├── webcam.html
│   ├── register.html
│   └── people.html
├── docs/
│   ├── manual-tecnico-parcial.md # Manual técnico parcial
│   └── BANCO_DE_DADOS.md         # Estrutura do banco de dados e DER
├── LICENSE
└── README.md
```

## Documentação complementar

- [Manual técnico parcial](docs/manual-tecnico-parcial.md)
- [Estrutura do banco de dados e DER](docs/BANCO_DE_DADOS.md)
- Repositório: https://github.com/Matheus-OV/Catraca-de-Reconhecimento-Facial-UBM

## Equipe e licença

| Integrante | Papel no projeto | GitHub |
| --- | --- | --- |
| Karolaine Teixeira F. Barbosa | Back-end | [K4rolTeixeira](https://github.com/K4rolTeixeira) |
| Matheus de Oliveira Viana | QA Tester | [Matheus-OV](https://github.com/Matheus-OV) |
| Rian Oliveira Moreira | Documentação Técnica | [Rian-ui-max](https://github.com/Rian-ui-max) |
| Ricardo Felipe Rabello de Souza | Front-end | [RicardoFRS](https://github.com/RicardoFRS) |
| Ricardo dos Santos Medeiros | Back-end | [RICARDO-medeiros01](https://github.com/RICARDO-medeiros01) |

**Licença:** MIT License (veja o arquivo [LICENSE](LICENSE)).

Projeto desenvolvido na disciplina **Práticas Extensionistas Integradoras III — Engenharia de Software, UBM, 2026**.
