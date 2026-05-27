from flask import Flask, request, jsonify, render_template_string
from groq import Groq
import sqlite3
import os
from datetime import datetime

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
CREATE TABLE IF NOT EXISTS mensagens_memoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversa_id TEXT,
    usuario TEXT,
    data TEXT,
    horario TEXT,
    remetente TEXT,
    conteudo TEXT,
    nivel_emocional TEXT
)
""")

conn.commit()


def buscar_historico(usuario, limite=20):
    cursor.execute("""
        SELECT remetente, conteudo, nivel_emocional, data, horario
        FROM mensagens_memoria
        WHERE usuario=?
        ORDER BY id DESC
        LIMIT ?
    """, (usuario, limite))
    return cursor.fetchall()


def salvar_mensagem(conversa_id, usuario, remetente, conteudo, nivel_emocional):
    agora = datetime.now()

    cursor.execute("""
        INSERT INTO mensagens_memoria
        (conversa_id, usuario, data, horario, remetente, conteudo, nivel_emocional)
        VALUES (?, ?, ?, ?, ?, ?, ?)
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


def analisar_risco_emocional(texto, historico):
    texto_lower = texto.lower()

    leve = ["cansado", "triste", "preocupado", "desanimado", "estressado"]

    moderado = [
        "ansioso", "ansiedade", "medo", "sozinho", "isolado",
        "sem energia", "não consigo dormir", "insônia"
    ]

    elevado = [
        "desesperança", "não aguento", "muito mal",
        "sem saída", "colapso", "não consigo continuar"
    ]

    critico = [
        "não quero mais viver",
        "quero sumir",
        "não vejo saída",
        "vou me machucar"
    ]

    pontos = 0

    for palavra in leve:
        if palavra in texto_lower:
            pontos += 1

    for palavra in moderado:
        if palavra in texto_lower:
            pontos += 2

    for palavra in elevado:
        if palavra in texto_lower:
            pontos += 4

    for palavra in critico:
        if palavra in texto_lower:
            pontos += 8

    historico_texto = " ".join([
        h[1].lower()
        for h in historico
        if h[0] == "user"
    ])

    repeticoes = [
        "triste", "ansioso", "ansiedade", "sozinho",
        "cansado", "sem energia", "não consigo dormir"
    ]

    for palavra in repeticoes:
        if historico_texto.count(palavra) >= 3:
            pontos += 2

    if pontos >= 8:
        return "crítico"
    elif pontos >= 5:
        return "elevado"
    elif pontos >= 2:
        return "moderado"
    else:
        return "leve"


def sugerir_profissional(texto, historico, nivel_risco):
    texto_lower = texto.lower()

    if nivel_risco == "crítico":
        return {
            "tipo_profissional": "Ajuda humana imediata",
            "motivo": "A mensagem indica necessidade de apoio humano imediato.",
            "urgencia": "crítica"
        }

    if "ansiedade" in texto_lower or "ansioso" in texto_lower or "medo" in texto_lower:
        return {
            "tipo_profissional": "Psicólogo especializado em ansiedade",
            "motivo": "Pode ajudar em medo, tensão ou preocupação frequente.",
            "urgencia": nivel_risco
        }

    if "família" in texto_lower or "mãe" in texto_lower or "pai" in texto_lower:
        return {
            "tipo_profissional": "Psicólogo familiar",
            "motivo": "Pode ajudar em conflitos ou dificuldades familiares.",
            "urgencia": nivel_risco
        }

    if "escola" in texto_lower or "prova" in texto_lower or "professor" in texto_lower:
        return {
            "tipo_profissional": "Psicólogo escolar ou orientador educacional",
            "motivo": "Pode ajudar em dificuldades emocionais ligadas aos estudos.",
            "urgencia": nivel_risco
        }

    if "perdi" in texto_lower or "luto" in texto_lower or "morreu" in texto_lower:
        return {
            "tipo_profissional": "Psicólogo especializado em luto",
            "motivo": "Pode ajudar a lidar com perdas e sofrimento emocional.",
            "urgencia": nivel_risco
        }

    return {
        "tipo_profissional": "Psicólogo clínico",
        "motivo": "Pode ajudar a compreender sentimentos persistentes.",
        "urgencia": nivel_risco
    }


def resumir_contexto(historico):
    if not historico:
        return "Sem histórico emocional anterior."

    niveis = [h[2] for h in historico]
    mensagens_usuario = [h[1] for h in historico if h[0] == "user"]

    resumo = ""

    if niveis.count("moderado") >= 2 or niveis.count("elevado") >= 1:
        resumo += "O usuário vem demonstrando sinais emocionais recorrentes. "

    if any("cansado" in m.lower() for m in mensagens_usuario):
        resumo += "Há menções de cansaço emocional. "

    if any("sozinho" in m.lower() for m in mensagens_usuario):
        resumo += "Há sinais de isolamento ou solidão. "

    if any("ansioso" in m.lower() or "ansiedade" in m.lower() for m in mensagens_usuario):
        resumo += "Há sinais de ansiedade ou preocupação frequente. "

    if any("não consigo dormir" in m.lower() or "insônia" in m.lower() for m in mensagens_usuario):
        resumo += "Há sinais de dificuldade para dormir. "

    return resumo if resumo else "Histórico sem padrão emocional forte."


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
}

body{
    font-family:Arial, Helvetica, sans-serif;
    height:100vh;
    overflow:hidden;
    background:
        radial-gradient(circle at top left, rgba(124,58,237,0.55), transparent 34%),
        radial-gradient(circle at bottom right, rgba(6,182,212,0.45), transparent 34%),
        linear-gradient(135deg,#0F172A,#111827);
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
    font-weight:bold;
}

.chats{
    flex:1;
    overflow-y:auto;
    margin-top:20px;
}

.chat-item{
    background:rgba(31,41,55,0.92);
    padding:13px 42px 13px 13px;
    border-radius:16px;
    margin-bottom:10px;
    cursor:pointer;
    position:relative;
    color:#E5E7EB;
    font-size:14px;
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
}

.main{
    flex:1;
    display:flex;
    flex-direction:column;
    background:rgba(248,250,252,0.92);
    border-radius:28px;
    overflow:hidden;
    box-shadow:0 25px 70px rgba(0,0,0,0.25);
}

.top{
    padding:20px 24px;
    background:rgba(255,255,255,0.86);
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

.tema-btn,
.mobile-history-btn{
    border:none;
    background:#111827;
    color:white;
    padding:11px 16px;
    border-radius:15px;
    cursor:pointer;
}

.mobile-history-btn{
    display:none;
    background:linear-gradient(135deg,var(--roxo),var(--azul));
}

.mobile-history{
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
    animation:msgIn 0.25s ease;
}

@keyframes msgIn{
    from{
        opacity:0;
        transform:translateY(10px);
    }
    to{
        opacity:1;
        transform:translateY(0);
    }
}

.user{
    background:linear-gradient(135deg,var(--roxo),var(--roxo2));
    color:white;
    margin-left:auto;
}

.bot{
    background:white;
    color:#111;
}

.typing{
    display:flex;
    gap:5px;
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
    gap:10px;
    padding:16px;
    background:white;
}

.input-area input{
    flex:1;
    padding:15px;
    border:none;
    border-radius:15px;
    background:#F1F5F9;
}

.input-area button{
    border:none;
    padding:15px 25px;
    border-radius:15px;
    background:linear-gradient(135deg,var(--azul),var(--roxo));
    color:white;
    cursor:pointer;
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
    padding:38px;
    border-radius:30px;
    text-align:center;
    box-shadow:0 35px 90px rgba(0,0,0,0.35);
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
}

@media(max-width:800px){

    body{
        overflow:hidden;
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
        padding:14px;
        gap:10px;
    }

    .top h2{
        font-size:19px;
    }

    .subtitle{
        font-size:12px;
    }

    .mobile-history-btn{
        display:block;
        padding:10px 12px;
        font-size:13px;
    }

    .mobile-history{
        display:none;
        position:fixed;
        top:72px;
        left:10px;
        right:10px;
        max-height:55vh;
        overflow-y:auto;
        background:#111827;
        color:white;
        z-index:999;
        padding:15px;
        border-radius:18px;
        box-shadow:0 20px 50px rgba(0,0,0,0.35);
    }

    .mobile-history.open{
        display:block;
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

<div class="mobile-history" id="mobileHistory">
    <h3>Conversas</h3>
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
            <button onclick="novaConversa()">+ Nova conversa</button>
        </div>

        <div class="chats" id="listaChats"></div>
    </div>

    <div class="main">

        <div class="top">
            <div>
                <h2 id="titulo">Nova conversa</h2>
                <div class="subtitle">O Calmi está aqui para te ouvir 💙</div>
            </div>

            <button class="mobile-history-btn" onclick="toggleHistoricoMobile()">☰ Histórico</button>
            <button class="tema-btn" onclick="toggleTema()">🌙</button>
        </div>

        <div class="chat" id="chat">
            <div class="message bot">
                Olá 😊 Eu sou o Calmi.<br><br>
                Como você está se sentindo hoje?
            </div>
        </div>

        <div class="input-area">
            <input id="mensagem" placeholder="Digite aqui...">
            <button onclick="enviarMensagem()">Enviar</button>
        </div>

    </div>

</div>

<script>
let usuarioAtual="";
let conversaAtual=crypto.randomUUID();

function toggleTema(){
    document.body.classList.toggle("dark");
}

function toggleHistoricoMobile(){
    document.getElementById("mobileHistory").classList.toggle("open");
}

function login(){
    let usuario=document.getElementById("usuario").value;
    let senha=document.getElementById("senha").value;

    if(usuario.trim()==="" || senha.trim()===""){
        alert("Preencha usuário e senha.");
        return;
    }

    fetch("/login",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({usuario,senha})
    })
    .then(res=>res.json())
    .then(dados=>{
        if(dados.status==="ok"){
            usuarioAtual=usuario;
            document.getElementById("login").style.display="none";
            document.getElementById("nomeUsuario").innerText=usuario;
            document.getElementById("avatar").innerText=usuario[0].toUpperCase();
            novaConversa();
            carregarConversas();
        }
    });
}

function novaConversa(){
    conversaAtual=crypto.randomUUID();

    document.getElementById("titulo").innerText="Nova conversa";

    document.getElementById("chat").innerHTML=`
        <div class="message bot">
            Olá 😊 Eu sou o Calmi.<br><br>
            Como você está se sentindo hoje?
        </div>
    `;
}

async function enviarMensagem(){
    let input=document.getElementById("mensagem");
    let mensagem=input.value;

    if(mensagem.trim()==="") return;

    let chat=document.getElementById("chat");

    chat.innerHTML+=`
        <div class="message user">
            ${mensagem}
        </div>
    `;

    input.value="";

    let botDiv=document.createElement("div");
    botDiv.className="message bot";
    botDiv.innerHTML=`
        <div class="typing">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;

    chat.appendChild(botDiv);
    chat.scrollTop=chat.scrollHeight;

    let resposta=await fetch("/chat",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            usuario:usuarioAtual,
            conversa:conversaAtual,
            mensagem:mensagem
        })
    });

    let dados=await resposta.json();

    botDiv.innerHTML="";

    let texto=dados.resposta;
    let i=0;

    let intervalo=setInterval(()=>{
        botDiv.innerHTML+=texto[i];
        i++;
        chat.scrollTop=chat.scrollHeight;

        if(i>=texto.length){
            clearInterval(intervalo);
        }
    },12);

    carregarConversas();
}

function carregarConversas(){
    fetch("/conversas/"+usuarioAtual)
    .then(res=>res.json())
    .then(dados=>{
        let lista=document.getElementById("listaChats");
        let listaMobile=document.getElementById("listaChatsMobile");

        if(lista) lista.innerHTML="";
        if(listaMobile) listaMobile.innerHTML="";

        dados.forEach(conversa=>{
            let item=`
                <div class="chat-item">
                    <div onclick="abrirConversa('${conversa.id}')">
                        ${conversa.nome}
                    </div>

                    <button class="delete-btn" onclick="deletarConversa('${conversa.id}')">
                        x
                    </button>
                </div>
            `;

            if(lista) lista.innerHTML+=item;
            if(listaMobile) listaMobile.innerHTML+=item;
        });
    });
}

function abrirConversa(id){
    fetch("/abrir/"+id)
    .then(res=>res.json())
    .then(dados=>{
        conversaAtual=id;

        document.getElementById("mobileHistory").classList.remove("open");

        let chat=document.getElementById("chat");
        chat.innerHTML="";

        dados.mensagens.forEach(msg=>{
            chat.innerHTML+=`
                <div class="message ${msg.tipo}">
                    ${msg.texto}
                </div>
            `;
        });
    });
}

function deletarConversa(id){
    fetch("/deletar/"+id)
    .then(()=>{
        carregarConversas();
        novaConversa();
    });
}

document.getElementById("mensagem").addEventListener("keypress",function(e){
    if(e.key==="Enter"){
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
    dados=request.get_json()

    usuario=dados["usuario"]
    senha=dados["senha"]

    cursor.execute(
        "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
        (usuario, senha)
    )

    existe=cursor.fetchone()

    if not existe:
        cursor.execute(
            "INSERT INTO usuarios(usuario, senha) VALUES (?, ?)",
            (usuario, senha)
        )
        conn.commit()

    return jsonify({"status":"ok"})


@app.route("/chat", methods=["POST"])
def chat():
    try:
        dados=request.get_json()

        usuario=dados["usuario"]
        conversa=dados["conversa"]
        mensagem=dados["mensagem"]

        historico=buscar_historico(usuario)
        risco=analisar_risco_emocional(mensagem,historico)
        profissional=sugerir_profissional(mensagem,historico,risco)
        contexto=resumir_contexto(historico)

        cursor.execute(
            "SELECT * FROM conversas WHERE id=?",
            (conversa,)
        )

        existe=cursor.fetchone()

        if not existe:
            cursor.execute(
                "INSERT INTO conversas VALUES (?, ?, ?)",
                (conversa, usuario, mensagem[:30])
            )

        cursor.execute(
            "INSERT INTO mensagens VALUES (?, ?, ?)",
            (conversa, "user", mensagem)
        )

        salvar_mensagem(conversa, usuario, "user", mensagem, risco)

        if risco=="crítico":
            resposta_texto=(
                "💙 Eu percebo que você pode estar passando por algo muito pesado. "
                "Você não precisa enfrentar isso sozinho. "
                "Procure agora alguém de confiança, um responsável ou ajuda profissional. "
                "No Brasil, o CVV atende pelo 188."
            )
        else:
            prompt=f"""
Você é o Calmi.

Contexto emocional recente:
{contexto}

Nível emocional detectado:
{risco}

Sugestão profissional:
{profissional["tipo_profissional"]}

Regras:
- Seja acolhedor.
- Não diagnostique.
- Não substitua terapia.
- Fale em português brasileiro.
- Responda de forma curta, humana e natural.

Mensagem:
{mensagem}
"""

            resposta=client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role":"system","content":prompt},
                    {"role":"user","content":mensagem}
                ]
            )

            resposta_texto=resposta.choices[0].message.content

            if risco=="elevado":
                resposta_texto+=(
                    "<br><br>💙 Pode ser útil conversar com "
                    f"{profissional['tipo_profissional']}. "
                    "Você merece apoio de verdade."
                )

        cursor.execute(
            "INSERT INTO mensagens VALUES (?, ?, ?)",
            (conversa, "bot", resposta_texto)
        )

        salvar_mensagem(conversa, usuario, "bot", resposta_texto, risco)

        conn.commit()

        return jsonify({"resposta":resposta_texto})

    except Exception as erro:
        print(erro)
        return jsonify({"resposta":"Erro ao conectar com a IA 😔"})


@app.route("/conversas/<usuario>")
def listar_conversas(usuario):
    cursor.execute(
        "SELECT * FROM conversas WHERE usuario=?",
        (usuario,)
    )

    resultados=cursor.fetchall()

    lista=[]

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

    mensagens=cursor.fetchall()

    lista=[]

    for msg in mensagens:
        lista.append({
            "tipo":msg[1],
            "texto":msg[2]
        })

    return jsonify({"mensagens":lista})


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

    return jsonify({"status":"ok"})


if __name__=="__main__":
    app.run(debug=True)