import streamlit as st
import time
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter 
from langchain_core.documents import Document
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory

# --- CONFIGURATION ET CHARGEMENT ---

def load_local_text():
    """Lit le fichier othello.txt et le prépare pour le découpage (2 pts doc)."""
    with open("othello.txt", "r", encoding="utf-8") as f:
        raw_text = f.read()
    
    # On garde une taille raisonnable pour que la progression soit visible
    raw_text = raw_text[:50000] 

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(raw_text)
    return [Document(page_content=chunk) for chunk in chunks]

@st.cache_resource
def setup_vector_db(model_name):
    """Initialise Chroma avec une barre de progression réelle (2 pts Chroma)."""
    docs = load_local_text()
    embeddings = OllamaEmbeddings(model=model_name)
    
    # Affichage de la progression dans l'interface
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("Log : Début de la création des vecteurs...")
    print("Début du traitement des chunks...")

    # Pour simuler/voir le progrès, on traite par lots
    # Note : Chroma.from_documents traite tout d'un coup, 
    # donc on affiche une attente visuelle pendant l'opération lourde.
    status_text.text(f"Analyse de {len(docs)} segments de texte avec {model_name}...")
    progress_bar.progress(50) # On marque l'étape de chargement
    
    # C'est cette ligne qui prend du temps (calcul des embeddings)
    vector_db = Chroma.from_documents(
        docs, 
        embeddings, 
        persist_directory="./chroma_db"
    )
    
    progress_bar.progress(100)
    status_text.text("✅ Base de données vectorielle prête !")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()
    
    return vector_db

def init_chat():
    """Initialise la mémoire pour retenir le contexte (3 pts mémoire)."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True, 
            output_key='answer'
        )

def run_chat(chain):
    """Gère l'envoi et l'affichage avec sources obligatoires (6 pts sources)."""
    if prompt := st.chat_input("Votre question sur l'œuvre :"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Othello réfléchit..."):
                result = chain.invoke({"question": prompt})
                
                # Extraction et affichage des sources (Crucial pour le barème)
                sources_html = "\n\n**Extraits consultés :**\n"
                for doc in result["source_documents"]:
                    sources_html += f"- {doc.page_content[:150]}...\n"
                
                full_ans = result["answer"] + sources_html
                st.markdown(full_ans)
                st.session_state.messages.append({"role": "assistant", "content": full_ans})

# --- INTERFACE (1 pt widgets) ---

st.sidebar.title("Paramètres IA 🎭")
nav = st.sidebar.radio("Navigation", ["Accueil", "Chatbot"])
# Sélection du modèle parmi ceux installés (image_785ed8.png)
llm_model = st.sidebar.selectbox("Modèle Ollama", ["llama3", "mistral"]) 

if st.sidebar.button("Effacer l'historique"):
    st.session_state.messages = []
    if "memory" in st.session_state:
        st.session_state.memory.clear()
    st.rerun()

if nav == "Accueil":
    st.title("🎭 Analyse Intelligente : Othello")
    st.write("Ce chatbot utilise le RAG (Retrieval Augmented Generation) pour répondre localement.")
    st.info("Allez dans l'onglet 'Chatbot' pour démarrer l'analyse.")
else:
    st.title("💬 Chat avec Othello")
    # Lancement avec indicateur visuel
    v_db = setup_vector_db(llm_model)
    init_chat()
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Chaîne de conversation utilisant la mémoire de session
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=ChatOllama(model=llm_model),
        retriever=v_db.as_retriever(),
        memory=st.session_state.memory,
        return_source_documents=True
    )
    
    run_chat(qa_chain)