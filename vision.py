"""Módulo de Visão Computacional para Detecção, Cadastro e Reconhecimento Facial.

Utiliza OpenCV e NumPy nativamente (sem exigir compilação C++/dlib ou GPU),
oferecendo detecção facial via Haar Cascade com equalização de histograma e
extração de embeddings faciais normalizados de 128 dimensões para comparação
por distância euclidiana/similaridade de cosseno.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np

import sqlite3

from db import (
    SITUACOES,
    add_person,
    delete_person,
    get_all_people,
    get_person,
    save_detection,
)

BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = Path(os.getenv("PHOTOS_DIR", str(BASE_DIR / "photos")))
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

RECOGNITION_THRESHOLD = float(os.getenv("RF_THRESHOLD", "0.45"))


def _get_cascade() -> cv2.CascadeClassifier:
    """Carrega o classificador Haar Cascade frontal nativo do OpenCV."""
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    return cv2.CascadeClassifier(cascade_path)


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Converte bytes de imagem (JPEG/PNG/WebP) em matriz BGR do OpenCV."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Arquivo de imagem inválido ou corrompido.")
    return img


def encode_image_base64(img: np.ndarray) -> str:
    """Codifica uma imagem BGR do OpenCV para string JPEG em Base64."""
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise RuntimeError("Falha ao codificar imagem de saída.")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def detect_face_boxes(
    img: np.ndarray,
    scale_factor: float = 1.1,
    min_neighbors: int = 5,
    min_size: tuple[int, int] = (40, 40),
) -> list[tuple[int, int, int, int]]:
    """Detecta rostos na imagem e retorna lista de caixas `(x, y, w, h)`.

    Ordena os rostos encontrados do maior para o menor em área.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)
    cascade = _get_cascade()
    faces = cascade.detectMultiScale(
        gray_eq,
        scaleFactor=scale_factor,
        minNeighbors=min_neighbors,
        minSize=min_size,
    )
    if len(faces) == 0:
        return []
    boxes = [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]
    boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
    return boxes


def extract_face_embedding(face_bgr: np.ndarray) -> np.ndarray:
    """Extrai um vetor descritor facial normalizado de 128 dimensões (float64).

    Combina:
    1. Intensidades espaciais normalizadas com CLAHE (64 dimensões - grade 8x8).
    2. Magnitudes e direções de gradientes Sobel em blocos espaciais (48 dimensões).
    3. Histograma de contraste local normalizado (16 dimensões).
    O vetor resultante possui norma L2 unitária para comparação rápida e estável.
    """
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    # Recorta margem interna de 10% para reduzir interferência do fundo
    h, w = gray.shape[:2]
    if h > 20 and w > 20:
        pad_y, pad_x = int(h * 0.1), int(w * 0.1)
        gray = gray[pad_y : h - pad_y, pad_x : w - pad_x]

    resized = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    norm_gray = clahe.apply(resized)

    # 1. Grade espacial 8x8 (64 valores)
    spatial = cv2.resize(norm_gray, (8, 8), interpolation=cv2.INTER_AREA).astype(
        np.float64
    ).flatten()
    spatial = (spatial - np.mean(spatial)) / (np.std(spatial) + 1e-7)

    # 2. Gradientes horizontais e verticais Sobel em grade 4x6 (24 + 24 = 48 valores)
    gx = cv2.Sobel(norm_gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(norm_gray, cv2.CV_64F, 0, 1, ksize=3)
    gx_small = cv2.resize(np.abs(gx), (6, 4), interpolation=cv2.INTER_AREA).flatten()
    gy_small = cv2.resize(np.abs(gy), (6, 4), interpolation=cv2.INTER_AREA).flatten()
    grad_feat = np.concatenate([gx_small, gy_small])
    grad_feat = grad_feat / (np.linalg.norm(grad_feat) + 1e-7)

    # 3. Histograma de distribuição de tons (16 bins)
    hist = cv2.calcHist([norm_gray], [0], None, [16], [0, 256]).flatten().astype(
        np.float64
    )
    hist = hist / (np.linalg.norm(hist) + 1e-7)

    embedding = np.concatenate([spatial * 0.5, grad_feat * 0.35, hist * 0.15]).astype(
        np.float64
    )
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    return embedding


def match_person(
    face_enc: np.ndarray,
    known_people: list[dict[str, Any]],
    threshold: float | None = None,
) -> tuple[dict[str, Any] | None, float]:
    """Encontra a pessoa cadastrada mais parecida com o rosto.

    Retorna `(pessoa, confianca)`. Se a menor distância euclidiana superar o
    limiar, retorna `(None, 0.0)` (rosto desconhecido).
    """
    limit = RECOGNITION_THRESHOLD if threshold is None else threshold
    best_person: dict[str, Any] | None = None
    best_dist = float("inf")

    for person in known_people:
        raw = person.get("embedding")
        if not raw:
            continue
        known_enc = np.frombuffer(raw, dtype=np.float64)
        if len(known_enc) != len(face_enc):
            continue
        dist = float(np.linalg.norm(known_enc - face_enc))
        if dist < best_dist:
            best_dist = dist
            best_person = person

    if best_person is not None and best_dist <= limit:
        confidence = max(0.0, min(100.0, round((1.0 - (best_dist / 1.0)) * 100.0, 1)))
        return best_person, confidence
    return None, 0.0


def match_embedding(
    face_enc: np.ndarray,
    known_people: list[dict[str, Any]],
    threshold: float | None = None,
) -> tuple[str, float]:
    """Compara o embedding de um rosto com o banco de pessoas cadastradas.

    Retorna `(nome, confianca)` onde `nome` é `'Desconhecido'` caso a menor
    distância euclidiana supere o limiar configurado.
    """
    person, confidence = match_person(face_enc, known_people, threshold)
    if person is None:
        return "Desconhecido", 0.0
    return person["name"], confidence


def decide_access(person: dict[str, Any] | None) -> tuple[str, str]:
    """Decide se o acesso é liberado e informa o motivo.

    Regras: rosto não cadastrado é negado; pessoa cadastrada só é liberada
    se a situação da matrícula for "ativa" (trancada, cancelada e formada
    são negadas).
    """
    if person is None:
        return "negado", "Rosto não cadastrado"
    situacao = person.get("situacao") or "ativa"
    if situacao == "ativa":
        return "liberado", "Matrícula ativa"
    return "negado", f"Matrícula {situacao}"


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name)


def delete_person_with_files(person_id: int) -> bool:
    """Remove a pessoa do banco e apaga também o arquivo da foto em `photos/`.

    Atende ao pedido de exclusão dos dados biométricos (LGPD): o vetor facial
    sai do banco e o recorte do rosto sai do disco.
    """
    person = get_person(person_id)
    if person is None:
        return False
    removed = delete_person(person_id)
    if removed:
        for f in PHOTOS_DIR.glob(f"{person_id}_*.jpg"):
            f.unlink(missing_ok=True)
        # Arquivo no formato antigo (só o nome), se nenhuma outra pessoa o usa.
        others = [p for p in get_all_people() if p["name"] == person["name"]]
        if not others:
            (PHOTOS_DIR / f"{_safe_name(person['name'])}.jpg").unlink(missing_ok=True)
    return removed


def register_person_from_bytes(
    name: str,
    image_bytes: bytes,
    matricula: str = "",
    situacao: str = "ativa",
    consent: bool = False,
) -> dict[str, Any]:
    """Valida o cadastro, detecta o rosto principal, gera o embedding e salva no SQLite.

    Regras: nome e matrícula obrigatórios; só é possível cadastrar com a
    matrícula ativa; o termo de consentimento (LGPD) precisa ser aceito.
    """
    clean_name = name.strip()
    clean_matricula = (matricula or "").strip()
    if not clean_name:
        return {"success": False, "error": "O nome da pessoa é obrigatório."}
    if not clean_matricula:
        return {"success": False, "error": "Informe a matrícula."}
    if situacao not in SITUACOES:
        return {
            "success": False,
            "error": f"Situação inválida. Use: {', '.join(SITUACOES)}.",
        }
    if situacao != "ativa":
        return {
            "success": False,
            "error": "Só é possível cadastrar pessoas com matrícula ativa.",
        }
    if not consent:
        return {
            "success": False,
            "error": "É necessário aceitar o termo de consentimento para o uso da imagem do rosto.",
        }

    img = decode_image_bytes(image_bytes)
    boxes = detect_face_boxes(img)
    if not boxes:
        return {
            "success": False,
            "error": "Nenhum rosto foi detectado na imagem enviada. Tente uma foto frontal bem iluminada.",
        }

    x, y, w, h = boxes[0]
    crop = img[y : y + h, x : x + w]
    embedding = extract_face_embedding(crop)

    ok, crop_buf = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        return {"success": False, "error": "Erro ao processar recorte do rosto."}

    photo_bytes = crop_buf.tobytes()
    try:
        person_id = add_person(
            clean_name,
            embedding.tobytes(),
            photo_bytes,
            matricula=clean_matricula,
            situacao=situacao,
            consented=True,
        )
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Já existe uma pessoa cadastrada com essa matrícula."}

    # O arquivo leva o id no nome: pessoas com o mesmo nome não se sobrescrevem.
    photo_file = PHOTOS_DIR / f"{person_id}_{_safe_name(clean_name)}.jpg"
    photo_file.write_bytes(photo_bytes)

    return {
        "success": True,
        "person_id": person_id,
        "name": clean_name,
        "matricula": clean_matricula,
        "situacao": situacao,
        "box": [x, y, w, h],
        "photo_b64": base64.b64encode(photo_bytes).decode("utf-8"),
    }


def analyze_image_bytes(
    image_bytes: bytes,
    image_name: str = "upload.jpg",
    blur_faces: bool = False,
    record_history: bool = True,
) -> dict[str, Any]:
    """Executa detecção e reconhecimento facial completo sobre uma imagem.

    Retorna dicionário contendo a quantidade de rostos, lista de rostos com
    coordenadas e nomes reconhecidos, além da imagem anotada em Base64.
    """
    img = decode_image_bytes(image_bytes)
    annotated = img.copy()
    boxes = detect_face_boxes(img)
    known_people = get_all_people()

    faces_info: list[dict[str, Any]] = []
    recognized_names: list[str] = []
    decisions: list[str] = []

    for x, y, w, h in boxes:
        crop = img[y : y + h, x : x + w]
        emb = extract_face_embedding(crop)
        person, confidence = match_person(emb, known_people)
        name = person["name"] if person else "Desconhecido"
        access, reason = decide_access(person)

        if person is not None:
            recognized_names.append(name)
        decisions.append(f"{name}: {access} ({reason})")

        if blur_faces:
            roi = annotated[y : y + h, x : x + w]
            annotated[y : y + h, x : x + w] = cv2.GaussianBlur(roi, (99, 99), 30)
        else:
            if access == "liberado":
                color = (40, 180, 99)  # verde
            elif person is not None:
                color = (60, 60, 220)  # vermelho: cadastrado, mas matrícula não ativa
            else:
                color = (0, 165, 255)  # laranja: desconhecido
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            if person is not None:
                label = f"{name} ({confidence:.0f}%) - {access.upper()}"
            else:
                label = "Rosto Detectado - NEGADO"
            cv2.putText(
                annotated,
                label,
                (x, max(20, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        faces_info.append(
            {
                "box": [x, y, w, h],
                "name": name,
                "confidence": confidence,
                "person_id": person["id"] if person else None,
                "access": access,
                "reason": reason,
            }
        )

    if record_history:
        save_detection(image_name, len(boxes), recognized_names, decisions)

    # Decisão geral (usada pela catraca): vale a do maior rosto, o mais próximo da câmera.
    if faces_info:
        decision = {"access": faces_info[0]["access"], "reason": faces_info[0]["reason"]}
    else:
        decision = {"access": "negado", "reason": "Nenhum rosto detectado"}

    return {
        "decision": decision,
        "faces_count": len(boxes),
        "recognized_names": recognized_names,
        "faces": faces_info,
        "annotated_image_b64": encode_image_base64(annotated),
    }
