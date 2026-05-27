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

body{
    font-family:Arial, Helvetica, sans-serif;
    height:100vh;
    overflow:hidden;
    background:#0F172A;
}

.container{
    display:flex;
    width:100%;
    height:100vh;
}

.sidebar{
    width:300px;
    background:#111827;
    color:white;
    display:flex;
    flex-direction:column;
    padding:15px;
}

.logo{
    text-align:center;
    padding:15px;
}

.logo h1{
    font-size:45px;
    color:#60A5FA;
}

.logo p{
    color:#9CA3AF;
}

.profile{
    display:flex;
    align-items:center;
    gap:10px;
    margin-top:20px;
    background:#1F2937;
    padding:10px;
    border-radius:15px;
}

.avatar{
    width:50px;
    height:50px;
    border-radius:50%;
    background:#4F46E5;
    display:flex;
    justify-content:center;
    align-items:center;
    font-weight:bold;
}

.new-chat button{
    width:100%;
    margin-top:20px;
    padding:14px;
    border:none;
    background:#4F46E5;
    color:white;
    border-radius:12px;
    cursor:pointer;
    font-weight:bold;
}

.chats{
    flex:1;
    overflow-y:auto;
    margin-top:20px;
}

.chat-item{
    background:#1F2937;
    padding:12px;
    border-radius:12px;
    margin-bottom:10px;
    cursor:pointer;
    position:relative;
}

.delete-btn{
    position:absolute;
    right:10px;
    top:10px;
    border:none;
    width:22px;
    height:22px;
    border-radius:50%;
    background:red;
    color:white;
    cursor:pointer;
}

.main{
    flex:1;
    display:flex;
    flex-direction:column;
    background:#F3F4F6;
}

.top{
    padding:20px;
    background:white;
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.top h2{
    color:#4F46E5;
}

.subtitle{
    color:#64748B;
    font-size:13px;
}

.tema-btn{
    border:none;
    background:#111827;
    color:white;
    padding:10px 15px;
    border-radius:10px;
    cursor:pointer;
}

.chat{
    flex:1;
    overflow-y:auto;
    padding:20px;
}

.message{
    max-width:75%;
    padding:14px;
    border-radius:15px;
    margin-bottom:15px;
    line-height:1.5;
    animation:fade 0.3s ease;
}

.user{
    background:#4F46E5;
    color:white;
    margin-left:auto;
}

.bot{
    background:white;
    color:#111;
    box-shadow:0 0 10px rgba(0,0,0,0.05);
}

.input-area{
    display:flex;
    gap:10px;
    padding:15px;
    background:white;
}

.input-area input{
    flex:1;
    padding:14px;
    border:none;
    border-radius:12px;
    background:#F3F4F6;
    font-size:15px;
}

.input-area button{
    padding:14px 25px;
    border:none;
    border-radius:12px;
    background:#06B6D4;
    color:white;
    cursor:pointer;
    font-weight:bold;
}

.dark .main{
    background:#0F172A;
}

.dark .top{
    background:#111827;
    color:white;
}

.dark .bot{
    background:#1F2937;
    color:white;
}

.dark .input-area{
    background:#111827;
}

.dark .input-area input{
    background:#1F2937;
    color:white;
}

.login{
    position:fixed;
    inset:0;
    background:linear-gradient(135deg,#4F46E5,#7C3AED,#06B6D4);
    display:flex;
    justify-content:center;
    align-items:center;
    z-index:999;
}

.login-box{
    width:400px;
    background:white;
    padding:35px;
    border-radius:20px;
    text-align:center;
}

.login-box h1{
    font-size:50px;
    color:#4F46E5;
}

.login-box p{
    color:gray;
    margin-bottom:20px;
}

.login-box input{
    width:100%;
    padding:14px;
    border:none;
    background:#eee;
    border-radius:12px;
    margin-top:10px;
}

.login-box button{
    width:100%;
    margin-top:15px;
    padding:14px;
    border:none;
    border-radius:12px;
    background:#4F46E5;
    color:white;
    cursor:pointer;
    font-weight:bold;
}

@keyframes fade{
    from{
        opacity:0;
        transform:translateY(10px);
    }

    to{
        opacity:1;
        transform:translateY(0px);
    }
}

/* CELULAR */

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

        <input type="text" id="usuario" placeholder="Usuário">
        <input type="password" id="senha" placeholder="Senha">

        <button onclick="login()">Entrar</button>
    </div>
</div>

<div class="container">

    <div class="sidebar">
        <div class="logo">
            <h1>Calmi</h1>
            <p>IA emocional</p>
        </div>

        <div class="profile">
            <div class="avatar" id="avatar">C</div>
            <div>
                <h3 id="nomeUsuario">Usuário</h3>
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
                <div class="subtitle">O Calmi está aqui para te ouvir.</div>
            </div>

            <button class="tema-btn" onclick="toggleTema()">🌙</button>
        </div>

        <div class="chat" id="chat">
            <div class="message bot">
                Olá 😊 Eu sou o Calmi.<br><br>
                Como você está se sentindo hoje?
            </div>
        </div>

        <div class="input-area">
            <input type="text" id="mensagem" placeholder="Converse com o Calmi...">
            <button onclick="enviarMensagem()">Enviar</button>
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
    let usuario = document.getElementById("usuario").value;
    let senha = document.getElementById("senha").value;

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

            document.getElementById("login").style.display = "none";
            document.getElementById("nomeUsuario").innerText = usuario;
            document.getElementById("avatar").innerText = usuario[0].toUpperCase();

            novaConversa();
            carregarConversas();
        }
    });
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

async function enviarMensagem(){
    let input = document.getElementById("mensagem");
    let mensagem = input.value;

    if(mensagem.trim() == "") return;

    let chat = document.getElementById("chat");

    chat.innerHTML += `
        <div class="message user">
            ${mensagem}
        </div>
    `;

    input.value = "";

    let botDiv = document.createElement("div");
    botDiv.className = "message bot";
    botDiv.innerHTML = "Calmi está pensando...";
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
    }, 15);

    carregarConversas();
}

function carregarConversas(){
    fetch("/conversas/" + usuarioAtual)
    .then(res => res.json())
    .then(dados => {
        let lista = document.getElementById("listaChats");
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
                    >x</button>
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

        let chat = document.getElementById("chat");
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

document.getElementById("mensagem").addEventListener("keypress", function(e){
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

        palavras_emocao = [
            "triste",
            "sozinho",
            "depressivo",
            "desanimado",
            "ansioso",
            "ansiedade",
            "medo",
            "raiva",
            "cansado",
            "preocupado"
        ]

        if any(p in mensagem.lower() for p in palavras_emocao):
            cursor.execute(
                "INSERT INTO memoria VALUES (?, ?)",
                (
                    usuario,
                    "Usuário demonstrou uma emoção forte ou dificuldade emocional."
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

        conn.commit()

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
- Seja gentil, humano e acolhedor.
- Responda de forma natural.
- Use emojis às vezes.
- Não seja frio.
- Não diga que é psicólogo.
- Não substitua ajuda profissional.
- Responda em poucas frases.

Memórias do usuário:
{contexto}
'''
                },
                {
                    "role":"user",
                    "content":mensagem
                }
            ]
        )

        resposta_texto = resposta.choices[0].message.content

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