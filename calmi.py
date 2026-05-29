from flask import Flask, request, jsonify, render_template_string, session, Response
from groq import Groq
import psycopg2
import psycopg2.extras
import os
import base64
import json
import re
import urllib.request
import urllib.error
import html as html_lib
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "calmi-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # limite de 12MB para imagens/áudios

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ==========================================
# BANCO SUPABASE / POSTGRESQL
# ==========================================

def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        cursor_factory=psycopg2.extras.DictCursor
    )


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL
    )
    """)

    try:
        cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS foto_perfil TEXT")
    except Exception:
        pass


    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversas (
        id TEXT PRIMARY KEY,
        usuario TEXT NOT NULL,
        nome TEXT NOT NULL
    )
    """)

    try:
        cur.execute("ALTER TABLE conversas ADD COLUMN IF NOT EXISTS fixada BOOLEAN DEFAULT FALSE")
    except Exception:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mensagens (
        id SERIAL PRIMARY KEY,
        conversa_id TEXT NOT NULL,
        tipo TEXT NOT NULL,
        texto TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mensagens_memoria (
        id SERIAL PRIMARY KEY,
        conversa_id TEXT,
        usuario TEXT NOT NULL,
        data TEXT,
        horario TEXT,
        remetente TEXT,
        conteudo TEXT,
        nivel_emocional TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notas_usuario (
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL,
        titulo TEXT,
        conteudo TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS humor_diario (
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL,
        humor TEXT NOT NULL,
        observacao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lembretes_usuario (
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL,
        texto TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


init_db()


# ==========================================
# MEMÓRIA
# ==========================================

def buscar_historico(usuario, limite=20):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT remetente, conteudo, nivel_emocional, data, horario
        FROM mensagens_memoria
        WHERE usuario=%s
        ORDER BY id DESC
        LIMIT %s
    """, (usuario, limite))

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return dados


def salvar_mensagem(conversa_id, usuario, remetente, conteudo, nivel_emocional):
    agora = datetime.now()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO mensagens_memoria
        (conversa_id, usuario, data, horario, remetente, conteudo, nivel_emocional)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        conversa_id,
        usuario,
        agora.strftime("%d/%m/%Y"),
        agora.strftime("%H:%M"),
        remetente,
        conteudo,
        nivel_emocional
    ))

    conn.commit()
    cur.close()
    conn.close()


# ==========================================
# ANÁLISE EMOCIONAL
# ==========================================

def analisar_risco_emocional(texto, historico):
    texto = texto.lower()

    pontos = 0

    leve = [
        "cansado",
        "triste",
        "preocupado",
        "desanimado",
        "estressado"
    ]

    moderado = [
        "ansioso",
        "ansiedade",
        "medo",
        "sozinho",
        "isolado",
        "sem energia",
        "insônia",
        "não consigo dormir"
    ]

    elevado = [
        "não aguento",
        "muito mal",
        "sem saída",
        "colapso",
        "não consigo continuar",
        "sem forças"
    ]

    critico = [
        "não quero mais viver",
        "quero sumir",
        "não vejo saída"
    ]

    for palavra in leve:
        if palavra in texto:
            pontos += 1

    for palavra in moderado:
        if palavra in texto:
            pontos += 2

    for palavra in elevado:
        if palavra in texto:
            pontos += 4

    for palavra in critico:
        if palavra in texto:
            pontos += 8

    historico_texto = " ".join([
        h["conteudo"].lower()
        for h in historico
        if h["remetente"] == "user"
    ])

    repeticoes = [
        "triste",
        "ansioso",
        "sozinho",
        "cansado",
        "sem energia",
        "não consigo dormir"
    ]

    for palavra in repeticoes:
        if historico_texto.count(palavra) >= 3:
            pontos += 2

    if pontos >= 8:
        return "crítico"

    if pontos >= 5:
        return "elevado"

    if pontos >= 2:
        return "moderado"

    return "leve"


def sugerir_profissional(texto, risco):
    texto = texto.lower()

    if risco == "crítico":
        return "Ajuda humana imediata"

    if "ansiedade" in texto or "ansioso" in texto or "medo" in texto:
        return "Psicólogo especializado em ansiedade"

    if "família" in texto or "pai" in texto or "mãe" in texto:
        return "Psicólogo familiar"

    if "escola" in texto or "prova" in texto or "professor" in texto:
        return "Psicólogo escolar ou orientador educacional"

    if "luto" in texto or "perdi" in texto or "morreu" in texto:
        return "Psicólogo especializado em luto"

    return "Psicólogo clínico"


def resumir_contexto(historico):

    if not historico:
        return "Sem histórico emocional anterior."

    textos = [

        h["conteudo"].lower()

        for h in historico

        if h["remetente"] == "user"

    ]

    resumo = ""

    if any(
        "cansado" in texto
        for texto in textos
    ):

        resumo += (
            "O usuário mencionou "
            "cansaço emocional. "
        )

    if any(
        "sozinho" in texto
        for texto in textos
    ):

        resumo += (
            "O usuário mencionou "
            "solidão ou isolamento. "
        )

    if any(
        "ansioso" in texto
        or "ansiedade" in texto

        for texto in textos
    ):

        resumo += (
            "O usuário mencionou "
            "ansiedade ou preocupação. "
        )

    if any(
        "não consigo dormir" in texto
        or "insônia" in texto

        for texto in textos
    ):

        resumo += (
            "O usuário mencionou "
            "dificuldade para dormir. "
        )

    return (
        resumo
        if resumo
        else "Histórico sem padrão emocional forte."
    )


# ==========================================
# NOTAS, HUMOR E DASHBOARD
# ==========================================

def buscar_notas(usuario, limite=10):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, titulo, conteudo, criado_em
        FROM notas_usuario
        WHERE usuario=%s
        ORDER BY id DESC
        LIMIT %s
        """,
        (usuario, limite)
    )
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return dados


def resumir_notas(usuario):
    notas = buscar_notas(usuario, 8)

    if not notas:
        return "Sem anotações importantes cadastradas."

    resumo = []

    for nota in notas:
        titulo = nota["titulo"] or "Anotação"
        conteudo = nota["conteudo"]
        resumo.append(f"- {titulo}: {conteudo}")

    return "\n".join(resumo)


def salvar_humor(usuario, humor, observacao=""):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO humor_diario(usuario, humor, observacao)
        VALUES (%s,%s,%s)
        """,
        (usuario, humor, observacao)
    )
    conn.commit()
    cur.close()
    conn.close()


def buscar_dashboard(usuario):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT humor, observacao, criado_em
        FROM humor_diario
        WHERE usuario=%s
        ORDER BY id DESC
        LIMIT 7
        """,
        (usuario,)
    )
    humores = cur.fetchall()

    cur.execute(
        """
        SELECT nivel_emocional, COUNT(*) AS total
        FROM mensagens_memoria
        WHERE usuario=%s AND remetente='user'
        GROUP BY nivel_emocional
        """,
        (usuario,)
    )
    riscos = cur.fetchall()

    cur.close()
    conn.close()

    return humores, riscos


def sugestao_profissional_detalhada(texto, risco):
    texto_lower = texto.lower()

    if risco == "crítico":
        if "ansiedade" in texto_lower or "pânico" in texto_lower or "medo" in texto_lower:
            profissional = "psicólogo especializado em ansiedade/crise e apoio humano imediato"
        elif "família" in texto_lower or "pai" in texto_lower or "mãe" in texto_lower:
            profissional = "psicólogo familiar ou psicólogo clínico com experiência em crise emocional"
        elif "luto" in texto_lower or "perdi" in texto_lower or "morreu" in texto_lower:
            profissional = "psicólogo especializado em luto e apoio humano imediato"
        else:
            profissional = "psicólogo clínico especializado em crise emocional"

        return (
            f"Pode ser importante procurar {profissional}. "
            "Se existir risco imediato, procure agora um responsável, alguém de confiança, "
            "um serviço local de emergência ou o CVV 188."
        )

    if risco == "elevado":
        return f"Pode ser útil conversar com {sugerir_profissional(texto, risco)}. Você merece apoio de verdade."

    return f"Pode ser útil conversar com {sugerir_profissional(texto, risco)} se isso continuar pesando."


HTML = """

<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Calmi AI</title>

<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#2563EB">


<style>
*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

:root{
    --roxo:#4F46E5;
    --roxo2:#7C3AED;
    --azul:#06B6D4;
    --fundo:#0F172A;
}

body{
    font-family:Arial, Helvetica, sans-serif;
    height:100vh;
    overflow:hidden;
    background:
        radial-gradient(circle at top left, rgba(124,58,237,.55), transparent 35%),
        radial-gradient(circle at bottom right, rgba(6,182,212,.45), transparent 35%),
        linear-gradient(135deg,#0F172A,#111827);
}

.container{
    height:100vh;
    width:100%;
    display:flex;
    gap:18px;
    padding:18px;
}

.sidebar{
    width:310px;
    background:rgba(17,24,39,.9);
    color:white;
    border-radius:28px;
    padding:18px;
    display:flex;
    flex-direction:column;
    box-shadow:0 25px 70px rgba(0,0,0,.35);
}

.logo{
    text-align:center;
    padding:18px;
    border-bottom:1px solid rgba(255,255,255,.1);
}

.logo h1{
    font-size:46px;
    background:linear-gradient(135deg,#60A5FA,#A78BFA,#22D3EE);
    -webkit-background-clip:text;
    color:transparent;
}

.logo p{
    color:#CBD5E1;
    font-size:14px;
    margin-top:5px;
}

.profile{
    margin-top:18px;
    display:flex;
    align-items:center;
    gap:12px;
    background:rgba(31,41,55,.9);
    padding:13px;
    border-radius:20px;
}

.avatar{
    width:54px;
    height:54px;
    border-radius:50%;
    background:linear-gradient(135deg,var(--roxo),var(--azul));
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:bold;
    font-size:22px;
    overflow:hidden;
    cursor:pointer;
    flex-shrink:0;
}

.avatar img{
    width:100%;
    height:100%;
    object-fit:cover;
}

.avatar:hover{
    outline:2px solid rgba(96,165,250,.8);
}

.avatar.avatar-pop{
    animation:avatarPop .45s ease;
}

@keyframes avatarPop{
    0%{transform:scale(.88); opacity:.65;}
    60%{transform:scale(1.08); opacity:1;}
    100%{transform:scale(1);}
}

.profile-actions{
    position:fixed;
    background:#111827;
    color:white;
    border:1px solid rgba(255,255,255,.12);
    border-radius:16px;
    padding:8px;
    display:none;
    flex-direction:column;
    gap:6px;
    z-index:3000;
    box-shadow:0 18px 50px rgba(0,0,0,.35);
    min-width:170px;
}

.profile-actions.open{
    display:flex;
}

.profile-actions button{
    border:none;
    border-radius:12px;
    padding:11px 12px;
    cursor:pointer;
    color:white;
    font-weight:bold;
    text-align:left;
    background:#1F2937;
}

.profile-actions button:hover{
    background:#374151;
}

.profile-actions .danger{
    background:#7F1D1D;
}

.profile-actions .danger:hover{
    background:#991B1B;
}

.mobile-profile{
    display:none;
}

.status{
    color:#86EFAC;
    font-size:12px;
    margin-top:4px;
}

.new-chat button,
.logout-btn{
    width:100%;
    margin-top:14px;
    padding:14px;
    border:none;
    border-radius:16px;
    color:white;
    font-weight:bold;
    cursor:pointer;
}

.new-chat button{
    background:linear-gradient(135deg,var(--roxo),var(--roxo2));
}

.logout-btn{
    background:#EF4444;
}

.chats{
    flex:1;
    overflow-y:auto;
    margin-top:20px;
}

.chat-item{
    background:rgba(31,41,55,.95);
    color:#E5E7EB;
    padding:13px 42px 13px 13px;
    border-radius:16px;
    margin-bottom:10px;
    cursor:pointer;
    position:relative;
    font-size:14px;
}

.delete-btn{
    position:absolute;
    right:10px;
    top:50%;
    transform:translateY(-50%);
    width:24px;
    height:24px;
    border:none;
    border-radius:50%;
    background:#EF4444;
    color:white;
    cursor:pointer;
}

.main{
    flex:1;
    display:flex;
    flex-direction:column;
    background:rgba(248,250,252,.95);
    border-radius:28px;
    overflow:hidden;
    box-shadow:0 25px 70px rgba(0,0,0,.25);
}

.top{
    padding:20px 24px;
    background:rgba(255,255,255,.95);
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.top h2{
    color:var(--roxo);
}

.subtitle{
    color:#64748B;
    font-size:13px;
    margin-top:4px;
}

.top-actions{
    display:flex;
    gap:8px;
}

.tema-btn,
.mobile-menu-btn{
    border:none;
    padding:11px 14px;
    border-radius:14px;
    background:#111827;
    color:white;
    cursor:pointer;
}

.mobile-menu-btn{
    display:none;
    background:linear-gradient(135deg,var(--roxo),var(--azul));
}

.mobile-menu{
    display:none;
}

.chat{
    flex:1;
    overflow-y:auto;
    padding:24px;
}

.message{
    max-width:75%;
    padding:15px;
    border-radius:18px;
    margin-bottom:14px;
    line-height:1.5;
    word-wrap:break-word;
}

.preview-img{
    max-width:230px;
    max-height:230px;
    border-radius:14px;
    display:block;
    margin-top:8px;
}

.attach-btn{
    width:48px;
    height:48px;
    display:flex;
    align-items:center;
    justify-content:center;
    border:none;
    border-radius:16px;
    background:linear-gradient(135deg,var(--roxo),var(--azul)) !important;
    color:white;
    cursor:pointer;
    flex-shrink:0;
    padding:0 !important;
    box-shadow:0 8px 22px rgba(79,70,229,.25);
    transition:.22s ease;
}

.attach-btn:hover{
    transform:translateY(-2px) scale(1.03);
    box-shadow:0 12px 28px rgba(6,182,212,.28);
}

.attach-btn svg{
    width:22px;
    height:22px;
}

.attach-btn.recording{
    background:linear-gradient(135deg,#EF4444,#F97316) !important;
    animation:pulseMic 1s infinite;
}

@keyframes pulseMic{
    0%{transform:scale(1)}
    50%{transform:scale(1.06)}
    100%{transform:scale(1)}
}

.user{
    margin-left:auto;
    color:white;
    background:linear-gradient(135deg,var(--roxo),var(--roxo2));
}

.bot{
    background:white;
    color:#111827;
    box-shadow:0 10px 25px rgba(0,0,0,.08);
}

.typing{
    display:flex;
    gap:5px;
}

.dot{
    width:7px;
    height:7px;
    border-radius:50%;
    background:#7C3AED;
    animation:dot 1s infinite ease-in-out;
}

.dot:nth-child(2){
    animation-delay:.15s;
}

.dot:nth-child(3){
    animation-delay:.3s;
}

@keyframes dot{
    0%,80%,100%{
        opacity:.4;
        transform:scale(.7);
    }

    40%{
        opacity:1;
        transform:scale(1);
    }
}

.input-area{
    display:flex;
    gap:10px;
    padding:14px;
    background:white;
    border-top:1px solid rgba(0,0,0,.06);
}

.input-area input{
    flex:1;
    min-width:0;
    padding:14px;
    border:none;
    border-radius:15px;
    background:#F1F5F9;
    font-size:15px;
    outline:none;
}

.input-area button{
    border:none;
    padding:14px 22px;
    border-radius:15px;
    background:linear-gradient(135deg,var(--azul),var(--roxo));
    color:white;
    font-weight:bold;
    cursor:pointer;
    white-space:nowrap;
}

.dark .main{
    background:#0F172A;
}

.dark .top,
.dark .input-area{
    background:#111827;
    color:white;
}

.dark .bot{
    background:#1F2937;
    color:white;
}

.dark .input-area input{
    background:#1F2937;
    color:white;
}

.login{
    position:fixed;
    inset:0;
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:999;
    background:
        radial-gradient(circle at top left,#7C3AED,transparent 35%),
        radial-gradient(circle at bottom right,#06B6D4,transparent 35%),
        #0F172A;
}

.login-box{
    width:430px;
    background:rgba(255,255,255,.95);
    padding:40px;
    border-radius:30px;
    text-align:center;
    box-shadow:0 35px 90px rgba(0,0,0,.35);
}

.login-box h1{
    font-size:56px;
    background:linear-gradient(135deg,var(--roxo),var(--roxo2),var(--azul));
    -webkit-background-clip:text;
    color:transparent;
}

.login-box p{
    color:#64748B;
    margin-bottom:24px;
}

.tabs{
    display:flex;
    gap:10px;
    margin-bottom:20px;
}

.tab{
    flex:1;
    padding:12px;
    border:none;
    border-radius:12px;
    cursor:pointer;
    font-weight:bold;
    background:#E5E7EB;
    color:#111827;
}

.activeTab{
    background:linear-gradient(135deg,var(--roxo),var(--azul));
    color:white;
}

.login-box input{
    width:100%;
    padding:15px;
    border:none;
    background:#F1F5F9;
    border-radius:16px;
    margin-top:12px;
    outline:none;
}

.login-btn{
    width:100%;
    margin-top:18px;
    padding:15px;
    border:none;
    border-radius:16px;
    background:linear-gradient(135deg,var(--roxo),var(--azul));
    color:white;
    cursor:pointer;
    font-weight:bold;
}

.error{
    margin-top:12px;
    color:#EF4444;
    font-size:14px;
    min-height:20px;
}

.loading{
    opacity:.7;
    pointer-events:none;
}


.audio-recorder{
    display:none;
    align-items:center;
    gap:12px;
    padding:12px 14px;
    background:rgba(255,255,255,.96);
    border-top:1px solid rgba(0,0,0,.06);
    box-shadow:0 -8px 22px rgba(0,0,0,.06);
}

.audio-recorder.show{
    display:flex;
}

.rec-status{
    display:flex;
    align-items:center;
    gap:8px;
    font-weight:bold;
    color:#111827;
    min-width:92px;
}

.rec-dot{
    width:10px;
    height:10px;
    border-radius:50%;
    background:#EF4444;
    animation:recPulse 1s infinite;
}

@keyframes recPulse{
    0%{opacity:.35; transform:scale(.9)}
    50%{opacity:1; transform:scale(1.15)}
    100%{opacity:.35; transform:scale(.9)}
}

.wave-bars{
    flex:1;
    height:34px;
    display:flex;
    align-items:center;
    gap:4px;
    padding:0 6px;
    border-radius:18px;
    background:#F1F5F9;
    overflow:hidden;
}

.wave-bars span{
    display:block;
    width:4px;
    height:10px;
    border-radius:10px;
    background:linear-gradient(180deg,var(--roxo),var(--azul));
    animation:waveMove .8s infinite ease-in-out;
}

.wave-bars span:nth-child(2){animation-delay:.08s}
.wave-bars span:nth-child(3){animation-delay:.16s}
.wave-bars span:nth-child(4){animation-delay:.24s}
.wave-bars span:nth-child(5){animation-delay:.32s}
.wave-bars span:nth-child(6){animation-delay:.4s}
.wave-bars span:nth-child(7){animation-delay:.48s}
.wave-bars span:nth-child(8){animation-delay:.56s}
.wave-bars span:nth-child(9){animation-delay:.64s}
.wave-bars span:nth-child(10){animation-delay:.72s}

@keyframes waveMove{
    0%,100%{height:8px}
    50%{height:28px}
}

.rec-action{
    border:none;
    width:42px;
    height:42px;
    border-radius:14px;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    color:white;
    font-weight:bold;
    flex-shrink:0;
}

.stop-rec{
    background:#EF4444;
}

.cancel-rec{
    background:#64748B;
}

.send-rec{
    background:linear-gradient(135deg,var(--azul),var(--roxo));
}

.audio-preview{
    display:flex;
    flex:1;
    align-items:center;
    gap:10px;
}

.audio-preview audio{
    width:100%;
    max-height:40px;
}

/* CARD DE ÁUDIO NO CHAT */
.audio-card{
    display:flex;
    align-items:center;
    gap:12px;
    padding:12px;
    margin-top:6px;
    border-radius:18px;
    background:rgba(255,255,255,.18);
    border:1px solid rgba(255,255,255,.18);
    max-width:340px;
}

.audio-icon{
    width:44px;
    height:44px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    flex-shrink:0;
    background:rgba(255,255,255,.22);
    color:white;
    box-shadow:0 8px 22px rgba(0,0,0,.18);
}

.audio-icon svg{
    width:22px;
    height:22px;
}

.audio-info{
    flex:1;
    min-width:0;
}

.audio-title{
    font-weight:bold;
    font-size:13px;
    margin-bottom:6px;
    opacity:.95;
}

.chat-audio{
    width:100%;
    max-width:245px;
    height:34px;
    display:block;
}

.audio-transcription{
    margin-top:10px;
    padding:10px 12px;
    border-radius:14px;
    background:rgba(255,255,255,.16);
    font-size:13px;
    line-height:1.4;
}

.bot .audio-card{
    background:#F1F5F9;
    border:1px solid rgba(15,23,42,.06);
}

.bot .audio-icon{
    background:linear-gradient(135deg,var(--roxo),var(--azul));
}

.bot .audio-title{
    color:#111827;
}

.dark .bot .audio-card{
    background:#111827;
    border:1px solid rgba(255,255,255,.08);
}

.dark .bot .audio-title{
    color:white;
}

.dark .audio-recorder{
    background:#111827;
    border-top:1px solid rgba(255,255,255,.08);
}

.dark .rec-status{
    color:white;
}

.dark .wave-bars{
    background:#1F2937;
}

@media(max-width:800px){
    body{
        overflow:hidden;
    }

    .container{
        height:100vh;
        display:block;
        padding:0;
    }

    .sidebar{
        display:none;
    }

    .main{
        width:100%;
        height:100vh;
        border-radius:0;
    }

    .top{
        padding:14px;
        gap:10px;
    }

    .top h2{
        font-size:19px;
    }

    .subtitle{
        font-size:12px;
    }

    .mobile-menu-btn{
        display:block;
    }

    .mobile-menu{
        display:flex;
        flex-direction:column;
        position:fixed;
        top:0;
        left:-86%;
        width:84%;
        height:100vh;
        background:#111827;
        color:white;
        z-index:1000;
        padding:18px;
        transition:.3s ease;
        box-shadow:20px 0 60px rgba(0,0,0,.45);
    }

    .mobile-menu.open{
        left:0;
    }

    .mobile-menu-header{
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:18px;
    }

    .mobile-menu-header h2{
        color:#60A5FA;
    }

    .mobile-menu-header button{
        border:none;
        width:34px;
        height:34px;
        border-radius:50%;
        background:#EF4444;
        color:white;
        cursor:pointer;
    }

    .mobile-profile{
        display:flex;
        align-items:center;
        gap:12px;
        padding:13px;
        border-radius:18px;
        background:rgba(31,41,55,.9);
        margin-bottom:16px;
    }

    .mobile-profile .avatar{
        width:62px;
        height:62px;
    }

    .mobile-profile small{
        color:#CBD5E1;
        display:block;
        margin-top:3px;
    }

    .profile-actions{
        left:18px !important;
        right:18px !important;
        top:auto !important;
        bottom:18px !important;
        min-width:0;
    }

    .mobile-new-chat{
        width:100%;
        padding:14px;
        border:none;
        border-radius:14px;
        background:linear-gradient(135deg,var(--roxo),var(--azul));
        color:white;
        font-weight:bold;
        margin-bottom:14px;
        cursor:pointer;
    }

    .chat{
        padding:14px;
        padding-bottom:86px;
    }

    .message{
        max-width:90%;
        font-size:14px;
        padding:13px;
        border-radius:16px;
    }

    .preview-img{
        max-width:180px;
        max-height:180px;
    }

    .input-area{
        position:fixed;
        bottom:0;
        left:0;
        right:0;
        z-index:60;
        padding:10px;
        gap:8px;
        background:white;
        box-shadow:0 -8px 25px rgba(0,0,0,.12);
    }

    .dark .input-area{
        background:#111827;
    }

    .input-area input{
        padding:13px;
        font-size:14px;
    }

    .input-area button{
        padding:13px 16px;
        font-size:14px;
    }

    .input-area .attach-btn{
        width:46px;
        height:46px;
        padding:0 !important;
        border-radius:15px;
    }


    .audio-recorder{
        position:fixed;
        left:0;
        right:0;
        bottom:68px;
        z-index:61;
        padding:10px;
        gap:8px;
    }

    .rec-status{
        min-width:76px;
        font-size:13px;
    }

    .wave-bars{
        height:32px;
    }

    .rec-action{
        width:38px;
        height:38px;
        border-radius:12px;
    }

    .login-box{
        width:90%;
        padding:28px;
    }

    .login-box h1{
        font-size:46px;
    }
}


.quick-panel{
    margin-top:14px;
    background:rgba(31,41,55,.88);
    border-radius:18px;
    padding:12px;
}

.quick-panel h4{
    color:#DBEAFE;
    margin-bottom:8px;
    font-size:14px;
}

.mood-grid,.mode-grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:7px;
}

.mood-grid button,.mode-grid button,.side-action{
    border:none;
    border-radius:12px;
    padding:9px;
    cursor:pointer;
    background:#1F2937;
    color:white;
    font-weight:bold;
}

.mood-grid button:hover,.mode-grid button:hover,.side-action:hover{
    background:#374151;
}

.side-action{
    width:100%;
    margin-top:8px;
    background:linear-gradient(135deg,var(--roxo),var(--azul));
}

.notes-panel,.dashboard-panel{
    display:none;
    position:fixed;
    right:24px;
    top:90px;
    width:380px;
    max-width:calc(100vw - 30px);
    max-height:78vh;
    overflow:auto;
    background:white;
    color:#111827;
    z-index:1200;
    border-radius:24px;
    box-shadow:0 30px 90px rgba(0,0,0,.35);
    padding:18px;
}

.notes-panel.open,.dashboard-panel.open{
    display:block;
}

.panel-head{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:12px;
}

.panel-head button{
    border:none;
    background:#EF4444;
    color:white;
    border-radius:50%;
    width:30px;
    height:30px;
    cursor:pointer;
}

.notes-panel input,.notes-panel textarea,.notes-panel select{
    width:100%;
    margin-top:8px;
    padding:12px;
    border:none;
    border-radius:12px;
    background:#F1F5F9;
    outline:none;
}

.notes-panel textarea{
    min-height:90px;
    resize:vertical;
}

.note-card,.dash-card{
    background:#F8FAFC;
    border-radius:16px;
    padding:12px;
    margin-top:10px;
    border:1px solid #E5E7EB;
}

.note-card button{
    margin-top:8px;
    border:none;
    background:#EF4444;
    color:white;
    padding:7px 10px;
    border-radius:10px;
    cursor:pointer;
}

.speak-btn{
    display:inline-flex;
    align-items:center;
    gap:5px;
    border:none;
    margin-top:10px;
    padding:7px 10px;
    border-radius:10px;
    background:#E0F2FE;
    color:#075985;
    cursor:pointer;
}

@media(max-width:800px){
    .notes-panel,.dashboard-panel{
        left:10px;
        right:10px;
        top:75px;
        width:auto;
        max-height:72vh;
    }
}



/* Melhorias de experiência */
.chat-search{
    width:100%;
    margin-top:14px;
    padding:12px 14px;
    border:none;
    border-radius:14px;
    background:#1F2937;
    color:white;
    outline:none;
}

.chat-search::placeholder{
    color:#94A3B8;
}

.pin-btn{
    position:absolute;
    right:38px;
    top:50%;
    transform:translateY(-50%);
    width:24px;
    height:24px;
    border:none;
    border-radius:50%;
    background:#334155;
    color:white;
    cursor:pointer;
}

.pin-btn.fixed{
    background:#F59E0B;
}

.favorite-btn{
    display:inline-flex;
    align-items:center;
    gap:5px;
    border:none;
    margin-top:8px;
    margin-left:6px;
    padding:7px 10px;
    border-radius:10px;
    background:#FEF3C7;
    color:#92400E;
    cursor:pointer;
}

.favorite-btn.active{
    background:#F59E0B;
    color:white;
}

.speak-btn.listening{
    background:#DBEAFE;
    color:#1D4ED8;
    box-shadow:0 0 0 3px rgba(59,130,246,.12);
}

.speak-waves{
    display:inline-flex;
    align-items:center;
    gap:2px;
    margin-left:4px;
}

.speak-waves span{
    width:3px;
    height:8px;
    border-radius:8px;
    background:#2563EB;
    animation:speakWave .7s infinite ease-in-out;
}

.speak-waves span:nth-child(2){animation-delay:.12s}
.speak-waves span:nth-child(3){animation-delay:.24s}

@keyframes speakWave{
    0%,100%{height:6px; opacity:.5}
    50%{height:14px; opacity:1}
}

.toast{
    position:fixed;
    left:50%;
    bottom:24px;
    transform:translateX(-50%) translateY(20px);
    background:#111827;
    color:white;
    padding:12px 16px;
    border-radius:14px;
    opacity:0;
    pointer-events:none;
    z-index:5000;
    box-shadow:0 18px 50px rgba(0,0,0,.35);
    transition:.25s ease;
    max-width:90vw;
    text-align:center;
}

.toast.show{
    opacity:1;
    transform:translateX(-50%) translateY(0);
}

.input-area textarea{
    flex:1;
    min-width:0;
    max-height:120px;
    padding:14px;
    border:none;
    border-radius:15px;
    background:#F1F5F9;
    font-size:15px;
    outline:none;
    resize:none;
    font-family:Arial, Helvetica, sans-serif;
}

.dark .input-area textarea{
    background:#1F2937;
    color:white;
}

@media(max-width:800px){
    .chat-search{
        margin-bottom:10px;
    }

    .input-area textarea{
        padding:13px;
        font-size:14px;
    }
}


/* LOGO CALMI - SITE / APP */
.brand-logo-card{
    display:flex;
    align-items:center;
    justify-content:center;
    gap:12px;
    width:100%;
}

.brand-logo-mark{
    width:64px;
    height:64px;
    border-radius:22px;
    display:flex;
    align-items:center;
    justify-content:center;
    background:linear-gradient(145deg,rgba(37,99,235,.95),rgba(79,70,229,.85));
    box-shadow:
        0 18px 42px rgba(37,99,235,.35),
        inset 0 1px 0 rgba(255,255,255,.25);
    flex-shrink:0;
    overflow:hidden;
}

.brand-logo-mark svg{
    width:58px;
    height:58px;
    filter:drop-shadow(0 8px 12px rgba(0,0,0,.18));
}

.brand-text{
    display:flex;
    flex-direction:column;
    align-items:flex-start;
    line-height:1.1;
}

.brand-text h1,
.brand-text h2{
    margin:0;
}

.logo .brand-text h1{
    font-size:38px;
}

.brand-text p,
.brand-text span{
    color:#CBD5E1;
    font-size:13px;
    margin-top:6px;
}

.login-brand{
    display:flex;
    flex-direction:column;
    align-items:center;
    gap:12px;
    margin-bottom:16px;
}

.login-brand .brand-logo-mark{
    width:86px;
    height:86px;
    border-radius:28px;
}

.login-brand .brand-logo-mark svg{
    width:76px;
    height:76px;
}

.mobile-brand{
    display:flex;
    align-items:center;
    gap:10px;
}

.mobile-brand .brand-logo-mark{
    width:44px;
    height:44px;
    border-radius:16px;
}

.mobile-brand .brand-logo-mark svg{
    width:40px;
    height:40px;
}

.mobile-brand h2{
    margin:0;
    color:#60A5FA;
}

@media(max-width:800px){
    .brand-logo-card{
        justify-content:flex-start;
    }

    .logo .brand-text h1{
        font-size:34px;
    }

    .brand-logo-mark{
        width:58px;
        height:58px;
        border-radius:20px;
    }

    .brand-logo-mark svg{
        width:52px;
        height:52px;
    }
}

</style>
</head>
<body>

<div class="login" id="login">

    <div class="login-box">

        <div class="login-brand">
            
<div class="brand-logo-mark" aria-hidden="true">
    <svg viewBox="0 0 120 90" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="calmiBlue" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#60A5FA"/>
                <stop offset="100%" stop-color="#2563EB"/>
            </linearGradient>
            <linearGradient id="calmiMint" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#99F6E4"/>
                <stop offset="100%" stop-color="#2DD4BF"/>
            </linearGradient>
        </defs>
        <path d="M46 9C23 9 8 23 8 42c0 13 8 24 21 30l-5 14 18-9c2 .2 4 .3 6 .3 24 0 42-14 42-34S70 9 46 9Z" fill="url(#calmiBlue)"/>
        <path d="M82 30c18 2 30 13 30 29 0 10-6 20-16 25l4 12-15-7c-2 .2-4 .3-6 .3-14 0-26-6-32-16 23-1 41-15 41-34 0-3-.2-6-1-9Z" fill="url(#calmiMint)"/>
        <path d="M31 40c3-7 13-7 16 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
        <path d="M58 40c3-7 13-7 16 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
        <path d="M43 56c8 9 20 9 28 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
    </svg>
</div>

            <div>
                <h1>Calmi</h1>
                <p>Sua IA emocional 💙</p>
            </div>
        </div>

        <div class="tabs">

            <button
                class="tab activeTab"
                id="tabLogin"
                onclick="mudarTab('login')"
            >
                Entrar
            </button>

            <button
                class="tab"
                id="tabCadastro"
                onclick="mudarTab('cadastro')"
            >
                Cadastrar
            </button>

        </div>

        <input
            type="text"
            id="usuario"
            placeholder="Usuário"
        >

        <input
            type="password"
            id="senha"
            placeholder="Senha"
        >

        <div class="error" id="erro"></div>

        <button
            class="login-btn"
            id="botaoLogin"
            onclick="enviarAuth()"
        >
            Entrar
        </button>

    </div>

</div>

<input
    type="file"
    id="fotoPerfilInput"
    accept="image/png,image/jpeg,image/webp"
    style="display:none"
    onchange="alterarFotoPerfil(this)"
>

<div class="profile-actions" id="profileActions">
    <button onclick="selecionarNovaFoto()">📷 Trocar foto</button>
    <button class="danger" onclick="removerFotoPerfil()">🗑️ Remover foto</button>
</div>



<div class="notes-panel" id="notesPanel">
    <div class="panel-head">
        <h3>📝 Anotações importantes</h3>
        <button onclick="toggleNotas()">×</button>
    </div>
    <p style="font-size:13px;color:#64748B">A IA usa essas anotações para entender melhor seu contexto.</p>
    <input id="notaTitulo" placeholder="Título da anotação">
    <textarea id="notaConteudo" placeholder="Ex: Tenho prova sexta, estou preocupado com meu pai, quero melhorar minha ansiedade..."></textarea>
    <button class="side-action" onclick="salvarNota()">Salvar anotação</button>
    <div id="listaNotas"></div>
</div>

<div class="dashboard-panel" id="dashboardPanel">
    <div class="panel-head">
        <h3>📊 Meu emocional</h3>
        <button onclick="toggleDashboard()">×</button>
    </div>
    <div id="dashboardConteudo">Carregando...</div>
</div>

<div class="mobile-menu" id="mobileMenu">

    <div class="mobile-menu-header">

        <div class="mobile-brand">
            
<div class="brand-logo-mark" aria-hidden="true">
    <svg viewBox="0 0 120 90" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="calmiBlue" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#60A5FA"/>
                <stop offset="100%" stop-color="#2563EB"/>
            </linearGradient>
            <linearGradient id="calmiMint" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#99F6E4"/>
                <stop offset="100%" stop-color="#2DD4BF"/>
            </linearGradient>
        </defs>
        <path d="M46 9C23 9 8 23 8 42c0 13 8 24 21 30l-5 14 18-9c2 .2 4 .3 6 .3 24 0 42-14 42-34S70 9 46 9Z" fill="url(#calmiBlue)"/>
        <path d="M82 30c18 2 30 13 30 29 0 10-6 20-16 25l4 12-15-7c-2 .2-4 .3-6 .3-14 0-26-6-32-16 23-1 41-15 41-34 0-3-.2-6-1-9Z" fill="url(#calmiMint)"/>
        <path d="M31 40c3-7 13-7 16 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
        <path d="M58 40c3-7 13-7 16 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
        <path d="M43 56c8 9 20 9 28 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
    </svg>
</div>

            <h2>Calmi</h2>
        </div>

        <button onclick="toggleMenuMobile()">✕</button>

    </div>

    <div class="mobile-profile">
        <div class="avatar" id="avatarMobile" title="Foto de perfil" onclick="abrirMenuFoto(event)">C</div>
        <div>
            <h3 id="nomeUsuarioMobile">Usuário</h3>
            <small>Toque na foto para alterar</small>
            <div class="status">● Online</div>
        </div>
    </div>

    <button
        class="mobile-new-chat"
        onclick="novaConversaMobile()"
    >
        + Nova conversa
    </button>

    <button class="logout-btn" onclick="logout()">
        Sair da conta
    </button>

    <button class="side-action" onclick="toggleNotas(); toggleMenuMobile();">📝 Anotações</button>
    <button class="side-action" onclick="toggleDashboard(); toggleMenuMobile();">📊 Dashboard</button>
    <button class="side-action" onclick="exportarConversa(); toggleMenuMobile();">📄 Exportar conversa</button>
    <button class="side-action" onclick="modoRapido('respiração'); toggleMenuMobile();">🧘 Respirar</button>
    <button class="side-action" onclick="modoRapido('sono'); toggleMenuMobile();">🌙 Dormir melhor</button>

    <br>

    <h3>Histórico</h3>

    <input class="chat-search" id="buscaConversasMobile" placeholder="Buscar conversas..." oninput="filtrarConversas(this.value)">

    <br>

    <div id="listaChatsMobile"></div>

</div>

<div class="container">

    <div class="sidebar">

        <div class="logo">

            <div class="brand-logo-card">
                
<div class="brand-logo-mark" aria-hidden="true">
    <svg viewBox="0 0 120 90" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="calmiBlue" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#60A5FA"/>
                <stop offset="100%" stop-color="#2563EB"/>
            </linearGradient>
            <linearGradient id="calmiMint" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#99F6E4"/>
                <stop offset="100%" stop-color="#2DD4BF"/>
            </linearGradient>
        </defs>
        <path d="M46 9C23 9 8 23 8 42c0 13 8 24 21 30l-5 14 18-9c2 .2 4 .3 6 .3 24 0 42-14 42-34S70 9 46 9Z" fill="url(#calmiBlue)"/>
        <path d="M82 30c18 2 30 13 30 29 0 10-6 20-16 25l4 12-15-7c-2 .2-4 .3-6 .3-14 0-26-6-32-16 23-1 41-15 41-34 0-3-.2-6-1-9Z" fill="url(#calmiMint)"/>
        <path d="M31 40c3-7 13-7 16 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
        <path d="M58 40c3-7 13-7 16 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
        <path d="M43 56c8 9 20 9 28 0" fill="none" stroke="white" stroke-width="7" stroke-linecap="round"/>
    </svg>
</div>

                <div class="brand-text">
                    <h1>Calmi</h1>
                    <p>IA emocional inteligente</p>
                </div>
            </div>

        </div>

        <div class="profile">

            <div class="avatar" id="avatar" title="Foto de perfil" onclick="abrirMenuFoto(event)">C</div>

            <div>

                <h3 id="nomeUsuario">Usuário</h3>

                <div class="status">● Online</div>

            </div>

        </div>

        <div class="new-chat">

            <button onclick="novaConversa()">
                + Nova conversa
            </button>

        </div>

        <input class="chat-search" id="buscaConversas" placeholder="Buscar conversas..." oninput="filtrarConversas(this.value)">

        <button class="logout-btn" onclick="logout()">
            Sair da conta
        </button>

        <div class="quick-panel">
            <h4>Como você está hoje?</h4>
            <div class="mood-grid">
                <button onclick="registrarHumor('😊 Muito bem')">😊</button>
                <button onclick="registrarHumor('🙂 Bem')">🙂</button>
                <button onclick="registrarHumor('😐 Neutro')">😐</button>
                <button onclick="registrarHumor('😔 Mal')">😔</button>
                <button onclick="registrarHumor('😢 Muito mal')">😢</button>
                <button onclick="toggleDashboard()">📊</button>
            </div>
        </div>

        <div class="quick-panel">
            <h4>Ferramentas</h4>
            <button class="side-action" onclick="toggleNotas()">📝 Anotações</button>
            <button class="side-action" onclick="exportarConversa()">📄 Exportar conversa</button>
            <button class="side-action" onclick="modoRapido('respiração')">🧘 Respirar</button>
            <button class="side-action" onclick="modoRapido('sono')">🌙 Dormir melhor</button>
        </div>

        <div class="chats" id="listaChats"></div>

    </div>

    <div class="main">

        <div class="top">

            <div>

                <h2 id="titulo">Nova conversa</h2>

                <div class="subtitle">
                    O Calmi está aqui para te ouvir 💙
                </div>

            </div>

            <div class="top-actions">

                <button
                    class="mobile-menu-btn"
                    onclick="toggleMenuMobile()"
                >
                    ☰
                </button>

                <button class="tema-btn" onclick="toggleTema()">
                    🌙
                </button>

            </div>

        </div>

        <div class="chat" id="chat">

            <div class="message bot">
                Olá 😊 Eu sou o Calmi.<br><br>
                Como você está se sentindo hoje?
            </div>

        </div>


        <div class="audio-recorder" id="audioRecorder">
            <div class="rec-status" id="recStatus">
                <span class="rec-dot"></span>
                <span id="recTimer">00:00</span>
            </div>

            <div class="wave-bars" id="waveBars">
                <span></span><span></span><span></span><span></span><span></span>
                <span></span><span></span><span></span><span></span><span></span>
            </div>

            <div class="audio-preview" id="audioPreview" style="display:none">
                <audio id="audioPreviewPlayer" controls></audio>
            </div>

            <button class="rec-action stop-rec" id="stopAudioBtn" type="button" onclick="pararGravacaoAudio()" title="Parar gravação">■</button>
            <button class="rec-action cancel-rec" id="cancelAudioBtn" type="button" onclick="cancelarAudio()" title="Cancelar">×</button>
            <button class="rec-action send-rec" id="sendAudioBtn" type="button" onclick="enviarAudioPendente()" title="Enviar áudio" style="display:none">➤</button>
        </div>

        <div class="input-area">

            <button class="attach-btn" type="button" title="Enviar imagem" aria-label="Enviar imagem" onclick="document.getElementById('imagemInput').click()">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="5" width="18" height="16" rx="3"></rect>
                    <circle cx="9" cy="11" r="2"></circle>
                    <path d="M21 17l-5.2-5.2a2 2 0 0 0-2.8 0L6 19"></path>
                    <path d="M15 5l1.2-2h2.6L20 5"></path>
                </svg>
            </button>

            <input
                type="file"
                id="imagemInput"
                accept="image/png,image/jpeg,image/webp"
                style="display:none"
                onchange="enviarImagem(this)"
            >

            <button class="attach-btn" id="audioBtn" type="button" title="Gravar áudio" aria-label="Gravar áudio" onclick="alternarGravacaoAudio()">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="22"></line>
                    <line x1="8" y1="22" x2="16" y2="22"></line>
                </svg>
            </button>

            <textarea
                id="mensagem"
                placeholder="Digite sua mensagem..."
                autocomplete="off"
                rows="1"
            ></textarea>

            <button onclick="enviarMensagem()">
                Enviar
            </button>

        </div>

    </div>

</div>

<div class="toast" id="toast"></div>

<script>
let usuarioAtual = "";

function gerarUUID(){
    if(window.crypto && crypto.randomUUID){
        return crypto.randomUUID();
    }

    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function(c){
        let r = Math.random() * 16 | 0;
        let v = c === "x" ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

let conversaAtual = gerarUUID();
let modo = "login";
let mediaRecorder = null;
let audioChunks = [];
let gravandoAudio = false;
let audioStream = null;
let audioTimer = null;
let audioSeconds = 0;
let audioBlobPendente = null;
let audioPreviewUrl = null;
let conversasCache = [];
let filtroAtualConversas = "";


function mostrarToast(texto){
    let toast = document.getElementById("toast");
    if(!toast){ return; }
    toast.innerText = texto;
    toast.classList.add("show");
    clearTimeout(window.toastTimer);
    window.toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 2600);
}

function aplicarTemaAutomatico(){
    try{
        let temaManual = localStorage.getItem("calmiTemaManual");
        if(temaManual === "dark"){
            document.body.classList.add("dark");
            return;
        }
        if(temaManual === "light"){
            document.body.classList.remove("dark");
            return;
        }
        if(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches){
            document.body.classList.add("dark");
        }
    }catch(erro){
        console.log("Tema automático indisponível:", erro);
    }
}

function salvarTemaAtual(){
    localStorage.setItem(
        "calmiTemaManual",
        document.body.classList.contains("dark") ? "dark" : "light"
    );
}

function getConversasFixadas(){
    try{
        return JSON.parse(localStorage.getItem("calmiConversasFixadas") || "[]");
    }catch(e){
        return [];
    }
}

function setConversasFixadas(lista){
    localStorage.setItem("calmiConversasFixadas", JSON.stringify(lista));
}

function conversaEstaFixada(id){
    return getConversasFixadas().includes(id);
}

function alternarFixarConversa(id, event){
    if(event){ event.stopPropagation(); }
    let lista = getConversasFixadas();
    if(lista.includes(id)){
        lista = lista.filter(item => item !== id);
        mostrarToast("Conversa desafixada");
    }else{
        lista.push(id);
        mostrarToast("Conversa fixada");
    }
    setConversasFixadas(lista);
    renderizarListaConversas(conversasCache);
}

function filtrarConversas(valor){
    filtroAtualConversas = (valor || "").toLowerCase();
    let busca = document.getElementById("buscaConversas");
    let buscaMobile = document.getElementById("buscaConversasMobile");
    if(busca && busca.value !== valor){ busca.value = valor; }
    if(buscaMobile && buscaMobile.value !== valor){ buscaMobile.value = valor; }
    renderizarListaConversas(conversasCache);
}

function chaveFavorito(texto){
    return "calmiFav_" + btoa(unescape(encodeURIComponent((texto || "").slice(0, 160))));
}

function adicionarBotaoFavorito(el, texto){
    if(!el || el.querySelector(".favorite-btn")) return;
    let chave = chaveFavorito(texto);
    let ativo = localStorage.getItem(chave) === "1";
    let botao = document.createElement("button");
    botao.className = "favorite-btn" + (ativo ? " active" : "");
    botao.innerHTML = ativo ? "⭐ Favorita" : "☆ Favoritar";
    botao.onclick = () => {
        let agoraAtivo = localStorage.getItem(chave) === "1";
        if(agoraAtivo){
            localStorage.removeItem(chave);
            botao.classList.remove("active");
            botao.innerHTML = "☆ Favoritar";
            mostrarToast("Mensagem removida dos favoritos");
        }else{
            localStorage.setItem(chave, "1");
            botao.classList.add("active");
            botao.innerHTML = "⭐ Favorita";
            mostrarToast("Mensagem favoritada");
        }
    };
    el.appendChild(document.createElement("br"));
    el.appendChild(botao);
}

function mudarTab(tipo){

    modo = tipo;

    document.getElementById("tabLogin").classList.remove("activeTab");
    document.getElementById("tabCadastro").classList.remove("activeTab");

    document.getElementById("erro").innerText = "";

    if(tipo === "login"){

        document.getElementById("tabLogin").classList.add("activeTab");
        document.getElementById("botaoLogin").innerText = "Entrar";

    }else{

        document.getElementById("tabCadastro").classList.add("activeTab");
        document.getElementById("botaoLogin").innerText = "Criar conta";

    }
}

async function enviarAuth(){

    let usuarioInput = document.getElementById("usuario");
    let senhaInput = document.getElementById("senha");
    let erroBox = document.getElementById("erro");
    let botao = document.getElementById("botaoLogin");

    let usuario = usuarioInput ? usuarioInput.value : "";
    let senha = senhaInput ? senhaInput.value : "";

    if(usuario.trim() === "" || senha.trim() === ""){

        if(erroBox){
            erroBox.innerText = "Preencha usuário e senha.";
        }

        return;
    }

    let rota = modo === "login" ? "/login" : "/cadastro";

    try{

        if(botao){
            botao.classList.add("loading");
            botao.disabled = true;
        }

        let resposta = await fetch(rota, {
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            credentials:"same-origin",
            body:JSON.stringify({
                usuario,
                senha
            })
        });

        let dados = await resposta.json();

        if(botao){
            botao.classList.remove("loading");
            botao.disabled = false;
        }

        if(dados.status === "ok"){

            usuarioAtual = dados.usuario || usuario;

            iniciarApp(usuarioAtual);

            return;
        }

        if(erroBox){
            erroBox.innerText = dados.erro || "Erro ao entrar.";
        }

    }catch(erro){

        console.log("Erro login:", erro);

        if(botao){
            botao.classList.remove("loading");
            botao.disabled = false;
        }

        if(erroBox){
            erroBox.innerText = "Erro ao conectar. Tente recarregar a página.";
        }
    }
}

function iniciarApp(usuario){

    try{

        usuarioAtual = usuario;

        let telaLogin = document.getElementById("login");
        if(telaLogin){
            telaLogin.style.display = "none";
        }

        let nomeUsuario = document.getElementById("nomeUsuario");
        if(nomeUsuario){
            nomeUsuario.innerText = usuario;
        }

        let nomeMobile = document.getElementById("nomeUsuarioMobile");
        if(nomeMobile){
            nomeMobile.innerText = usuario;
        }

        atualizarAvatarInicial(usuario);

        carregarFotoPerfil().catch(() => {});
        novaConversa();
        carregarConversas();

    }catch(erro){

        console.log("Erro ao iniciar app:", erro);

        let telaLogin = document.getElementById("login");
        if(telaLogin){
            telaLogin.style.display = "none";
        }
    }
}

function animarAvatar(el){
    if(!el) return;
    el.classList.remove("avatar-pop");
    void el.offsetWidth;
    el.classList.add("avatar-pop");
}

function atualizarAvatarInicial(usuario){

    let letra = (usuario || "C")[0].toUpperCase();
    let avatar = document.getElementById("avatar");
    let avatarMobile = document.getElementById("avatarMobile");

    if(avatar){
        avatar.innerHTML = letra;
        animarAvatar(avatar);
    }

    if(avatarMobile){
        avatarMobile.innerHTML = letra;
        animarAvatar(avatarMobile);
    }
}

function aplicarFotoPerfil(foto){

    let avatar = document.getElementById("avatar");
    let avatarMobile = document.getElementById("avatarMobile");

    if(foto){
        if(avatar){
            avatar.innerHTML = `<img src="${foto}" alt="Foto de perfil">`;
            animarAvatar(avatar);
        }

        if(avatarMobile){
            avatarMobile.innerHTML = `<img src="${foto}" alt="Foto de perfil">`;
            animarAvatar(avatarMobile);
        }
    }else{
        atualizarAvatarInicial(usuarioAtual || "C");
    }
}

function abrirMenuFoto(event){
    event.stopPropagation();

    let menu = document.getElementById("profileActions");

    if(!menu){
        return;
    }

    let rect = event.currentTarget.getBoundingClientRect();

    menu.style.left = Math.min(rect.left, window.innerWidth - 190) + "px";
    menu.style.top = (rect.bottom + 8) + "px";

    menu.classList.toggle("open");
}

function fecharMenuFoto(){
    let menu = document.getElementById("profileActions");

    if(menu){
        menu.classList.remove("open");
    }
}

function selecionarNovaFoto(){
    fecharMenuFoto();
    document.getElementById("fotoPerfilInput").click();
}

async function removerFotoPerfil(){
    fecharMenuFoto();

    let resposta = await fetch("/perfil/remover",{
        method:"POST"
    });

    let dados = await resposta.json();

    if(dados.status === "ok"){
        aplicarFotoPerfil(null);
    }else{
        alert(dados.erro || "Não consegui remover a foto.");
    }
}

document.addEventListener("click", function(e){
    let menu = document.getElementById("profileActions");

    if(menu && !menu.contains(e.target)){
        menu.classList.remove("open");
    }
});

async function carregarFotoPerfil(){

    try{

        let resposta = await fetch("/perfil");
        let dados = await resposta.json();

        if(dados.foto_perfil){
            aplicarFotoPerfil(dados.foto_perfil);
        }else{
            aplicarFotoPerfil(null);
        }

    }catch(erro){
        console.log("Erro ao carregar foto:", erro);
        aplicarFotoPerfil(null);
    }
}

async function alterarFotoPerfil(inputArquivo){

    let arquivo = inputArquivo.files[0];

    if(!arquivo){
        return;
    }

    if(arquivo.size > 2 * 1024 * 1024){
        alert("A foto precisa ter até 2MB.");
        inputArquivo.value = "";
        return;
    }

    let leitor = new FileReader();

    leitor.onload = async function(){

        let fotoBase64 = leitor.result;

        let resposta = await fetch("/perfil",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({foto_perfil:fotoBase64})
        });

        let dados = await resposta.json();

        if(dados.status === "ok"){
            aplicarFotoPerfil(fotoBase64);
        }else{
            alert(dados.erro || "Não consegui salvar a foto.");
        }
    };

    leitor.readAsDataURL(arquivo);
    inputArquivo.value = "";
}

function verificarSessao(){

    fetch("/session", {credentials:"same-origin"})
    .then(res => res.json())
    .then(dados => {

        if(dados.logado){

            iniciarApp(dados.usuario);

        }
    })
    .catch(erro => {
        console.log("Sem sessão ativa:", erro);
    });
}

function logout(){

    fetch("/logout")
    .then(() => {
        location.reload();
    });
}

function toggleTema(){

    document.body.classList.toggle("dark");
    salvarTemaAtual();
    mostrarToast(document.body.classList.contains("dark") ? "Tema escuro ativado" : "Tema claro ativado");
}

function toggleMenuMobile(){

    document.getElementById("mobileMenu").classList.toggle("open");
}

function novaConversa(){

    conversaAtual = gerarUUID();

    document.getElementById("titulo").innerText = "Nova conversa";

    document.getElementById("chat").innerHTML = `
        <div class="message bot">
            Olá 😊 Eu sou o Calmi.<br><br>
            Como você está se sentindo hoje?
        </div>
    `;
}

function novaConversaMobile(){

    novaConversa();

    document.getElementById("mobileMenu").classList.remove("open");
}

async function enviarMensagem(){

    let input = document.getElementById("mensagem");
    let mensagem = input.value;

    if(mensagem.trim() === ""){
        return;
    }

    let chat = document.getElementById("chat");

    chat.innerHTML += `
        <div class="message user">
            ${mensagem}
        </div>
    `;

    adicionarBotaoFavorito(chat.lastElementChild, mensagem);

    input.value = "";
    input.style.height = "auto";

    let botDiv = document.createElement("div");

    botDiv.className = "message bot";

    botDiv.innerHTML = `
        <div style="font-size:13px;color:#64748B;margin-bottom:6px">Calmi está pensando...</div>
        <div class="typing">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;

    chat.appendChild(botDiv);

    chat.scrollTop = chat.scrollHeight;

    let resposta = await fetch("/chat", {
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            conversa:conversaAtual,
            mensagem:mensagem
        })
    });

    let dados = await resposta.json();

    botDiv.innerHTML = "";

    let texto = dados.resposta || "Não consegui responder agora.";
    let i = 0;

    let intervalo = setInterval(() => {

        botDiv.innerHTML += texto[i];

        i++;

        chat.scrollTop = chat.scrollHeight;

        if(i >= texto.length){

            clearInterval(intervalo);
            adicionarBotaoVoz(botDiv, texto);
            adicionarBotaoFavorito(botDiv, texto);
        }

    }, 12);

    carregarConversas();
}


async function enviarImagem(inputArquivo){

    let arquivo = inputArquivo.files[0];

    if(!arquivo){
        return;
    }

    if(arquivo.size > 4 * 1024 * 1024){
        alert("A imagem precisa ter até 4MB.");
        inputArquivo.value = "";
        return;
    }

    let chat = document.getElementById("chat");
    let imagemURL = URL.createObjectURL(arquivo);

    chat.innerHTML += `
        <div class="message user">
            Imagem enviada 📷
            <img class="preview-img" src="${imagemURL}">
        </div>
    `;

    let botDiv = document.createElement("div");
    botDiv.className = "message bot";
    botDiv.innerHTML = `
        <div style="font-size:13px;color:#64748B;margin-bottom:6px">Calmi está pensando...</div>
        <div class="typing">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;

    chat.appendChild(botDiv);
    chat.scrollTop = chat.scrollHeight;

    let formData = new FormData();
    formData.append("conversa", conversaAtual);
    formData.append("imagem", arquivo);

    let resposta = await fetch("/imagem", {
        method:"POST",
        body:formData
    });

    let dados = await resposta.json();

    botDiv.innerHTML = "";

    let texto = dados.resposta || "Não consegui analisar essa imagem agora.";
    let i = 0;

    let intervalo = setInterval(() => {
        botDiv.innerHTML += texto[i];
        i++;
        chat.scrollTop = chat.scrollHeight;

        if(i >= texto.length){
            clearInterval(intervalo);
            adicionarBotaoVoz(botDiv, texto);
            adicionarBotaoFavorito(botDiv, texto);
        }
    }, 12);

    inputArquivo.value = "";
    carregarConversas();
}

function formatarTempo(segundos){
    let min = String(Math.floor(segundos / 60)).padStart(2,"0");
    let sec = String(segundos % 60).padStart(2,"0");
    return `${min}:${sec}`;
}

function mostrarPainelGravacao(){
    document.getElementById("audioRecorder").classList.add("show");
    document.getElementById("recStatus").style.display = "flex";
    document.getElementById("waveBars").style.display = "flex";
    document.getElementById("stopAudioBtn").style.display = "flex";
    document.getElementById("cancelAudioBtn").style.display = "flex";
    document.getElementById("sendAudioBtn").style.display = "none";
    document.getElementById("audioPreview").style.display = "none";
    document.getElementById("recTimer").innerText = "00:00";
}

function mostrarPreviewAudio(){
    document.getElementById("audioRecorder").classList.add("show");
    document.getElementById("recStatus").style.display = "none";
    document.getElementById("waveBars").style.display = "none";
    document.getElementById("stopAudioBtn").style.display = "none";
    document.getElementById("sendAudioBtn").style.display = "flex";
    document.getElementById("cancelAudioBtn").style.display = "flex";
    document.getElementById("audioPreview").style.display = "flex";
}

function esconderPainelAudio(){
    document.getElementById("audioRecorder").classList.remove("show");
}

function iniciarTimerAudio(){
    audioSeconds = 0;
    document.getElementById("recTimer").innerText = "00:00";

    if(audioTimer){
        clearInterval(audioTimer);
    }

    audioTimer = setInterval(() => {
        audioSeconds++;
        document.getElementById("recTimer").innerText = formatarTempo(audioSeconds);
    }, 1000);
}

function pararTimerAudio(){
    if(audioTimer){
        clearInterval(audioTimer);
        audioTimer = null;
    }
}

async function alternarGravacaoAudio(){
    if(gravandoAudio){
        pararGravacaoAudio();
        return;
    }

    let botao = document.getElementById("audioBtn");

    try{
        audioStream = await navigator.mediaDevices.getUserMedia({audio:true});

        audioChunks = [];
        audioBlobPendente = null;

        if(audioPreviewUrl){
            URL.revokeObjectURL(audioPreviewUrl);
            audioPreviewUrl = null;
        }

        mediaRecorder = new MediaRecorder(audioStream);

        mediaRecorder.ondataavailable = function(event){
            if(event.data.size > 0){
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = function(){
            if(audioStream){
                audioStream.getTracks().forEach(track => track.stop());
                audioStream = null;
            }

            pararTimerAudio();

            audioBlobPendente = new Blob(audioChunks, {type:"audio/webm"});
            audioPreviewUrl = URL.createObjectURL(audioBlobPendente);

            document.getElementById("audioPreviewPlayer").src = audioPreviewUrl;
            mostrarPreviewAudio();
        };

        mediaRecorder.start();
        gravandoAudio = true;
        botao.classList.add("recording");
        botao.title = "Parar gravação";
        mostrarPainelGravacao();
        iniciarTimerAudio();

    }catch(erro){
        alert("Não consegui acessar o microfone. Verifique a permissão do navegador.");
    }
}

function pararGravacaoAudio(){
    gravandoAudio = false;

    let botao = document.getElementById("audioBtn");
    botao.classList.remove("recording");
    botao.title = "Gravar áudio";

    if(mediaRecorder && mediaRecorder.state !== "inactive"){
        mediaRecorder.stop();
    }
}

function cancelarAudio(){
    if(gravandoAudio){
        gravandoAudio = false;

        if(mediaRecorder && mediaRecorder.state !== "inactive"){
            mediaRecorder.stop();
        }
    }

    pararTimerAudio();

    if(audioStream){
        audioStream.getTracks().forEach(track => track.stop());
        audioStream = null;
    }

    audioChunks = [];
    audioBlobPendente = null;

    if(audioPreviewUrl){
        URL.revokeObjectURL(audioPreviewUrl);
        audioPreviewUrl = null;
    }

    document.getElementById("audioBtn").classList.remove("recording");
    esconderPainelAudio();
}

async function enviarAudioPendente(){
    if(!audioBlobPendente){
        return;
    }

    await enviarAudio(audioBlobPendente, audioPreviewUrl);

    audioBlobPendente = null;
    audioChunks = [];
    esconderPainelAudio();
}

async function enviarAudio(audioBlob, audioUrl){

    if(audioBlob.size > 8 * 1024 * 1024){
        alert("O áudio ficou muito grande. Grave um áudio menor.");
        return;
    }

    let chat = document.getElementById("chat");

    chat.innerHTML += `
        <div class="message user">
            <div class="audio-card">
                <div class="audio-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                        <line x1="12" y1="19" x2="12" y2="22"></line>
                        <line x1="8" y1="22" x2="16" y2="22"></line>
                    </svg>
                </div>
                <div class="audio-info">
                    <div class="audio-title">Áudio enviado</div>
                    <audio class="chat-audio" controls src="${audioUrl}"></audio>
                </div>
            </div>
        </div>
    `;

    let botDiv = document.createElement("div");
    botDiv.className = "message bot";
    botDiv.innerHTML = `
        <div style="font-size:13px;color:#64748B;margin-bottom:6px">Calmi está pensando...</div>
        <div class="typing">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;

    chat.appendChild(botDiv);
    chat.scrollTop = chat.scrollHeight;

    let formData = new FormData();
    formData.append("conversa", conversaAtual);
    formData.append("audio", audioBlob, "audio.webm");

    let resposta = await fetch("/audio",{
        method:"POST",
        body:formData
    });

    let dados = await resposta.json();

    botDiv.innerHTML = "";
let texto = dados.resposta || "Não consegui entender o áudio agora.";
    let i = 0;

    let intervalo = setInterval(() => {
        botDiv.innerHTML += texto[i];
        i++;
        chat.scrollTop = chat.scrollHeight;

        if(i >= texto.length){
            clearInterval(intervalo);
            adicionarBotaoVoz(botDiv, texto);
            adicionarBotaoFavorito(botDiv, texto);
        }
    }, 12);

    carregarConversas();
}

function renderizarListaConversas(dados){

    let lista = document.getElementById("listaChats");
    let listaMobile = document.getElementById("listaChatsMobile");

    if(lista){ lista.innerHTML = ""; }
    if(listaMobile){ listaMobile.innerHTML = ""; }

    let fixadas = getConversasFixadas();
    let filtradas = (dados || []).filter(conversa => {
        return !filtroAtualConversas || conversa.nome.toLowerCase().includes(filtroAtualConversas);
    });

    filtradas.sort((a,b) => {
        let af = fixadas.includes(a.id) ? 1 : 0;
        let bf = fixadas.includes(b.id) ? 1 : 0;
        return bf - af;
    });

    filtradas.forEach(conversa => {
        let fixa = fixadas.includes(conversa.id);
        let nomeSeguro = conversa.nome;
        let item = `
            <div class="chat-item">
                <div onclick="abrirConversa('${conversa.id}')">
                    ${fixa ? "📌 " : ""}${nomeSeguro}
                </div>

                <button
                    class="pin-btn ${fixa ? "fixed" : ""}"
                    onclick="alternarFixarConversa('${conversa.id}', event)"
                    title="Fixar conversa"
                >
                    📌
                </button>

                <button
                    class="delete-btn"
                    onclick="deletarConversa('${conversa.id}')"
                >
                    x
                </button>
            </div>
        `;

        if(lista){ lista.innerHTML += item; }
        if(listaMobile){ listaMobile.innerHTML += item; }
    });
}

function carregarConversas(){

    fetch("/conversas")
    .then(res => res.json())
    .then(dados => {
        conversasCache = dados || [];
        renderizarListaConversas(conversasCache);
    });
}

function renderizarMensagemSalva(msg){

    let chat = document.getElementById("chat");

    let div = document.createElement("div");
    div.className = `message ${msg.tipo}`;
    div.innerHTML = msg.texto;

    chat.appendChild(div);

    if(msg.tipo === "bot" && !div.querySelector(".speak-btn")){
        adicionarBotaoVoz(div, msg.texto);
    }

    adicionarBotaoFavorito(div, msg.texto);
}

function abrirConversa(id){

    fetch("/abrir/" + id)
    .then(res => res.json())
    .then(dados => {

        conversaAtual = id;

        document.getElementById("mobileMenu").classList.remove("open");

        let chat = document.getElementById("chat");

        chat.innerHTML = "";

        dados.mensagens.forEach(msg => {
            renderizarMensagemSalva(msg);
        });

        chat.scrollTop = chat.scrollHeight;
    });
}

function deletarConversa(id){

    fetch("/deletar/" + id)
    .then(() => {

        carregarConversas();

        novaConversa();
    });
}

document.getElementById("mensagem")
.addEventListener("keydown", function(e){

    if(e.key === "Enter" && !e.shiftKey){
        e.preventDefault();
        enviarMensagem();
    }
});

document.getElementById("mensagem")
.addEventListener("input", function(){
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 120) + "px";
});


let audioRespostaAtual = null;
let botaoAudioAtual = null;
let audioUrlAtual = null;

function limparTextoParaAudio(texto){
    let div = document.createElement("div");
    div.innerHTML = texto;
    return (div.textContent || div.innerText || "").trim();
}

function resetarBotaoAudio(botao){
    if(botao){
        botao.innerHTML = "🔊 Ouvir resposta";
        botao.classList.remove("listening");
    }
}

function pararAudioAtual(){
    if(audioRespostaAtual){
        audioRespostaAtual.pause();
        audioRespostaAtual.currentTime = 0;
        audioRespostaAtual = null;
    }

    if(audioUrlAtual){
        URL.revokeObjectURL(audioUrlAtual);
        audioUrlAtual = null;
    }

    resetarBotaoAudio(botaoAudioAtual);
    botaoAudioAtual = null;

    if("speechSynthesis" in window){
        speechSynthesis.cancel();
    }
}

async function ouvirRespostaCodificada(textoCodificado, botao){
    let texto = decodeURIComponent(escape(atob(textoCodificado)));
    texto = limparTextoParaAudio(texto);

    if(botaoAudioAtual === botao && audioRespostaAtual){
        pararAudioAtual();
        return;
    }

    pararAudioAtual();

    botaoAudioAtual = botao;
    botao.innerHTML = "⏳ Carregando voz...";
    botao.classList.add("listening");

    try{
        let resposta = await fetch("/tts", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({texto:texto})
        });

        if(!resposta.ok){
            throw new Error("Falha no TTS");
        }

        let blob = await resposta.blob();
        audioUrlAtual = URL.createObjectURL(blob);
        audioRespostaAtual = new Audio(audioUrlAtual);

        audioRespostaAtual.onended = () => {
            pararAudioAtual();
        };

        audioRespostaAtual.onerror = () => {
            pararAudioAtual();
            mostrarToast("Não foi possível reproduzir o áudio agora.");
        };

        botao.innerHTML = `⏹ Parar de ouvir <span class="speak-waves"><span></span><span></span><span></span></span>`;
        await audioRespostaAtual.play();

    }catch(erro){
        console.log(erro);

        pararAudioAtual();
        resetarBotaoAudio(botao);

        mostrarToast("A voz humanizada não carregou. Verifique a voz da ElevenLabs.");
    }
}

function adicionarBotaoVoz(el, texto){
    let safe = btoa(unescape(encodeURIComponent(texto)));
    el.innerHTML += `<br><button class="speak-btn" onclick="ouvirRespostaCodificada('${safe}', this)">🔊 Ouvir resposta</button>`;
}

function toggleNotas(){
    document.getElementById('notesPanel').classList.toggle('open');
    carregarNotas();
}

async function carregarNotas(){
    let res = await fetch('/notas');
    let dados = await res.json();
    let lista = document.getElementById('listaNotas');
    lista.innerHTML = '';
    dados.forEach(n => {
        lista.innerHTML += `<div class="note-card"><strong>${n.titulo || 'Anotação'}</strong><br>${n.conteudo}<br><button onclick="deletarNota(${n.id})">Excluir</button></div>`;
    });
}

async function salvarNota(){
    let titulo = document.getElementById('notaTitulo').value;
    let conteudo = document.getElementById('notaConteudo').value;
    if(!conteudo.trim()){ alert('Escreva uma anotação.'); return; }
    await fetch('/notas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({titulo,conteudo})});
    document.getElementById('notaTitulo').value='';
    document.getElementById('notaConteudo').value='';
    carregarNotas();
}

async function deletarNota(id){
    await fetch('/notas/'+id,{method:'DELETE'});
    carregarNotas();
}

async function registrarHumor(humor){
    await fetch('/humor',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({humor})});
    mostrarToast('Humor registrado: '+humor);
}

function toggleDashboard(){
    document.getElementById('dashboardPanel').classList.toggle('open');
    carregarDashboard();
}

async function carregarDashboard(){
    let res = await fetch('/dashboard');
    let d = await res.json();
    let html = '<div class="dash-card"><strong>Últimos humores</strong><br>';
    if(!d.humores.length){ html += 'Nenhum humor registrado ainda.'; }
    d.humores.forEach(h => html += `${h.humor} <small>${h.data}</small><br>`);
    html += '</div><div class="dash-card"><strong>Níveis emocionais</strong><br>';
    if(!d.riscos.length){ html += 'Sem dados suficientes.'; }
    d.riscos.forEach(r => html += `${r.nivel}: ${r.total}<br>`);
    html += '</div>';
    document.getElementById('dashboardConteudo').innerHTML = html;
}

function exportarConversa(){
    if(!conversaAtual){
        mostrarToast('Abra uma conversa primeiro.');
        return;
    }

    let escolhaPdf = confirm("Deseja exportar em PDF?\n\nOK = PDF\nCancelar = TXT");

    window.open(
        (escolhaPdf ? '/exportar_pdf/' : '/exportar/') + conversaAtual,
        '_blank'
    );
}

function modoRapido(tipo){
    let msg = tipo === 'respiração'
        ? 'Calmi, me guie em um exercício de respiração curto e calmo.'
        : 'Calmi, me ajude a relaxar para dormir melhor hoje.';
    document.getElementById('mensagem').value = msg;
    enviarMensagem();
}

window.enviarAuth = enviarAuth;
window.mudarTab = mudarTab;
window.toggleMenuMobile = toggleMenuMobile;
window.toggleTema = toggleTema;

aplicarTemaAutomatico();
verificarSessao();
</script>

</body>
</html>
"""




@app.route("/favicon.svg")
def favicon_svg():
    svg = """<svg viewBox='0 0 120 90' xmlns='http://www.w3.org/2000/svg'>
    <defs>
    <linearGradient id='b' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='#60A5FA'/><stop offset='100%' stop-color='#2563EB'/></linearGradient>
    <linearGradient id='m' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='#99F6E4'/><stop offset='100%' stop-color='#2DD4BF'/></linearGradient>
    </defs>
    <path d='M46 9C23 9 8 23 8 42c0 13 8 24 21 30l-5 14 18-9c2 .2 4 .3 6 .3 24 0 42-14 42-34S70 9 46 9Z' fill='url(#b)'/>
    <path d='M82 30c18 2 30 13 30 29 0 10-6 20-16 25l4 12-15-7c-2 .2-4 .3-6 .3-14 0-26-6-32-16 23-1 41-15 41-34 0-3-.2-6-1-9Z' fill='url(#m)'/>
    <path d='M31 40c3-7 13-7 16 0' fill='none' stroke='white' stroke-width='7' stroke-linecap='round'/>
    <path d='M58 40c3-7 13-7 16 0' fill='none' stroke='white' stroke-width='7' stroke-linecap='round'/>
    <path d='M43 56c8 9 20 9 28 0' fill='none' stroke='white' stroke-width='7' stroke-linecap='round'/>
    </svg>"""
    return Response(svg, mimetype="image/svg+xml")


@app.route("/")
def home():
    return render_template_string(HTML)



@app.route("/tts", methods=["POST"])
def gerar_audio_tts():
    try:
        if not ELEVENLABS_API_KEY:
            return jsonify({"erro": "ELEVENLABS_API_KEY não configurada."}), 500

        if not ELEVENLABS_VOICE_ID:
            return jsonify({"erro": "ELEVENLABS_VOICE_ID não configurada."}), 500

        dados = request.get_json() or {}
        texto = (dados.get("texto") or "").strip()

        if not texto:
            return jsonify({"erro": "Texto vazio."}), 400

        if len(texto) > 2500:
            texto = texto[:2500]

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

        payload = {
            "text": texto,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.8,
                "style": 0.25,
                "use_speaker_boost": True
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=45) as resposta:
            audio = resposta.read()

        return Response(audio, mimetype="audio/mpeg")

    except urllib.error.HTTPError as erro:
        print("Erro ElevenLabs:", erro.read().decode("utf-8", errors="ignore"))
        return jsonify({"erro": "Erro ao gerar voz com ElevenLabs."}), 500

    except Exception as erro:
        print("Erro TTS:", erro)
        return jsonify({"erro": "Erro ao gerar voz."}), 500

@app.route("/session")
def verificar_session():

    if "usuario" in session:

        return jsonify({
            "logado": True,
            "usuario": session["usuario"]
        })

    return jsonify({
        "logado": False
    })


@app.route("/cadastro", methods=["POST"])
def cadastro():

    dados = request.get_json()

    usuario = dados["usuario"]
    senha = dados["senha"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM usuarios WHERE usuario=%s",
        (usuario,)
    )

    existe = cur.fetchone()

    if existe:

        cur.close()
        conn.close()

        return jsonify({
            "status": "erro",
            "erro": "Usuário já existe."
        })

    cur.execute(
        "INSERT INTO usuarios(usuario, senha) VALUES (%s,%s)",
        (usuario, senha)
    )

    conn.commit()

    session["usuario"] = usuario

    cur.close()
    conn.close()

    return jsonify({
        "status": "ok",
        "usuario": usuario
    })


@app.route("/login", methods=["POST"])
def login():

    dados = request.get_json()

    usuario = dados["usuario"]
    senha = dados["senha"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM usuarios WHERE usuario=%s",
        (usuario,)
    )

    user = cur.fetchone()

    if not user:

        cur.close()
        conn.close()

        return jsonify({
            "status": "erro",
            "erro": "Conta não encontrada."
        })

    if user["senha"] != senha:

        cur.close()
        conn.close()

        return jsonify({
            "status": "erro",
            "erro": "Senha incorreta."
        })

    session["usuario"] = usuario

    cur.close()
    conn.close()

    return jsonify({
        "status": "ok",
        "usuario": usuario
    })


@app.route("/perfil", methods=["GET", "POST"])
def perfil():

    if "usuario" not in session:
        return jsonify({"status":"erro", "erro":"Você precisa estar logado."})

    usuario = session["usuario"]

    conn = get_db()
    cur = conn.cursor()

    if request.method == "GET":

        cur.execute(
            "SELECT foto_perfil FROM usuarios WHERE usuario=%s",
            (usuario,)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        return jsonify({
            "foto_perfil": user["foto_perfil"] if user and user["foto_perfil"] else None
        })

    dados = request.get_json()
    foto = dados.get("foto_perfil")

    if not foto or not foto.startswith("data:image/"):
        cur.close()
        conn.close()
        return jsonify({"status":"erro", "erro":"Imagem inválida."})

    if len(foto) > 3_000_000:
        cur.close()
        conn.close()
        return jsonify({"status":"erro", "erro":"Imagem muito grande."})

    cur.execute(
        "UPDATE usuarios SET foto_perfil=%s WHERE usuario=%s",
        (foto, usuario)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status":"ok"})


@app.route("/perfil/remover", methods=["POST"])
def remover_perfil():

    if "usuario" not in session:
        return jsonify({"status":"erro", "erro":"Você precisa estar logado."})

    usuario = session["usuario"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE usuarios SET foto_perfil=NULL WHERE usuario=%s",
        (usuario,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status":"ok"})


@app.route("/logout")
def logout():

    session.clear()

    return jsonify({
        "status": "ok"
    })


@app.route("/chat", methods=["POST"])
def chat():

    try:

        if "usuario" not in session:

            return jsonify({
                "resposta": "Você precisa estar logado."
            })

        if client is None:

            return jsonify({
                "resposta": "A API da Groq não foi configurada."
            })

        dados = request.get_json()

        usuario = session["usuario"]
        conversa = dados["conversa"]
        mensagem = dados["mensagem"]

        historico = buscar_historico(usuario)

        risco = analisar_risco_emocional(
            mensagem,
            historico
        )

        profissional = sugerir_profissional(
            mensagem,
            risco
        )

        contexto = resumir_contexto(historico)
        notas_contexto = resumir_notas(usuario)

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM conversas WHERE id=%s",
            (conversa,)
        )

        existe = cur.fetchone()

        if not existe:

            cur.execute(
                "INSERT INTO conversas(id, usuario, nome) VALUES (%s,%s,%s)",
                (
                    conversa,
                    usuario,
                    mensagem[:30]
                )
            )

        cur.execute(
            "INSERT INTO mensagens(conversa_id, tipo, texto) VALUES (%s,%s,%s)",
            (
                conversa,
                "user",
                mensagem
            )
        )

        conn.commit()

        cur.close()
        conn.close()

        salvar_mensagem(
            conversa,
            usuario,
            "user",
            mensagem,
            risco
        )

        if risco == "crítico":

            resposta_texto = (
                "💙 Eu percebo que você pode estar passando por algo muito pesado. "
                "Você não precisa enfrentar isso sozinho. "
                + sugestao_profissional_detalhada(mensagem, risco) + " "
                "No Brasil, o CVV atende pelo 188, e também é importante falar com um responsável, alguém de confiança ou emergência local se houver risco imediato."
            )

        else:

            prompt = f"""
Você é o Calmi.

Contexto emocional recente:
{contexto}

Nível emocional detectado:
{risco}

Sugestão de apoio:
{profissional}

Anotações importantes do usuário:
{notas_contexto}

Regras:
- Seja acolhedor.
- Não diagnostique.
- Não substitua terapia.
- Fale em português brasileiro.
- Responda de forma curta, humana e natural.
- Em risco elevado, recomende apoio profissional com calma.

Mensagem:
{mensagem}
"""

            resposta = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": mensagem
                    }
                ]
            )

            resposta_texto = resposta.choices[0].message.content

            if risco == "elevado":

                resposta_texto += (
                    "<br><br>💙 Pode ser útil conversar com "
                    f"{profissional}. Você merece apoio de verdade."
                )

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO mensagens(conversa_id, tipo, texto) VALUES (%s,%s,%s)",
            (
                conversa,
                "bot",
                resposta_texto
            )
        )

        conn.commit()

        cur.close()
        conn.close()

        salvar_mensagem(
            conversa,
            usuario,
            "bot",
            resposta_texto,
            risco
        )

        return jsonify({
            "resposta": resposta_texto
        })

    except Exception as erro:

        print(erro)

        return jsonify({
            "resposta": "Erro ao conectar com a IA 😔"
        })



@app.route("/imagem", methods=["POST"])
def analisar_imagem():

    try:

        if "usuario" not in session:

            return jsonify({
                "resposta": "Você precisa estar logado."
            })

        if client is None:

            return jsonify({
                "resposta": "A API da Groq não foi configurada."
            })

        usuario = session["usuario"]
        conversa = request.form.get("conversa")
        imagem = request.files.get("imagem")

        if not conversa:
            return jsonify({"resposta": "Conversa não encontrada."})

        if not imagem:
            return jsonify({"resposta": "Nenhuma imagem foi enviada."})

        if imagem.mimetype not in ["image/jpeg", "image/png", "image/webp"]:
            return jsonify({"resposta": "Envie uma imagem JPG, PNG ou WEBP."})

        imagem_bytes = imagem.read()

        if len(imagem_bytes) > 4 * 1024 * 1024:
            return jsonify({"resposta": "A imagem é muito grande. Envie uma imagem de até 4MB."})

        base64_image = base64.b64encode(imagem_bytes).decode("utf-8")
        data_url = f"data:{imagem.mimetype};base64,{base64_image}"

        historico = buscar_historico(usuario)
        contexto = resumir_contexto(historico)
        notas_contexto = resumir_notas(usuario)

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM conversas WHERE id=%s",
            (conversa,)
        )

        existe = cur.fetchone()

        if not existe:

            cur.execute(
                "INSERT INTO conversas(id, usuario, nome) VALUES (%s,%s,%s)",
                (
                    conversa,
                    usuario,
                    "Imagem enviada"
                )
            )

        cur.execute(
            "INSERT INTO mensagens(conversa_id, tipo, texto) VALUES (%s,%s,%s)",
            (
                conversa,
                "user",
                "📷 Imagem enviada"
            )
        )

        conn.commit()
        cur.close()
        conn.close()

        salvar_mensagem(
            conversa,
            usuario,
            "user",
            "Imagem enviada para análise.",
            "leve"
        )

        prompt = f"""
Você é o Calmi, uma IA emocional acolhedora.

Contexto emocional recente do usuário:
{contexto}

Analise a imagem enviada de forma cuidadosa e útil.
Regras:
- Responda em português brasileiro.
- Descreva o que você consegue observar na imagem.
- Se a imagem parecer relacionada a emoção, ambiente, estudo, trabalho ou rotina, comente de forma acolhedora.
- Não identifique pessoas reais na imagem.
- Não faça diagnósticos médicos, psicológicos ou legais pela imagem.
- Se a imagem mostrar algo preocupante, recomende buscar ajuda humana/profissional de forma calma.
- Seja breve, claro e gentil.
"""

        resposta = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=700
        )

        resposta_texto = resposta.choices[0].message.content

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO mensagens(conversa_id, tipo, texto) VALUES (%s,%s,%s)",
            (
                conversa,
                "bot",
                resposta_texto
            )
        )

        conn.commit()
        cur.close()
        conn.close()

        salvar_mensagem(
            conversa,
            usuario,
            "bot",
            resposta_texto,
            "leve"
        )

        return jsonify({
            "resposta": resposta_texto
        })

    except Exception as erro:

        print(erro)

        return jsonify({
            "resposta": "Erro ao analisar a imagem 😔"
        })


@app.route("/audio", methods=["POST"])
def analisar_audio():

    try:

        if "usuario" not in session:
            return jsonify({"resposta":"Você precisa estar logado."})

        if client is None:
            return jsonify({"resposta":"A API da Groq não foi configurada."})

        usuario = session["usuario"]
        conversa = request.form.get("conversa")
        audio = request.files.get("audio")

        if not conversa:
            return jsonify({"resposta":"Conversa não encontrada."})

        if not audio:
            return jsonify({"resposta":"Nenhum áudio foi enviado."})

        audio_bytes = audio.read()

        if len(audio_bytes) > 8 * 1024 * 1024:
            return jsonify({"resposta":"O áudio é muito grande. Envie um áudio menor."})

        transcricao = client.audio.transcriptions.create(
            file=(audio.filename or "audio.webm", audio_bytes, audio.mimetype or "audio/webm"),
            model="whisper-large-v3-turbo",
            language="pt",
            response_format="json"
        )

        texto_audio = getattr(transcricao, "text", "").strip()

        if not texto_audio:
            return jsonify({"resposta":"Não consegui entender o áudio com clareza."})

        historico = buscar_historico(usuario)
        risco = analisar_risco_emocional(texto_audio, historico)
        profissional = sugerir_profissional(texto_audio, risco)
        contexto = resumir_contexto(historico)
        notas_contexto = resumir_notas(usuario)

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM conversas WHERE id=%s",
            (conversa,)
        )

        existe = cur.fetchone()

        if not existe:
            cur.execute(
                "INSERT INTO conversas(id, usuario, nome) VALUES (%s,%s,%s)",
                (conversa, usuario, texto_audio[:30])
            )

        audio_mime = audio.mimetype or "audio/webm"
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        audio_src = f"data:{audio_mime};base64,{audio_base64}"
        texto_audio_html = html_lib.escape(texto_audio)

        mensagem_usuario = f"""
            <div class="audio-card">
                <div class="audio-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                        <line x1="12" y1="19" x2="12" y2="22"></line>
                        <line x1="8" y1="22" x2="16" y2="22"></line>
                    </svg>
                </div>

                <div class="audio-info">
                    <div class="audio-title">Áudio enviado</div>
                    <audio class="chat-audio" controls src="{audio_src}"></audio>
                </div>
            </div>

            <div class="audio-transcription">
                <strong>Transcrição:</strong> {texto_audio_html}
            </div>
        """

        cur.execute(
            "INSERT INTO mensagens(conversa_id, tipo, texto) VALUES (%s,%s,%s)",
            (conversa, "user", mensagem_usuario)
        )

        conn.commit()
        cur.close()
        conn.close()

        salvar_mensagem(conversa, usuario, "user", texto_audio, risco)

        if risco == "crítico":
            resposta_texto = (
                "Eu entendi seu áudio. 💙 Você parece estar passando por algo muito pesado. "
                "Você não precisa enfrentar isso sozinho. Procure alguém de confiança, um responsável "
                "ou ajuda profissional. No Brasil, o CVV atende pelo 188."
            )
        else:
            prompt = f"""
Você é o Calmi.

O usuário enviou um áudio. Transcrição:
{texto_audio}

Contexto emocional recente:
{contexto}

Nível emocional detectado:
{risco}

Sugestão de apoio:
{profissional}

Anotações importantes do usuário:
{notas_contexto}

Regras:
- Responda como se tivesse ouvido o áudio do usuário.
- Seja acolhedor.
- Não diagnostique.
- Não substitua terapia.
- Fale em português brasileiro.
- Responda de forma curta, humana e natural.
"""

            resposta = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role":"system", "content":prompt},
                    {"role":"user", "content":texto_audio}
                ]
            )

            resposta_texto = resposta.choices[0].message.content

            if risco == "elevado":
                resposta_texto += (
                    "<br><br>💙 Pode ser útil conversar com "
                    f"{profissional}. Você merece apoio de verdade."
                )

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO mensagens(conversa_id, tipo, texto) VALUES (%s,%s,%s)",
            (conversa, "bot", resposta_texto)
        )

        conn.commit()
        cur.close()
        conn.close()

        salvar_mensagem(conversa, usuario, "bot", resposta_texto, risco)

        return jsonify({"resposta":resposta_texto, "transcricao":texto_audio})

    except Exception as erro:
        print(erro)
        return jsonify({"resposta":"Erro ao processar o áudio 😔"})


@app.route("/conversas")
def listar_conversas():

    if "usuario" not in session:

        return jsonify([])

    usuario = session["usuario"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, nome FROM conversas WHERE usuario=%s ORDER BY nome ASC",
        (usuario,)
    )

    resultados = cur.fetchall()

    lista = []

    for conversa in resultados:

        lista.append({
            "id": conversa["id"],
            "nome": conversa["nome"]
        })

    cur.close()
    conn.close()

    return jsonify(lista)


@app.route("/abrir/<id>")
def abrir(id):

    if "usuario" not in session:

        return jsonify({
            "mensagens": []
        })

    usuario = session["usuario"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM conversas WHERE id=%s AND usuario=%s",
        (
            id,
            usuario
        )
    )

    conversa = cur.fetchone()

    if not conversa:

        cur.close()
        conn.close()

        return jsonify({
            "mensagens": []
        })

    cur.execute(
        "SELECT tipo, texto FROM mensagens WHERE conversa_id=%s ORDER BY id ASC",
        (id,)
    )

    mensagens = cur.fetchall()

    lista = []

    for msg in mensagens:

        lista.append({
            "tipo": msg["tipo"],
            "texto": msg["texto"]
        })

    cur.close()
    conn.close()

    return jsonify({
        "mensagens": lista
    })


@app.route("/deletar/<id>")
def deletar(id):

    if "usuario" not in session:

        return jsonify({
            "status": "erro"
        })

    usuario = session["usuario"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM mensagens WHERE conversa_id=%s",
        (id,)
    )

    cur.execute(
        "DELETE FROM mensagens_memoria WHERE conversa_id=%s AND usuario=%s",
        (
            id,
            usuario
        )
    )

    cur.execute(
        "DELETE FROM conversas WHERE id=%s AND usuario=%s",
        (
            id,
            usuario
        )
    )

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "ok"
    })


@app.route("/notas", methods=["GET", "POST"])
def notas():
    if "usuario" not in session:
        return jsonify([] if request.method == "GET" else {"status":"erro"})

    usuario = session["usuario"]

    if request.method == "GET":
        notas = buscar_notas(usuario, 30)
        return jsonify([
            {
                "id": n["id"],
                "titulo": n["titulo"],
                "conteudo": n["conteudo"]
            }
            for n in notas
        ])

    dados = request.get_json()
    titulo = dados.get("titulo", "").strip()
    conteudo = dados.get("conteudo", "").strip()

    if not conteudo:
        return jsonify({"status":"erro", "erro":"Anotação vazia."})

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notas_usuario(usuario, titulo, conteudo) VALUES (%s,%s,%s)",
        (usuario, titulo, conteudo)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status":"ok"})


@app.route("/notas/<int:nota_id>", methods=["DELETE"])
def deletar_nota(nota_id):
    if "usuario" not in session:
        return jsonify({"status":"erro"})

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM notas_usuario WHERE id=%s AND usuario=%s",
        (nota_id, session["usuario"])
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status":"ok"})


@app.route("/humor", methods=["POST"])
def humor():
    if "usuario" not in session:
        return jsonify({"status":"erro"})

    dados = request.get_json()
    salvar_humor(session["usuario"], dados.get("humor", "😐 Neutro"), dados.get("observacao", ""))
    return jsonify({"status":"ok"})


@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return jsonify({"humores": [], "riscos": []})

    humores, riscos = buscar_dashboard(session["usuario"])
    return jsonify({
        "humores": [
            {"humor": h["humor"], "observacao": h["observacao"], "data": str(h["criado_em"])[:16]}
            for h in humores
        ],
        "riscos": [
            {"nivel": r["nivel_emocional"], "total": r["total"]}
            for r in riscos
        ]
    })


@app.route("/exportar/<id>")
def exportar(id):
    if "usuario" not in session:
        return "Você precisa estar logado.", 401

    usuario = session["usuario"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM conversas WHERE id=%s AND usuario=%s", (id, usuario))
    conversa = cur.fetchone()

    if not conversa:
        cur.close()
        conn.close()
        return "Conversa não encontrada.", 404

    cur.execute("SELECT tipo, texto FROM mensagens WHERE conversa_id=%s ORDER BY id ASC", (id,))
    mensagens = cur.fetchall()
    cur.close()
    conn.close()

    linhas = [f"Calmi AI - Exportação da conversa: {conversa['nome']}", ""]

    for m in mensagens:
        remetente = "Você" if m["tipo"] == "user" else "Calmi"
        texto = m["texto"].replace("<br>", "\n")
        linhas.append(f"{remetente}: {texto}")
        linhas.append("")

    return "\n".join(linhas), 200, {
        "Content-Type":"text/plain; charset=utf-8",
        "Content-Disposition":"attachment; filename=conversa_calmi.txt"
    }



@app.route("/exportar_pdf/<id>")
def exportar_pdf(id):
    if "usuario" not in session:
        return "Você precisa estar logado.", 401

    usuario = session["usuario"]
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM conversas WHERE id=%s AND usuario=%s", (id, usuario))
    conversa = cur.fetchone()

    if not conversa:
        cur.close()
        conn.close()
        return "Conversa não encontrada.", 404

    cur.execute("SELECT tipo, texto FROM mensagens WHERE conversa_id=%s ORDER BY id ASC", (id,))
    mensagens = cur.fetchall()

    cur.close()
    conn.close()

    html_pdf = f"""
    <!DOCTYPE html>
    <html lang='pt-br'>
    <head>
        <meta charset='UTF-8'>
        <title>Conversa Calmi</title>
        <style>
            body{{font-family:Arial, sans-serif; padding:30px; color:#111827;}}
            h1{{color:#4F46E5;}}
            .msg{{margin:14px 0; padding:12px; border-radius:12px; background:#F1F5F9;}}
            .user{{border-left:5px solid #4F46E5;}}
            .bot{{border-left:5px solid #06B6D4;}}
            audio,img,svg,button{{display:none !important;}}
        </style>
    </head>
    <body>
        <h1>Calmi AI</h1>
        <h2>{html_lib.escape(conversa['nome'])}</h2>
    """

    for m in mensagens:
        remetente = "Você" if m["tipo"] == "user" else "Calmi"
        texto_limpo = re.sub(r"<[^>]+>", " ", m["texto"])
        texto_limpo = html_lib.escape(" ".join(texto_limpo.split()))
        classe = "user" if m["tipo"] == "user" else "bot"
        html_pdf += f"<div class='msg {classe}'><strong>{remetente}:</strong><br>{texto_limpo}</div>"

    html_pdf += "</body></html>"

    return html_pdf, 200, {
        "Content-Type":"text/html; charset=utf-8",
        "Content-Disposition":"attachment; filename=conversa_calmi.html"
    }


if __name__ == "__main__":
    app.run(debug=True)