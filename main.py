
import streamlit as st
from extractor import extract_text
from processor import process_publications, agrupar_unicos_com_duplicatas
from exporter import export_to_docx
from io import BytesIO
from datetime import datetime
import base64
import zipfile
from PIL import Image

st.set_page_config(page_title="Comparador de Publicações Jurídicas", layout="centered")

# Mostrar logo centralizado
try:
    logo = Image.open("MCTS-removebg-preview.png")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(logo, use_container_width=False, width=300)
except:
    st.warning("Logo não encontrada")

st.markdown("<h2 style='text-align:center;'>Comparador de Publicações Jurídicas</h2>", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Selecione arquivos .docx", type=["docx"], accept_multiple_files=True)
split = st.checkbox("Deseja dividir o Diário Consolidado?")
num_partes = st.number_input("Quantidade de pessoas", min_value=1, max_value=10, step=1, value=2, disabled=not split)

if st.button("Comparar e Exportar"):
    if not uploaded_files:
        st.warning("Por favor, envie pelo menos um arquivo.")
    else:
        dados = []
        for file in uploaded_files:
            texto = extract_text(file)
            pubs = process_publications(texto, file.name)
            dados.extend(pubs)

        unicos, duplicados = agrupar_unicos_com_duplicatas(dados)

        st.success(f"Total de publicações únicas: {len(unicos)}")
        st.info(f"Publicações duplicadas: {len(duplicados)}")

        partes = [unicos[i::num_partes] for i in range(num_partes)] if split else [unicos]

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for i, parte in enumerate(partes, 1):
                buffer = BytesIO()
                export_to_docx(parte, duplicados, buffer)
                nome_arquivo = f"publicacoes_parte_{i}.docx"
                zipf.writestr(nome_arquivo, buffer.getvalue())
                b64 = base64.b64encode(buffer.getvalue()).decode()
                link = f'<a href="data:application/octet-stream;base64,{b64}" download="{nome_arquivo}">📥 Baixar Parte {i}</a>'
                st.markdown(link, unsafe_allow_html=True)

        zip_buffer.seek(0)
        zip_b64 = base64.b64encode(zip_buffer.read()).decode()
        st.markdown(f"<a href='data:application/zip;base64,{zip_b64}' download='publicacoes_divididas.zip'>📦 Baixar Todas as Partes (.zip)</a>", unsafe_allow_html=True)
