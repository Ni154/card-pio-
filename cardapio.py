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
from streamlit_autorefresh import st_autorefresh

# CONFIGURACAO
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
if "pedido" not in st.session_state:
    st.session_state.pedido = []

# INTERFACE SUPERIOR LOGIN
if not st.session_state.logado:
    st.title("🔐 Login Administrativo")
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if senha == "admin123":
            st.session_state.logado = True
            st.success("Bem-vindo ao sistema Quero Batata!")
            st.experimental_rerun()
        else:
            st.error("Senha incorreta.")
else:
    # MENU SUPERIOR APÓS LOGIN
    st.image(st.session_state.logo if st.session_state.logo else "https://i.imgur.com/1ZQZ1Zl.png", width=150)
    menu = st.selectbox("Escolha uma opção:", ["📦 Fazer Pedido", "🗂️ Painel de Pedidos", "📊 Relatórios"], index=0)

    # TEMA E LOGO
    with st.sidebar:
        st.selectbox("Tema", ["light", "dark"], index=0 if st.session_state.tema == "light" else 1, key="tema")
        logo_file = st.file_uploader("Enviar logo", type=["png", "jpg", "jpeg"])
        if logo_file:
            st.session_state.logo = Image.open(logo_file)

    if st.session_state.tema == "dark":
        st.markdown("""
            <style>
            body { background-color: #1E1E1E; color: white; }
            </style>
        """, unsafe_allow_html=True)

    # CARDAPIO
    cardapio = [
        {"nome": "Bacon com brócolis", "descricao": "Purê com mussarela, bacon, brócolis. Catupiry ou Cheddar.", "preco": 36.00, "imagem": "brocolis.jpg"},
        {"nome": "Bacon com milho", "descricao": "Purê com mussarela, bacon, milho. Catupiry ou Cheddar.", "preco": 37.00, "imagem": "milho.jpg"},
        {"nome": "Bacon com mussarela", "descricao": "Purê, mussarela, bacon crocante. Batata palha.", "preco": 45.00, "imagem": "mussarela.jpg"},
        {"nome": "Bacon e cheddar", "descricao": "Purê, cheddar, bacon. Catupiry ou Cheddar.", "preco": 45.00, "imagem": "cheddar.jpg"}
    ]

    # PEDIDO
    if menu == "📦 Fazer Pedido":
        st.title("🥔 Cardápio")
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
                        st.success(f"{item['nome']} adicionado!")

        st.header("🧾 Seu Pedido")
        total = sum(i["preco"] for i in st.session_state.pedido)
        for i in st.session_state.pedido:
            st.write(f"- {i['nome']} — R$ {i['preco']:.2f}")
        st.markdown(f"**Total: R$ {total:.2f}**")

        st.header("📦 Entrega")
        with st.form("form_pedido"):
            nome = st.text_input("Nome")
            endereco = st.text_area("Endereço")
            pagamento = st.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão"])
            obs = st.text_input("Observações")
            submit = st.form_submit_button("📲 Finalizar Pedido")
            if submit:
                if nome and endereco and st.session_state.pedido:
                    itens_txt = "\n".join(f"{i['nome']} (R$ {i['preco']:.2f})" for i in st.session_state.pedido)
                    cursor.execute("""
                        INSERT INTO pedidos (nome, endereco, pagamento, observacao, itens, total, datahora, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (nome, endereco, pagamento, obs, itens_txt, total, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pendente"))
                    conn.commit()
                    st.session_state.pedido = []
                    st.success("✅ Pedido registrado!")
                    st.markdown("""
                        <audio autoplay>
                        <source src="https://www.myinstants.com/media/sounds/mixkit-correct-answer-reward-952.wav" type="audio/wav">
                        </audio>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Preencha tudo corretamente.")

    # PAINEL
    elif menu == "🗂️ Painel de Pedidos":
        st_autorefresh(interval=10000, key="refresh")
        st.title("🗂️ Pedidos Recebidos")
        pedidos = cursor.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
        for p in pedidos:
            with st.expander(f"#{p[0]} | {p[1]} | R$ {p[6]:.2f} | {p[8]}"):
                st.write(f"📍 {p[2]} | 💳 {p[3]} | 📝 {p[4]}")
                st.write(p[5])
                st.write(f"🕒 {p[7]}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✅ Entregue", key=f"ent_{p[0]}"):
                        cursor.execute("UPDATE pedidos SET status='Entregue' WHERE id=?", (p[0],))
                        conn.commit()
                        st.experimental_rerun()
                with col2:
                    if st.button("🗑️ Excluir", key=f"del_{p[0]}"):
                        cursor.execute("DELETE FROM pedidos WHERE id=?", (p[0],))
                        conn.commit()
                        st.experimental_rerun()
                with col3:
                    if st.button("📄 Comprovante PDF", key=f"pdf_{p[0]}"):
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial", size=12)
                        pdf.cell(200, 10, txt="Comprovante de Pedido", ln=True, align='C')
                        pdf.ln(10)
                        pdf.multi_cell(0, 10, f"Cliente: {p[1]}\nEndereço: {p[2]}\nPagamento: {p[3]}\nObservação: {p[4]}\n\nItens:\n{p[5]}\n\nTotal: R$ {p[6]:.2f}\nData/Hora: {p[7]}\nStatus: {p[8]}")
                        buffer = BytesIO()
                        pdf.output(buffer)
                        st.download_button("⬇️ Baixar Comprovante", data=buffer.getvalue(), file_name=f"pedido_{p[0]}.pdf")

    # RELATÓRIOS
    elif menu == "📊 Relatórios":
        st.title("📊 Relatórios de Vendas")
        df = pd.read_sql_query("SELECT * FROM pedidos", conn)
        if df.empty:
            st.info("Sem dados.")
        else:
            df['data'] = pd.to_datetime(df['datahora']).dt.date
            periodo = st.date_input("Filtrar por data:", [])
            if len(periodo) == 2:
                df = df[(df['data'] >= pd.to_datetime(periodo[0])) & (df['data'] <= pd.to_datetime(periodo[1]))]

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
            top = pd.Series(itens).value_counts().reset_index()
            top.columns = ['Produto', 'Qtd']
            st.plotly_chart(px.bar(top, x='Produto', y='Qtd', title='Top Produtos'))

            st.subheader("💳 Faturamento por Forma de Pagamento")
            pg = df.groupby('pagamento')['total'].sum().reset_index()
            st.plotly_chart(px.pie(pg, names='pagamento', values='total'))
