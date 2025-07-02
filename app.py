import streamlit as st
import sqlite3
import os
from datetime import datetime
from PIL import Image
import base64
import io
import uuid

# ----- CONFIGURAÇÕES INICIAIS -----
st.set_page_config(page_title="Cardápio Online", layout="wide")

# ----- CONEXÃO COM BANCO -----
# Conectar ao banco
conn = sqlite3.connect("cardapio.db", check_same_thread=False)
cursor = conn.cursor()

# Criar tabela de configurações se não existir
cursor.execute("""
CREATE TABLE IF NOT EXISTS configuracoes (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    loja_aberta INTEGER DEFAULT 1,
    whatsapp TEXT DEFAULT '',
    tema TEXT DEFAULT 'Claro',
    logo TEXT DEFAULT ''
)
""")

# Inserir linha padrão se não existir
cursor.execute("INSERT OR IGNORE INTO configuracoes (id) VALUES (1)")
conn.commit()
# Criar tabela de categorias
cursor.execute("""
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT
)
""")

# Inserir categoria padrão se não houver nenhuma
cursor.execute("SELECT COUNT(*) FROM categorias")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO categorias (nome) VALUES ('Lanches')")
    conn.commit()

# Criar tabela de produtos
cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    descricao TEXT,
    preco REAL,
    imagem TEXT,
    categoria TEXT
)
""")

# Criar tabela de pedidos
cursor.execute("""
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_nome TEXT,
    endereco TEXT,
    pagamento TEXT,
    itens TEXT,
    data TEXT,
    status TEXT DEFAULT 'Pendente'
)
""")


# ----- FUNÇÕES AUXILIARES -----
def salvar_imagem(imagem):
    if imagem:
        caminho = f"imagens/{uuid.uuid4().hex}_{imagem.name}"
        with open(caminho, "wb") as f:
            f.write(imagem.getbuffer())
        return caminho
    return ""

def carregar_logo():
    cursor.execute("SELECT logo FROM configuracoes WHERE id = 1")
    resultado = cursor.fetchone()
    return resultado[0] if resultado else ""

def gerar_pdf_pedido(pedido):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 800, f"Pedido de {pedido['cliente_nome']}")
    c.drawString(100, 780, f"Endereço: {pedido['endereco']}")
    c.drawString(100, 760, f"Pagamento: {pedido['pagamento']}")
    y = 740
    for item in pedido['itens']:
        c.drawString(100, y, f"- {item}")
        y -= 20
    c.drawString(100, y - 20, f"Data: {pedido['data']}")
    c.save()
    buffer.seek(0)
    return buffer

def abrir_loja():
    cursor.execute("UPDATE configuracoes SET loja_aberta = 1 WHERE id = 1")
    conn.commit()

def fechar_loja():
    cursor.execute("UPDATE configuracoes SET loja_aberta = 0 WHERE id = 1")
    conn.commit()

def loja_esta_aberta():
    cursor.execute("SELECT loja_aberta FROM configuracoes WHERE id = 1")
    return cursor.fetchone()[0] == 1

# ----- INTERFACE DO CLIENTE (CARDÁPIO) -----
def pagina_cardapio():
    if not loja_esta_aberta():
        st.warning("Loja está fechada no momento.")
        st.stop()

    st.title("🍔 Cardápio")
    categorias = [c[0] for c in cursor.execute("SELECT nome FROM categorias").fetchall()]
    categoria_selecionada = st.sidebar.selectbox("Categorias", categorias)

    produtos = cursor.execute("SELECT nome, descricao, preco, imagem FROM produtos WHERE categoria = ?", (categoria_selecionada,)).fetchall()

    carrinho = []
    for nome, descricao, preco, imagem in produtos:
        with st.container():
            col1, col2 = st.columns([1,3])
            with col1:
                if imagem and os.path.exists(imagem):
                    st.image(imagem, width=100)
            with col2:
                st.markdown(f"### {nome}")
                st.markdown(descricao)
                st.markdown(f"**R$ {preco:.2f}**")
                if st.button(f"Adicionar {nome}"):
                    carrinho.append(f"{nome} - R$ {preco:.2f}")

    st.markdown("---")
    st.subheader("🛒 Finalizar Pedido")
    nome = st.text_input("Seu nome")
    endereco = st.text_input("Endereço de entrega")
    pagamento = st.selectbox("Forma de pagamento", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"])

    if st.button("Enviar Pedido"):
        if nome and endereco and pagamento:
            data = datetime.now().strftime("%d/%m/%Y %H:%M")
            pedido_texto = f"Pedido de {nome}\nEndereço: {endereco}\nPagamento: {pagamento}\n" + "\n".join(carrinho)
            cursor.execute("INSERT INTO pedidos (cliente_nome, endereco, pagamento, itens, data) VALUES (?, ?, ?, ?, ?)",
                           (nome, endereco, pagamento, "\n".join(carrinho), data))
            conn.commit()
            pedido_dict = {"cliente_nome": nome, "endereco": endereco, "pagamento": pagamento, "itens": carrinho, "data": data}
            buffer = gerar_pdf_pedido(pedido_dict)
            st.success("Pedido enviado com sucesso!")
            b64 = base64.b64encode(buffer.read()).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="pedido.pdf">📄 Baixar Comprovante PDF</a>'
            st.markdown(href, unsafe_allow_html=True)
            numero = cursor.execute("SELECT whatsapp FROM configuracoes WHERE id = 1").fetchone()[0]
            msg = pedido_texto.replace('\n', '%0A')
            st.markdown(f"[📤 Enviar para WhatsApp](https://wa.me/{numero}?text={msg})")
        else:
            st.error("Preencha todos os campos para finalizar o pedido.")

# ----- INTERFACE DO PAINEL ADMIN -----
def painel_administrativo():
    menu = st.sidebar.radio("Menu", ["Início", "Cadastrar Produtos", "Gerenciar Categorias", "Pedidos", "Configurações"])

    if menu == "Início":
        st.title("Painel Administrativo")

    elif menu == "Cadastrar Produtos":
        st.title("Cadastrar Produto")
        nome = st.text_input("Nome")
        descricao = st.text_area("Descrição")
        preco = st.number_input("Preço", min_value=0.0, format="%.2f")
        categorias = [c[0] for c in cursor.execute("SELECT nome FROM categorias").fetchall()]
        categoria = st.selectbox("Categoria", categorias)
        imagem = st.file_uploader("Imagem do Produto", type=["jpg", "jpeg", "png"])

        if st.button("Salvar Produto"):
            caminho_imagem = salvar_imagem(imagem)
            cursor.execute("INSERT INTO produtos (nome, descricao, preco, imagem, categoria) VALUES (?, ?, ?, ?, ?)",
                           (nome, descricao, preco, caminho_imagem, categoria))
            conn.commit()
            st.success("Produto salvo com sucesso!")

    elif menu == "Gerenciar Categorias":
        st.title("Gerenciar Categorias")
        nova = st.text_input("Nova Categoria")
        if st.button("Adicionar Categoria"):
            cursor.execute("INSERT INTO categorias (nome) VALUES (?)", (nova,))
            conn.commit()
            st.success("Categoria adicionada")
        st.markdown("### Categorias Atuais")
        for c in cursor.execute("SELECT id, nome FROM categorias").fetchall():
            st.write(f"{c[0]} - {c[1]}")

    elif menu == "Pedidos":
        st.title("Pedidos Recebidos")
        pedidos = cursor.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
        for pedido in pedidos:
            with st.expander(f"📦 Pedido #{pedido[0]} - {pedido[1]} - {pedido[6]}"):
                st.text(pedido[3])
                st.text(pedido[4])
                st.text(f"Data: {pedido[5]}")
                col1, col2 = st.columns(2)
                if col1.button("✅ Marcar como Entregue", key=f"entregue_{pedido[0]}"):
                    cursor.execute("UPDATE pedidos SET status = 'Entregue' WHERE id = ?", (pedido[0],))
                    conn.commit()
                if col2.button("🗑️ Excluir", key=f"excluir_{pedido[0]}"):
                    cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido[0],))
                    conn.commit()

    elif menu == "Configurações":
        st.title("Configurações")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔴 Fechar Loja"):
                fechar_loja()
            if st.button("🟢 Abrir Loja"):
                abrir_loja()
        with col2:
            whatsapp = st.text_input("Número do WhatsApp (somente números)")
            if st.button("Salvar WhatsApp"):
                cursor.execute("UPDATE configuracoes SET whatsapp = ? WHERE id = 1", (whatsapp,))
                conn.commit()
                st.success("Número salvo")

# ----- LOGIN -----
def login():
    st.title("🔐 Login Administrativo")
    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if user == "admin" and senha == "admin123":
            st.session_state["logado"] = True
        else:
            st.error("Usuário ou senha incorretos")

# ----- INTERFACE PRINCIPAL -----
logo = carregar_logo()
if logo and os.path.exists(logo):
    st.image(logo, width=150)

menu_principal = st.sidebar.radio("Acesso", ["Cardápio", "Admin"])

if menu_principal == "Cardápio":
    pagina_cardapio()
elif menu_principal == "Admin":
    if "logado" not in st.session_state:
        login()
    elif st.session_state["logado"]:
        painel_administrativo()
