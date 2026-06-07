"""
Comparateur de télémétrie F1
----------------------------
Application Streamlit qui compare la télémétrie de deux pilotes sur leur
meilleur tour, à partir des données réelles fournies par FastF1.

Fonctionnalités :
  - sélection de l'année, du Grand Prix et de la session
  - choix de deux pilotes parmi ceux réellement présents dans la session
  - affichage configurable de plusieurs canaux (vitesse, accélérateur, etc.)
  - carte du circuit colorée selon la vitesse, avec numéros de virages
  - comparaison du pilote le plus rapide, d'un médian et du plus lent du plateau

Lancement : python -m streamlit run app.py
"""

import streamlit as st
import fastf1
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import os

# Crée le dossier de cache s'il n'existe pas encore, puis l'active.
os.makedirs('cache', exist_ok=True)
fastf1.Cache.enable_cache('cache')


# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------

@st.cache_data
def charger_session(annee, gp, session_type):
    """Charge une session FastF1 et la met en cache.

    Le décorateur @st.cache_data évite de recharger les données (opération
    lente) à chaque interaction de l'utilisateur avec l'interface : pour des
    arguments identiques, le résultat est servi depuis la mémoire.
    """
    session = fastf1.get_session(annee, gp, session_type)
    session.load()
    return session


def charger_tour_pilote(session, code_pilote):
    """Retourne le meilleur tour d'un pilote et sa télémétrie.

    On utilise get_car_data() plutôt que get_telemetry() : ce dernier tente
    un calcul du "pilote devant" qui échoue sur certaines sessions dont les
    données de position sont incomplètes. add_distance() ajoute la colonne
    'Distance' nécessaire pour tracer en fonction de la position sur le tour.
    """
    tour = session.laps.pick_drivers(code_pilote).pick_fastest()
    telemetrie = tour.get_car_data().add_distance()
    return tour, telemetrie


# ---------------------------------------------------------------------------
# Fonctions d'affichage
# ---------------------------------------------------------------------------

def tracer_canaux(tel1, tel2, canaux, label1, label2):
    """Trace les canaux sélectionnés, un étage par canal, axe X partagé."""
    fig, axes = plt.subplots(
        len(canaux), 1, figsize=(13, 3 * len(canaux)), sharex=True
    )
    # subplots renvoie un objet unique (et non une liste) quand il n'y a qu'un
    # seul graphe : on le met dans une liste pour traiter tous les cas pareil.
    if len(canaux) == 1:
        axes = [axes]

    for ax, canal in zip(axes, canaux):
        # 'Brake' est un booléen (True/False) : on le convertit en 0/100
        # pour qu'il soit lisible à la même échelle que les autres canaux.
        y1 = tel1[canal] * 100 if canal == 'Brake' else tel1[canal]
        y2 = tel2[canal] * 100 if canal == 'Brake' else tel2[canal]

        ax.plot(tel1['Distance'], y1, color='red', label=label1)
        ax.plot(tel2['Distance'], y2, color='blue', label=label2)
        ax.set_ylabel(canal)
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Distance (m)")
    plt.tight_layout()
    return fig


def tracer_circuit(tour, session, nom_gp, label_pilote):
    """Trace le circuit vu du dessus, coloré selon la vitesse, virages numérotés.

    La position (X, Y) et la vitesse proviennent de deux sources distinctes ;
    merge_channels() les aligne sur une base de temps commune pour qu'elles
    aient le même nombre de points.
    """
    position = tour.get_pos_data()
    donnees_voiture = tour.get_car_data()
    fusion = position.merge_channels(donnees_voiture)

    x = fusion['X'].to_numpy()
    y = fusion['Y'].to_numpy()
    vitesse = fusion['Speed'].to_numpy()

    # Le tracé est découpé en segments élémentaires (point -> point suivant)
    # afin que chaque segment puisse recevoir sa propre couleur.
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(figsize=(8, 8))
    trace = LineCollection(segments, cmap='plasma')
    trace.set_array(vitesse)                        # la couleur suit la vitesse
    trace.set_clim(vitesse.min(), vitesse.max())    # bornes de l'échelle de couleur
    trace.set_linewidth(4)
    ax.add_collection(trace)
    ax.autoscale()   # ajuste les limites des axes au tracé (add_collection ne le fait pas seul)

    # Numéros de virages : données officielles du circuit, si disponibles.
    try:
        virages = session.get_circuit_info().corners
        decalage = 500   # distance de décalage du numéro (à ajuster selon le circuit)

        for _, virage in virages.iterrows():
            # 'Angle' indique la direction vers l'extérieur du virage : on
            # projette un petit décalage dans cette direction pour éloigner
            # le numéro du tracé et ne pas masquer le dégradé de vitesse.
            angle = np.deg2rad(virage['Angle'])
            x_texte = virage['X'] + decalage * np.cos(angle)
            y_texte = virage['Y'] + decalage * np.sin(angle)

            # Petit trait reliant le numéro décalé à son virage, pour rester clair.
            ax.plot([virage['X'], x_texte], [virage['Y'], y_texte],
                    color='grey', linewidth=0.5, alpha=0.5)

            ax.text(
                x_texte, y_texte, str(virage['Number']),
                fontsize=11, color='white', ha='center', va='center',
                bbox=dict(boxstyle='circle', facecolor='black', alpha=0.7)
            )
    except Exception:
        # Certains circuits/saisons n'exposent pas les virages : on ignore
        # silencieusement plutôt que de faire échouer tout l'affichage.
        pass

    ax.axis('equal')   # proportions réelles (un virage ne doit pas être écrasé)
    ax.axis('off')     # on ne montre que le tracé, pas de repère gradué
    ax.set_title(f"Circuit {nom_gp} - vitesse de {label_pilote}")
    fig.colorbar(trace, ax=ax, label='Vitesse (km/h)')
    return fig


def tracer_enveloppe_plateau(session):
    """Trace la vitesse du pilote le plus rapide, d'un pilote médian et du plus lent.

    Les pilotes sont classés par le temps de leur meilleur tour. On sélectionne
    les trois positions (1er, milieu du classement, dernier) et on superpose
    leurs courbes de vitesse pour visualiser l'écart de performance.
    """
    # Pour chaque pilote, on récupère son meilleur tour et le temps associé.
    classement = []   # liste de (code_pilote, temps_au_tour, tour)
    for code in session.laps['Driver'].unique():
        tour = session.laps.pick_drivers(code).pick_fastest()
        if tour is None or tour.empty or tour['LapTime'] is None:
            continue
        classement.append((code, tour['LapTime'], tour))

    # On trie du plus rapide (temps le plus court) au plus lent.
    classement.sort(key=lambda element: element[1])

    if len(classement) < 3:
        return None   # pas assez de pilotes pour un trio pertinent

    plus_rapide = classement[0]
    median = classement[len(classement) // 2]
    plus_lent = classement[-1]

    selection = [
        (plus_rapide, 'green',  'Le plus rapide'),
        (median,      'orange', 'Médian'),
        (plus_lent,   'red',    'Le plus lent'),
    ]

    fig, ax = plt.subplots(figsize=(13, 5))
    for (code, temps, tour), couleur, role in selection:
        tel = tour.get_car_data().add_distance()
        # On formate le temps au tour (un Timedelta) en minutes:secondes.
        secondes = temps.total_seconds()
        temps_str = f"{int(secondes // 60)}:{secondes % 60:06.3f}"
        ax.plot(tel['Distance'], tel['Speed'], color=couleur,
                label=f"{role} : {code} ({temps_str})")

    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Vitesse (km/h)")
    ax.set_title("Vitesse : le plus rapide vs médian vs le plus lent du plateau")
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("Comparateur de télémétrie F1")

# Choix de la session
annee = st.selectbox("Année", [2024, 2023, 2022, 2021])
gp = st.text_input("Grand Prix", "Monza")
session_type = st.selectbox("Session", ['Q', 'R', 'FP1', 'FP2', 'FP3'])

# On charge la session ici pour pouvoir proposer la liste réelle des pilotes.
# En cas d'entrée invalide (GP mal orthographié, etc.), on affiche un message
# clair et on stoppe proprement le script.
try:
    session = charger_session(annee, gp, session_type)
    pilotes_dispo = sorted(session.laps['Driver'].unique())
except Exception as e:
    st.error(f"Impossible de charger cette session : {e}")
    st.stop()

# Sélection des deux pilotes, côte à côte
col1, col2 = st.columns(2)
with col1:
    pilote1 = st.selectbox("Pilote 1", pilotes_dispo, index=0)
with col2:
    pilote2 = st.selectbox("Pilote 2", pilotes_dispo, index=1)

# Canaux de télémétrie à comparer
canaux = st.multiselect(
    "Données à afficher",
    ['Speed', 'Throttle', 'Brake', 'RPM', 'nGear'],
    default=['Speed', 'Throttle']
)

afficher_circuit = st.checkbox("Afficher la carte du circuit (colorée par la vitesse)")
afficher_enveloppe = st.checkbox("Comparer le plus rapide / médian / le plus lent du plateau")

# ---------------------------------------------------------------------------
# Génération à la demande
# ---------------------------------------------------------------------------

if st.button("Générer"):
    tour1, tel1 = charger_tour_pilote(session, pilote1)
    tour2, tel2 = charger_tour_pilote(session, pilote2)

    if not canaux:
        st.warning("Choisis au moins un canal à afficher.")
    else:
        st.pyplot(tracer_canaux(tel1, tel2, canaux, pilote1, pilote2))

    if afficher_circuit:
        st.pyplot(tracer_circuit(tour1, session, gp, pilote1))

    if afficher_enveloppe:
        fig_env = tracer_enveloppe_plateau(session)
        if fig_env is None:
            st.warning("Pas assez de pilotes exploitables dans cette session.")
        else:
            st.pyplot(fig_env)