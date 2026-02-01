import streamlit as st
import os
import uuid
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_text_splitters import RecursiveCharacterTextSplitter 
from langchain_core.documents import Document
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory

# configuration initiale de la page streamlit
st.set_page_config(page_title="Othello AI - Mistral", layout="wide")

# le session state sert à garder l'historique des discussions
if "chats" not in st.session_state:
    #ici on initialise un dictionnaire vide pour stocker les discussions
    st.session_state.chats = {}
# si aucune discussion n'est sélectionnée on initialise la variable à None, de fait on crée une nouvelle discussion
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# on définit la fonction pour le RAG
def load_text():
    # sur le site on a le texte de othello dans un fichier txte utf-8. On doit donc spécifier l'encodage
    with open("othello.txt", "r", encoding="utf-8") as f:
        text = f.read()
    # on découpe le texte en parties pour le RAG afin d'améliorer la pertinence des réponses
    #la taille du chunk est de 500 caractères comme spécifié dans l'assignment
    # l'overlap est de 100 caractères pour garder du contexte entre les chunks. 
    # (il récupère les 100 derniers caractères du chunk précédent afin d'amléliorer la cohérence)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    # on crée une liste de documents à partir des chunks
    return [Document(page_content=chunk) for chunk in splitter.split_text(text)]

# le @st.cache_resourceest un décorateur qui permet de ne pas recalculer la base de données à chaque interaction
@st.cache_resource
# on définit la fonction qui configure la base de données vectorielle
def setup_db(api_key):
    # on utilise les embeddings Mistral AI (chaque IA à son propre modèle d'embedding mistral n'a pas le meme que chatgpt)
    embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
    # on définit le directory où sera stockée la base de données chromadb
    persist_dir = "./chroma_db_mistral"
    # on test se la base de données existe déjà
    if os.path.exists(persist_dir):
        # si oui on la charge
        return Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    else:
        # sinon on la crée à partir des documents
        docs = load_text()
        return Chroma.from_documents(docs, embeddings, persist_directory=persist_dir)

#on définit la fonction pour créer une nouvelle discussion
def create_new_chat():
    # chaque discussion a un id unique
    new_id = str(uuid.uuid4())
    # le titre par défaut est Discussion + numéro de la discussion
    # chaque discussion a son propre historique de messages et sa propre mémoire
    st.session_state.chats[new_id] = {
        "title": f"Discussion {len(st.session_state.chats) + 1}",
        "messages": [],
        "memory": ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key='answer')
    }
    # on met à jour l'id de la discussion courante
    st.session_state.current_chat_id = new_id

# on crée la barre latérale
with st.sidebar:
    # titre de l'application
    st.title("📚 Othello AI")
    
    # création du bouton pour la nouvelle disccussion avec du markdown pour le visuel
    if st.button("➕ Nouvelle discussion", use_container_width=True):
        # on appelle la fonction pour créer une nouvelle discussion
        create_new_chat()
    
    # st.divider crée une ligne de séparation dans la barre latérale afin de mieux organiser les disucssions
    st.divider()
    # le titre de la section est historique pour les discussions précédentes
    st.subheader("Historique")
    # on fait une boucle sur les discussions existantes
    for chat_id, chat_data in st.session_state.chats.items():
        # Bouton pour switcher entre les discussions
        if st.button(f"💬 {chat_data['title']}", key=chat_id, use_container_width=True):
            # on met à jour l'id de la discussion courante pour afficher l'historique qui correspond
            st.session_state.current_chat_id = chat_id
    
    # on remet une séparation pour une nouvelle section
    st.divider()
    # initialisation de la navigation entre les pages
    # on a une page d'accueil, une page pour le chatbot et une page pour le comparatif des modèles
    page = st.radio("Navigation", ["🏠 Accueil", "💬 Chatbot", "🧠 Comparatif Modèles"])
    # c'est l'espace pour que l'utilisateur entre sa clé Mistral AI
    api_key = st.text_input("🔑 Clé API Mistral", type="password")

# si la page sélectionnée est l'accueil
# on affiche le titre et les instructions relatives à l'utilisation de l'application
if page == "🏠 Accueil":
    st.title("🎭 Analyse d'Othello avec Mistral AI")
    st.write("Pour utiliser ce chatbot, entrez votre clé API Mistral AI dans la barre latérale. " \
    "Créez une nouvelle discussion et posez vos questions sur le texte d'Othello. " \
    "Le chatbot utilise la technique de RAG (Retrieval-Augmented Generation) pour fournir des réponses précises basées sur le texte." \
    "\n\n" "si vous n'avez pas de clé API, vous pouvez en obtenir une gratuitement sur le site de Mistral AI.")
    st.markdown("lien : [Mistral AI](https://console.mistral.ai/home)")
# si la page sélectionnée est le comparatif des modèles alors on affiche un tableau comparatif entre les deux modèles mistral disponibles
elif page == "🧠 Comparatif Modèles":
    st.title("Comparatif des modèles Mistral")
    st.write("Voici les deux modèles disponibles dans ce chatbot :")
    st.table({
        "Modèle": ["mistral-small-latest", "mistral-large-latest"],
        "Force": ["Vitesse & Efficacité", "Raisonnement complexe & Nuances"],
        "Usage": ["Questions simples", "Analyses littéraires poussées"]
    })
# si la page sélectionnée est le chatbot
elif page == "💬 Chatbot":
    # on vérifie que l'utilisateur a bien entré sa clé API
    if not api_key:
        st.error("Veuillez entrer votre clé API Mistral.")
    # on vérifie qu'une discussion est sélectionnée
    elif st.session_state.current_chat_id is None:
        st.info("Cliquez sur '➕ Nouvelle discussion' pour démarrer.")
    # si une discussion est sélectionnée on affiche l'historique des messages
    else:
        chat = st.session_state.chats[st.session_state.current_chat_id]
        # on affiche le titre de la discussion
        st.title(f"Discussion : {chat['title']}")
        # on laisse le choix du modèle à l'utilisateur
        model_choice = st.selectbox("Modèle Mistral", ["mistral-small-latest", "mistral-large-latest"])
        # on configure la base de données vectorielle
        v_db = setup_db(api_key)

        # affichage de l'historique des messages de la discussion selectionnée
        for m in chat["messages"]:
            # affichage des messages précédents. m["role"] sert à différencier les messages utilisateur et agent
            with st.chat_message(m["role"]):
                # on affiche le contenu du chat en markdown
                st.markdown(m["content"])
        #le prompt pour que l'utilisateur entre sa question
        if prompt := st.chat_input("Posez votre question sur Othello"):
            # ajout du message utilisateur à l'historique
            chat["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # on définit la réponse de l'agent
            with st.chat_message("assistant"):
                # le spinner c'est le message qui s'affiche pendant le traitement
                with st.spinner("Analyse du texte..."):
                    # initialisation de la chaine question-réponse
                    qa_chain = ConversationalRetrievalChain.from_llm(
                        llm=ChatMistralAI(mistral_api_key=api_key, model=model_choice),
                        retriever=v_db.as_retriever(search_kwargs={"k": 3}), # On prend les 3 meilleures sources
                        memory=chat["memory"],
                        return_source_documents=True
                    )
                    # on utilise invoke pour appeler la chaine avec la question de l'utilisateur
                    response = qa_chain.invoke({"question": prompt})
                    # on récupère la réponse générée par l'agent
                    answer = response["answer"]
                    # on récupère les documents sources utilisés pour générer la réponse
                    source_docs = response["source_documents"]

                    # on formate les sources pour avoir seulement celles qui nous ont servi à répondre
                    source_text = "\n\n**🔍 Sources utilisées pour cette réponse :**\n"
                    # on affiche les 3 premiers extraits de chaque document source
                    for i, doc in enumerate(source_docs):
                        # on définit une limite de 3 extraits pour pas surchager la réponse
                        source_text += f"**Extrait {i+1} :** {doc.page_content[:200]}...\n"
                    
                    # la réponse complete c'est la réponse + les sources
                    full_response = answer + source_text
                    st.markdown(full_response)
                    
                    # on sauve l'historique en ajoutant la réponse de l'agent dans la liste chat["messages"]
                    chat["messages"].append({"role": "assistant", "content": full_response})
                    
                    # pour renommer la discussion on fait comme toutes les IA, on prend les 30 premiers caractères du premier prompt
                    if len(chat["messages"]) == 2:
                        chat["title"] = prompt[:30] + "..."
                        st.rerun()