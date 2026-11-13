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

from db import add_person, get_all_people, save_detection

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


def match_embedding(
    face_enc: np.ndarray,
    known_people: list[dict[str, Any]],
    threshold: float | None = None,
) -> tuple[str, float]:
    """Compara o embedding de um rosto com o banco de pessoas cadastradas.

    Retorna `(nome, confianca)` onde `nome` é `'Desconhecido'` caso a menor
    distância euclidiana supere o limiar configurado.
    """
    limit = RECOGNITION_THRESHOLD if threshold is None else threshold
    best_name = "Desconhecido"
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
            best_name = person["name"]

    if best_dist <= limit:
        confidence = max(0.0, min(100.0, round((1.0 - (best_dist / 1.0)) * 100.0, 1)))
        return best_name, confidence
    return "Desconhecido", 0.0


def register_person_from_bytes(name: str, image_bytes: bytes) -> dict[str, Any]:
    """Detecta o rosto principal na imagem, gera o embedding e salva no SQLite."""
    clean_name = name.strip()
    if not clean_name:
        return {"success": False, "error": "O nome da pessoa é obrigatório."}

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
    safe_filename = "".join(c if c.isalnum() or c in "_-" else "_" for c in clean_name)
    photo_file = PHOTOS_DIR / f"{safe_filename}.jpg"
    photo_file.write_bytes(photo_bytes)

    person_id = add_person(clean_name, embedding.tobytes(), photo_bytes)
    return {
        "success": True,
        "person_id": person_id,
        "name": clean_name,
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

    for x, y, w, h in boxes:
        crop = img[y : y + h, x : x + w]
        emb = extract_face_embedding(crop)
        name, confidence = match_embedding(emb, known_people)

        if name != "Desconhecido":
            recognized_names.append(name)

        if blur_faces:
            roi = annotated[y : y + h, x : x + w]
            annotated[y : y + h, x : x + w] = cv2.GaussianBlur(roi, (99, 99), 30)
        else:
            color = (40, 180, 99) if name != "Desconhecido" else (0, 165, 255)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            label = (
                f"{name} ({confidence:.0f}%)"
                if name != "Desconhecido"
                else "Rosto Detectado"
            )
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
            }
        )

    if record_history:
        save_detection(image_name, len(boxes), recognized_names)

    return {
        "faces_count": len(boxes),
        "recognized_names": recognized_names,
        "faces": faces_info,
        "annotated_image_b64": encode_image_base64(annotated),
    }
