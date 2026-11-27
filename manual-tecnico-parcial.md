# Manual Técnico Parcial — Catraca de Reconhecimento Facial UBM

Versão: 1.1 · Data: 26/11/2026 · Repositório: https://github.com/Matheus-OV/Catraca-de-Reconhecimento-Facial-UBM

## 1. Público-alvo e tarefas

Este manual se destina a: desenvolvedor que vai assumir a manutenção do sistema ou integrar a catraca física do campus ao sistema de reconhecimento facial.

Ao final da leitura, essa pessoa deve conseguir:

- integrar um novo cliente (a catraca física ou uma nova tela) às rotas existentes da API para cadastrar pessoas, reconhecer rostos e obter a decisão de acesso (resolvida na seção 2)
- alterar o cadastro ou o reconhecimento facial sem quebrar as regras que decidem quem é liberado, quem é negado e quem é "Desconhecido" (resolvida na seção 3)
- saber o que o sistema ainda **não** garante em precisão e em segurança antes de colocá-lo em uso real (resolvida na seção 4)

Para instalar e executar o sistema, consulte o [README](../README.md). A estrutura do banco de dados está em [BANCO_DE_DADOS.md](BANCO_DE_DADOS.md).

## 2. Referência da API

### Visão geral

Esta referência cobre as 6 rotas REST usadas pelas telas de webcam, cadastro e pessoas. Um cliente externo, como a catraca, deve usar essas mesmas rotas. **Nenhuma rota exige autenticação** (veja a seção 4.2). Endereço base: http://localhost:8000 (a porta pode ser alterada pela variável de ambiente `PORT`). As rotas `POST` recebem `multipart/form-data`; a rota de situação também aceita JSON. Todas as rotas respondem em JSON.

Nos exemplos abaixo, os textos em Base64 foram encurtados com `...`. Os exemplos são respostas reais, geradas com as imagens da pasta `examples/`.

#### POST /api/analyze

Detecta todos os rostos de uma imagem, informa quem foi reconhecido entre as pessoas cadastradas e devolve a decisão de acesso (liberado ou negado) com o motivo.

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

Resposta de sucesso: 200 OK. Os campos são:

- `decision`: decisão geral usada pela catraca. Vale a decisão do **maior rosto** (o mais próximo da câmera). Sem rostos, vem `{"access": "negado", "reason": "Nenhum rosto detectado"}`.
- `faces`: um item por rosto, com a posição (`box`: x, y, largura, altura), o nome, a confiança, o `person_id` (`null` para desconhecido), a decisão (`access`) e o motivo (`reason`).
- `faces_count`, `recognized_names` e `annotated_image_b64` (imagem com as marcações).

Exemplo real com `examples/img.jpg`, depois de cadastrar uma pessoa:

```json
{
  "success": true,
  "decision": { "access": "liberado", "reason": "Matrícula ativa" },
  "faces_count": 4,
  "recognized_names": ["Maria Silva"],
  "faces": [
    { "box": [269, 392, 226, 226], "name": "Maria Silva", "confidence": 100.0, "person_id": 1, "access": "liberado", "reason": "Matrícula ativa" },
    { "box": [284, 94, 218, 218], "name": "Desconhecido", "confidence": 0.0, "person_id": null, "access": "negado", "reason": "Rosto não cadastrado" }
  ],
  "annotated_image_b64": "/9j/4AAQSkZJRgABAQAA..."
}
```

(Os outros 2 rostos da imagem, também desconhecidos, foram omitidos.)

Erros possíveis:

| Código | Mensagem | Quando acontece |
|---|---|---|
| 400 | `"Nenhuma imagem enviada."` | O campo `image` não foi enviado |
| 400 | `"Arquivo de imagem inválido ou corrompido."` | O arquivo não é uma imagem |
| 413 | (página de erro do Flask) | O arquivo passa de 16 MB |

#### POST /api/register

Cadastra uma pessoa a partir do nome, da matrícula, do aceite do termo de consentimento (LGPD) e de uma foto do rosto.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| name | texto | Sim | Nome da pessoa. Espaços no início e no fim são removidos |
| matricula | texto | Sim | Matrícula da pessoa. Não pode repetir a de outro cadastro |
| consent | texto (`true`, `on`, `1` ou `sim`) | Sim | Aceite do termo de consentimento. Qualquer outro valor, ou a ausência do campo, recusa o cadastro |
| situacao | texto | Não | Situação da matrícula. Padrão: `ativa`. Só `ativa` pode ser cadastrada |
| image | arquivo (JPEG, PNG ou WebP) | Sim | Foto com o rosto da pessoa, de preferência frontal e bem iluminada |

Exemplo de requisição:

```bash
curl -X POST http://localhost:8000/api/register \
  -F "name=Maria Silva" \
  -F "matricula=20260123" \
  -F "consent=true" \
  -F "image=@examples/img.jpg"
```

Resposta de sucesso: 200 OK, com o `person_id` gerado, os dados do cadastro, a posição do rosto usado e o recorte do rosto em Base64.

```json
{
  "success": true,
  "person_id": 1,
  "name": "Maria Silva",
  "matricula": "20260123",
  "situacao": "ativa",
  "box": [269, 392, 226, 226],
  "photo_b64": "/9j/4AAQSkZJRgABAQAA..."
}
```

Erros possíveis (todos com código 400, exceto o último):

| Mensagem | Quando acontece |
|---|---|
| `"Informe o nome e envie a imagem."` | Falta o nome (ou ele só tem espaços) ou a imagem |
| `"Informe a matrícula."` | Falta a matrícula |
| `"Situação inválida. Use: ativa, trancada, cancelada, formada."` | `situacao` tem um valor fora da lista |
| `"Só é possível cadastrar pessoas com matrícula ativa."` | `situacao` é `trancada`, `cancelada` ou `formada` |
| `"É necessário aceitar o termo de consentimento para o uso da imagem do rosto."` | `consent` não foi enviado ou não é um valor de aceite |
| `"Arquivo de imagem inválido ou corrompido."` | O arquivo não é uma imagem |
| `"Nenhum rosto foi detectado na imagem enviada. Tente uma foto frontal bem iluminada."` | A foto não tem rosto detectável |
| `"Já existe uma pessoa cadastrada com essa matrícula."` | A matrícula já está em outro cadastro |
| 413 (página de erro do Flask) | O arquivo passa de 16 MB |

#### GET /api/people

Lista todas as pessoas cadastradas, em ordem alfabética.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| (nenhum) | — | — | Esta rota não recebe parâmetros |

Exemplo de requisição:

```bash
curl http://localhost:8000/api/people
```

Resposta de sucesso: 200 OK, com o total (`count`) e a lista de pessoas com `id`, `name`, `matricula`, `situacao`, `created_at` e `consent_at` (horários em UTC) e `photo_b64`. O embedding facial não é devolvido, mas **a foto do rosto é** (veja a seção 4.2).

```json
{
  "count": 1,
  "people": [
    {
      "id": 1,
      "name": "Maria Silva",
      "matricula": "20260123",
      "situacao": "ativa",
      "created_at": "2026-11-26 19:35:39",
      "consent_at": "2026-11-26 19:35:39",
      "photo_b64": "/9j/4AAQSkZJRgAB..."
    }
  ]
}
```

Erros possíveis: esta rota não tem erros previstos. Sem cadastros, ela devolve `count: 0` e a lista vazia.

#### POST /api/people/{id}/situacao

Altera a situação da matrícula de uma pessoa. A rota também aceita o método `PATCH`. É assim que se bloqueia o acesso de quem trancou, cancelou ou se formou, sem apagar o cadastro.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| id | inteiro (na rota) | Sim | `id` da pessoa, obtido em `GET /api/people` |
| situacao | texto (JSON ou formulário) | Sim | `ativa`, `trancada`, `cancelada` ou `formada` |

Exemplo de requisição:

```bash
curl -X POST http://localhost:8000/api/people/1/situacao \
  -H "Content-Type: application/json" \
  -d '{"situacao": "trancada"}'
```

Resposta de sucesso: 200 OK.

```json
{ "success": true, "id": 1, "situacao": "trancada" }
```

Erros possíveis:

| Código | Resposta | Quando acontece |
|---|---|---|
| 400 | `"Situação inválida. Use: ativa, trancada, cancelada, formada."` | `situacao` ausente ou fora da lista |
| 404 | `{"success": false, "id": 99, "situacao": "ativa"}` | Não existe pessoa com esse `id` |

#### DELETE /api/people/{id}

Remove a pessoa cadastrada com o `id` informado. Apaga o registro do banco (inclusive o vetor facial) e o arquivo da foto na pasta `photos/`, atendendo ao pedido de exclusão dos dados biométricos (LGPD). A rota também aceita o método `POST`.

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

Resposta de sucesso: 200 OK, com o total (`count`) e os registros com `id`, `image_name`, `faces_count`, `recognized_names` (texto separado por vírgula, ou `"Nenhum"`), `decisions` (decisão e motivo de cada rosto, separados por `;`) e `created_at` (horário UTC).

```json
{
  "count": 1,
  "detections": [
    {
      "id": 1,
      "image_name": "img.jpg",
      "faces_count": 4,
      "recognized_names": "Maria Silva",
      "decisions": "Maria Silva: liberado (Matrícula ativa); Desconhecido: negado (Rosto não cadastrado); Desconhecido: negado (Rosto não cadastrado); Desconhecido: negado (Rosto não cadastrado)",
      "created_at": "2026-11-26 19:35:39"
    }
  ]
}
```

Erros possíveis: 500 Internal Server Error quando `limit` não é um número inteiro (ex.: `?limit=abc`). Um `limit` negativo (ex.: `?limit=-1`) não dá erro: o SQLite entende como "sem limite" e devolve o histórico inteiro.

## 3. Regras de negócio

### Visão geral

Estas são as regras que o código aplica hoje no cadastro, no reconhecimento facial e na decisão de acesso. Elas vêm do objetivo do projeto (substituir a carteirinha por reconhecimento facial no controle de acesso ao campus) e foram conferidas no código e em testes com as imagens da pasta `examples/`. Todas ficam no back-end (`vision.py` e `db.py`): as telas só repetem algumas validações para avisar o usuário mais cedo.

#### Cadastro

| Código | Regra | Onde é aplicada no código | Exemplo do que acontece |
|---|---|---|---|
| RN01 | Toda pessoa cadastrada precisa ter um nome que não esteja vazio | `app.py` (`register_page`, `api_register`) e `vision.py` (`register_person_from_bytes`) | Cadastrar com o nome `"   "` retorna 400 com `"Informe o nome e envie a imagem."` |
| RN02 | A matrícula é obrigatória e não pode se repetir | `vision.py` (`register_person_from_bytes`) e `db.py` (índice único `idx_people_matricula`) | Cadastrar de novo a matrícula `20260123` retorna 400 com `"Já existe uma pessoa cadastrada com essa matrícula."` |
| RN03 | Só é possível cadastrar pessoas com a matrícula ativa | `vision.py` (`register_person_from_bytes`) | Enviar `situacao=trancada` retorna 400 com `"Só é possível cadastrar pessoas com matrícula ativa."` |
| RN04 | O cadastro só é feito se a pessoa aceitar o termo de consentimento (LGPD); a data e a hora do aceite são gravadas em `consent_at` | `vision.py` (`register_person_from_bytes`) e `db.py` (`add_person`) | Sem `consent=true`, retorna 400 e nada é salvo |
| RN05 | Só é possível cadastrar uma foto em que um rosto seja detectado | `vision.py` (`register_person_from_bytes`) | Uma foto sem rosto retorna 400 com `"Nenhum rosto foi detectado na imagem enviada..."` e nada é salvo |
| RN06 | Se a foto do cadastro tiver vários rostos, apenas o maior (mais próximo da câmera) é cadastrado | `vision.py` (`detect_face_boxes` ordena por área; `register_person_from_bytes` usa o primeiro) | Com `examples/img.jpg` (4 rostos), só o rosto de 226 x 226 pixels foi cadastrado |
| RN07 | Excluir uma pessoa apaga o registro do banco (com o vetor facial) e o arquivo da foto em `photos/` | `vision.py` (`delete_person_with_files`) | Depois de `DELETE /api/people/1`, a pessoa some de `GET /api/people` e o arquivo `photos/1_*.jpg` é apagado |

#### Reconhecimento

| Código | Regra | Onde é aplicada no código | Exemplo do que acontece |
|---|---|---|---|
| RN08 | Um rosto só é reconhecido se a distância até o cadastro mais parecido for menor ou igual ao limiar `RF_THRESHOLD` (padrão `0.45`); senão, ele é "Desconhecido" | `vision.py` (`match_person`) | Rostos não cadastrados voltam como `"Desconhecido"` com confiança `0.0`. Aumentar o limiar faz o sistema confundir pessoas parecidas |
| RN09 | A confiança do reconhecimento é calculada como `(1 - distância) x 100`, entre 0 e 100 | `vision.py` (`match_person`) | A mesma foto usada no cadastro é reconhecida com confiança `100.0` |
| RN10 | Rostos menores que 40 x 40 pixels não são detectados | `vision.py` (`detect_face_boxes`, `min_size=(40, 40)`) | Uma pessoa muito longe da câmera não é contada em `faces_count` |
| RN11 | A imagem enviada precisa ser um arquivo de imagem válido de até 16 MB | `vision.py` (`decode_image_bytes`) e `app.py` (`MAX_CONTENT_LENGTH`) | Um arquivo que não é imagem retorna 400; um arquivo maior que 16 MB retorna 413 |

#### Decisão de acesso

| Código | Regra | Onde é aplicada no código | Exemplo do que acontece |
|---|---|---|---|
| RN12 | Rosto não cadastrado é sempre negado | `vision.py` (`decide_access`) | `"access": "negado"`, `"reason": "Rosto não cadastrado"` (marcação laranja) |
| RN13 | Pessoa reconhecida só é liberada se a situação da matrícula for `ativa`; `trancada`, `cancelada` e `formada` são negadas | `vision.py` (`decide_access`) e `db.py` (`SITUACOES`) | Depois de trancar a matrícula, a mesma foto volta com `"reason": "Matrícula trancada"` (marcação vermelha) |
| RN14 | Com vários rostos na imagem, a decisão geral (`decision`) é a do maior rosto, o mais próximo da câmera. Sem rosto, o acesso é negado | `vision.py` (`analyze_image_bytes`) | Com `examples/img.jpg`, a decisão geral é a de Maria Silva, mesmo havendo 3 desconhecidos atrás |

#### Histórico e privacidade

| Código | Regra | Onde é aplicada no código | Exemplo do que acontece |
|---|---|---|---|
| RN15 | Análises feitas pela página inicial sempre entram no histórico; pela API, só quando `record=true`. Os quadros da tela de webcam não são registrados | `app.py` (`index`, `api_analyze`) e `templates/webcam.html` | Analisar uma foto pela API sem `record` não cria registro em `GET /api/detections` |
| RN16 | Cada registro do histórico guarda a decisão e o motivo de cada rosto | `vision.py` (`analyze_image_bytes`) e `db.py` (`save_detection`) | O campo `decisions` traz `"Maria Silva: liberado (Matrícula ativa); Desconhecido: negado (...)"` |
| RN17 | No modo privacidade (`blur`), os rostos são desfocados e nenhum nome é desenhado na imagem, mas o reconhecimento continua sendo feito e devolvido no JSON | `vision.py` (`analyze_image_bytes`) | Com `blur=true`, a imagem volta desfocada e `recognized_names` continua preenchido |

## 4. Limitações conhecidas

Esta seção existe para que ninguém coloque o sistema em uso real achando que ele garante mais do que garante hoje.

### 4.1 Algoritmo de reconhecimento

O "descritor facial de 128 dimensões" (`extract_face_embedding` em `vision.py`) **não vem de um modelo de reconhecimento facial treinado** (como uma rede neural). Ele é uma combinação de três medidas simples do recorte do rosto, já reduzido para 64 x 64 pixels e com o contraste equalizado (CLAHE):

| Parte | Tamanho | O que mede | Peso |
|---|---|---|---|
| Grade de pixels | 64 valores (8 x 8) | Brilho médio de cada região do rosto | 0,50 |
| Bordas (Sobel) | 48 valores | Força das bordas horizontais e verticais | 0,35 |
| Histograma de tons | 16 valores | Distribuição de tons claros e escuros | 0,15 |

Isso funciona como demonstração, mas tem consequências:

- **É sensível a ângulo, pose e luz.** Em teste com o rosto cadastrado de `examples/img.jpg`, a mesma imagem espelhada teve distância 1,51, muito acima do limiar de 0,45: a própria pessoa deixou de ser reconhecida. Ou seja, basta virar o rosto para o sistema não reconhecer quem está cadastrado.
- **Pode confundir pessoas diferentes.** O descritor compara "aparência geral" (claro/escuro, bordas), e não traços do rosto. Nos 9 rostos de `examples/`, a menor distância entre pessoas diferentes foi 0,88, mas essa amostra é pequena demais para medir a taxa de falsa aceitação.
- **Contradiz a meta do backlog.** O item 7 do backlog exige no máximo 0,1% de falsa aceitação. Com o descritor atual, essa meta não está garantida nem foi medida. Atingi-la exige trocar o descritor por um modelo de reconhecimento facial treinado e medir a taxa com um conjunto de testes adequado.
- **Não há prova de vida.** O sistema não distingue um rosto real de uma foto impressa ou da tela de um celular. Uma foto de uma pessoa cadastrada pode liberar o acesso.

### 4.2 Segurança

- **Não há login.** Qualquer pessoa que acesse o endereço do servidor pode cadastrar rostos (`POST /api/register`), excluir cadastros (`DELETE /api/people/{id}`, que **também aceita `POST`**) e alterar a situação da matrícula (`POST /api/people/{id}/situacao`), liberando ou bloqueando o acesso de qualquer pessoa.
- **As fotos de rosto ficam expostas.** `GET /api/people` devolve a foto do rosto de todas as pessoas cadastradas, sem login. Foto de rosto é dado biométrico, ou seja, dado pessoal sensível pela LGPD.
- **Mensagens de erro internas são devolvidas ao cliente.** As rotas devolvem o texto da exceção do Python em caso de erro inesperado, o que pode revelar detalhes internos.
- **Uso recomendado hoje:** apenas em rede local controlada, para demonstração. Antes do uso real, é preciso no mínimo exigir login de administrador nas rotas de cadastro, exclusão, alteração de situação e listagem.

## 5. Próximas seções previstas

| Seção prevista | Quando será incluída |
|---|---|
| Arquitetura básica | Entrega final do semestre |
| Implantação no servidor | Entrega final do semestre |
| Solução de problemas | Entrega final do semestre |
| Guia de manutenção | Entrega final do semestre |

A estrutura do banco de dados, antes prevista aqui, já está documentada em [BANCO_DE_DADOS.md](BANCO_DE_DADOS.md).
