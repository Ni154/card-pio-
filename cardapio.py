import streamlit as st
from PIL import Image
import urllib.parse
import os
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px

# CONFIG
st.set_page_config(page_title="Quero Batata", layout="wide")

# BD
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

# IMAGENS
def carregar_imagem(nome_arquivo):
    caminho = os.path.join("imagens", nome_arquivo)
    if os.path.exists(caminho):
        return Image.open(caminho)
    else:
        return None

# CARDÁPIO
cardapio = [
    {"nome": "Bacon com brócolis", "descricao": "Purê com mussarela, bacon, brócolis. Catupiry ou Cheddar.", "preco": 36.00, "imagem": "brocolis.jpg"},
    {"nome": "Bacon com milho", "descricao": "Purê com mussarela, bacon, milho. Catupiry ou Cheddar.", "preco": 37.00, "imagem": "milho.jpg"},
    {"nome": "Bacon com mussarela", "descricao": "Purê, mussarela, bacon crocante. Batata palha.", "preco": 45.00, "imagem": "mussarela.jpg"},
    {"nome": "Bacon e cheddar", "descricao": "Purê, cheddar, bacon. Catupiry ou Cheddar.", "preco": 45.00, "imagem": "cheddar.jpg"}
]

# MENU
menu = st.sidebar.radio("Navegação", ["📦 Fazer Pedido", "🗂️ Painel de Pedidos", "📊 Relatórios"])

# FAZER PEDIDO
if menu == "📦 Fazer Pedido":
    if "pedido" not in st.session_state:
        st.session_state.pedido = []

    st.title("🥔 Quero Batata - Cardápio")

    for item in cardapio:
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                imagem = carregar_imagem(item["imagem"])
                if imagem:
                    st.image(imagem, width=100)
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

    total = 0
    if st.session_state.pedido:
        for item in st.session_state.pedido:
            st.write(f"- {item['nome']} — R$ {item['preco']:.2f}")
            total += item["preco"]
        st.markdown(f"### 💰 Total: R$ {total:.2f}")
    else:
        st.write("Seu pedido está vazio.")

    st.divider()
    st.header("📦 Entrega e Pagamento")

    with st.form("form_pedido"):
        nome = st.text_input("Nome completo")
        endereco = st.text_area("Endereço de entrega")
        pagamento = st.selectbox("Forma de pagamento", ["Pix", "Dinheiro", "Cartão"])
        observacao = st.text_input("Observações (opcional)")
        enviar = st.form_submit_button("📲 Finalizar Pedido via WhatsApp")

        if enviar:
            if not nome or not endereco:
                st.warning("Por favor, preencha nome e endereço.")
            elif not st.session_state.pedido:
                st.warning("Adicione ao menos um item ao pedido.")
            else:
                mensagem = f"🍟 *Pedido de {nome}*\n\n"
                itens_texto = ""
                for item in st.session_state.pedido:
                    mensagem += f"• {item['nome']} — R$ {item['preco']:.2f}\n"
                    itens_texto += f"{item['nome']} (R$ {item['preco']:.2f})\n"
                mensagem += f"\n💰 *Total:* R$ {total:.2f}\n"
                mensagem += f"\n📍 *Endereço:* {endereco}\n"
                mensagem += f"💳 *Pagamento:* {pagamento}\n"
                if observacao:
                    mensagem += f"📝 *Observação:* {observacao}\n"
                mensagem += "\nPedido feito via Quero Batata 🥔"

                cursor.execute("""
                    INSERT INTO pedidos (nome, endereco, pagamento, observacao, itens, total, datahora, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (nome, endereco, pagamento, observacao, itens_texto, total, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pendente"))
                conn.commit()

                # SOM
                st.markdown("""
                    <audio id="notificacao" autoplay>
                        <source src="https://www.myinstants.com/media/sounds/mixkit-correct-answer-reward-952.wav" type="audio/wav">
                    </audio>
                    <script>
                        document.getElementById("notificacao").play();
                    </script>
                """, unsafe_allow_html=True)

                link_whats = f"https://wa.me/SEUNUMERO?text={urllib.parse.quote(mensagem)}"
                st.success("✅ Pedido registrado com sucesso!")
                st.markdown(f"[📲 Enviar no WhatsApp]({link_whats})", unsafe_allow_html=True)
                st.session_state.pedido = []

# PAINEL DE PEDIDOS
elif menu == "🗂️ Painel de Pedidos":
    st.title("🗂️ Painel de Pedidos")
    pedidos = cursor.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()

    if not pedidos:
        st.info("Nenhum pedido registrado.")
    else:
        for pedido in pedidos:
            with st.expander(f"Pedido #{pedido[0]} | {pedido[1]} | {pedido[7][:16]}"):
                st.write(f"📦 **Itens:**\n{pedido[5]}")
                st.write(f"💰 **Total:** R$ {pedido[6]:.2f}")
                st.write(f"📍 **Endereço:** {pedido[2]}")
                st.write(f"💳 **Pagamento:** {pedido[3]}")
                if pedido[4]:
                    st.write(f"📝 **Obs:** {pedido[4]}")
                st.write(f"📅 **Data/Hora:** {pedido[7]}")
                st.write(f"✅ **Status:** `{pedido[8]}`")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Marcar como Entregue", key=f"entregue_{pedido[0]}"):
                        cursor.execute("UPDATE pedidos SET status = 'Entregue' WHERE id = ?", (pedido[0],))
                        conn.commit()
                        st.success("Atualizado.")
                        st.experimental_rerun()
                with col2:
                    if st.button("🗑️ Excluir", key=f"excluir_{pedido[0]}"):
                        cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido[0],))
                        conn.commit()
                        st.warning("Excluído.")
                        st.experimental_rerun()

# RELATÓRIOS
elif menu == "📊 Relatórios":
    st.title("📊 Relatórios e Gráficos")

    df = pd.read_sql_query("SELECT * FROM pedidos", conn)
    if df.empty:
        st.info("Nenhum dado para exibir.")
    else:
        df['data'] = pd.to_datetime(df['datahora']).dt.date

        # VENDAS POR DIA
        vendas_dia = df.groupby('data')['total'].sum().reset_index()
        fig1 = px.bar(vendas_dia, x='data', y='total', title='Vendas por Dia (R$)')
        st.plotly_chart(fig1, use_container_width=True)

        # PRODUTOS MAIS VENDIDOS
        todos_itens = []
        for linha in df['itens']:
            for item in linha.split("\n"):
                nome = item.split("(")[0].strip()
                if nome:
                    todos_itens.append(nome)
        produtos_df = pd.Series(todos_itens).value_counts().reset_index()
        produtos_df.columns = ['Produto', 'Quantidade']
        fig2 = px.bar(produtos_df, x='Produto', y='Quantidade', title='Produtos mais vendidos')
        st.plotly_chart(fig2, use_container_width=True)

        # FORMAS DE PAGAMENTO
        pagamento_df = df.groupby('pagamento')['total'].sum().reset_index()
        fig3 = px.pie(pagamento_df, names='pagamento', values='total', title='Faturamento por Forma de Pagamento')
        st.plotly_chart(fig3, use_container_width=True)
