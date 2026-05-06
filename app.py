import streamlit as st
import fitz
import os
import re
import zipfile

st.set_page_config(page_title="Hub RH", layout="centered", page_icon="📂")

# =========================
# CSS
# =========================
st.markdown("""
<style>
body {background-color:#f5f7fa;}

.main-title {
    text-align:center;
    font-size:36px;
    font-weight:bold;
    color:#1e293b;
}

.subtitle {
    text-align:center;
    font-size:16px;
    color:#64748b;
    margin-bottom:30px;
}

.stButton button {
    width:100%;
    height:90px;
    border-radius:14px;
    background:#ffffff;
    border:1px solid #e2e8f0;
    font-size:18px;
    font-weight:600;
}

.upload-box {
    background:white;
    border-radius:15px;
    padding:30px;
    text-align:center;
    margin-top:30px;
    box-shadow:0 4px 12px rgba(0,0,0,0.05);
}

.footer {
    text-align:center;
    color:#94a3b8;
    margin-top:50px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.markdown("<div class='main-title'>📂 Hub de Documentos RH</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Organize seus documentos com poucos cliques</div>", unsafe_allow_html=True)

# =========================
# ESTADO
# =========================
if "tipo_doc" not in st.session_state:
    st.session_state.tipo_doc = None

def set_tipo(tipo):
    st.session_state.tipo_doc = tipo

# =========================
# BOTÕES
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    st.button("📄 Ficha", on_click=set_tipo, args=("ficha",))
with col2:
    st.button("📑 TRCT", on_click=set_tipo, args=("trct",))
with col3:
    st.button("🪪 Seguro", on_click=set_tipo, args=("seguro",))

col4, col5, col6 = st.columns(3)

with col4:
    st.button("⏱️ Ponto RM", on_click=set_tipo, args=("ponto",))
with col5:
    st.button("💰 Informe", on_click=set_tipo, args=("informe",))
with col6:
    st.empty()

if st.session_state.tipo_doc:
    st.success(f"📌 Tipo selecionado: {st.session_state.tipo_doc.upper()}")

# =========================
# UPLOAD
# =========================
st.markdown("<div class='upload-box'>📤 Envie seu PDF</div>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("", type="pdf")

executar = st.button("🚀 Processar Documento")

# =========================
# UTIL
# =========================
def limpar_nome(nome):
    nome = nome.replace("\n", " ").replace("\r", " ")
    nome = re.sub(r'\s+', ' ', nome)
    nome = re.sub(r'[\\/*?:"<>|]', "", nome)
    return nome.strip()

def salvar_pdf(doc, paginas, nome):
    os.makedirs("output", exist_ok=True)
    nome = limpar_nome(nome)
    caminho = f"output/{nome}.pdf"

    if os.path.exists(caminho):
        try:
            os.remove(caminho)
        except:
            pass

    novo = fitz.open()
    for p in paginas:
        novo.insert_pdf(doc, from_page=p, to_page=p)

    novo.save(caminho)
    novo.close()

    return nome + ".pdf"

# =========================
# FICHA (OK)
# =========================
def processar_ficha(doc):
    arquivos, grupo, nome_atual = [], [], None

    for i, p in enumerate(doc):
        texto = p.get_text()
        linhas = [l.strip() for l in texto.split("\n") if l.strip()]

        nome_encontrado = None

        for idx, linha in enumerate(linhas):
            if "MATRICULA" in linha.upper():
                for j in range(idx-1, max(idx-6, 0), -1):
                    cand = linhas[j]
                    if re.fullmatch(r"[A-ZÁ-Ú\s]+", cand):
                        if 2 <= len(cand.split()) <= 6 and "MAE" not in cand and "PAI" not in cand:
                            nome_encontrado = cand
                            break

        if nome_encontrado:
            if grupo and nome_atual:
                arquivos.append(salvar_pdf(doc, grupo, nome_atual + " FRE"))
                grupo = []
            nome_atual = nome_encontrado

        grupo.append(i)

    if grupo and nome_atual:
        arquivos.append(salvar_pdf(doc, grupo, nome_atual + " FRE"))

    return arquivos

# =========================
# TRCT (OK)
# =========================
def processar_trct(doc):
    arquivos, grupo, nome = [], [], "Desconhecido"

    for i, p in enumerate(doc):
        texto = p.get_text()
        linhas = [l.strip() for l in texto.split("\n") if l.strip()]

        if "TERMO RESCIS" in texto.upper():
            if grupo:
                arquivos.append(salvar_pdf(doc, grupo, nome + " TRCT"))
                grupo = []

            for idx, linha in enumerate(linhas):
                if "11" in linha and "NOME" in linha.upper():
                    for j in range(idx-1, max(idx-6, 0), -1):
                        cand = linhas[j]
                        if re.fullmatch(r"[A-ZÁ-Ú\s]+", cand):
                            if 2 <= len(cand.split()) <= 5 and "MAE" not in cand:
                                nome = cand
                                break

        grupo.append(i)

    if grupo:
        arquivos.append(salvar_pdf(doc, grupo, nome + " TRCT"))

    return arquivos

# =========================
# SEGURO (CORRIGIDO)
# =========================
def processar_seguro(doc):
    from collections import defaultdict
    grupos = defaultdict(list)

    for i, p in enumerate(doc):
        texto = p.get_text().upper()

        candidatos = re.findall(r"[A-ZÁ-Ú\s]{15,}", texto[:1000])

        nome = "Desconhecido"

        for n in candidatos:
            n = n.strip()

            if any(palavra in n for palavra in [
                "REQUERIMENTO",
                "SEGURO",
                "BENEFICIO",
                "DECLARO",
                "DIREITO"
            ]):
                continue

            if 3 <= len(n.split()) <= 6:
                nome = n
                break

        nome = limpar_nome(nome)
        grupos[nome].append(i)

    arquivos = []

    for nome, paginas in grupos.items():
        arquivos.append(salvar_pdf(doc, paginas, nome + " SD"))

    return arquivos

# =========================
# PONTO (OK)
# =========================
def processar_ponto(doc):
    arquivos = []

    for i, p in enumerate(doc):
        texto = p.get_text()
        linhas = texto.split("\n")

        nome = "Desconhecido"
        for l in linhas:
            if re.fullmatch(r"[A-ZÁ-Ú\s]+", l):
                if 3 <= len(l.split()) <= 6:
                    nome = l
                    break

        arquivos.append(salvar_pdf(doc, [i], nome + " PONTO RM"))

    return arquivos

# =========================
# INFORME (OK)
# =========================
def processar_informe(doc):
    arquivos, grupo, cpf = [], [], "SEM_CPF"

    for i, p in enumerate(doc):
        texto = p.get_text()

        if "INFORME DE RENDIMENTOS" in texto.upper():
            if grupo:
                arquivos.append(salvar_pdf(doc, grupo, cpf))
                grupo = []

            m = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', texto)
            if m:
                cpf = re.sub(r'\D', '', m.group())

        grupo.append(i)

    if grupo:
        arquivos.append(salvar_pdf(doc, grupo, cpf))

    return arquivos

# =========================
# EXECUÇÃO
# =========================
if executar:

    if not st.session_state.tipo_doc:
        st.error("⚠️ Selecione o tipo de documento.")
    elif not uploaded_file:
        st.error("⚠️ Envie um PDF.")
    else:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

        tipo = st.session_state.tipo_doc

        if tipo == "ficha":
            arquivos = processar_ficha(doc)
        elif tipo == "trct":
            arquivos = processar_trct(doc)
        elif tipo == "seguro":
            arquivos = processar_seguro(doc)
        elif tipo == "ponto":
            arquivos = processar_ponto(doc)
        else:
            arquivos = processar_informe(doc)

        st.success("✔ Processamento concluído")

        for arq in arquivos:
            st.write("📄", arq)

        zip_path = "output/documentos.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for arq in arquivos:
                zipf.write(f"output/{arq}", arq)

        with open(zip_path, "rb") as f:
            st.download_button(
    label="📥 Baixar ZIP",
    data=f,
    file_name="documentos.zip",
    mime="application/zip"
)

# =========================
# FOOTER
# =========================
st.markdown("""
<div class='footer'>
🚀 Desenvolvido por <b>Gustavo Francisco</b>
</div>
""", unsafe_allow_html=True)
