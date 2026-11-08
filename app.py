import streamlit as st

# --- CONSTANTES ---
CP_EAU = 4.186  # kJ/kg.°C (1 L d'eau ≈ 1 kg)

# Débit max unitaire indicatif des FWM PRO (L/min), mesuré à 60°C primaire / 45°C ECS
CAPACITES_FWM = {
    "FWM PRO 70": 27.4,
    "FWM PRO 90": 35.8,
    "FWM PRO 170": 61.3,
}
T_PRIMAIRE_REF = 60.0
T_ECS_REF = 45.0
DELTA_REF = T_PRIMAIRE_REF - T_ECS_REF  # écart de référence fixe (15 K)
NB_STATIONS_MAX = 6


def libelle_config(config):
    modele, nb = config
    return f"{modele} (1 Station)" if nb == 1 else f"{nb} x {modele} (Cascade)"


def debit_max_cascade(modele, nb, t_primaire, t_ecs):
    """Débit ECS max estimé de la cascade pour une T° primaire donnée.

    Approximation linéaire sur l'écart primaire / ECS par rapport au point de référence.
    """
    delta = t_primaire - t_ecs
    if delta <= 0:
        return 0.0
    return CAPACITES_FWM[modele] * (delta / DELTA_REF) * nb


st.set_page_config(
    page_title="Simulation Ballon Tampon & FWM PRO",
    layout="wide"
)

st.title("🛢️ Outil de Dimensionnement ECS & Tampon Primaire (FWM PRO)")
st.markdown("Simulez l'autonomie et les temps de chauffe d'un ballon tampon primaire couplé à une station d'échange **FWM PRO** (avec gestion des cascades jusqu'à 6 modules).")

# --- BARRE LATÉRALE : SAISIES UTILISATEUR ---
st.sidebar.header("1. Paramètres du Système")
vol_tampon = st.sidebar.number_input("Volume tampon primaire (L)", min_value=50, max_value=5000, value=500, step=50)

options_fwm = [(m, nb) for m in CAPACITES_FWM for nb in range(1, NB_STATIONS_MAX + 1)]
config_fwm = st.sidebar.selectbox("Sélection Modèle / Cascade FWM PRO", options_fwm, format_func=libelle_config)
modele_actif, nb_stations = config_fwm
libelle_fwm = libelle_config(config_fwm)

puissance_pac = st.sidebar.number_input("Puissance PAC générateur (kW)", min_value=2.0, max_value=200.0, value=16.0, step=1.0)

st.sidebar.header("2. Consignes Primaire")
t_consigne = st.sidebar.number_input("T° primaire de consigne (°C)", min_value=40.0, max_value=85.0, value=60.0, step=1.0)
t_redemarrage = st.sidebar.number_input("T° redémarrage de chauffe (°C)", min_value=30.0, max_value=80.0, value=50.0, step=1.0)

st.sidebar.header("3. Soutirage ECS Secondaire")
t_froid = st.sidebar.number_input("T° eau froide réseau (°C)", min_value=5.0, max_value=20.0, value=10.0, step=1.0)
t_ecs = st.sidebar.number_input("T° de soutirage ECS (°C)", min_value=35.0, max_value=65.0, value=45.0, step=1.0)
debit_saisie = st.sidebar.number_input("Débit ECS de puisage (L/min)", min_value=1.0, max_value=500.0, value=20.0, step=1.0)
pincement = st.sidebar.number_input(
    "Pincement échangeur (K)", min_value=0.0, max_value=15.0, value=5.0, step=1.0,
    help="Écart minimal entre la T° primaire et la T° ECS pour que la station produise l'ECS à la consigne."
)

# T° primaire minimale permettant encore de produire l'ECS à t_ecs
t_primaire_min = t_ecs + pincement

# --- CAPACITÉ DE LA CASCADE ---
debit_max_consigne = debit_max_cascade(modele_actif, nb_stations, t_consigne, t_ecs)
debit_max_redemarrage = debit_max_cascade(modele_actif, nb_stations, t_redemarrage, t_ecs)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**ℹ️ Capacité max estimée ({libelle_fwm}) :**<br>"
    f"<span style='font-size: 18px; color: #0083B8;'>**{debit_max_consigne:.1f} L/min**</span> à {t_consigne:.0f}°C primaire<br>"
    f"<span style='font-size: 18px; color: #0083B8;'>**{debit_max_redemarrage:.1f} L/min**</span> à {t_redemarrage:.0f}°C primaire (cas défavorable)",
    unsafe_allow_html=True
)

# --- VÉRIFICATIONS PHYSIQUES DES TEMPÉRATURES ---
erreurs = []
if t_redemarrage >= t_consigne:
    erreurs.append("La température de redémarrage doit être strictement inférieure à la température de consigne primaire.")
if t_ecs <= t_froid:
    erreurs.append(f"La température ECS ({t_ecs}°C) doit être supérieure à la température d'eau froide ({t_froid}°C).")
if t_primaire_min >= t_consigne:
    erreurs.append(
        f"La température primaire de consigne ({t_consigne}°C) doit dépasser la T° ECS + pincement "
        f"({t_ecs}°C + {pincement:.0f} K = {t_primaire_min}°C)."
    )

if erreurs:
    for err in erreurs:
        st.error(f"❌ Erreur : {err}")
else:
    if t_primaire_min > t_redemarrage:
        st.warning(
            f"⚠️ **Attention :** la T° de redémarrage ({t_redemarrage}°C) est inférieure à T° ECS + pincement "
            f"({t_primaire_min}°C). L'ECS ne sera plus garantie à {t_ecs}°C avant que la chauffe ne redémarre."
        )
    if debit_saisie > debit_max_redemarrage:
        st.warning(
            f"⚠️ **Alerte Débit :** le débit sélectionné ({debit_saisie:.1f} L/min) dépasse la capacité estimée de "
            f"**{libelle_fwm}** en fin de tranche ({debit_max_redemarrage:.1f} L/min à {t_redemarrage}°C primaire)."
        )

    # --- CALCULS THERMODYNAMIQUES ---
    # Tranche utile jusqu'au redémarrage, limitée par la T° primaire minimale exploitable
    t_bas_tranche = max(t_redemarrage, t_primaire_min)
    delta_t_tampon = t_consigne - t_bas_tranche

    # 1. Énergie utile stockée dans le tampon avant redémarrage (kJ et kWh)
    energie_stockee_kj = vol_tampon * CP_EAU * delta_t_tampon
    energie_stockee_kwh = energie_stockee_kj / 3600

    # 2. Temps de chauffe de la PAC (de T_redémarrage à T_consigne, sans puisage)
    energie_chauffe_kj = vol_tampon * CP_EAU * (t_consigne - t_redemarrage)
    temps_chauffe_min = energie_chauffe_kj / puissance_pac / 60

    # 3. Volume ECS produit à T_ecs grâce aux calories du tampon
    energie_par_litre_ecs = CP_EAU * (t_ecs - t_froid)
    vol_ecs_total = energie_stockee_kj / energie_par_litre_ecs

    # 4. Temps de soutirage continu avant redémarrage de la PAC
    temps_soutirage_min = vol_ecs_total / debit_saisie

    # 5. Autonomie totale avec la PAC en marche après redémarrage
    puissance_ecs_kw = debit_saisie * energie_par_litre_ecs / 60.0
    puissance_nette_kw = puissance_ecs_kw - puissance_pac
    energie_reserve_kj = vol_tampon * CP_EAU * max(0.0, t_redemarrage - t_primaire_min)
    if puissance_nette_kw <= 0:
        autonomie_totale_min = None  # la PAC couvre seule le besoin
    else:
        autonomie_totale_min = temps_soutirage_min + energie_reserve_kj / puissance_nette_kw / 60

    # --- AFFICHAGE DES RÉSULTATS ---
    st.markdown("---")
    st.header("📊 Résultats de la Simulation")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Temps de chauffe PAC",
            value=f"{temps_chauffe_min:.1f} min",
            help="Temps nécessaire à la PAC pour remonter le tampon de T_redémarrage à T_consigne, sans puisage."
        )

    with col2:
        st.metric(
            label="Volume ECS soutirable",
            value=f"{vol_ecs_total:.1f} L",
            help="Volume d'ECS disponible dans la tranche utile du tampon, avant redémarrage de la PAC."
        )

    with col3:
        st.metric(
            label="Autonomie avant redémarrage",
            value=f"{temps_soutirage_min:.1f} min",
            help="Durée de soutirage continu au débit indiqué avant que la chauffe ne redémarre."
        )

    with col4:
        st.metric(
            label="Autonomie totale (PAC en marche)",
            value="Illimitée" if autonomie_totale_min is None else f"{autonomie_totale_min:.1f} min",
            help="Durée de soutirage continu jusqu'à ce que le primaire atteigne T° ECS + pincement, "
                 "en tenant compte de l'apport de la PAC après redémarrage."
        )

    # --- DÉTAILS ET PUISSANCE ---
    st.markdown("---")
    st.markdown("### 🔍 Détails du Bilan Thermique")

    bilan_pac = (
        f"la PAC couvre seule le besoin (excédent {-puissance_nette_kw:.2f} kW)"
        if puissance_nette_kw <= 0
        else f"déficit de {puissance_nette_kw:.2f} kW comblé par le tampon"
    )

    st.info(f"""
    * **Configuration sélectionnée :** {libelle_fwm}
    * **Débit de tirage simulé :** {debit_saisie:.1f} L/min
    * **Puissance thermique instantanée absorbée à l'ECS :** {puissance_ecs_kw:.2f} kW
    * **Bilan avec PAC ({puissance_pac:.1f} kW) :** {bilan_pac}
    * **Énergie utile stockée dans le tampon :** {energie_stockee_kwh:.2f} kWh ({energie_stockee_kj:,.0f} kJ)
    * **Écart thermique utile sur le tampon (ΔT) :** {delta_t_tampon:.1f} °C ({t_consigne}°C → {t_bas_tranche}°C)
    * **T° primaire minimale exploitable :** {t_primaire_min}°C (T° ECS + pincement)
    """)
