import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import re
import numpy as np
from PIL import Image

# Configuration de la page
st.set_page_config(
    page_title="Analyse APOGEE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fonctions de nettoyage
def nettoyer_liste(texte):
    if pd.isna(texte):
        return []
    elements = [e.strip() for e in re.split(r',\s+', texte)]
    return [e for e in elements if e]

# Chargement des données
@st.cache_data
def charger_donnees(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        df['Privileges'] = df['Privilèges APOGEE'].apply(nettoyer_liste)
        df['Centres_Gestion'] = df['Centre Gestion'].apply(nettoyer_liste)
        df['Centres_Traitement'] = df['Centre Traitement'].apply(nettoyer_liste)
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier: {e}")
        return None

# Interface Streamlit
st.title("📊 Analyse Dynamique des Données APOGEE")
st.markdown("""
Cette application permet d'analyser les privilèges APOGEE par établissement avec des visualisations interactives.
""")

# Upload du fichier
uploaded_file = st.sidebar.file_uploader("Télécharger votre fichier CSV", type="csv")

if uploaded_file is not None:
    df = charger_donnees(uploaded_file)
    
    if df is not None:
        # Sidebar - Filtres
        st.sidebar.header("Filtres")
        etablissements = st.sidebar.multiselect(
            "Sélectionner des établissements",
            options=df['Etablissement'].unique(),
            default=df['Etablissement'].unique()
        )
        
        privileges_selectionnes = st.sidebar.multiselect(
            "Sélectionner des privilèges",
            options=sorted(list(set([p for sublist in df['Privileges'] for p in sublist]))),
            default=[]
        )
        
        # Appliquer les filtres
        df_filtre = df[df['Etablissement'].isin(etablissements)]
        if privileges_selectionnes:
            df_filtre = df_filtre[df_filtre['Privileges'].apply(
                lambda x: any(p in x for p in privileges_selectionnes)
            )]

        # Métriques clés
        st.header("Indicateurs Clés")
        col1, col2, col3 = st.columns(3)
        col1.metric("Nombre d'utilisateurs", len(df_filtre))
        col2.metric("Nombre d'établissements", df_filtre['Etablissement'].nunique())
        col3.metric("Utilisateurs avec Théses HDR", 
                   len(df_filtre[df_filtre['Privileges'].apply(lambda x: 'Théses HDR' in x)]))

        # Onglets
        tab1, tab2, tab3, tab4 = st.tabs([
            "📌 Répartition par Établissement", 
            "🔑 Analyse des Privilèges", 
            "👥 Utilisateurs Spéciaux",
            "🏫 Tous les utilisateurs par Établissement"
        ])

        with tab1:
            st.subheader("Répartition des Utilisateurs par Établissement")
            
            # Diagramme circulaire
            fig, ax = plt.subplots(figsize=(8, 8))
            users_par_etab = df_filtre['Etablissement'].value_counts()
            wedges, texts, autotexts = ax.pie(
                users_par_etab,
                labels=users_par_etab.index,
                autopct='%1.1f%%',
                startangle=90,
                pctdistance=0.85,
                textprops={'fontsize': 10}
            )
            plt.setp(autotexts, size=10, weight="bold")
            plt.title('Répartition des utilisateurs', pad=20)
            st.pyplot(fig)

            # Tableau détaillé
            st.dataframe(
                users_par_etab.reset_index().rename(
                    columns={'index': 'Établissement', 'Etablissement': 'Nombre d\'utilisateurs'}
                ),
                height=300,
                use_container_width=True
            )

        with tab2:
            st.subheader("Analyse des Privilèges")
            
            # Top 5 des privilèges
            st.markdown("**Top 5 des privilèges**")
            top_privileges = pd.Series(
                [p for sublist in df_filtre['Privileges'] for p in sublist]
            ).value_counts().head(5)
            
            fig, ax = plt.subplots(figsize=(10, 4))
            top_privileges.plot(kind='barh', color='skyblue', edgecolor='black')
            plt.xlabel('Nombre d\'occurrences')
            plt.ylabel('Privilège')
            for i, v in enumerate(top_privileges):
                ax.text(v + 0.5, i, str(v), color='black', va='center')
            st.pyplot(fig)

            # Distribution par établissement
            st.markdown("**Distribution des privilèges par établissement**")
            
            privileges_etab = df_filtre.explode('Privileges').groupby(
                ['Etablissement', 'Privileges']).size().unstack().fillna(0)
            
            # Sélectionner les privilèges à afficher
            privileges_a_afficher = st.multiselect(
                "Choisir les privilèges à visualiser",
                options=privileges_etab.columns,
                default=privileges_etab.columns[:3]
            )
            
            if privileges_a_afficher:
                fig, ax = plt.subplots(figsize=(12, 6))
                privileges_etab[privileges_a_afficher].plot(
                    kind='bar', 
                    stacked=True,
                    ax=ax,
                    width=0.8
                )
                plt.xticks(rotation=45, ha='right')
                plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.warning("Veuillez sélectionner au moins un privilège")

        with tab3:
            st.subheader("Analyse des Utilisateurs Spéciaux")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Utilisateurs avec 'Théses HDR'**")
                users_theses_hdr = df_filtre[df_filtre['Privileges'].apply(
                    lambda x: 'Théses HDR' in x)]
                
                if not users_theses_hdr.empty:
                    st.dataframe(
                        users_theses_hdr[['Nom & Prenom', 'Etablissement', 'Privileges']],
                        height=300
                    )
                else:
                    st.info("Aucun utilisateur avec 'Théses HDR' trouvé")
            
            with col2:
                st.markdown("**Utilisateurs avec tous les privilèges sauf 'Théses HDR'**")
                tous_privileges = set([p for sublist in df['Privileges'] for p in sublist])
                tous_privileges.discard('Théses HDR')
                
                users_tous_sauf_theses = df_filtre[df_filtre['Privileges'].apply(
                    lambda x: all(priv in x for priv in tous_privileges)
                )]
                
                if not users_tous_sauf_theses.empty:
                    st.dataframe(
                        users_tous_sauf_theses[['Nom & Prenom', 'Etablissement', 'Privileges']],
                        height=300
                    )
                else:
                    st.info("Aucun utilisateur correspondant trouvé")

        with tab4:
            st.subheader("Liste complète des utilisateurs par Établissement")
            
            # Grouper par établissement
            df_grouped = df_filtre.sort_values('Etablissement')
            
            # Créer un expander pour chaque établissement
            for etablissement in sorted(df_grouped['Etablissement'].unique()):
                with st.expander(f"🏛️ {etablissement} ({len(df_grouped[df_grouped['Etablissement'] == etablissement])} utilisateurs)"):
                    st.dataframe(
                        df_grouped[df_grouped['Etablissement'] == etablissement][
                            ['Nom & Prenom', 'Email', 'Privileges', 'Centre Gestion', 'Centre Traitement']
                        ],
                        column_config={
                            "Email": st.column_config.TextColumn("Email", width="medium"),
                            "Privileges": st.column_config.ListColumn("Privilèges"),
                            "Centre Gestion": st.column_config.TextColumn("Centre Gestion", width="small"),
                            "Centre Traitement": st.column_config.TextColumn("Centre Traitement", width="small")
                        },
                        hide_index=True,
                        use_container_width=True
                    )

        # Télécharger les résultats
        st.sidebar.download_button(
            label="Télécharger les résultats",
            data=df_filtre.to_csv(index=False).encode('utf-8'),
            file_name='resultats_analyse_apogee.csv',
            mime='text/csv'
        )

else:
    st.info("Veuillez télécharger un fichier CSV pour commencer l'analyse")
    st.image("https://via.placeholder.com/800x400?text=T%C3%A9l%C3%A9chargez+votre+fichier+CSV", use_column_width=True)