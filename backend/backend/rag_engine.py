# backend/rag_engine.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import os

# Charger le modèle d'embedding
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Chemins
INDEX_PATH = "vector_db/reports.index"
TEXTS_PATH = "vector_db/texts.pkl"

# Données initiales (à enrichir plus tard)
initial_texts = [
    "Introduction : présentez le contexte, les objectifs et la portée du rapport.",
    "Méthodologie : expliquez les outils, sources et étapes utilisées.",
    "Analyse des risques : identifiez les menaces internes et externes.",
    "Conclusion : résumez les points clés et proposez des recommandations."
]

# Créer ou charger l'index FAISS
def load_faiss_index():
    if os.path.exists(INDEX_PATH):
        index = faiss.read_index(INDEX_PATH)
    else:
        dimension = 384  # taille du vecteur de all-MiniLM-L6-v2
        index = faiss.IndexFlatL2(dimension)
        embeddings = embedding_model.encode(initial_texts)
        index.add(np.array(embeddings))
        faiss.write_index(index, INDEX_PATH)
        with open(TEXTS_PATH, "wb") as f:
            pickle.dump(initial_texts, f)
    return index

# Charger les textes
def load_texts():
    if os.path.exists(TEXTS_PATH):
        with open(TEXTS_PATH, "rb") as f:
            return pickle.load(f)
    return initial_texts

# Rechercher les textes similaires
def search_similar(query: str, k: int = 3):
    index = load_faiss_index()
    texts = load_texts()
    query_embedding = embedding_model.encode([query])
    distances, indices = index.search(np.array(query_embedding), k)
    return [texts[i] for i in indices[0]]

# Ajouter un nouveau texte (ex: nouvelle section de rapport)
def add_to_faiss(text: str):
    index = load_faiss_index()
    texts = load_texts()
    new_embedding = embedding_model.encode([text])
    index.add(np.array(new_embedding))
    faiss.write_index(index, INDEX_PATH)
    texts.append(text)
    with open(TEXTS_PATH, "wb") as f:
        pickle.dump(texts, f)