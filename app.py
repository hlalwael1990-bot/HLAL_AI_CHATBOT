import streamlit as st
import os
import base64
import tempfile
import pandas as pd
import hmac

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from docx import Document
from duckduckgo_search import DDGS

# -----------------------------
# LOAD ENV
# -----------------------------

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
PASSWORD = os.getenv("APP_PASSWORD")

# -----------------------------
# STREAMLIT CONFIG
# -----------------------------

st.set_page_config(
    page_title="HLAL AI",
    page_icon="🤖",
    layout="wide"
)

# -----------------------------
# DARK MODE STYLE
# -----------------------------

st.markdown("""
<style>
body { background-color:#0e1117; color:white;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SESSION STATES
# -----------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "auth" not in st.session_state:
    st.session_state.auth = False

if "client" not in st.session_state:
    st.session_state.client = None

if "page" not in st.session_state:
    st.session_state.page = "Chat"

if "pending_files" not in st.session_state:
    st.session_state.pending_files = []

# -----------------------------
# SIDEBAR LOGIN + NAVIGATION
# -----------------------------

with st.sidebar:

    st.title("🤖 HLAL AI")

    if not st.session_state.auth:

        st.subheader("Sign In")

        method = st.radio(
            "Login Method",
            ["Password", "API Key (Optional)"]
        )

        with st.form("login_form"):

            pw = st.text_input(
                "Enter Password / API Key",
                type="password"
            )

            submit = st.form_submit_button("Sign In")

            if submit:

                if method == "Password":

                    if hmac.compare_digest(pw, PASSWORD):

                        st.session_state.client = OpenAI(api_key=API_KEY)
                        st.session_state.auth = True
                        st.rerun()

                    else:
                        st.error("Wrong password")

                else:

                    if pw.startswith("sk-"):

                        st.session_state.client = OpenAI(api_key=pw)
                        st.session_state.auth = True
                        st.rerun()

                    else:
                        st.error("Invalid API key")

        st.stop()

    st.divider()

    if st.button("💬 Chat"):
        st.session_state.page = "Chat"

    if st.button("📷 Camera Vision"):
        st.session_state.page = "Camera"

    if st.button("🎤 Voice Chat"):
        st.session_state.page = "Voice"

    if st.button("🎨 Image Generation"):
        st.session_state.page = "Image"

    if st.button("🔊 Text To Speech"):
        st.session_state.page = "TTS"

    st.divider()

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []

    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.session_state.messages = []
        st.rerun()

client = st.session_state.client

# -----------------------------
# WEB SEARCH
# -----------------------------

def web_search(query):

    results = ""

    with DDGS() as ddgs:

        data = list(ddgs.text(query, max_results=5))

    for r in data:

        results += f"{r['title']} - {r['body']}\n"

    return results

# -----------------------------
# PDF READER
# -----------------------------

def read_pdf(file):

    reader = PdfReader(file)

    text = ""

    for page in reader.pages:

        text += page.extract_text()

    return text

# -----------------------------
# CHAT PAGE
# -----------------------------

if st.session_state.page == "Chat":

    st.title("💬 HLAL AI Chatbot")

    # Welcome Message
    if len(st.session_state.messages) == 0:

        welcome = """
### 🤖 You are welcome in Mr. Wael Hlal AI Chatbot  
How can I assist you today?

---

### 🤖 اهلا وسهلا بك في روبوت وائل هلال للذكاء الاصطناعي  
كيف يمكنني مساعدتك اليوم؟
"""

        st.session_state.messages.append(
            {"role": "assistant", "content": welcome}
        )

    for msg in st.session_state.messages:

        avatar = "🤖" if msg["role"] == "assistant" else "👤"

        with st.chat_message(msg["role"], avatar=avatar):

            st.markdown(msg["content"])

    uploaded_files = st.file_uploader(
        "Attach files",
        accept_multiple_files=True,
        type=["pdf","docx","csv","xlsx","png","jpg","jpeg"]
    )

    if uploaded_files:

        for f in uploaded_files:

            if f not in st.session_state.pending_files:

                st.session_state.pending_files.append(f)

    user_input = st.chat_input("Ask anything...")

    if user_input:

        content = user_input

        if "search" in user_input.lower() or "بحث" in user_input:

            results = web_search(user_input)

            content += f"\n\nWeb Results:\n{results}"

        for file in st.session_state.pending_files:

            if file.type == "application/pdf":

                text = read_pdf(file)

                content += f"\n\nPDF Content:\n{text[:12000]}"

            elif "word" in file.type:

                doc = Document(file)

                text = "\n".join([p.text for p in doc.paragraphs])

                content += f"\n\nDOCX:\n{text}"

            elif file.type == "text/csv":

                df = pd.read_csv(file)

                content += f"\n\nCSV:\n{df}"

            elif "excel" in file.type:

                df = pd.read_excel(file)

                content += f"\n\nExcel:\n{df}"

        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        response_text = ""

        with st.chat_message("assistant"):

            placeholder = st.empty()

            with client.responses.stream(
                model="gpt-5.2",
                input=st.session_state.messages
            ) as stream:

                for event in stream:

                    if event.type == "response.output_text.delta":

                        response_text += event.delta

                        placeholder.markdown(response_text)

        st.session_state.messages.append(
            {"role": "assistant", "content": response_text}
        )

        st.session_state.pending_files = []

        st.rerun()

# -----------------------------
# CAMERA VISION
# -----------------------------

if st.session_state.page == "Camera":

    st.title("📷 AI Camera Vision")

    st.write("Capture an image and ask AI about it")

    image = st.camera_input("Take a photo")

    question = st.text_input("Ask about the image")

    if image:

        st.image(image, use_container_width=True)

        if question:

            image_bytes = image.getvalue()

            base64_img = base64.b64encode(image_bytes).decode()

            with st.spinner("Analyzing image..."):

                response = client.responses.create(
                    model="gpt-5.2",
                    input=[{
                        "role":"user",
                        "content":[
                            {"type":"input_text","text":question},
                            {
                                "type":"input_image",
                                "image_url":f"data:image/jpeg;base64,{base64_img}"
                            }
                        ]
                    }]
                )

            st.write(response.output_text)

# -----------------------------
# VOICE CHAT
# -----------------------------

if st.session_state.page == "Voice":

    st.title("🎤 Voice Assistant")

    audio = st.audio_input("Speak")

    if audio:

        transcript = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio
        )

        user_text = transcript.text

        st.write("You:", user_text)

        response = client.responses.create(
            model="gpt-5.2",
            input=user_text
        )

        reply = response.output_text

        st.write("AI:", reply)

# -----------------------------
# IMAGE GENERATION
# -----------------------------

if st.session_state.page == "Image":

    st.title("🎨 Image Generator")

    prompt = st.text_input("Describe image")

    if st.button("Generate"):

        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        img = base64.b64decode(result.data[0].b64_json)

        st.image(img)

# -----------------------------
# TEXT TO SPEECH
# -----------------------------

if st.session_state.page == "TTS":

    st.title("🔊 Text To Speech")

    text = st.text_area("Enter text")

    if st.button("Generate Voice"):

        speech_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")

        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text
        )

        speech.stream_to_file(speech_file.name)

        audio = open(speech_file.name, "rb")

        st.audio(audio.read())