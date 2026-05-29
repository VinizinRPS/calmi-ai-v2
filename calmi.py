
# CALMI BALLOON-ONLY ICON VERSION
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
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "calmi-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # limite de 12MB para imagens/áudios

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ==========================================
# LOGO OFICIAL CALMI / PWA
# ==========================================

CALMI_ICON_BASE64 = """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"""


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

<link rel="icon" href="/icon-192.png" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#2563EB">
<link rel="manifest" href="/manifest.json">


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
    width:56px;
    height:56px;
    border-radius:18px;
    display:flex;
    align-items:center;
    justify-content:center;
    background:linear-gradient(145deg,#4F46E5,#06B6D4);
    box-shadow:0 12px 28px rgba(37,99,235,.22);
    flex-shrink:0;
    overflow:hidden;
}

.brand-logo-mark svg{
    width:48px;
    height:48px;
    filter:drop-shadow(0 5px 7px rgba(0,0,0,.12));
}

.bubble-main{
    fill:#3B82F6;
}

.bubble-second{
    fill:#2DD4BF;
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
    width:42px;
    height:42px;
    border-radius:14px;
}

.mobile-brand .brand-logo-mark svg{
    width:37px;
    height:37px;
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
        width:52px;
        height:52px;
        border-radius:17px;
    }

    .brand-logo-mark svg{
        width:45px;
        height:45px;
    }
}

/* EMOÇÕES NOMEADAS */
.mood-grid-named button{
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    gap:4px;
    min-height:62px;
    padding:10px 6px;
    font-size:20px;
}

.mood-grid-named button small{
    font-size:10.5px;
    font-weight:700;
    opacity:.92;
    line-height:1;
}

.dashboard-action{
    margin-top:12px;
}

/* Sidebar e menu mobile sempre escuros */
body:not(.dark) .sidebar,
body:not(.dark) .mobile-menu{
    background:#111827 !important;
    color:white !important;
}

body:not(.dark) .profile,
body:not(.dark) .mobile-profile,
body:not(.dark) .quick-panel,
body:not(.dark) .chat-item{
    background:rgba(31,41,55,.92) !important;
    color:white !important;
}

body:not(.dark) .brand-text p,
body:not(.dark) .brand-text span,
body:not(.dark) .mobile-profile small{
    color:#E5E7EB !important;
}

body:not(.dark) .chat-search{
    background:#1F2937 !important;
    color:white !important;
}


/* Ajuste fino do rostinho dentro do balão */
.brand-logo-mark svg{
    transform:translate(-1px, 0px) scale(1.02);
}


/* LOGO OFICIAL EM IMAGEM - NÃO REDESENHAR O ROSTO */
.brand-logo-mark.official-logo{
    background:transparent !important;
    box-shadow:none !important;
    border-radius:18px;
}

.brand-logo-mark.official-logo img,
.calmi-logo-img{
    width:100%;
    height:100%;
    object-fit:contain;
    display:block;
    transform:none !important;
    filter:none !important;
}

.brand-logo-mark svg{
    transform:none !important;
}

</style>
</head>
<body>

<div class="login" id="login">

    <div class="login-box">

        <div class="login-brand">
            
<div class="brand-logo-mark official-logo" aria-hidden="true">
    <img class="calmi-logo-img" src="/icon-512.png" alt="Calmi">
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
            
<div class="brand-logo-mark official-logo" aria-hidden="true">
    <img class="calmi-logo-img" src="/icon-512.png" alt="Calmi">
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
                
<div class="brand-logo-mark official-logo" aria-hidden="true">
    <img class="calmi-logo-img" src="/icon-512.png" alt="Calmi">
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
            <div class="mood-grid mood-grid-named">
                <button onclick="registrarHumor('😊 Feliz')">
                    <div>😊</div>
                    <small>Feliz</small>
                </button>

                <button onclick="registrarHumor('🙂 Bem')">
                    <div>🙂</div>
                    <small>Bem</small>
                </button>

                <button onclick="registrarHumor('😐 Neutro')">
                    <div>😐</div>
                    <small>Neutro</small>
                </button>

                <button onclick="registrarHumor('😔 Triste')">
                    <div>😔</div>
                    <small>Triste</small>
                </button>

                <button onclick="registrarHumor('😟 Ansioso')">
                    <div>😟</div>
                    <small>Ansioso</small>
                </button>

                <button onclick="registrarHumor('😢 Muito mal')">
                    <div>😢</div>
                    <small>Muito mal</small>
                </button>
            </div>

            <button class="side-action dashboard-action" onclick="toggleDashboard()">
                📊 Dashboard Emocional
            </button>
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


function atualizarIconeTema(){
    let botao = document.querySelector(".tema-btn");
    if(botao){
        botao.innerText = document.body.classList.contains("dark") ? "☀️" : "🌙";
    }
}

function toggleTema(){

    document.body.classList.toggle("dark");
    salvarTemaAtual();
    atualizarIconeTema();
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

    let escolhaPdf = confirm(`Deseja exportar em PDF?

OK = PDF
Cancelar = TXT`);

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


if("serviceWorker" in navigator){
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    });
}

aplicarTemaAutomatico();
atualizarIconeTema();
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




@app.route("/icon-512.png")
def icon_512():
    img = base64.b64decode(CALMI_ICON_BASE64)
    return Response(img, mimetype="image/png")


@app.route("/icon-192.png")
def icon_192():
    try:
        from PIL import Image
        imagem = Image.open(BytesIO(base64.b64decode(CALMI_ICON_BASE64))).convert("RGBA")
        imagem = imagem.resize((192, 192))
        buffer = BytesIO()
        imagem.save(buffer, format="PNG")
        return Response(buffer.getvalue(), mimetype="image/png")
    except Exception:
        img = base64.b64decode(CALMI_ICON_BASE64)
        return Response(img, mimetype="image/png")


@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    try:
        from PIL import Image
        imagem = Image.open(BytesIO(base64.b64decode(CALMI_ICON_BASE64))).convert("RGBA")
        imagem = imagem.resize((180, 180))
        buffer = BytesIO()
        imagem.save(buffer, format="PNG")
        return Response(buffer.getvalue(), mimetype="image/png")
    except Exception:
        img = base64.b64decode(CALMI_ICON_BASE64)
        return Response(img, mimetype="image/png")


@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "CALMi",
        "short_name": "CALMi",
        "description": "IA emocional inteligente",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0F172A",
        "theme_color": "#2563EB",
        "orientation": "portrait",
        "icons": [
            {
                "src": "/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    })


@app.route("/service-worker.js")
def service_worker():
    js = """
self.addEventListener('install', event => {
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', event => {
    event.respondWith(fetch(event.request));
});
"""
    return Response(js, mimetype="application/javascript")


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