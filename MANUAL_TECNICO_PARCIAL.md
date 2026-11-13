# Manual Técnico Parcial — Sistema de Reconhecimento Facial Simplificado

Este documento apresenta a documentação técnica parcial da versão simplificada do sistema de Detecção, Cadastro e Reconhecimento Facial, estruturada em duas seções:
- **Seção 1:** Especificações Técnicas e Dependências
- **Seção 2:** Guia de Módulos, Funções e Rotas da API

---

## Seção 1: Especificações Técnicas e Dependências

### 1.1 Visão Geral da Arquitetura
A versão simplificada foi projetada sob uma arquitetura monolítica modular de três camadas (**Apresentação Web**, **Processamento de Visão Computacional** e **Persistência Local**), eliminando serviços externos complexos presentes na versão original (como servidor PostgreSQL dedicado, compilação nativa de `dlib` e modelos pesados de tradução de áudio Whisper e geração de legendas via LLM).

```
+-------------------------------------------------------------------+
|                   Camada de Apresentação (Web)                    |
|     HTML5 + Canvas Webcam + Fetch API (Templates Jinja2/Flask)    |
+---------------------------------+---------------------------------+
                                  | HTTP / Multipart / JSON
                                  v
+-------------------------------------------------------------------+
|                Camada de Aplicação e Visão (Python)               |
|  app.py (Controlador Flask)  <--->  vision.py (OpenCV + NumPy)    |
+---------------------------------+---------------------------------+
                                  | SQL Nativo (sqlite3)
                                  v
+-------------------------------------------------------------------+
|                    Camada de Persistência Local                   |
|        db.py -> reconhecimento.db (SQLite) + pasta photos/        |
+-------------------------------------------------------------------+
```

### 1.2 Stack Tecnológica e Dependências

| Componente | Tecnologia / Pacote | Versão Mínima | Papel no Sistema |
| :--- | :--- | :--- | :--- |
| **Linguagem Base** | Python | `>= 3.10` | Execução do backend e processamento matricial |
| **Servidor Web** | `flask` | `>= 3.0.0` | Roteamento HTTP, renderização de templates HTML e API JSON |
| **Visão Computacional** | `opencv-python` (`cv2`) | `4.13.0.92` | Detecção facial via Haar Cascade, CLAHE, gradientes Sobel e manipulação de imagem |
| **Álgebra Linear** | `numpy` | `>= 1.26.0` | Geração, normalização L2 e cálculo de distância euclidiana dos embeddings |
| **Banco de Dados** | `sqlite3` (Stdlib) | Nativo do Python | Armazenamento relacional local de pessoas, embeddings binários e histórico |

### 1.3 Comparativo Técnico de Simplificação

| Aspecto | Projeto Original (`Reconhecimento_Facial-main`) | Versão Simplificada |
| :--- | :--- | :--- |
| **Banco de Dados** | PostgreSQL externo obrigatório (`POSTGRES_DSN`, `psycopg2`) | SQLite3 nativo em arquivo único (`reconhecimento.db`), zero configuração |
| **Dependências Python** | 16 pacotes (`torch>=2.6`, `transformers`, `ultralytics`, `mediapipe`, `face_recognition`, `sounddevice` etc.) | Apenas 3 pacotes com pacotes binários pré-compilados (`flask`, `opencv-python`, `numpy`) |
| **Tempo de Inicialização** | Alto (download de múltiplos GB de pesos da Hugging Face e compilação C++) | Segundos via `./iniciar.sh` |
| **Interface de Uso** | Múltiplos submenus CLI (`questionary`) + 14 templates Flask dispersos | Interface Web unificada em 4 telas claras + API REST JSON |

### 1.4 Pipeline de Detecção e Extração de Embeddings
1. **Pré-processamento e Detecção (`detect_face_boxes`):**
   - A imagem recebida é convertida para escala de cinza (`COLOR_BGR2GRAY`) e submetida à equalização global de histograma (`cv2.equalizeHist`) para reduzir variações de iluminação.
   - O classificador `haarcascade_frontalface_default.xml` localiza as regiões faciais, ordenando os rostos detectados em ordem decrescente de área `(w * h)`.
2. **Extração do Descritor Facial de 128 Dimensões (`extract_face_embedding`):**
   - O recorte facial tem 10% de suas bordas externas aparadas para remover interferências de fundo, é redimensionado para `64x64` pixels e normalizado com **CLAHE** (*Contrast Limited Adaptive Histogram Equalization*).
   - São extraídos e concatenados três vetores complementares:
     - **64 dimensões:** Grade espacial `8x8` normalizada por média zero e desvio padrão unitário (peso `0.50`).
     - **48 dimensões:** Magnitudes dos gradientes horizontais e verticais de Sobel amostradas em grade `6x4` e normalizadas por norma L2 (peso `0.35`).
     - **16 dimensões:** Histograma de distribuição tonal de 16 faixas normalizado por norma L2 (peso `0.15`).
   - O vetor resultante de `128` posições (`float64`) é normalizado para norma L2 unitária (`||v|| = 1.0`).
3. **Comparação e Reconhecimento (`match_embedding`):**
   - Calcula-se a distância euclidiana `d = ||e_consulta - e_cadastrado||_2` contra todos os registros da tabela `people`.
   - Caso a menor distância seja inferior ou igual a `RF_THRESHOLD` (padrão `0.45`), a identidade correspondente é atribuída com pontuação de similaridade `(1 - d) * 100%`.

### 1.5 Esquema do Banco de Dados (`reconhecimento.db`)
- **Tabela `people`:**
  - `id` (`INTEGER PRIMARY KEY AUTOINCREMENT`) — Identificador único da pessoa.
  - `name` (`TEXT NOT NULL`) — Nome da pessoa cadastrada.
  - `embedding` (`BLOB NOT NULL`) — Vetor numpy `float64` de 128 dimensões serializado em bytes (`1024 bytes`).
  - `photo` (`BLOB`) — Imagem JPEG do rosto recortado no momento do cadastro.
  - `created_at` (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`) — Data e hora do cadastro.
- **Tabela `detections`:**
  - `id` (`INTEGER PRIMARY KEY AUTOINCREMENT`) — Identificador único do evento.
  - `image_name` (`TEXT`) — Nome do arquivo ou origem (`webcam_frame.jpg`).
  - `faces_count` (`INTEGER NOT NULL`) — Total de rostos detectados na imagem.
  - `recognized_names` (`TEXT`) — Lista de nomes reconhecidos separados por vírgula.
  - `created_at` (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`) — Data e hora da detecção.

---

## Seção 2: Guia de Módulos, Funções e Rotas da API

### 2.1 Módulo de Persistência (`db.py`)
Responsável pela criação automática do banco SQLite e pelas operações CRUD sobre pessoas e detecções.

| Função | Assinatura | Descrição e Retorno |
| :--- | :--- | :--- |
| `get_conn` | `get_conn() -> Generator[sqlite3.Connection, None, None]` | Gerenciador de contexto que abre e fecha conexões seguras ao arquivo SQLite com `sqlite3.Row`. |
| `init_db` | `init_db() -> None` | Cria as tabelas `people` e `detections` caso não existam. Executado automaticamente no início. |
| `add_person` | `add_person(name: str, embedding_bytes: bytes, photo_bytes: bytes) -> int` | Insere uma nova pessoa com seu vetor facial e foto recortada. Retorna o `id` gerado. |
| `get_all_people` | `get_all_people() -> list[dict[str, Any]]` | Retorna todas as pessoas cadastradas contendo `id`, `name`, `embedding` (bytes), `photo_b64` (string Base64) e `created_at`. |
| `delete_person` | `delete_person(person_id: int) -> bool` | Exclui o registro da pessoa correspondente ao `person_id`. Retorna `True` se removido com sucesso. |
| `save_detection` | `save_detection(image_name: str, faces_count: int, recognized_names: list[str]) -> int` | Registra uma execução de detecção/reconhecimento no histórico e retorna o `id` do evento. |
| `list_detections` | `list_detections(limit: int = 50) -> list[dict[str, Any]]` | Lista os últimos `limit` eventos de detecção em ordem decrescente de ID. |

---

### 2.2 Módulo de Visão Computacional (`vision.py`)
Concentra o processamento de imagens, detecção facial, extração de descritores e anotação visual.

| Função | Assinatura | Descrição e Retorno |
| :--- | :--- | :--- |
| `decode_image_bytes` | `decode_image_bytes(image_bytes: bytes) -> np.ndarray` | Decodifica bytes brutos de imagem em matriz BGR do OpenCV. Lança `ValueError` se inválida. |
| `encode_image_base64` | `encode_image_base64(img: np.ndarray) -> str` | Codifica uma matriz BGR em JPEG e retorna sua representação textual em Base64. |
| `detect_face_boxes` | `detect_face_boxes(img: np.ndarray, scale_factor=1.1, min_neighbors=5, min_size=(40, 40)) -> list[tuple[int, int, int, int]]` | Localiza todos os rostos na imagem e retorna lista de tuplas `(x, y, w, h)` ordenada do maior para o menor rosto. |
| `extract_face_embedding` | `extract_face_embedding(face_bgr: np.ndarray) -> np.ndarray` | Gera o descritor facial normalizado de 128 dimensões (`dtype=float64`) a partir do recorte BGR de um rosto. |
| `match_embedding` | `match_embedding(face_enc: np.ndarray, known_people: list[dict], threshold: float \| None = None) -> tuple[str, float]` | Compara `face_enc` com a lista de pessoas cadastradas. Retorna `(nome, similaridade_percentual)`. |
| `register_person_from_bytes` | `register_person_from_bytes(name: str, image_bytes: bytes) -> dict[str, Any]` | Detecta o rosto principal na foto enviada, extrai o embedding, salva o recorte em `photos/` e persiste no banco SQLite. |
| `analyze_image_bytes` | `analyze_image_bytes(image_bytes: bytes, image_name="upload.jpg", blur_faces=False, record_history=True) -> dict[str, Any]` | Executa detecção e reconhecimento em todos os rostos da imagem, desenha caixas delimitadoras (ou aplica desfoque) e retorna os metadados e a imagem anotada em Base64. |

---

### 2.3 Aplicação Web e Rotas da API (`app.py`)

#### Rotas de Interface Web (HTML)

| Método | Rota | Template Renderizado | Descrição |
| :--- | :--- | :--- | :--- |
| `GET`, `POST` | `/` | `templates/index.html` | Página inicial para envio de foto, detecção de rostos, reconhecimento de pessoas cadastradas e modo privacidade (desfoque). |
| `GET` | `/webcam` | `templates/webcam.html` | Interface de monitoramento em tempo real via webcam com sobreposição gráfica em `<canvas>`. |
| `GET`, `POST` | `/register` | `templates/register.html` | Formulário de cadastro de nova pessoa via upload de arquivo ou captura direta da webcam. |
| `GET` | `/people` | `templates/people.html` | Painel de gerenciamento de pessoas cadastradas (com exclusão) e tabela de histórico de detecções. |

#### Rotas da API REST (JSON)

1. **`POST /api/analyze`**
   - **Descrição:** Processa uma imagem enviada via `multipart/form-data` para detecção e reconhecimento facial.
   - **Parâmetros (`form-data`):**
     - `image` (arquivo obrigatório): Imagem JPEG/PNG/WebP.
     - `record` (opcional, `"true"` ou `"false"`): Define se a análise deve ser salva na tabela `detections`.
     - `blur` (opcional, `"true"` ou `"false"`): Aplica desfoque gaussiano nos rostos detectados.
   - **Exemplo de Resposta (`200 OK`):**
     ```json
     {
       "success": true,
       "faces_count": 1,
       "recognized_names": ["Maria Silva"],
       "faces": [
         {
           "box": [142, 88, 164, 164],
           "name": "Maria Silva",
           "confidence": 84.5
         }
       ],
       "annotated_image_b64": "/9j/4AAQSkZJRgABAQAAAQABAAD..."
     }
     ```

2. **`POST /api/register`**
   - **Descrição:** Cadastra uma nova pessoa a partir de seu nome e imagem facial.
   - **Parâmetros (`form-data`):**
     - `name` (texto obrigatório): Nome da pessoa.
     - `image` (arquivo obrigatório): Foto contendo o rosto da pessoa.
   - **Exemplo de Resposta (`200 OK`):**
     ```json
     {
       "success": true,
       "person_id": 1,
       "name": "Maria Silva",
       "box": [142, 88, 164, 164],
       "photo_b64": "/9j/4AAQSkZJRgABAQAAAQABAAD..."
     }
     ```

3. **`GET /api/people`**
   - **Descrição:** Lista todas as pessoas cadastradas no banco SQLite.
   - **Exemplo de Resposta (`200 OK`):**
     ```json
     {
       "count": 1,
       "people": [
         {
           "id": 1,
           "name": "Maria Silva",
           "created_at": "2026-11-13 09:25:00",
           "photo_b64": "/9j/4AAQSkZJRgABAQAAAQABAAD..."
         }
       ]
     }
     ```

4. **`DELETE /api/people/<int:person_id>`**
   - **Descrição:** Remove uma pessoa cadastrada pelo seu `id`.
   - **Exemplo de Resposta (`200 OK`):**
     ```json
     {
       "success": true,
       "deleted_id": 1
     }
     ```

5. **`GET /api/detections`**
   - **Descrição:** Retorna os registros mais recentes do histórico de detecções (parâmetro de query opcional `?limit=50`).
   - **Exemplo de Resposta (`200 OK`):**
     ```json
     {
       "count": 1,
       "detections": [
         {
           "id": 1,
           "image_name": "img.jpg",
           "faces_count": 1,
           "recognized_names": "Maria Silva",
           "created_at": "2026-11-13 09:26:12"
         }
       ]
     }
     ```
