import time
import streamlit as st
import pytesseract
from gtts import gTTS
from deep_translator import GoogleTranslator, MyMemoryTranslator
from PIL import Image, ImageOps
from io import BytesIO

st.set_page_config(page_title="Lector de carteles", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@500&display=swap');
.stApp {
    background-color: #1b1b3a;
}
[data-testid="stHeader"] {
    background: transparent;
}
section[data-testid="stSidebar"] {
    background-color: #25254d;
}
.stApp p, .stApp label, .stApp li {
    color: #f3e9ff;
}
h1, h2, h3 {
    font-family: 'Fredoka', sans-serif;
    color: #ff9f1c !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #ff9f1c;
    border-radius: 12px;
}
[data-testid="stAlert"] {
    background-color: #2f2f5e !important;
    border: 1px solid #ff9f1c;
}
[data-testid="stAlert"] * {
    color: #f3e9ff !important;
}
[data-testid="stFileUploaderDropzone"] {
    background-color: #25254d !important;
    border: 1px dashed #ff9f1c;
}
[data-testid="stFileUploaderDropzone"] * {
    color: #f3e9ff !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background-color: #ff9f1c !important;
    color: #1b1b3a !important;
}
div.stButton > button, div.stDownloadButton > button {
    background-color: #ff9f1c;
    color: #1b1b3a !important;
    border: none;
    border-radius: 20px;
    font-weight: bold;
    padding: 8px 24px;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background-color: #f3e9ff;
}
</style>
""", unsafe_allow_html=True)

idiomas_ocr = {
    "Español": ("spa", "es-ES"),
    "Inglés": ("eng", "en-GB"),
    "Español e inglés": ("spa+eng", "es-ES"),
}

voces = {
    "Español": ("es", "es-ES"),
    "Inglés": ("en", "en-GB"),
    "Japonés": ("ja", "ja-JP"),
    "Francés": ("fr", "fr-FR"),
    "Portugués": ("pt", "pt-BR"),
    "Italiano": ("it", "it-IT"),
    "Coreano": ("ko", "ko-KR"),
    "Mandarín": ("zh-CN", "zh-CN"),
}


@st.cache_data(show_spinner=False)
def traducir(texto, destino, origen_mm, destino_mm):
    for intento in range(3):
        try:
            return GoogleTranslator(source="auto", target=destino).translate(texto)
        except Exception:
            time.sleep(2)
    return MyMemoryTranslator(source=origen_mm, target=destino_mm).translate(texto[:450])


if "cuaderno" not in st.session_state:
    st.session_state.cuaderno = []

with st.sidebar:
    st.subheader("Configuración")
    idioma_cartel = st.selectbox("Idioma del cartel", list(idiomas_ocr.keys()))
    idioma_voz = st.selectbox("Quiero escucharlo en", list(voces.keys()), index=2)
    lenta = st.toggle("Voz lenta")
    blanco_negro = st.checkbox("Blanco y negro puro (para fotos difíciles)")

st.title("🗺️ Lector de carteles")
st.write("Apunta a un cartel, menú o letrero y escúchalo en tu idioma.")

modo = st.radio("¿De dónde viene la imagen?", ["Subir imagen", "Tomar foto"], horizontal=True)

if modo == "Subir imagen":
    archivo = st.file_uploader("Foto del cartel", type=["jpg", "jpeg", "png"])
else:
    archivo = st.camera_input("Apunta al cartel y toma la foto")

if archivo is not None:
    original = ImageOps.exif_transpose(Image.open(archivo)).convert("RGB")
    procesada = ImageOps.autocontrast(ImageOps.grayscale(original))
    if blanco_negro:
        procesada = procesada.point(lambda p: 255 if p > 128 else 0)
    st.image(original, caption="Tu cartel", use_container_width=True)

    if st.button("Leer el cartel"):
        try:
            with st.spinner("Leyendo, traduciendo y preparando la voz..."):
                crudo = pytesseract.image_to_string(procesada, lang=idiomas_ocr[idioma_cartel][0])
                texto = " ".join(crudo.split())[:1500]
                if texto == "":
                    st.info("No encontré letras. Prueba con 'Blanco y negro puro' o con una foto más nítida.")
                else:
                    codigo, codigo_mm = voces[idioma_voz]
                    traducido = traducir(texto, codigo, idiomas_ocr[idioma_cartel][1], codigo_mm)
                    audio = BytesIO()
                    gTTS(traducido, lang=codigo, slow=lenta).write_to_fp(audio)
                    st.session_state.cuaderno.insert(0, {
                        "original": texto,
                        "traducido": traducido,
                        "idioma": idioma_voz,
                        "audio": audio.getvalue(),
                    })
        except pytesseract.TesseractNotFoundError:
            st.error("No encuentro Tesseract. Agrega un archivo packages.txt con tesseract-ocr y tesseract-ocr-spa.")
        except Exception as e:
            st.error(f"No se pudo completar la lectura: {e}")

st.divider()
st.header("Cuaderno de viaje")

if len(st.session_state.cuaderno) == 0:
    st.write("Aquí aparecerán tus lecturas.")
else:
    if st.button("Borrar cuaderno"):
        st.session_state.cuaderno = []
        st.rerun()

for i, item in enumerate(st.session_state.cuaderno):
    with st.container(border=True):
        st.caption("El cartel dice")
        st.write(item["original"])
        st.caption(f"En {item['idioma']}")
        st.write(item["traducido"])
        st.audio(item["audio"], format="audio/mp3")
        st.download_button("Descargar audio", item["audio"], file_name=f"cartel_{i}.mp3", mime="audio/mp3", key=f"d{i}")
