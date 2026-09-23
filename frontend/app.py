"""Upload a Food-11 image and call the private inference service."""
import os

import requests
import streamlit as st

INFERENCE_URL = os.environ.get("INFERENCE_URL", "http://127.0.0.1:8000").rstrip("/")


def classify(name, content, content_type):
    response = requests.post(
        f"{INFERENCE_URL}/predict",
        files={"file": (name, content, content_type)}, timeout=60,
    )
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="Food-11", page_icon="🍽️")
st.title("Food-11 : reconnaître un plat")
st.write("Choisis une photo pour obtenir une catégorie parmi les 11 aliments du modèle.")
uploaded = st.file_uploader("Photo du plat", type=["jpg", "jpeg", "png"])
if uploaded is not None:
    try:
        st.image(uploaded, width=300)
    except Exception:
        st.error("Cette image ne peut pas être affichée.")
    if st.button("Analyser la photo", type="primary"):
        try:
            with st.spinner("Analyse en cours…"):
                result = classify(uploaded.name, uploaded.getvalue(), uploaded.type)
            st.success(f"Catégorie : {result['category']}")
            st.metric("Confiance du modèle", f"{result['confidence']:.1%}")
            st.caption("La confiance est un score du modèle ; la prédiction peut être incorrecte.")
        except requests.HTTPError as exc:
            st.error(f"L’API a refusé la photo (HTTP {exc.response.status_code}). Vérifie le format et la taille (10 Mio maximum).")
        except requests.RequestException:
            st.error("Le service est momentanément indisponible. Réessaie dans quelques instants.")
