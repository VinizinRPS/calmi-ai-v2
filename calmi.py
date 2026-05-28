from flask import Flask, request, jsonify, render_template_string, session
from groq import Groq
import psycopg2
import psycopg2.extras
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "calmi-dev-secret")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


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


def analisar_risco_emocional(texto, historico):
    texto = texto.lower()

    pontos = 0

    leve = ["cansado", "triste", "preocupado", "desanimado"]
    moderado = ["ansioso", "ansiedade", "medo", "sozinho", "sem energia", "não consigo dormir"]
    elevado = ["não aguento", "muito mal", "sem saída", "colapso", "não consigo continuar"]
    critico = ["não quero mais viver", "quero sumir", "não vejo saída"]

    for p in leve:
        if p in texto:
            pontos += 1

    for p in moderado:
        if p in texto:
            pontos += 2

    for p in elevado:
        if p in texto:
            pontos += 4

    for p in critico:
        if p in texto:
            pontos += 8

    historico_texto = " ".join([
        h["conteudo"].lower()
        for h in historico
        if h["remetente"] == "user"
    ])

    for p in ["triste", "ansioso", "sozinho", "cansado", "sem energia"]:
        if historico_texto.count(p) >= 3:
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

    if any("cansado" in t for t in textos):
        resumo += "O usuário mencionou cansaço emocional. "

    if any("sozinho" in t for t in textos):
        resumo += "O usuário mencionou solidão ou isolamento. "

    if any("ansioso" in t or "ansiedade" in t for t in textos):
        resumo += "O usuário mencionou ansiedade ou preocupação. "

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
padding:14px;
border:none;
border-radius:15px;
background:#F1F5F9;
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
}

.login{
position:fixed;
inset:0;
display:flex;
align-items:center;
justify-content:center;
background:
radial-gradient(circle at top left,#7C3AED,transparent 35%),
radial-gradient(circle at bottom right,#06B6D4,transparent 35%),
#0F172A;
z-index:999;
}

.login-box{
width:430px;
background:rgba(255,255,255,.95);
padding:40px;
border-radius:30px;
text-align:center;
}

.tabs{
display:flex;
gap:10px;
margin-bottom:25px;
}

.tab{
flex:1;
padding:12px;
border:none;
border-radius:12px;
cursor:pointer;
font-weight:bold;
}

.activeTab{
background:linear-gradient(135deg,var(--roxo),var(--azul));
color:white;
}

.login-box h1{
font-size:56px;

background:
linear-gradient(
135deg,
var(--roxo),
var(--roxo2),
var(--azul)
);

-webkit-background-clip:text;

color:transparent;
}

.login-box input{

width:100%;

padding:15px;

margin-top:12px;

border:none;

border-radius:15px;

background:#F1F5F9;

outline:none;

}

.login-btn{

width:100%;

padding:15px;

margin-top:18px;

border:none;

border-radius:15px;

background:
linear-gradient(
135deg,
var(--roxo),
var(--azul)
);

color:white;

font-weight:bold;

cursor:pointer;

}

.error{

margin-top:12px;

color:red;

font-size:14px;

}

.loading{

opacity:.7;

pointer-events:none;

}

@media(max-width:800px){

.container{
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

.mobile-menu-btn{
display:block;
}

.chat{
padding:14px;
padding-bottom:90px;
}

.message{
max-width:90%;
font-size:14px;
}

.input-area{
position:fixed;
left:0;
right:0;
bottom:0;
}

.login-box{
width:92%;
padding:30px;
}

.login-box h1{
font-size:45px;
}

}
</style>
</head>

<body>

<div class="login" id="login">

<div class="login-box">

<h1>Calmi</h1>

<p>
Sua IA emocional 💙
</p>

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
id="usuario"
placeholder="Usuário"
>

<input
id="senha"
type="password"
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

""" + HTML.split("</body>")[0].split("<body>")[1] + """

<script>

let modo="login";

function mudarTab(tipo){

modo=tipo;

document
.getElementById("tabLogin")
.classList.remove("activeTab");

document
.getElementById("tabCadastro")
.classList.remove("activeTab");

if(tipo=="login"){

document
.getElementById("tabLogin")
.classList.add("activeTab");

document
.getElementById("botaoLogin")
.innerText="Entrar";

}else{

document
.getElementById("tabCadastro")
.classList.add("activeTab");

document
.getElementById("botaoLogin")
.innerText="Criar Conta";

}

document
.getElementById("erro")
.innerText="";

}

async function enviarAuth(){

let usuario=
document.getElementById("usuario").value;

let senha=
document.getElementById("senha").value;

if(usuario.trim()=="" || senha.trim()==""){

document
.getElementById("erro")
.innerText="Preencha tudo.";

return;

}

let rota=
modo=="login"
?"/login"
:"/cadastro";

let botao=
document.getElementById("botaoLogin");

botao.classList.add("loading");

let req=
await fetch(
rota,
{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
usuario,
senha
})

}

);

let dados=
await req.json();

botao.classList.remove("loading");

if(dados.status=="ok"){

location.reload();

return;

}

document
.getElementById("erro")
.innerText=dados.erro;

}

</script>

</body>

</html>
"""


@app.route("/cadastro",methods=["POST"])
def cadastro():

dados=request.get_json()

usuario=dados["usuario"]

senha=dados["senha"]

conn=get_db()

cur=conn.cursor()

cur.execute(
"SELECT * FROM usuarios WHERE usuario=%s",
(usuario,)
)

existe=cur.fetchone()

if existe:

return jsonify({

"status":"erro",

"erro":"Usuário já existe."

})

cur.execute(

"INSERT INTO usuarios(usuario,senha) VALUES(%s,%s)",

(usuario,senha)

)

conn.commit()

session["usuario"]=usuario

cur.close()

conn.close()

return jsonify({

"status":"ok"

})


@app.route("/login",methods=["POST"])
def login():

dados=request.get_json()

usuario=dados["usuario"]

senha=dados["senha"]

conn=get_db()

cur=conn.cursor()

cur.execute(

"SELECT * FROM usuarios WHERE usuario=%s",

(usuario,)

)

user=cur.fetchone()

if not user:

return jsonify({

"status":"erro",

"erro":"Conta não encontrada."

})

if user["senha"] != senha:

return jsonify({

"status":"erro",

"erro":"Senha incorreta."

})

session["usuario"]=usuario

cur.close()

conn.close()

return jsonify({

"status":"ok"

})


if __name__=="__main__":
app.run(debug=True)