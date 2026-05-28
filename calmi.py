from flask import Flask, request, jsonify, render_template_string, session
from groq import Groq
import psycopg2
import psycopg2.extras
import os
import base64
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "calmi-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # limite de 4MB para uploads

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversas (
        id TEXT PRIMARY KEY,
        usuario TEXT NOT NULL,
        nome TEXT NOT NULL
    )
    """)

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


HTML = """

<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Calmi AI</title>

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
    padding:14px 16px !important;
    background:#111827 !important;
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

    .login-box{
        width:90%;
        padding:28px;
    }

    .login-box h1{
        font-size:46px;
    }
}
</style>
</head>
<body>

<div class="login" id="login">

    <div class="login-box">

        <h1>Calmi</h1>

        <p>Sua IA emocional 💙</p>

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

<div class="mobile-menu" id="mobileMenu">

    <div class="mobile-menu-header">

        <h2>Calmi</h2>

        <button onclick="toggleMenuMobile()">✕</button>

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

    <br>

    <h3>Histórico</h3>

    <br>

    <div id="listaChatsMobile"></div>

</div>

<div class="container">

    <div class="sidebar">

        <div class="logo">

            <h1>Calmi</h1>

            <p>IA emocional inteligente</p>

        </div>

        <div class="profile">

            <div class="avatar" id="avatar">C</div>

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

        <button class="logout-btn" onclick="logout()">
            Sair da conta
        </button>

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

        <div class="input-area">

            <button class="attach-btn" type="button" onclick="document.getElementById('imagemInput').click()">
                📷
            </button>

            <input
                type="file"
                id="imagemInput"
                accept="image/png,image/jpeg,image/webp"
                style="display:none"
                onchange="enviarImagem(this)"
            >

            <input
                type="text"
                id="mensagem"
                placeholder="Digite sua mensagem..."
                autocomplete="off"
            >

            <button onclick="enviarMensagem()">
                Enviar
            </button>

        </div>

    </div>

</div>

<script>
let usuarioAtual = "";
let conversaAtual = crypto.randomUUID();
let modo = "login";

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

    let usuario = document.getElementById("usuario").value;
    let senha = document.getElementById("senha").value;

    if(usuario.trim() === "" || senha.trim() === ""){

        document.getElementById("erro").innerText =
            "Preencha usuário e senha.";

        return;
    }

    let rota = modo === "login" ? "/login" : "/cadastro";

    let botao = document.getElementById("botaoLogin");

    botao.classList.add("loading");

    let resposta = await fetch(rota, {
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            usuario,
            senha
        })
    });

    let dados = await resposta.json();

    botao.classList.remove("loading");

    if(dados.status === "ok"){

        usuarioAtual = dados.usuario || usuario;

        iniciarApp(usuarioAtual);

        return;
    }

    document.getElementById("erro").innerText =
        dados.erro || "Erro ao entrar.";
}

function iniciarApp(usuario){

    usuarioAtual = usuario;

    document.getElementById("login").style.display = "none";

    document.getElementById("nomeUsuario").innerText = usuario;

    document.getElementById("avatar").innerText =
        usuario[0].toUpperCase();

    novaConversa();

    carregarConversas();
}

function verificarSessao(){

    fetch("/session")
    .then(res => res.json())
    .then(dados => {

        if(dados.logado){

            iniciarApp(dados.usuario);

        }
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
}

function toggleMenuMobile(){

    document.getElementById("mobileMenu").classList.toggle("open");
}

function novaConversa(){

    conversaAtual = crypto.randomUUID();

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

    input.value = "";

    let botDiv = document.createElement("div");

    botDiv.className = "message bot";

    botDiv.innerHTML = `
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
        }
    }, 12);

    inputArquivo.value = "";
    carregarConversas();
}

function carregarConversas(){

    fetch("/conversas")
    .then(res => res.json())
    .then(dados => {

        let lista = document.getElementById("listaChats");
        let listaMobile = document.getElementById("listaChatsMobile");

        if(lista){
            lista.innerHTML = "";
        }

        if(listaMobile){
            listaMobile.innerHTML = "";
        }

        dados.forEach(conversa => {

            let item = `
                <div class="chat-item">
                    <div onclick="abrirConversa('${conversa.id}')">
                        ${conversa.nome}
                    </div>

                    <button
                        class="delete-btn"
                        onclick="deletarConversa('${conversa.id}')"
                    >
                        x
                    </button>
                </div>
            `;

            if(lista){
                lista.innerHTML += item;
            }

            if(listaMobile){
                listaMobile.innerHTML += item;
            }
        });
    });
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

            chat.innerHTML += `
                <div class="message ${msg.tipo}">
                    ${msg.texto}
                </div>
            `;
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
.addEventListener("keypress", function(e){

    if(e.key === "Enter"){

        enviarMensagem();
    }
});

verificarSessao();
</script>

</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML)


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
                "Procure agora alguém de confiança, um responsável ou ajuda profissional. "
                "No Brasil, o CVV atende pelo 188."
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


if __name__ == "__main__":
    app.run(debug=True)