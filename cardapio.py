import streamlit as st
from PIL import Image
import urllib.parse
import os
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
from io import BytesIO
from fpdf import FPDF

# CONFIGURACAO DA PAGINA
st.set_page_config(page_title="Quero Batata", layout="wide")

# BANCO DE DADOS
conn = sqlite3.connect("pedidos.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    endereco TEXT,
    pagamento TEXT,
    observacao TEXT,
    itens TEXT,
    total REAL,
    datahora TEXT,
    status TEXT
)
""")
conn.commit()

# SESSAO
if "logado" not in st.session_state:
    st.session_state.logado = False
if "tema" not in st.session_state:
    st.session_state.tema = "light"
if "logo" not in st.session_state:
    st.session_state.logo = None

# ESTILO
if st.session_state.tema == "dark":
    st.markdown("""
        <style>
        body { background-color: #1E1E1E; color: white; }
        </style>
    """, unsafe_allow_html=True)

# UPLOAD LOGO
with st.sidebar:
    st.image(st.session_state.logo if st.session_state.logo else "https://i.imgur.com/1ZQZ1Zl.png", width=150)
    logo_file = st.file_uploader("Enviar logo", type=["png", "jpg", "jpeg"])
    if logo_file:
        st.session_state.logo = Image.open(logo_file)

    st.selectbox("Tema", ["light", "dark"], index=0 if st.session_state.tema == "light" else 1, key="tema")

# CARDAPIO
cardapio = [
    {"nome": "Bacon com brócolis", "descricao": "Purê com mussarela, bacon, brócolis. Catupiry ou Cheddar.", "preco": 36.00, "imagem": "brocolis.jpg"},
    {"nome": "Bacon com milho", "descricao": "Purê com mussarela, bacon, milho. Catupiry ou Cheddar.", "preco": 37.00, "imagem": "milho.jpg"},
    {"nome": "Bacon com mussarela", "descricao": "Purê, mussarela, bacon crocante. Batata palha.", "preco": 45.00, "imagem": "mussarela.jpg"},
    {"nome": "Bacon e cheddar", "descricao": "Purê, cheddar, bacon. Catupiry ou Cheddar.", "preco": 45.00, "imagem": "cheddar.jpg"}
]

# MENU
menu = st.sidebar.radio("Menu", ["🔐 Login", "📦 Fazer Pedido", "🗂️ Painel de Pedidos", "📊 Relatórios"])

# LOGIN
if menu == "🔐 Login":
    st.title("🔒 Acesso Administrativo")
    senha = st.text_input("Digite a senha:", type="password")
    if st.button("Entrar"):
        if senha == "admin123":
            st.success("Acesso liberado.")
            st.session_state.logado = True
        else:
            st.error("Senha incorreta.")

# FAZER PEDIDO
if menu == "📦 Fazer Pedido":
    if "pedido" not in st.session_state:
        st.session_state.pedido = []

    st.title("🥔 Quero Batata - Cardápio")

    for item in cardapio:
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                caminho = os.path.join("imagens", item["imagem"])
                if os.path.exists(caminho):
                    st.image(caminho, width=100)
            with col2:
                st.markdown(f"### {item['nome']}")
                st.write(item["descricao"])
            with col3:
                st.markdown(f"**R$ {item['preco']:.2f}**")
                if st.button(f"🛒 Adicionar {item['nome']}", key=item["nome"]):
                    st.session_state.pedido.append(item)
                    st.success(f"{item['nome']} adicionado ao pedido!")

    st.divider()
    st.header("🧾 Seu Pedido")
    total = sum(item["preco"] for item in st.session_state.pedido)
    for item in st.session_state.pedido:
        st.write(f"- {item['nome']} — R$ {item['preco']:.2f}")
    st.markdown(f"### 💰 Total: R$ {total:.2f}")

    st.divider()
    st.header("📦 Entrega e Pagamento")
    with st.form("form_pedido"):
        nome = st.text_input("Nome completo")
        endereco = st.text_area("Endereço")
        pagamento = st.selectbox("Forma de pagamento", ["Pix", "Dinheiro", "Cartão"])
        obs = st.text_input("Observações")
        enviar = st.form_submit_button("📲 Finalizar Pedido")

        if enviar:
            if not nome or not endereco or not st.session_state.pedido:
                st.warning("Preencha todos os campos e adicione itens.")
            else:
                itens_texto = "\n".join(f"{i['nome']} (R$ {i['preco']:.2f})" for i in st.session_state.pedido)
                cursor.execute("""
                    INSERT INTO pedidos (nome, endereco, pagamento, observacao, itens, total, datahora, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (nome, endereco, pagamento, obs, itens_texto, total, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pendente"))
                conn.commit()
                st.session_state.pedido = []
                st.success("✅ Pedido registrado!")
                st.markdown("""
                <audio autoplay>
                    <source src="https://www.myinstants.com/media/sounds/mixkit-correct-answer-reward-952.wav" type="audio/wav">
                </audio>
                """, unsafe_allow_html=True)

# PAINEL DE PEDIDOS
if menu == "🗂️ Painel de Pedidos" and st.session_state.logado:
    st.title("🗂️ Pedidos Recebidos")
    pedidos = cursor.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    for p in pedidos:
        with st.expander(f"#{p[0]} | {p[1]} | {p[7][:16]}"):
            st.write(f"📍 {p[2]}")
            st.write(f"💳 {p[3]} | {p[4]}")
            st.write(f"🧾 {p[5]}")
            st.write(f"💰 R$ {p[6]:.2f}")
            st.write(f"🕒 {p[7]} | Status: {p[8]}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Marcar Entregue", key=f"ok{p[0]}"):
                    cursor.execute("UPDATE pedidos SET status = 'Entregue' WHERE id = ?", (p[0],))
                    conn.commit()
                    st.experimental_rerun()
            with col2:
                if st.button("🗑️ Excluir", key=f"del{p[0]}"):
                    cursor.execute("DELETE FROM pedidos WHERE id = ?", (p[0],))
                    conn.commit()
                    st.experimental_rerun()

# RELATÓRIOS
if menu == "📊 Relatórios" and st.session_state.logado:
    st.title("📊 Relatórios de Vendas")
    df = pd.read_sql_query("SELECT * FROM pedidos", conn)
    if df.empty:
        st.info("Sem dados.")
    else:
        df['data'] = pd.to_datetime(df['datahora']).dt.date
        st.subheader("📅 Vendas por Dia")
        vendas = df.groupby('data')['total'].sum().reset_index()
        st.plotly_chart(px.bar(vendas, x='data', y='total', title='Vendas por Dia'))

        st.subheader("🥇 Produtos Mais Vendidos")
        itens = []
        for linha in df['itens']:
            for i in linha.split("\n"):
                nome = i.split("(")[0].strip()
                if nome:
                    itens.append(nome)
        mais_vendidos = pd.Series(itens).value_counts().reset_index()
        mais_vendidos.columns = ['Produto', 'Qtd']
        st.plotly_chart(px.bar(mais_vendidos, x='Produto', y='Qtd', title='Top Produtos'))

        st.subheader("💳 Faturamento por Pagamento")
        pagamento = df.groupby('pagamento')['total'].sum().reset_index()
        st.plotly_chart(px.pie(pagamento, names='pagamento', values='total', title='Faturamento'))

        st.subheader("📄 Exportar Relatório PDF")
        if st.button("📥 Baixar PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for _, row in df.iterrows():
                pdf.multi_cell(0, 10, f"{row['datahora']} | {row['nome']} | R$ {row['total']:.2f}")
            buffer = BytesIO()
            pdf.output(buffer)
            st.download_button("📄 Download Relatório PDF", data=buffer.getvalue(), file_name="relatorio.pdf")

# BLOQUEIO
if menu in ["🗂️ Painel de Pedidos", "📊 Relatórios"] and not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login primeiro.")
