import os
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from passlib.context import CryptContext
from jose import jwt
import markdown2

from search_engine import retrieve_relevant_context
from gpt_utils import generate_answer
from db_logs import registrar_log
from logs_route import router as logs_router
from auth_utils import get_current_user
from prompt_router import inferir_tipo_de_prompt
from healthplan_log import registrar_healthplan

from sqlalchemy import create_engine, text
from io import StringIO
import csv

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.include_router(logs_router)

# ============================================================
# AUTENTICAÇÃO (VERSÃO 100% COMPATÍVEL COM PYTHON 3.10)
# ============================================================

SECRET_KEY = "segredo-teste"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 🔥 Usando SHA256_CRYPT — SEM BCRYPT (bcrypt NÃO funciona no Render Python 3.13)
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# Usuário de teste
fake_users = {
    "aluno1": pwd_context.hash("N4nd@M4c#2025")
}

def authenticate_user(username: str, password: str):
    """Verifica usuário/senha usando SHA256_CRYPT."""
    if username not in fake_users:
        return False
    return pwd_context.verify(password, fake_users[username])

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ============================================================
# ROTAS DE LOGIN
# ============================================================

@app.get("/")
def root():
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if not authenticate_user(username, password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuário ou senha inválidos."}
        )

    token = create_access_token({"sub": username})
    response = RedirectResponse(url="/chat", status_code=302)
    response.set_cookie(key="token", value=token, httponly=True)
    return response

# ============================================================
# CHAT
# ============================================================

@app.get("/chat", response_class=HTMLResponse)
def chat_get(request: Request, user: str = Depends(get_current_user)):
    return templates.TemplateResponse("chat.html", {"request": request, "history": []})

@app.post("/ask", response_class=HTMLResponse)
async def ask(
    request: Request,
    question: Optional[str] = Form(None),
    user: str = Depends(get_current_user)
):
    if not question:
        return RedirectResponse(url="/chat", status_code=302)

    form_data = await request.form()
    history_str = form_data.get("history", "[]")

    try:
        history = json.loads(history_str)
    except:
        history = []

    context = retrieve_relevant_context(question)
    tipo_de_prompt = inferir_tipo_de_prompt(question)

    # Registra Health Plan
    if tipo_de_prompt == "health_plan":
        registrar_healthplan(pergunta=question, usuario=user)

    chip_opcoes = [
        "Ver Exemplo de Plano", "Modelo no Canva", "Modelo PDF", "Novo Tema",
        "Preciso de exemplo", "Exemplo para Acne", "Tratamento Oral", "Cuidados Diários"
    ]
    is_chip = question.strip() in chip_opcoes
    is_first_question = (not history) and not is_chip

    # Gera resposta
    answer_markdown, quick_replies, progresso = generate_answer(
        question=question,
        context=context,
        history=history,
        tipo_de_prompt=tipo_de_prompt,
        is_first_question=is_first_question
    )

    answer_html = markdown2.markdown(answer_markdown)

    registrar_log(
        usuario=user,
        pergunta=question,
        resposta=answer_html,
        contexto=context,
        tipo_prompt=tipo_de_prompt
    )

    chip = question.strip() if question.strip() in chip_opcoes else None

    new_history = history + [{
        "user": question,
        "ai": answer_html,
        "quick_replies": quick_replies,
        "chip": chip,
        "progresso": progresso
    }]

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "history": new_history
    })

# ============================================================
# DASHBOARD
# ============================================================

DATABASE_URL = "sqlite:///logs.db"
engine = create_engine(DATABASE_URL)

def get_current_admin_user():
    return True

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(get_current_admin_user)):
    filtro_usuario = request.query_params.get("usuario", "")
    filtro_modulo = request.query_params.get("modulo", "")
    filtro_palavra = request.query_params.get("palavra", "")
    filtro_data_inicio = request.query_params.get("data_inicio", "")
    filtro_data_fim = request.query_params.get("data_fim", "")

    sql = "SELECT * FROM logs WHERE 1=1"
    params = {}

    if filtro_usuario:
        sql += " AND usuario LIKE :usuario"
        params["usuario"] = f"%{filtro_usuario}%"

    if filtro_modulo:
        sql += " AND modulo = :modulo"
        params["modulo"] = filtro_modulo

    if filtro_palavra:
        sql += " AND (pergunta LIKE :palavra OR resposta LIKE :palavra)"
        params["palavra"] = f"%{filtro_palavra}%"

    if filtro_data_inicio:
        sql += " AND data >= :data_inicio"
        params["data_inicio"] = filtro_data_inicio

    if filtro_data_fim:
        sql += " AND data <= :data_fim"
        params["data_fim"] = filtro_data_fim

    sql += " ORDER BY data DESC"

    with engine.connect() as conn:
        logs = conn.execute(text(sql), params).fetchall()
        total_usuarios = conn.execute(text("SELECT COUNT(DISTINCT usuario) FROM logs")).scalar()
        total_perguntas = conn.execute(text("SELECT COUNT(*) FROM logs")).scalar()
        perguntas_por_dia = conn.execute(text("""
            SELECT strftime('%Y-%m-%d', data) as dia, COUNT(*) as total
            FROM logs GROUP BY dia ORDER BY dia DESC
        """)).fetchall()
        perguntas_mais_frequentes = conn.execute(text("""
            SELECT pergunta, COUNT(*) as total
            FROM logs GROUP BY pergunta
            ORDER BY total DESC LIMIT 5
        """)).fetchall()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "logs": logs,
        "total_usuarios": total_usuarios,
        "total_perguntas": total_perguntas,
        "perguntas_por_dia": perguntas_por_dia,
        "perguntas_mais_frequentes": perguntas_mais_frequentes,
        "filtro_usuario": filtro_usuario,
        "filtro_modulo": filtro_modulo,
        "filtro_palavra": filtro_palavra,
        "filtro_data_inicio": filtro_data_inicio,
        "filtro_data_fim": filtro_data_fim
    })

@app.get("/dashboard/export", response_class=StreamingResponse)
async def dashboard_export(request: Request, user=Depends(get_current_admin_user)):

    filtro_usuario = request.query_params.get("usuario", "")
    filtro_modulo = request.query_params.get("modulo", "")
    filtro_palavra = request.query_params.get("palavra", "")
    filtro_data_inicio = request.query_params.get("data_inicio", "")
    filtro_data_fim = request.query_params.get("data_fim", "")

    sql = "SELECT * FROM logs WHERE 1=1"
    params = {}

    if filtro_usuario:
        sql += " AND usuario LIKE :usuario"
        params["usuario"] = f"%{filtro_usuario}%"

    if filtro_modulo:
        sql += " AND modulo = :modulo"
        params["modulo"] = filtro_modulo

    if filtro_palavra:
        sql += " AND (pergunta LIKE :palavra OR resposta LIKE :palavra)"
        params["palavra"] = f"%{filtro_palavra}%"

    if filtro_data_inicio:
        sql += " AND data >= :data_inicio"
        params["data_inicio"] = filtro_data_inicio

    if filtro_data_fim:
        sql += " AND data <= :data_fim"
        params["data_fim"] = filtro_data_fim

    sql += " ORDER BY data DESC"

    with engine.connect() as conn:
        logs = conn.execute(text(sql), params).fetchall()
        headers = logs[0].keys() if logs else ["usuario","modulo","aula","pergunta","resposta","data"]

    def iter_csv():
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(headers)
        for row in logs:
            cw.writerow([row[c] for c in headers])
        yield si.getvalue()

    return StreamingResponse(iter_csv(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=logs_export.csv"})
