"""Servidor Web Flask Simplificado para Detecção, Cadastro e Reconhecimento Facial."""

from __future__ import annotations

import os
from flask import Flask, jsonify, render_template, request

from db import SITUACOES, get_all_people, init_db, list_detections, update_situacao
from vision import (
    analyze_image_bytes,
    delete_person_with_files,
    register_person_from_bytes,
)

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # Limite de 16 MB por upload

# Inicializa automaticamente o banco SQLite na partida
init_db()


def _is_checked(value: str | None) -> bool:
    """Interpreta o valor de uma caixa de seleção/campo booleano de formulário."""
    return (value or "").strip().lower() in ("on", "true", "1", "sim")


@app.route("/", methods=["GET", "POST"])
def index():
    """Página principal: Upload de imagem para detecção e reconhecimento facial."""
    if request.method == "POST":
        file = request.files.get("image")
        blur = request.form.get("blur") == "on"
        if not file or not file.filename:
            return render_template("index.html", error="Selecione uma imagem válida.")
        try:
            image_bytes = file.read()
            result = analyze_image_bytes(
                image_bytes,
                image_name=file.filename,
                blur_faces=blur,
                record_history=True,
            )
            return render_template("index.html", result=result, filename=file.filename)
        except Exception as exc:  # noqa: BLE001
            return render_template("index.html", error=f"Erro ao processar imagem: {exc}")

    return render_template("index.html")


@app.route("/webcam")
def webcam_page():
    """Página de detecção e reconhecimento em tempo real via webcam."""
    return render_template("webcam.html")


@app.route("/register", methods=["GET", "POST"])
def register_page():
    """Página de cadastro de pessoas (por upload de arquivo ou captura da webcam)."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        matricula = request.form.get("matricula", "").strip()
        situacao = request.form.get("situacao", "ativa")
        consent = _is_checked(request.form.get("consent"))
        file = request.files.get("image")
        if not name or not file or not file.filename:
            return render_template(
                "register.html",
                error="Informe o nome e selecione uma foto.",
                situacoes=SITUACOES,
            )
        try:
            res = register_person_from_bytes(
                name, file.read(), matricula=matricula, situacao=situacao, consent=consent
            )
            if not res.get("success"):
                return render_template(
                    "register.html", error=res.get("error"), situacoes=SITUACOES
                )
            return render_template("register.html", registered=res, situacoes=SITUACOES)
        except Exception as exc:  # noqa: BLE001
            return render_template(
                "register.html", error=f"Erro no cadastro: {exc}", situacoes=SITUACOES
            )

    return render_template("register.html", situacoes=SITUACOES)


@app.route("/people")
def people_page():
    """Página de listagem/exclusão de pessoas cadastradas e histórico de detecções."""
    people = get_all_people()
    detections = list_detections(limit=30)
    return render_template(
        "people.html", people=people, detections=detections, situacoes=SITUACOES
    )


# ---------------------------------------------------------------------------
# Endpoints REST / JSON (utilizados pela Webcam e integrações externas)
# ---------------------------------------------------------------------------


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Analisa um quadro/imagem enviado via POST multipart e retorna JSON."""
    file = request.files.get("image")
    if not file:
        return jsonify({"success": False, "error": "Nenhuma imagem enviada."}), 400

    record = request.form.get("record", "false").lower() == "true"
    blur = request.form.get("blur", "false").lower() == "true"
    try:
        res = analyze_image_bytes(
            file.read(),
            image_name=file.filename or "webcam_frame.jpg",
            blur_faces=blur,
            record_history=record,
        )
        return jsonify({"success": True, **res})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/register", methods=["POST"])
def api_register():
    """Cadastra uma pessoa via API (usado pela captura da webcam e clientes REST).

    Campos: name, matricula, image (obrigatórios); consent (`true` = aceitou o
    termo, obrigatório); situacao (padrão `ativa`, só `ativa` pode ser cadastrada).
    """
    name = request.form.get("name", "").strip()
    file = request.files.get("image")
    if not name or not file:
        return (
            jsonify({"success": False, "error": "Informe o nome e envie a imagem."}),
            400,
        )
    try:
        res = register_person_from_bytes(
            name,
            file.read(),
            matricula=request.form.get("matricula", "").strip(),
            situacao=request.form.get("situacao", "ativa"),
            consent=_is_checked(request.form.get("consent")),
        )
        status = 200 if res.get("success") else 400
        return jsonify(res), status
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/people", methods=["GET"])
def api_list_people():
    """Retorna a lista de pessoas cadastradas em formato JSON."""
    people = get_all_people()
    sanitized = [
        {
            "id": p["id"],
            "name": p["name"],
            "created_at": p["created_at"],
            "matricula": p["matricula"],
            "situacao": p["situacao"],
            "consent_at": p["consent_at"],
            "photo_b64": p["photo_b64"],
        }
        for p in people
    ]
    return jsonify({"people": sanitized, "count": len(sanitized)})


@app.route("/api/people/<int:person_id>", methods=["DELETE", "POST"])
def api_delete_person(person_id: int):
    """Remove uma pessoa cadastrada pelo seu ID (banco e foto em disco)."""
    removed = delete_person_with_files(person_id)
    return jsonify({"success": removed, "deleted_id": person_id})


@app.route("/api/people/<int:person_id>/situacao", methods=["POST", "PATCH"])
def api_update_situacao(person_id: int):
    """Altera a situação da matrícula (ativa, trancada, cancelada ou formada)."""
    payload = request.get_json(silent=True) or request.form
    situacao = (payload.get("situacao") or "").strip().lower()
    if situacao not in SITUACOES:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Situação inválida. Use: {', '.join(SITUACOES)}.",
                }
            ),
            400,
        )
    updated = update_situacao(person_id, situacao)
    status = 200 if updated else 404
    return jsonify({"success": updated, "id": person_id, "situacao": situacao}), status


@app.route("/api/detections", methods=["GET"])
def api_list_detections():
    """Retorna o histórico recente de detecções em formato JSON."""
    limit = int(request.args.get("limit", "50"))
    rows = list_detections(limit=limit)
    return jsonify({"detections": rows, "count": len(rows)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"\n========================================================")
    print(f" Reconhecimento Facial Simplificado iniciado com sucesso!")
    print(f" Acesse no navegador: http://localhost:{port}")
    print(f"========================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
