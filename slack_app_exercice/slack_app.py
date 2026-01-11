import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import wikipedia
from pathlib import Path

# On charge le .env en utilisant override=True pour être sûr de bien écraser les vieilles versions en mémoire
load_dotenv(override=True)

# on récupère les variables d'environnement directement dans le .env (mesure de sécurité)
TOKEN_SLACK = os.environ.get("SLACK_BOT_TOKEN")
ID_CANAL = os.environ.get("CHANNEL_ID")

# on fait un test te chargement du token 
if TOKEN_SLACK is None:
    print("Erreur : Le Token n'est pas lu. Vérifie le fichier .env")
else:
    print(f"Token chargé : {TOKEN_SLACK[:10]}...")

# on initialise le bot slack
client = WebClient(token=TOKEN_SLACK)

try:
    print("Tentative d'envoi...")
    #on définit ke message à envoyer dès qu'il s'active
    client.chat_postMessage(
        channel=ID_CANAL,
        text="Bonjour tout le monde ! je suis de nouveau actif)"
    )
    print("ÇA MARCHE !")
except SlackApiError as e:
    # on affiche l'erreur si jamais cela échoue
    print(f"Erreur Slack : {e.response['error']}")

def interaction():
    try:
        # on récupère le dernier message du canal
        resultat = client.conversations_history(channel=ID_CANAL, limit=1)
        # on extrait le message
        messages = resultat.get("messages", [])
        
        if messages:
            msg = messages[0]
            texte = msg.get("text", "")
            # on récupère l'id de l'utilisateur qui a envoyé le dernier message
            user_id = msg.get("user", "quelqu'un")
            # balise pour voir le dernier message que le bot a lu
            print(f"Dernier message lu : {texte}")

            # on vérifie si le message contient le mot "bot" et que ce n'est pas le bot lui-même qui parle 
            # afin qu'il ne réponde pas à lui-même et créé une boucle infinie
            if "BOT" in texte.upper() and "bot_id" not in msg:
                print("Condition validée ! Envoi de la réponse...")
                # on définit le message qu'il envoit si le message contient le mot bot
                client.chat_postMessage(
                    channel=ID_CANAL, 
                    text=f"Bonjour <@{user_id}> ! Je suis le bot du Groupe 11 et j'ai bien reçu ton message."
                )
                print("✅ Interaction réussie !")
            else:
                print("Condition non remplie (soit pas de mot 'bot', soit c'est déjà le bot qui parle).")
    # on gère les erreurs potentielles autre que les conditions non remplies         
    except Exception as e:
        print(f"Erreur : {e}")
# on lance l'interaction
interaction()

############################################################################################

# on définit le dossier source des images, on est au même niveau que le fichier python
script_dir = Path(__file__).parent

dossier_source = script_dir / "dossier_image"

def envoyer_images():
    try:
        # On listes les fichiers présents dans le dossier source
        fichiers = os.listdir(dossier_source)
        print(f"Analyse du dossier... {len(fichiers)} fichiers trouvés.")

        for nom in fichiers:
            chemin = os.path.join(dossier_source, nom)
            
            # on fait un filtre pour ne prendre que les images en utilisant l'extension
            if nom.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                print(f"Envoi de {nom}...")
                client.files_upload_v2(
                    channel=ID_CANAL,
                    file=chemin,
                    initial_comment=f"Image automatique : {nom}"
                )
        print("Toutes les images ont été envoyées !")
    # on gère l'erreur si le dossier n'existe pas    
    except FileNotFoundError:
        print(f"Erreur : Le dossier '{dossier_source}' n'existe pas.")
    # on gère les autres erreurs potentielles lors de l'envoi    
    except Exception as e:
        print(f"Erreur lors de l'envoi : {e}")

# on lance l'envoie des images
envoyer_images()

#####################################################################################################

# on configure la langue pour Wikipedia
wikipedia.set_lang("fr")

# on charge le .env
load_dotenv(override=True)
BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
ID_CANAL = os.environ.get("CHANNEL_ID")
# on itialise le bot slack
client = WebClient(token=BOT_TOKEN)

# On garde en mémoire l'id du dernier message pour ne pas répondre en boucle
last_processed_ts = None

#on définit la fonction d'interaction avec Wikipedia
def wiki_bot_interaction():
    # globale sert à indiquer qu'on utilise la varaible définie en dehors de la fonction
    global last_processed_ts
    try:
        # on récupère le dernier message
        resultat = client.conversations_history(channel=ID_CANAL, limit=1)
        messages = resultat.get("messages", [])
        
        if messages:
            msg = messages[0]
            texte = msg.get("text", "")
            # ici on récupère l'heure précise à laquelle le message a été envoyé, c'est unique pour chaque message
            ts = msg.get("ts")
            
            # On vérifie si c'est un nouveau message et s'il contient "Wikipedia:"
            if ts != last_processed_ts and "Wikipedia:" in texte and "bot_id" not in msg:
                print(f"Requête détectée : {texte}")
                
                # on récupère le titre après les deux points
                titre = texte.split("Wikipedia:")[1].strip()
                
                try:
                    # on recherche le résumé et avec seulement un paragraphe
                    resume = wikipedia.summary(titre, sentences=1)
                    # on ajoute le titre et le résumé à la réponse et on ajoute les livres en markdown pour un peu plus de fun
                    reponse = f"📚 *Wikipedia : {titre}*\n\n{resume}"
                # il y a trop de résultats donc on demande des précisions
                except wikipedia.exceptions.DisambiguationError as e:
                    reponse = f"Trop de résultats pour '{titre}'. Sois plus précis !"
                # la page wikipedia n'existe pas
                except wikipedia.exceptions.PageError:
                    reponse = f"Désolé, je n'ai pas trouvé de page pour '{titre}'."
                # on gère les autres erreurs 
                except Exception:
                    reponse = "Une erreur est survenue lors de la recherche."

                # on envoi la réponse dasn le chat
                client.chat_postMessage(channel=ID_CANAL, text=reponse)
                # on marque ce message comme traité pour passer au suivant
                last_processed_ts = ts
                print("Réponse envoyée !")

    except Exception as e:
        print(f"Erreur : {e}")

# balise pour nous dire que le bot est actif et comment entrer le message
print(" WikiBot actif ! Écris 'Wikipedia:[titre]' dans Slack...")
try:
    # on fait une boucle infinie pour que le bot surveille en permanence les messages
    while True:
        wiki_bot_interaction()
        import time
        # il vérifie les messages toutes les 5 secondes
        time.sleep(5)
# on gère l'arrêt du bot proprement + une balise pour nous dire qu'il est bien arrêté
except KeyboardInterrupt:
    print("Bot arrêté.")