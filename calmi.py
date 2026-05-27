from flask import Flask, request, jsonify, render_template_string
from groq import Groq
import sqlite3
import os

app = Flask(__name__)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

conn = sqlite3.connect("calmi.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    senha TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversas (
    id TEXT,
    usuario TEXT,
    nome TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mensagens (
    conversa_id TEXT,
    tipo TEXT,
    texto TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS memoria (
    usuario TEXT,
    memoria TEXT
)
""")

conn.commit()

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
    --escuro:#0F172A;
    --card:#111827;
    --texto:#111827;
    --claro:#F8FAFC;
}

body{
    font-family:Arial, Helvetica, sans-serif;
    height:100vh;
    overflow:hidden;
    background:
        radial-gradient(circle at top left, rgba(124,58,237,0.55), transparent 34%),
        radial-gradient(circle at bottom right, rgba(6,182,212,0.45), transparent 34%),
        linear-gradient(135deg,#0F172A,#111827);
    animation:fundo 12s ease-in-out infinite alternate;
}

@keyframes fundo{
    from{
        background-position:0% 0%;
    }
    to{
        background-position:100% 100%;
    }
}

.container{
    display:flex;
    width:100%;
    height:100vh;
    padding:18px;
    gap:18px;
}

.sidebar{
    width:310px;
    background:rgba(17,24,39,0.82);
    color:white;
    display:flex;
    flex-direction:column;
    padding:18px;
    border-radius:28px;
    border:1px solid rgba(255,255,255,0.09);
    box-shadow:0 25px 70px rgba(0,0,0,0.35);
    backdrop-filter:blur(18px);
}

.logo{
    text-align:center;
    padding:18px;
    border-bottom:1px solid rgba(255,255,255,0.08);
}

.logo h1{
    font-size:46px;
    background:linear-gradient(135deg,#60A5FA,#A78BFA,#22D3EE);
    -webkit-background-clip:text;
    color:transparent;
}

.logo p{
    color:#CBD5E1;
    margin-top:6px;
    font-size:14px;
}

.profile{
    display:flex;
    align-items:center;
    gap:12px;
    margin-top:18px;
    background:rgba(31,41,55,0.9);
    padding:13px;
    border-radius:20px;
    border:1px solid rgba(255,255,255,0.08);
}

.avatar{
    width:54px;
    height:54px;
    border-radius:50%;
    background:linear-gradient(135deg,var(--roxo),var(--azul));
    display:flex;
    justify-content:center;
    align-items:center;
    font-weight:bold;
    font-size:22px;
    box-shadow:0 0 25px rgba(79,70,229,0.45);
}

.status{
    font-size:12px;
    color:#86EFAC;
    margin-top:4px;
}

.new-chat button{
    width:100%;
    margin-top:20px;
    padding:15px;
    border:none;
    background:linear-gradient(135deg,var(--roxo),var(--roxo2));
    color:white;
    border-radius:17px;
    cursor:pointer;
    transition:0.25s;
    font-weight:bold;
    font-size:15px;
    box-shadow:0 12px 28px rgba(79,70,229,0.3);
}

.new-chat button:hover{
    transform:translateY(-2px);
    box-shadow:0 18px 38px rgba(79,70,229,0.42);
}

.chats{
    flex:1;
    overflow-y:auto;
    margin-top:20px;
    padding-right:4px;
}

.chat-item{
    background:rgba(31,41,55,0.92);
    padding:13px 42px 13px 13px;
    border-radius:16px;
    margin-bottom:10px;
    cursor:pointer;
    transition:0.25s;
    position:relative;
    color:#E5E7EB;
    font-size:14px;
    border:1px solid rgba(255,255,255,0.06);
}

.chat-item:hover{
    background:#374151;
    transform:translateX(4px);
}

.delete-btn{
    position:absolute;
    right:10px;
    top:50%;
    transform:translateY(-50%);
    border:none;
    width:24px;
    height:24px;
    border-radius:50%;
    background:#EF4444;
    color:white;
    cursor:pointer;
    transition:0.2s;
}

.delete-btn:hover{
    transform:translateY(-50%) scale(1.1);
}

.main{
    flex:1;
    display:flex;
    flex-direction:column;
    background:rgba(248,250,252,0.92);
    border-radius:28px;
    overflow:hidden;
    box-shadow:0 25px 70px rgba(0,0,0,0.25);
    border:1px solid rgba(255,255,255,0.35);
    backdrop-filter:blur(18px);
}

.top{
    padding:20px 24px;
    background:rgba(255,255,255,0.86);
    display:flex;
    justify-content:space-between;
    align-items:center;
    border-bottom:1px solid rgba(15,23,42,0.07);
}

.top h2{
    color:var(--roxo);
    font-size:24px;
}

.subtitle{
    color:#64748B;
    font-size:13px;
    margin-top:4px;
}

.tema-btn{
    border:none;
    background:#111827;
    color:white;
    padding:11px 16px;
    border-radius:15px;
    cursor:pointer;
    transition:0.25s;
}

.tema-btn:hover{
    transform:scale(1.04);
}

.chat{
    flex:1;
    overflow-y:auto;
    padding:24px;
    background:
        linear-gradient(rgba(255,255,255,0.72),rgba(255,255,255,0.72)),
        radial-gradient(circle at top right,#DBEAFE,transparent 32%);
}

.message{
    max-width:74%;
    padding:15px 17px;
    border-radius:21px;
    margin-bottom:16px;
    line-height:1.5;
    animation:msgIn 0.28s ease;
    font-size:15px;
}

@keyframes msgIn{
    from{
        opacity:0;
        transform:translateY(10px) scale(0.98);
    }
    to{
        opacity:1;
        transform:translateY(0) scale(1);
    }
}

.user{
    background:linear-gradient(135deg,var(--roxo),var(--roxo2));
    color:white;
    margin-left:auto;
    border-bottom-right-radius:7px;
    box-shadow:0 12px 28px rgba(79,70,229,0.22);
}

.bot{
    background:white;
    color:#111827;
    border-bottom-left-radius:7px;
    box-shadow:0 12px 30px rgba(15,23,42,0.08);
    border:1px solid rgba(15,23,42,0.05);
}

.typing{
    display:flex;
    gap:5px;
    align-items:center;
}

.dot{
    width:7px;
    height:7px;
    background:#7C3AED;
    border-radius:50%;
    animation:dot 1s infinite ease-in-out;
}

.dot:nth-child(2){
    animation-delay:0.15s;
}

.dot:nth-child(3){
    animation-delay:0.3s;
}

@keyframes dot{
    0%,80%,100%{
        transform:scale(0.7);
        opacity:0.4;
    }
    40%{
        transform:scale(1);
        opacity:1;
    }
}

.input-area{
    display:flex;
    gap:12px;
    padding:18px;
    background:rgba(255,255,255,0.92);
    border-top:1px solid rgba(15,23,42,0.06);
}

.input-area input{
    flex:1;
    padding:16px;
    border:none;
    border-radius:17px;
    background:#F1F5F9;
    font-size:15px;
    outline:none;
    transition:0.2s;
}

.input-area input:focus{
    box-shadow:0 0 0 2px rgba(124,58,237,0.28);
    background:white;
}

.input-area button{
    padding:16px 28px;
    border:none;
    border-radius:17px;
    background:linear-gradient(135deg,var(--azul),var(--roxo));
    color:white;
    cursor:pointer;
    font-weight:bold;
    transition:0.25s;
    box-shadow:0 10px 24px rgba(6,182,212,0.25);
}

.input-area button:hover{
    transform:translateY(-2px);
}

.dark .main{
    background:rgba(15,23,42,0.94);
}

.dark .top{
    background:#111827;
    color:white;
    border:none;
}

.dark .top h2{
    color:#93C5FD;
}

.dark .subtitle{
    color:#CBD5E1;
}

.dark .chat{
    background:#0F172A;
}

.dark .bot{
    background:#1F2937;
    color:white;
    border:1px solid rgba(255,255,255,0.08);
}

.dark .input-area{
    background:#111827;
    border:none;
}

.dark .input-area input{
    background:#1F2937;
    color:white;
}

.login{
    position:fixed;
    inset:0;
    background:
        radial-gradient(circle at top left,#7C3AED,transparent 34%),
        radial-gradient(circle at bottom right,#06B6D4,transparent 34%),
        #0F172A;
    display:flex;
    justify-content:center;
    align-items:center;
    z-index:999;
}

.login-box{
    width:420px;
    background:rgba(255,255,255,0.92);
    backdrop-filter:blur(18px);
    padding:38px;
    border-radius:30px;
    text-align:center;
    box-shadow:0 35px 90px rgba(0,0,0,0.35);
    animation:loginIn 0.4s ease;
}

@keyframes loginIn{
    from{
        opacity:0;
        transform:translateY(18px) scale(0.98);
    }
    to{
        opacity:1;
        transform:translateY(0) scale(1);
    }
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

.login-box input{
    width:100%;
    padding:15px;
    border:none;
    background:#F1F5F9;
    border-radius:16px;
    margin-top:12px;
    outline:none;
}

.login-box input:focus{
    box-shadow:0 0 0 2px rgba(79,70,229,0.28);
}

.login-box button{
    width:100%;
    margin-top:18px;
    padding:15px;
    border:none;
    border-radius:16px;
    background:linear-gradient(135deg,var(--roxo),var(--azul));
    color:white;
    cursor:pointer;
    font-weight:bold;
    font-size:15px;
}

@media(max-width:800px){

    body{
        overflow:auto;
        background:#0F172A;
    }

    .container{
        height:100vh;
        padding:0;
        display:block;
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
        padding:16px;
    }

    .top h2{
        font-size:20px;
    }

    .subtitle{
        font-size:12px;
    }

    .chat{
        padding:14px;
    }

    .message{
        max-width:90%;
        font-size:14px;
        padding:13px;
        border-radius:16px;
    }

    .input-area{
        padding:10px;
        gap:8px;
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

        <input type="text" id="usuario" placeholder="Digite seu usuário">
        <input type="password" id="senha" placeholder="Digite sua senha">

        <button onclick="login()">Entrar no Calmi</button>
    </div>
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
            <button onclick="novaConversa()">+ Nova conversa</button>
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

            <button class="tema-btn" onclick="toggleTema()">
                🌙 Tema
            </button>
        </div>

        <div class="chat" id="chat">

            <div class="message bot">
                Olá 😊 Eu sou o <strong>Calmi</strong>.<br><br>
                Me conte como você está se sentindo hoje.
            </div>

        </div>

        <div class="input-area">
            <input
                type="text"
                id="mensagem"
                placeholder="Digite sua mensagem..."
            >

            <button onclick="enviarMensagem()">
                Enviar
            </button>
        </div>

    </div>

</div>

<script>

let usuarioAtual = "";
let conversaAtual = "";

function toggleTema(){
    document.body.classList.toggle("dark");
}

function login(){

    let usuario =
        document.getElementById("usuario").value;

    let senha =
        document.getElementById("senha").value;

    if(usuario.trim() === "" || senha.trim() === ""){
        alert("Preencha usuário e senha.");
        return;
    }

    fetch("/login", {
        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            usuario,
            senha
        })
    })

    .then(res => res.json())

    .then(dados => {

        if(dados.status == "ok"){

            usuarioAtual = usuario;

            document.getElementById("login").style.display =
                "none";

            document.getElementById("nomeUsuario").innerText =
                usuario;

            document.getElementById("avatar").innerText =
                usuario[0].toUpperCase();

            novaConversa();
            carregarConversas();
        }
    });
}

function novaConversa(){

    conversaAtual = crypto.randomUUID();

    document.getElementById("titulo").innerText =
        "Nova conversa";

    document.getElementById("chat").innerHTML = `
        <div class="message bot">
            Olá 😊 Eu sou o <strong>Calmi</strong>.<br><br>
            Como você está se sentindo hoje?
        </div>
    `;
}

async function enviarMensagem(){

    let input =
        document.getElementById("mensagem");

    let mensagem = input.value;

    if(mensagem.trim() == "") return;

    let chat =
        document.getElementById("chat");

    chat.innerHTML += `
        <div class="message user">
            ${mensagem}
        </div>
    `;

    input.value = "";

    let botDiv =
        document.createElement("div");

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
            usuario:usuarioAtual,
            conversa:conversaAtual,
            mensagem:mensagem
        })
    });

    let dados = await resposta.json();

    botDiv.innerHTML = "";

    let texto = dados.resposta;
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

function carregarConversas(){

    fetch("/conversas/" + usuarioAtual)

    .then(res => res.json())

    .then(dados => {

        let lista =
            document.getElementById("listaChats");

        lista.innerHTML = "";

        dados.forEach(conversa => {

            lista.innerHTML += `
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
        });
    });
}

function abrirConversa(id){

    fetch("/abrir/" + id)

    .then(res => res.json())

    .then(dados => {

        conversaAtual = id;

        let chat =
            document.getElementById("chat");

        chat.innerHTML = "";

        dados.mensagens.forEach(msg => {

            chat.innerHTML += `
                <div class="message ${msg.tipo}">
                    ${msg.texto}
                </div>
            `;
        });
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

</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/login", methods=["POST"])
def login():

    dados = request.get_json()

    usuario = dados["usuario"]
    senha = dados["senha"]

    cursor.execute(
        "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
        (usuario, senha)
    )

    existe = cursor.fetchone()

    if not existe:

        cursor.execute(
            "INSERT INTO usuarios(usuario, senha) VALUES (?, ?)",
            (usuario, senha)
        )

        conn.commit()

    return jsonify({
        "status":"ok"
    })

@app.route("/chat", methods=["POST"])
def chat():

    try:

        dados = request.get_json()

        usuario = dados["usuario"]
        conversa = dados["conversa"]
        mensagem = dados["mensagem"]

        cursor.execute(
            "SELECT * FROM conversas WHERE id=?",
            (conversa,)
        )

        existe = cursor.fetchone()

        if not existe:

            cursor.execute(
                "INSERT INTO conversas VALUES (?, ?, ?)",
                (
                    conversa,
                    usuario,
                    mensagem[:30]
                )
            )

        cursor.execute(
            "INSERT INTO mensagens VALUES (?, ?, ?)",
            (
                conversa,
                "user",
                mensagem
            )
        )

        cursor.execute(
            "SELECT memoria FROM memoria WHERE usuario=?",
            (usuario,)
        )

        memorias = cursor.fetchall()

        contexto = ""

        for memoria in memorias:
            contexto += memoria[0] + "\\n"

        resposta = client.chat.completions.create(

            model="llama-3.1-8b-instant",

            messages=[

                {
                    "role":"system",

                    "content":f'''
Você é o Calmi.

Uma IA emocional acolhedora.

Regras:
- Fale em português brasileiro.
- Seja gentil.
- Seja humano.
- Responda naturalmente.
- Use emojis às vezes.
- Não seja frio.
- Responda curto e acolhedor.

Memórias:
{contexto}
'''
                },

                {
                    "role":"user",
                    "content":mensagem
                }
            ]
        )

        resposta_texto =resposta.choices[0].message.content

        cursor.execute(
            "INSERT INTO mensagens VALUES (?, ?, ?)",
            (
                conversa,
                "bot",
                resposta_texto
            )
        )

        conn.commit()

        return jsonify({
            "resposta":resposta_texto
        })

    except Exception as erro:

        print(erro)

        return jsonify({
            "resposta":"Erro ao conectar com a IA 😔"
        })

@app.route("/conversas/<usuario>")
def listar_conversas(usuario):

    cursor.execute(
        "SELECT * FROM conversas WHERE usuario=?",
        (usuario,)
    )

    resultados = cursor.fetchall()

    lista = []

    for conversa in resultados:

        lista.append({
            "id":conversa[0],
            "nome":conversa[2]
        })

    return jsonify(lista)

@app.route("/abrir/<id>")
def abrir(id):

    cursor.execute(
        "SELECT * FROM mensagens WHERE conversa_id=?",
        (id,)
    )

    mensagens = cursor.fetchall()

    lista = []

    for msg in mensagens:

        lista.append({
            "tipo":msg[1],
            "texto":msg[2]
        })

    return jsonify({
        "mensagens":lista
    })

@app.route("/deletar/<id>")
def deletar(id):

    cursor.execute(
        "DELETE FROM mensagens WHERE conversa_id=?",
        (id,)
    )

    cursor.execute(
        "DELETE FROM conversas WHERE id=?",
        (id,)
    )

    conn.commit()

    return jsonify({
        "status":"ok"
    })

if __name__ == "__main__":
    app.run(debug=True)