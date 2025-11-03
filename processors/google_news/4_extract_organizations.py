#!/usr/bin/env python3
"""
Étape 4: Extrait et agrège les organisations mentionnées dans les articles
Input:  data/warehouse/google_news_<date>.csv
Output: data/warehouse/google_news_organizations_<date>.json
        data/warehouse/google_news_summaries_<date>.json
"""

import csv
import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
import os
from time import sleep
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# Configuration Gemini
GEMINI_MODEL = "gemini-2.5-flash"
MAX_WORKERS = 4  # Nombre de threads parallèles pour Gemini

# Prompt pour extraction d'organisations ET résumé
EXTRACTION_PROMPT = """Analyse cet article de presse québécois et extrais les informations suivantes.

TITRE DE L'ARTICLE: {titre}

CONTENU: {contenu}

INSTRUCTIONS IMPORTANTES:
- Concentre-toi UNIQUEMENT sur les organisations en lien direct avec le TITRE de l'article
- Ignore les organisations mentionnées dans les publicités, les suggestions d'articles ou les contenus non liés au titre
- Extrais TOUTES les organisations qui sont ACTEURS dans l'article (pas juste mentionnées passivement)
- Types recherchés:
  * Société civile: syndicats, associations, ordres professionnels, coalitions, OBNL, groupes de citoyens
  * Gouvernement: partis politiques, gouvernement du Québec, gouvernement fédéral, ministères, organismes publics
  * Municipalités et administrations locales
  * Entreprises et secteur privé si elles prennent position publiquement
- IMPORTANT: Inclure les partis politiques au pouvoir (ex: CAQ, gouvernement Legault) quand ils proposent des mesures, projets de loi, politiques

Pour chaque organisation pertinente, extrais:
1. NOM: Nom complet de l'organisation (ex: "Coalition Avenir Québec (CAQ)", "Gouvernement du Québec", "Fédération des travailleurs du Québec")
2. TYPE: Type d'organisation (parti politique, gouvernement, ministère, syndicat, association, ordre professionnel, coalition, OBNL, municipalité, entreprise, etc.)
3. ACTION: Action principale menée (propose, dépose, dénonce, demande, présente un mémoire, réagit, s'inquiète, critique, annonce, réforme, etc.)
4. ENJEU: Enjeu ou sujet principal en 5-10 mots
5. CITATION: Extrait textuel où l'organisation est mentionnée (1-2 phrases clés du contenu original)
6. RESUME: Mini-résumé de l'implication de l'organisation en 15-25 mots

Si aucune organisation n'est acteur EN LIEN AVEC LE TITRE, réponds avec une liste vide.

**TÂCHE 2: RÉSUMÉ DE L'ARTICLE**
Rédige un résumé concis de l'article en 3-4 phrases qui capture:
- Le sujet principal
- Les acteurs clés
- L'enjeu ou la problématique
- La position ou action principale

**IMPORTANT - FORMAT JSON:**
- Réponds UNIQUEMENT en JSON valide
- Échappe les guillemets dans les textes avec \"
- Remplace les apostrophes par des espaces simples
- Pas de retours à la ligne dans les valeurs de texte

Réponds UNIQUEMENT en format JSON:
{{
  "resume_article": "Résumé de 3-4 phrases...",
  "organisations": [
    {{
      "nom": "...",
      "type": "...",
      "action": "...",
      "enjeu": "...",
      "citation": "...",
      "resume": "..."
    }}
  ]
}}
"""


def initialize_gemini():
    """Initialise l'API Gemini"""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("❌ Erreur: Variable d'environnement GEMINI_API_KEY non définie")
        print("   Exécutez: export GEMINI_API_KEY='votre_clé_api'")
        exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    return model


def extract_organizations_and_summary(model, titre: str, contenu: str) -> dict:
    """Extrait les organisations ET le résumé d'un article avec Gemini"""
    try:
        # Limiter le contenu à 3000 caractères pour éviter tokens excessifs
        contenu_tronque = contenu[:3000] if len(contenu) > 3000 else contenu

        prompt = EXTRACTION_PROMPT.format(titre=titre, contenu=contenu_tronque)
        response = model.generate_content(prompt)

        # Parser la réponse JSON
        response_text = response.text.strip()

        # Nettoyer le markdown si présent
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        # Tenter de parser le JSON
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as json_err:
            # Tentative de nettoyage du JSON
            print(f"   ⚠️  JSON invalide, tentative de nettoyage...")

            # Nettoyer les retours à la ligne dans les chaînes
            import re
            # Remplacer les retours à la ligne entre guillemets par des espaces
            response_text = re.sub(r'"\s*\n\s*', '" ', response_text)

            # Retry le parsing
            try:
                data = json.loads(response_text)
                print(f"   ✅ JSON nettoyé et parsé avec succès")
            except json.JSONDecodeError:
                # Si ça échoue encore, logger et retourner vide
                print(f"   ❌ Impossible de parser le JSON: {str(json_err)[:100]}")
                # Sauvegarder le JSON problématique pour debug
                debug_file = Path("debug_json_error.txt")
                with open(debug_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n\n=== ERREUR POUR: {titre[:50]} ===\n")
                    f.write(response_text)
                    f.write(f"\nERREUR: {json_err}\n")
                return {"resume_article": "", "organisations": []}

        return {
            "resume_article": data.get("resume_article", ""),
            "organisations": data.get("organisations", [])
        }

    except Exception as e:
        print(f"   ❌ Erreur extraction: {str(e)[:100]}")
        return {"resume_article": "", "organisations": []}


def aggregate_organizations(all_extractions: list) -> dict:
    """Agrège les organisations par nom"""
    org_dict = defaultdict(lambda: {
        "mentions": 0,
        "articles": [],
        "enjeux": set(),
        "signaux": set(),
        "types": set()
    })

    for extraction in all_extractions:
        for org_data in extraction["organisations"]:
            nom = org_data["nom"]

            org_dict[nom]["mentions"] += 1
            org_dict[nom]["articles"].append({
                "titre": extraction["article"]["titre"],
                "source": extraction["article"]["source"],
                "url": extraction["article"]["url"],
                "signal": extraction["article"]["signal"],
                "action": org_data["action"],
                "enjeu": org_data["enjeu"],
                "citation": org_data.get("citation", ""),
                "resume": org_data.get("resume", "")
            })
            org_dict[nom]["enjeux"].add(org_data["enjeu"])
            org_dict[nom]["signaux"].add(extraction["article"]["signal"])
            org_dict[nom]["types"].add(org_data["type"])

    # Convertir en format final
    organisations = []
    for nom, data in org_dict.items():
        organisations.append({
            "nom": nom,
            "type": list(data["types"])[0] if len(data["types"]) == 1 else ", ".join(data["types"]),
            "mentions": data["mentions"],
            "articles": data["articles"],
            "enjeux_principaux": list(data["enjeux"]),
            "signaux": list(data["signaux"])
        })

    # Trier par nombre de mentions
    organisations.sort(key=lambda x: x["mentions"], reverse=True)

    return {"organisations": organisations}


def process_article(article_data):
    """Traite un article (pour parallélisation)"""
    i, article, model = article_data

    print(f"[{i}] {article['titre'][:60]}...")

    result = extract_organizations_and_summary(model, article['titre'], article['contenu'])

    extraction_data = {
        "article": {
            "titre": article['titre'],
            "source": article['source'],
            "url": article['url'],
            "signal": article['signal'],
            "resume": result["resume_article"]
        },
        "organisations": result["organisations"]
    }

    if result["organisations"]:
        print(f"[{i}] ✅ {len(result['organisations'])} organisation(s) extraite(s)")
    else:
        print(f"[{i}] ⚠️  Aucune organisation identifiée")

    return extraction_data


def main():
    """Extrait et agrège les organisations avec traitement parallèle"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    input_file = Path("data/warehouse") / f"google_news_{date_str}.csv"
    output_orgs_file = Path("data/warehouse") / f"google_news_organizations_{date_str}.json"
    output_summaries_file = Path("data/warehouse") / f"google_news_summaries_{date_str}.json"

    # Créer dossier pour extractions par article
    extractions_dir = Path("data/warehouse/org_extraites") / date_str
    extractions_dir.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        print(f"❌ Fichier introuvable: {input_file}")
        print(f"   Exécutez d'abord: python processors/google_news/3_build_warehouse.py")
        return

    print(f"🔍 Extraction des organisations et résumés - {date_str}\n")

    # Initialiser Gemini
    model = initialize_gemini()
    print("✅ API Gemini initialisée")
    print(f"⚡ Traitement parallèle avec {MAX_WORKERS} workers\n")

    # Lire les articles
    articles = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        articles = list(reader)

    print(f"📰 {len(articles)} articles à analyser\n")

    # Préparer les données pour traitement parallèle
    article_tasks = [(i+1, article, model) for i, article in enumerate(articles)]

    # Traiter en parallèle avec ThreadPoolExecutor
    all_extractions_data = []
    all_extractions = []
    summaries = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Soumettre toutes les tâches
        future_to_article = {executor.submit(process_article, task): task for task in article_tasks}

        # Récupérer les résultats au fur et à mesure
        for future in as_completed(future_to_article):
            extraction_data = future.result()
            all_extractions_data.append(extraction_data)

            # Sauvegarder extraction par article
            article_num = len(all_extractions_data)
            article_file = extractions_dir / f"article_{article_num:04d}.json"
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(extraction_data, f, ensure_ascii=False, indent=2)

            # Préparer pour agrégation
            if extraction_data["organisations"]:
                all_extractions.append({
                    "article": extraction_data["article"],
                    "organisations": extraction_data["organisations"]
                })

            # Collecter résumé
            summaries.append({
                "titre": extraction_data["article"]["titre"],
                "source": extraction_data["article"]["source"],
                "url": extraction_data["article"]["url"],
                "signal": extraction_data["article"]["signal"],
                "resume": extraction_data["article"]["resume"]
            })

    print()

    # Agréger par organisation
    print("📊 Agrégation des organisations...\n")
    aggregated_orgs = aggregate_organizations(all_extractions)

    # Sauvegarder le JSON des organisations
    with open(output_orgs_file, 'w', encoding='utf-8') as f:
        json.dump(aggregated_orgs, f, ensure_ascii=False, indent=2)

    # Sauvegarder le JSON des résumés
    with open(output_summaries_file, 'w', encoding='utf-8') as f:
        json.dump({"articles": summaries}, f, ensure_ascii=False, indent=2)

    # Résumé
    print(f"{'='*60}")
    print(f"✅ Extraction terminée!")
    print(f"📊 Résultats:")
    print(f"   Organisations uniques: {len(aggregated_orgs['organisations'])}")
    print(f"   Articles avec organisations: {len(all_extractions)}/{len(articles)}")
    print(f"   Fichier organisations: {output_orgs_file}")
    print(f"   Fichier résumés: {output_summaries_file}")
    print(f"   Extractions par article: {extractions_dir}/")

    # Top 10 organisations
    if aggregated_orgs['organisations']:
        print(f"\n🏆 Top 10 organisations (par mentions):")
        for i, org in enumerate(aggregated_orgs['organisations'][:10], 1):
            print(f"   {i}. {org['nom']} ({org['mentions']} mentions)")

    print(f"\n✅ Prêt pour analyse Stage 2 (Claude Code)")


if __name__ == "__main__":
    main()
