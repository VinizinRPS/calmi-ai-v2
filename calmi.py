from flask import Flask, request, jsonify, render_template_string
from groq import Groq
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

conn = sqlite3.connect("calmi.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, senha TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS conversas (id TEXT, usuario TEXT, nome TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS mensagens (conversa_id TEXT, tipo TEXT, texto TEXT)")
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
    texto = texto.lower()

    palavras = {
        "leve": ["cansado", "triste", "preocupado", "desanimado", "estressado"],
        "moderado": ["ansioso", "ansiedade", "medo", "sozinho", "isolado", "sem energia", "insônia", "não consigo dormir"],
        "elevado": ["desesperança", "não aguento", "muito mal", "sem saída", "colapso", "não consigo continuar"],
        "critico": ["não quero mais viver", "quero sumir", "não vejo saída"]
    }

    pontos = 0

    for p in palavras["leve"]:
        if p in texto:
            pontos += 1

    for p in palavras["moderado"]:
        if p in texto:
            pontos += 2

    for p in palavras["elevado"]:
        if p in texto:
            pontos += 4

    for p in palavras["critico"]:
        if p in texto:
            pontos += 8

    historico_texto = " ".join([h[1].lower() for h in historico if h[0] == "user"])

    for p in ["triste", "ansioso", "sozinho", "cansado", "sem energia", "não consigo dormir"]:
        if historico_texto.count(p) >= 3:
            pontos += 2

    if pontos >= 8:
        return "crítico"
    if pontos >= 5:
        return "elevado"
    if pontos >= 2:
        return "moderado"
    return "leve"

def sugerir_profissional(texto, nivel_risco):
    texto = texto.lower()

    if nivel_risco == "crítico":
        return "Ajuda humana imediata"

    if "ansiedade" in texto or "ansioso" in texto or "medo" in texto:
        return "Psicólogo especializado em ansiedade"

    if "família" in texto or "mãe" in texto or "pai" in texto:
        return "Psicólogo familiar"

    if "escola" in texto or "prova" in texto or "professor" in texto:
        return "Psicólogo escolar ou orientador educacional"

    if "luto" in texto or "perdi" in texto or "morreu" in texto:
        return "Psicólogo especializado em luto"

    return "Psicólogo clínico"

def resumir_contexto(historico):
    if not historico:
        return "Sem histórico emocional anterior."

    textos = [h[1].lower() for h in historico if h[0] == "user"]
    resumo = ""

    if any("cansado" in t for t in textos):
        resumo += "O usuário mencionou cansaço emocional. "

    if any("sozinho" in t for t in textos):
        resumo += "O usuário mencionou solidão ou isolamento. "

    if any("ansioso" in t or "ansiedade" in t for t in textos):
        resumo += "O usuário mencionou ansiedade ou preocupação. "

    if any("não consigo dormir" in t or "insônia" in t for t in textos):
        resumo += "O usuário mencionou dificuldade para dormir. "

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
    --fundo:#0F172A;
    --card:#111827;
    --claro:#F8FAFC;
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
    background:rgba(17,24,39,.88);
    color:white;
    border-radius:28px;
    padding:18px;
    display:flex;
    flex-direction:column;
    box-shadow:0 25px 70px rgba(0,0,0,.35);
    backdrop-filter:blur(16px);
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

.new-chat button{
    width:100%;
    margin-top:20px;
    padding:15px;
    border:none;
    border-radius:17px;
    background:linear-gradient(135deg,var(--roxo),var(--roxo2));
    color:white;
    font-weight:bold;
    cursor:pointer;
}

.chats{
    flex:1;
    overflow-y:auto;
    margin-top:20px;
    padding-right:4px;
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

.chat-item:hover{
    background:#374151;
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
    background:rgba(248,250,252,.94);
    border-radius:28px;
    overflow:hidden;
    box-shadow:0 25px 70px rgba(0,0,0,.25);
}

.top{
    padding:20px 24px;
    background:rgba(255,255,255,.9);
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
.mobile-history-btn{
    border:none;
    padding:11px 14px;
    border-radius:14px;
    background:#111827;
    color:white;
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
    padding-bottom:24px;
}

.message{
    max-width:75%;
    padding:15px;
    border-radius:18px;
    margin-bottom:14px;
    line-height:1.5;
    animation:msgIn .25s ease;
    word-wrap:break-word;
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

.dot:nth-child(2){animation-delay:.15s;}
.dot:nth-child(3){animation-delay:.3s;}

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
    width:100%;
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
    width:420px;
    background:rgba(255,255,255,.94);
    padding:38px;
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

.login-box input{
    width:100%;
    padding:15px;
    border:none;
    background:#F1F5F9;
    border-radius:16px;
    margin-top:12px;
    outline:none;
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

    .mobile-history-btn{
        display:block;
        font-size:13px;
        padding:10px 12px;
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
        box-shadow:0 20px 50px rgba(0,0,0,.35);
    }

    .mobile-history.open{
        display:block;
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

            <div class="top-actions">
                <button class="mobile-history-btn" onclick="toggleHistoricoMobile()">☰</button>
                <button class="tema-btn" onclick="toggleTema()">🌙</button>
            </div>
        </div>

        <div class="chat" id="chat">
            <div class="message bot">
                Olá 😊 Eu sou o Calmi.<br><br>
                Como você está se sentindo hoje?
            </div>
        </div>

        <div class="input-area">
            <input type="text" id="mensagem" placeholder="Digite sua mensagem..." autocomplete="off">
            <button type="button" onclick="enviarMensagem()">Enviar</button>
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

    let texto=dados.resposta || "Não consegui responder agora.";
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

        chat.scrollTop=chat.scrollHeight;
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
        profissional=sugerir_profissional(mensagem,risco)
        contexto=resumir_contexto(historico)

        cursor.execute("SELECT * FROM conversas WHERE id=?", (conversa,))
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
                    f"{profissional}. Você merece apoio de verdade."
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