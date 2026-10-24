import streamlit as st

st.set_page_config(
    page_title="Simulation Ballon Tampon & FWM PRO",
    layout="wide"
)

st.title("🛢️ Outil de Dimensionnement ECS & Tampon Primaire (FWM PRO)")
st.markdown("Simulez l'autonomie et les temps de chauffe d'un ballon tampon primaire couplé à une station d'échange **FWM PRO** (avec gestion des cascades jusqu'à 6 modules)[cite: 1].")

# --- BARRE LATÉRALE : SAISIES UTILISATEUR ---
st.sidebar.header("1. Paramètres du Système")
vol_tampon = st.sidebar.number_input("Volume tampon primaire (L)", min_value=50, max_value=5000, value=500, step=50)

# Génération des options de modèles et cascades (jusqu'à 6 stations comme indiqué dans la doc)
modeles_base = ["FWM PRO 70", "FWM PRO 90", "FWM PRO 170"]
options_fwm = []
for m in modeles_base:
    for nb in range(1, 7):
        if nb == 1:
        # FWM PRO seule
            options_fwm.append(f"{m} (1 Station)")
        else:
            options_fwm.append(f"{nb} x {m} (Cascade)")

selected_fwm_full = st.sidebar.selectbox("Sélection Modèle / Cascade FWM PRO", options_fwm)

# Extraction du modèle de base et du nombre de stations en cascade
for m in modeles_base:
    if m in selected_fwm_full:
        modele_actif = m
        break

# Récupération du nombre de stations
import re
match_nb = re.search(r'(\d+)\s*x', selected_fwm_full)
nb_stations = int(match_nb.group(1)) if match_nb else 1

puissance_pac = st.sidebar.number_input("Puissance PAC générateur (kW)", min_value=2.0, max_value=200.0, value=16.0, step=1.0)

st.sidebar.header("2. Consignes Primaire")
t_consigne = st.sidebar.number_input("T° primaire de consigne (°C)", min_value=40.0, max_value=85.0, value=60.0, step=1.0)
t_redemarrage = st.sidebar.number_input("T° redémarrage de chauffe (°C)", min_value=30.0, max_value=80.0, value=45.0, step=1.0)

st.sidebar.header("3. Soutirage ECS Secondaire")
t_froid = st.sidebar.number_input("T° eau froide réseau (°C)", min_value=5.0, max_value=20.0, value=10.0, step=1.0)

# Sélection au degré près
t_ecs = st.sidebar.number_input("T° de soutirage ECS (°C)", min_value=35.0, max_value=65.0, value=45.0, step=1.0)

# Saisie libre du débit selon les points de tirage
debit_saisie = st.sidebar.number_input("Débit ECS de puisage (L/min)", min_value=1.0, max_value=500.0, value=20.0, step=1.0)

# --- ESTIMATION INDICATIVE DE LA CAPACITÉ MAX DU FWM PRO (Unitaire) ---
capacites_fwm = {
    "FWM PRO 70": 27.4,   # L/min à 60°C primaire / 45°C ECS
    "FWM PRO 90": 35.8,   # L/min à 60°C primaire / 45°C ECS
    "FWM PRO 170": 61.3   # L/min à 60°C primaire / 45°C ECS
}
debit_max_unitaire = capacites_fwm.get(modele_actif, 30.0)

# Facteur d'ajustement selon l'écart de température réel
delta_ref = 60.0 - t_ecs
delta_actuel = t_consigne - t_ecs
if delta_ref > 0 and delta_actuel > 0:
    debit_max_unitaire = debit_max_unitaire * (delta_actuel / delta_ref)
else:
    debit_max_unitaire = 0.0

# Capacité totale de la cascade
debit_max_station = debit_max_unitaire * nb_stations

st.sidebar.markdown("---")
st.sidebar.markdown(f"**ℹ️ Capacité max estimée cascade ({selected_fwm_full}) :** <br><span style='font-size: 18px; color: #0083B8;'>**{max(0.0, debit_max_station):.1f} L/min**</span>", unsafe_allow_html=True)

# --- VÉRIFICATIONS PHYSIQUES DES TEMPÉRATURES ---
erreurs = []
if t_redemarrage >= t_consigne:
    erreurs.append("La température de redémarrage doit être strictement inférieure à la température de consigne primaire.")

if t_ecs >= t_consigne:
    erreurs.append(f"La température ECS ({t_ecs}°C) ne peut pas être supérieure ou égale à la température primaire de consigne ({t_consigne}°C).")

if t_ecs > t_redemarrage:
    st.warning(f"⚠️ **Attention :** La température ECS ({t_ecs}°C) est supérieure à la température de redémarrage du tampon ({t_redemarrage}°C). La température d'ECS chutera avant que le cycle de chauffe primaire ne soit réenclenché.")

if debit_saisie > debit_max_station and debit_max_station > 0:
    st.warning(f"⚠️ **Alerte Débit :** Le débit sélectionné ({debit_saisie:.1f} L/min) dépasse la capacité maximale estimée de votre configuration **{selected_fwm_full}** ({debit_max_station:.1f} L/min).")

if erreurs:
    for err in erreurs:
        st.error(f"❌ Erreur : {err}")
else:
    # --- CALCULS THERMODYNAMIQUES ---
    cp_eau = 4.186  # kJ/kg.°C
    delta_t_tampon = t_consigne - t_redemarrage
    
    # 1. Énergie utile stockée dans le tampon (kJ et kWh)
    energie_stockee_kj = vol_tampon * cp_eau * delta_t_tampon
    energie_stockee_kwh = energie_stockee_kj / 3600

    # 2. Temps de chauffe de la PAC (de T_redemarrage à T_consigne)
    temps_chauffe_sec = energie_stockee_kj / puissance_pac
    temps_chauffe_min = temps_chauffe_sec / 60

    # 3. Volume ECS produit à T_ecs grâce aux calories du tampon
    energie_par_litre_ecs = cp_eau * (t_ecs - t_froid)
    vol_ecs_total = energie_stockee_kj / energie_par_litre_ecs if energie_par_litre_ecs > 0 else 0

    # 4. Temps de soutirage continu au débit sélectionné avant redémarrage
    temps_soutirage_min = vol_ecs_total / debit_saisie if debit_saisie > 0 else 0

    # --- AFFICHAGE DES RÉSULTATS ---
    st.markdown("---")
    st.header("📊 Résultats de la Simulation")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Temps de chauffe PAC",
            value=f"{temps_chauffe_min:.1f} min",
            help="Temps nécessaire à la PAC pour remonter le tampon de T_redémarrage à T_consigne."
        )

    with col2:
        st.metric(
            label="Volume ECS soutirable",
            value=f"{vol_ecs_total:.1f} L",
            help="Volume total d'ECS disponible dans la tranche d'énergie utile du tampon."
        )

    with col3:
        st.metric(
            label="Autonomie au débit de tirage",
            value=f"{temps_soutirage_min:.1f} min",
            help="Durée de soutirage continu au débit de tirage indiqué avant que la chauffe ne redémarre."
        )

    # --- DÉTAILS ET PUISSANCE ---
    st.markdown("---")
    st.markdown("### 🔍 Détails du Bilan Thermique")
    
    puissance_ecs_kw = (debit_saisie * energie_par_litre_ecs) / 60.0
    
    st.info(f"""
    * **Configuration sélectionnée :** {selected_fwm_full}
    * **Débit de tirage simulé :** {debit_saisie:.1f} L/min
    * **Puissance thermique instantanée absorbée à l'ECS :** {puissance_ecs_kw:.2f} kW
    * **Énergie utile stockée dans le tampon :** {energie_stockee_kwh:.2f} kWh ({energie_stockee_kj:,.0f} kJ)
    * **Écart thermique utile sur le tampon ($\Delta T$) :** {delta_t_tampon:.1f} °C ({t_consigne}°C $\\rightarrow$ {t_redemarrage}°C)
    """)