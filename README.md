**Projeto Catraca de Reconhecimento Facial**  
Sistema web do nosso projeto para detectar rostos em imagens e webcam, cadastrar pessoas e reconhecer pessoas previamente cadastradas.  
**Sobre o projeto**  
O projeto Reconhecimento Facial surgiu da necessidade de melhorar a segurança e a praticidade no controle de acesso ao ambiente universitário. A proposta busca reduzir problemas relacionados ao uso de carteirinhas, como esquecimentos, atrasos na entrega e dificuldades na liberação de acesso. O sistema permite cadastrar pessoas, detectar e reconhecer rostos por imagens ou webcam, contribuindo para uma alternativa tecnológica de identificação. Seu público-alvo é a comunidade acadêmica, incluindo alunos, funcionários e demais pessoas que frequentam o campus.  
   
**Parceiro extensionista:** \[UBM\]  
**Tecnologias**  
As versões exatas das bibliotecas devem ser conferidas no arquivo `requirements.txt` .  
  
|  |  |  |  
| - | - | - |  
| **Tecnologia** |  **Versão** |  **Para que serve no projeto** |  
| Python |  3.10 ou superior |  Linguagem principal da aplicação |  
| Flask |  3.0.0 |  Interface web e servidor da aplicação |  
| OpenCV (`opencv-python`) |  4.13.0.92 |  Processamento de imagens e acesso à webcam |  
| NumPy |  1.26.0 |  Operações numéricas utilizadas no processamento |  
| SQLite |  Integrado ao Python (sqlite3) |  Armazenamento local dos cadastros e dados |  
  
   
**Pré-requisitos**  
Antes de executar o projeto, instale:  
- **Python 3.10 ou superior** — [Download oficial.](https://www.python.org/downloads/ "https://www.python.org/downloads/")  
  - Para conferir a instalação abra o Terminal e digite:  
  -   
```  
python --version  
   
```  
  -   
 No Linux/macOS, também pode ser necessário:  
  -   
```  
python3 --version  
   
```  
- **Git** — [Download oficial.](https://git-scm.com/downloads "https://git-scm.com/downloads")  
  - Para conferir a instalação:  
  -   
```  
git --version  
   
```  
No Windows, utilize o PowerShell. No Linux/macOS, utilize o terminal.  
**Instalação**  
1. **Clone o repositório:**  
2.   
```  
git clone [https://github.com/Matheus-OV/Catraca-de-Reconhecimento-Facial-UBM]  
 cd [NOME_DA_PASTA]  
   
```  
3. **Crie e ative um ambiente virtual.**  
4. Windows (PowerShell):  
5.   
```  
python -m venv .venv  
 .\.venv\Scripts\Activate.ps1  
   
```  
6. Linux/macOS:  
7.   
```  
python3 -m venv .venv  
 source .venv/bin/activate  
   
```  
8. **Instale as dependências:**  
9.   
```  
pip install -r requirements.txt  
   
```  
10. **No Linux/macOS, se preferir utilizar o script de inicialização automática, dê permissão de execução:**  
11.   
```  
chmod +x iniciar.sh  
   
```  
12. A inicialização pelo script é explicada na seção [Como executar.](#anchor-1 "#anchor-1")  
**Configuração**  
Nenhuma variável de ambiente é obrigatória para iniciar o projeto. É possível personalizar alguns parâmetros por meio das variáveis abaixo:  
  
|  |  |  |  |  
| - | - | - | - |  
| **Variável** |  **Obrigatória?** |  **Exemplo / valor padrão** |  **Descrição** |  
| `PORT` |  Não |  `8000` |  Porta HTTP utilizada pelo servidor Flask |  
| `RF_THRESHOLD` |  Não |  `0.45` |  Limiar máximo de distância euclidiana utilizado no reconhecimento facial |  
| `RF_DB_PATH` |  Não |  `./reconhecimento.db` |  Caminho do arquivo do banco de dados SQLite |  
| `PHOTOS_DIR` |  Não |  `./photos` |  Diretório utilizado para armazenar os recortes faciais |  
  
   
Não é necessário criar um arquivo `.env` para a execução padrão. Caso o projeto utilize um arquivo `.env` em alguma configuração adicional, não publique senhas, chaves ou tokens reais no repositório.  
**Como executar**  
**Windows (PowerShell)**  
Com o ambiente virtual ativado e as dependências instaladas, execute:  
```  
python app.py  
   
```  
Se o PowerShell bloquear a ativação do ambiente virtual, execute o comando abaixo e tente ativá-lo novamente:  
```  
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass  
   
```  
**Linux/macOS — inicialização automática**  
Na pasta do projeto, execute:  
```  
./iniciar.sh  
   
```  
O script `iniciar.sh` realiza as seguintes etapas:  
1. Cria o ambiente virtual `.venv`, caso ainda não exista.  
2. Instala as dependências listadas no `requirements.txt`.  
3. Inicializa o banco de dados local SQLite (`reconhecimento.db`) e a pasta `photos/`.  
4. Inicia o servidor web.  
**Linux/macOS — inicialização manual**  
Como alternativa ao script, execute:  
```  
python3 app.py  
   
```  
Após iniciar o servidor, abra o navegador no endereço:  
**http://localhost:8000**  
Se a porta tiver sido alterada pela variável `PORT`, utilize a porta configurada.  
**Exemplo de uso**  
O sistema oferece os seguintes fluxos principais:  
1. **Detectar e reconhecer uma foto (`/`):** acesse a página inicial e envie uma imagem nos formatos `.jpg`, `.png` ou `.webp`. O sistema localiza os rostos, verifica se correspondem a pessoas cadastradas, apresenta a similaridade e exibe a imagem processada. Também há a opção de desfocar os rostos detectados.  
2. **Utilizar a webcam ao vivo (`/webcam`):** abra a página da webcam para visualizar a detecção em tempo real no navegador. As marcações indicam pessoas reconhecidas e rostos ainda não identificados.  
3. **Cadastrar uma pessoa (`/register`):** envie uma foto ou capture uma imagem pela webcam do navegador. O sistema recorta o rosto principal e armazena os dados necessários para o reconhecimento.  
4. **Consultar pessoas e histórico (`/people`):** visualize as pessoas cadastradas, exclua cadastros e consulte as detecções recentes.  
**Imagens de demonstração:** \[adicionar capturas de tela na pasta `docs/img/` e inserir aqui as referências, por exemplo: `![Tela inicial](docs/img/tela-inicial.png)`\].  
**Testes**  
O README de origem não informa a existência de uma suíte de testes automatizados nem apresenta um comando para executá-la. Portanto, a validação pode ser feita manualmente pelos fluxos principais:  
1. Inicie a aplicação e acesse `http://localhost:8000`.  
2. Envie uma imagem na página inicial e verifique se os rostos são detectados.  
3. Cadastre uma pessoa em `/register`.  
4. Envie uma imagem dessa pessoa e verifique o resultado do reconhecimento.  
5. Acesse `/webcam` e confira a detecção pela câmera.  
6. Acesse `/people` e verifique se o cadastro e o histórico são exibidos.  
Se forem adicionados testes automatizados ao projeto, documente aqui o comando utilizado e o resultado esperado.  
**Estrutura do projeto**  
```  
reconhecimento_facial_simplificado/  
 ├── iniciar.sh                    # Inicialização automática no Linux/macOS  
 ├── requirements.txt              # Dependências Python  
 ├── app.py                         # Servidor Flask e rotas da aplicação  
 ├── vision.py                      # Detecção e reconhecimento facial  
 ├── db.py                          # Persistência local com SQLite  
 ├── examples/                      # Imagens de exemplo  
 ├── photos/                        # Recortes faciais gerados nos cadastros  
 ├── templates/                     # Páginas HTML da interface  
 │   ├── base.html  
 │   ├── index.html  
 │   ├── webcam.html  
 │   ├── register.html  
 │   └── people.html  
 ├── MANUAL_TECNICO_PARCIAL.md      # Manual técnico parcial  
 └── README.md                      # Instruções do projeto  
   
```  
**Documentação complementar**  
- Manual técnico parcial: [`MANUAL_TECNICO_PARCIAL.md`.](MANUAL_TECNICO_PARCIAL.md "MANUAL_TECNICO_PARCIAL.md")  
- Repositório do projeto: \[https://github.com/Matheus-OV/Catraca-de-Reconhecimento-Facial-UBM\].  
**Equipe e licença**  
  
|  |  |  |  
| - | - | - |  
| **Integrante** |  **Papel no projeto** |  **GitHub** |  
| Karolaine Teixeira F. Barbosa |  Back-end |  https://github.com/K4rolTeixeira |  
| Matheus de Oliveira Viana |  QA Tester |  https://github.com/Matheus-OV |  
| Rian Oliveira Moreira |  Documentação Técnica |  https://github.com/Rian-ui-max |  
| Ricardo Felipe Rabello de Souza |  Front-end |  https://github.com/RicardoFRS |  
| Ricardo dos Santos Medeiros |  Back-end |  https://github.com/RICARDO-medeiros01 |  
  
   
**\*\*Licença:\*\* MIT License**  
Projeto desenvolvido na disciplina **Práticas Extensionistas Integradoras III — Engenharia de Software, UBM, 2026**.  
