# Manual Técnico Parcial — Catraca de Reconhecimento Facial UBM

Versão: 1.0 · Data: 20/11/2026 · Repositório: https://github.com/Matheus-OV/Catraca-de-Reconhecimento-Facial-UBM

## 1. Público-alvo e tarefas

Este manual se destina a: desenvolvedor que vai assumir a manutenção do sistema ou integrar a catraca física do campus ao sistema de reconhecimento facial.

Ao final da leitura, essa pessoa deve conseguir:

- integrar um novo cliente (a catraca física ou uma nova tela) às rotas existentes da API para cadastrar pessoas e reconhecer rostos (resolvida na seção 2)
- alterar o cadastro ou o reconhecimento facial sem quebrar as regras que decidem quem é liberado e quem é "Desconhecido" (resolvida na seção 3)

Para instalar e executar o sistema, consulte o [README](../README.md).

## 2. Referência da API

### Visão geral

Esta referência cobre as 5 rotas REST usadas pelas telas de webcam, cadastro e pessoas, que são as mesmas que um cliente externo, como a catraca, deve usar. Nenhuma rota exige autenticação. Endereço base: http://localhost:8000 (a porta pode ser alterada pela variável de ambiente `PORT`). As rotas `POST` recebem `multipart/form-data` e todas as rotas respondem em JSON.

#### POST /api/analyze

Detecta todos os rostos de uma imagem e informa quem foi reconhecido entre as pessoas cadastradas.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| image | arquivo (JPEG, PNG ou WebP) | Sim | Foto ou quadro da webcam a ser analisado |
| record | texto (`true` ou `false`) | Não | Se `true`, salva a análise no histórico de detecções. Padrão: `false` |
| blur | texto (`true` ou `false`) | Não | Se `true`, desfoca os rostos na imagem devolvida. Padrão: `false` |

Exemplo de requisição:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "image=@examples/img.jpg" \
  -F "record=true"
```

Resposta de sucesso: 200 OK, com a quantidade de rostos, os nomes reconhecidos, a posição (`box`: x, y, largura, altura) e a confiança de cada rosto, além da imagem anotada em Base64. Exemplo real com `examples/img.jpg`, após cadastrar uma pessoa:

```json
{
  "success": true,
  "faces_count": 4,
  "recognized_names": ["Maria Silva"],
  "faces": [
    { "box": [269, 392, 226, 226], "name": "Maria Silva", "confidence": 100.0 },
    { "box": [284, 94, 218, 218], "name": "Desconhecido", "confidence": 0.0 }
  ],
  "annotated_image_b64": "/9j/4AAQSkZJRgABAQAA..."
}
```

Erros possíveis: 400 com `"Nenhuma imagem enviada."` quando o campo `image` não é enviado; 400 com `"Arquivo de imagem inválido ou corrompido."` quando o arquivo não é uma imagem; 413 quando o arquivo passa de 16 MB.

#### POST /api/register

Cadastra uma pessoa a partir do nome e de uma foto do rosto.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| name | texto | Sim | Nome da pessoa. Espaços no início e no fim são removidos |
| image | arquivo (JPEG, PNG ou WebP) | Sim | Foto com o rosto da pessoa, de preferência frontal e bem iluminada |

Exemplo de requisição:

```bash
curl -X POST http://localhost:8000/api/register \
  -F "name=Maria Silva" \
  -F "image=@examples/img.jpg"
```

Resposta de sucesso: 200 OK, com o `person_id` gerado, o nome, a posição do rosto usado no cadastro e o recorte do rosto em Base64.

```json
{
  "success": true,
  "person_id": 1,
  "name": "Maria Silva",
  "box": [269, 392, 226, 226],
  "photo_b64": "/9j/4AAQSkZJRgABAQAA..."
}
```

Erros possíveis: 400 com `"Informe o nome e envie a imagem."` quando falta o nome (ou ele só tem espaços) ou a imagem; 400 com `"Nenhum rosto foi detectado na imagem enviada. Tente uma foto frontal bem iluminada."` quando a foto não tem rosto; 400 com `"Arquivo de imagem inválido ou corrompido."` quando o arquivo não é uma imagem; 413 quando o arquivo passa de 16 MB.

#### GET /api/people

Lista todas as pessoas cadastradas, em ordem alfabética.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| (nenhum) | — | — | Esta rota não recebe parâmetros |

Exemplo de requisição:

```bash
curl http://localhost:8000/api/people
```

Resposta de sucesso: 200 OK, com o total (`count`) e a lista de pessoas com `id`, `name`, `created_at` (horário UTC) e `photo_b64`. O embedding facial não é devolvido.

```json
{
  "count": 1,
  "people": [
    { "id": 1, "name": "Maria Silva", "created_at": "2026-11-20 22:45:48", "photo_b64": "/9j/4AAQSkZJRgA..." }
  ]
}
```

Erros possíveis: esta rota não tem erros previstos. Sem cadastros, ela devolve `count: 0` e a lista vazia.

#### DELETE /api/people/{id}

Remove a pessoa cadastrada com o `id` informado. A rota também aceita o método `POST`.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| id | inteiro (na rota) | Sim | `id` da pessoa, obtido em `GET /api/people` |

Exemplo de requisição:

```bash
curl -X DELETE http://localhost:8000/api/people/1
```

Resposta de sucesso: 200 OK, com `"success": true` e o `deleted_id`.

```json
{ "success": true, "deleted_id": 1 }
```

Erros possíveis: 200 OK com `"success": false` quando não existe pessoa com esse `id` (a rota não devolve 404 nesse caso); 404 quando o `id` não é um número inteiro.

#### GET /api/detections

Lista o histórico mais recente de detecções, da mais nova para a mais antiga.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| limit | inteiro (na query string) | Não | Quantidade máxima de registros. Padrão: 50 |

Exemplo de requisição:

```bash
curl "http://localhost:8000/api/detections?limit=5"
```

Resposta de sucesso: 200 OK, com o total (`count`) e os registros com `id`, `image_name`, `faces_count`, `recognized_names` (texto separado por vírgula, ou `"Nenhum"`) e `created_at` (horário UTC).

```json
{
  "count": 1,
  "detections": [
    { "id": 1, "image_name": "img.jpg", "faces_count": 4, "recognized_names": "Maria Silva", "created_at": "2026-11-20 22:45:48" }
  ]
}
```

Erros possíveis: 500 Internal Server Error quando `limit` não é um número inteiro (ex.: `?limit=abc`).

## 3. Regras de negócio

### Visão geral

Estas são as regras que o código aplica hoje no cadastro e no reconhecimento facial. Elas vêm do objetivo do projeto (substituir a carteirinha por reconhecimento facial no controle de acesso ao campus) e foram conferidas no código e em testes com as imagens da pasta `examples/`.

| Código | Regra | Onde é aplicada no código | Exemplo do que acontece |
|---|---|---|---|
| RN01 | Toda pessoa cadastrada precisa ter um nome que não esteja vazio | `app.py` (`register_page`, `api_register`) e `vision.py` (`register_person_from_bytes`) | Cadastrar com o nome `"   "` retorna 400 com `"Informe o nome e envie a imagem."` |
| RN02 | Só é possível cadastrar uma foto em que um rosto seja detectado | `vision.py` (`register_person_from_bytes`) | Uma foto sem rosto retorna 400 com `"Nenhum rosto foi detectado na imagem enviada..."` e nada é salvo |
| RN03 | Se a foto do cadastro tiver vários rostos, apenas o maior (mais próximo da câmera) é cadastrado | `vision.py` (`detect_face_boxes` ordena por área; `register_person_from_bytes` usa o primeiro) | Com `examples/img.jpg` (4 rostos), só o rosto de 226 x 226 pixels foi cadastrado |
| RN04 | Um rosto só é reconhecido se a distância até o cadastro mais parecido for menor ou igual ao limiar `RF_THRESHOLD` (padrão `0.45`); senão, ele é "Desconhecido" | `vision.py` (`match_embedding`) | Rostos não cadastrados voltam como `"Desconhecido"` com confiança `0.0`. Aumentar o limiar faz o sistema confundir pessoas parecidas |
| RN05 | A confiança do reconhecimento é calculada como `(1 - distância) x 100`, entre 0 e 100 | `vision.py` (`match_embedding`) | A mesma foto usada no cadastro é reconhecida com confiança `100.0` |
| RN06 | Rostos menores que 40 x 40 pixels não são detectados | `vision.py` (`detect_face_boxes`, `min_size=(40, 40)`) | Uma pessoa muito longe da câmera não é contada em `faces_count` |
| RN07 | A imagem enviada precisa ser um arquivo de imagem válido de até 16 MB | `vision.py` (`decode_image_bytes`) e `app.py` (`MAX_CONTENT_LENGTH`) | Um arquivo que não é imagem retorna 400; um arquivo maior que 16 MB retorna 413 |
| RN08 | Análises feitas pela página inicial sempre entram no histórico; pela API, só quando `record=true`. Os quadros da tela de webcam não são registrados | `app.py` (`index`, `api_analyze`) e `templates/webcam.html` | Analisar uma foto pela API sem `record` não cria registro em `GET /api/detections` |
| RN09 | No modo privacidade (`blur`), os rostos são desfocados e nenhum nome é desenhado na imagem, mas o reconhecimento continua sendo feito e devolvido no JSON | `vision.py` (`analyze_image_bytes`) | Com `blur=true`, a imagem volta desfocada e `recognized_names` continua preenchido |

## 4. Próximas seções previstas

| Seção prevista | Quando será incluída |
|---|---|
| Arquitetura básica | Entrega final do semestre |
| Estrutura do banco de dados | Entrega final do semestre |
| Implantação no servidor | Entrega final do semestre |
| Solução de problemas | Entrega final do semestre |
| Guia de manutenção | Entrega final do semestre |
