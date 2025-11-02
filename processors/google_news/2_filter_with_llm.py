#!/usr/bin/env python3
"""
Étape 2: Filtre les articles avec Gemini API selon leur pertinence
Input:  data/lake/google_news_rss/<date>/articles_raw.csv
Output: data/lake/google_news_filtered/<date>/articles_filtered.csv
"""

import csv
from pathlib import Path
from datetime import datetime
import os
import google.generativeai as genai
from time import sleep


# Configuration Gemini
GEMINI_MODEL = "gemini-1.5-flash"
PERTINENCE_THRESHOLD = 4  # Garder seulement scores >= 4

# Prompt pour l'évaluation
EVALUATION_PROMPT = """Tu es un expert en affaires publiques et relations gouvernementales au Québec.

Opubliq (https://opubliq.com/) est une firme d'affaires publiques qui offre des services de:
- Lobbying et relations gouvernementales
- Communications publiques
- Gestion d'enjeux et de crise
- Veille stratégique

Évalue la pertinence de cet article de nouvelles pour identifier des clients potentiels.

Titre: {titre}
Source: {source}

Critères de pertinence:
- Score 5: Organisation clairement engagée en affaires publiques/lobbying/relations gouvernementales (ex: témoignage en commission parlementaire, recours judiciaire contre loi, campagne publique)
- Score 4: Organisation avec enjeux gouvernementaux significatifs (ex: ordre professionnel réagit à politique, association fait représentations)
- Score 3: Enjeu public mais lien indirect aux services d'Opubliq
- Score 2: Mention marginale d'organisations
- Score 1: Pas de lien avec les services d'Opubliq

IMPORTANT: Réponds UNIQUEMENT avec un chiffre entre 1 et 5. Aucun texte explicatif."""


def initialize_gemini():
    """Initialise l'API Gemini avec la clé d'environnement"""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("❌ Erreur: Variable d'environnement GEMINI_API_KEY non définie")
        print("   Exécutez: export GEMINI_API_KEY='votre_clé_api'")
        exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    return model


def evaluate_article(model, titre: str, source: str) -> int:
    """Évalue la pertinence d'un article avec Gemini"""
    try:
        prompt = EVALUATION_PROMPT.format(titre=titre, source=source)
        response = model.generate_content(prompt)

        # Extraire le score (devrait être juste un chiffre)
        score_text = response.text.strip()
        score = int(score_text)

        if score < 1 or score > 5:
            print(f"   ⚠️  Score invalide ({score}), défaut à 3")
            return 3

        return score

    except Exception as e:
        print(f"   ❌ Erreur évaluation: {e}")
        return 3  # Score par défaut en cas d'erreur


def main():
    """Filtre les articles avec Gemini API"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    input_file = Path("data/lake/google_news_rss") / date_str / "articles_raw.csv"

    if not input_file.exists():
        print(f"❌ Fichier introuvable: {input_file}")
        print(f"   Exécutez d'abord: python processors/google_news/1_parse_rss.py")
        return

    # Créer le dossier de sortie
    output_dir = Path("data/lake/google_news_filtered") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "articles_filtered.csv"

    print(f"🤖 Filtrage des articles avec Gemini - {date_str}")
    print(f"📊 Seuil de pertinence: >= {PERTINENCE_THRESHOLD}\n")

    # Initialiser Gemini
    model = initialize_gemini()
    print("✅ API Gemini initialisée\n")

    # Lire les articles
    articles = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        articles = list(reader)

    print(f"📰 {len(articles)} articles à évaluer\n")

    # Évaluer chaque article
    filtered_articles = []
    scores_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {article['titre'][:60]}...")

        score = evaluate_article(model, article['titre'], article['source'])
        scores_distribution[score] += 1

        print(f"   Score: {score}/5")

        if score >= PERTINENCE_THRESHOLD:
            article['pertinence_llm'] = score
            filtered_articles.append(article)
            print(f"   ✅ Conservé")
        else:
            print(f"   ❌ Rejeté")

        # Rate limiting: pause courte entre appels
        sleep(0.5)
        print()

    # Sauvegarder les articles filtrés
    if filtered_articles:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['signal', 'titre', 'source', 'url', 'pertinence_llm']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered_articles)

    # Résumé
    print(f"{'='*60}")
    print(f"✅ Filtrage terminé!")
    print(f"📊 Résultats:")
    print(f"   Articles initiaux: {len(articles)}")
    print(f"   Articles conservés: {len(filtered_articles)} ({len(filtered_articles)/len(articles)*100:.1f}%)")
    print(f"   Fichier: {output_file}")

    print(f"\n📈 Distribution des scores:")
    for score in range(5, 0, -1):
        count = scores_distribution[score]
        bar = "█" * (count // 2)
        print(f"   {score}: {bar} {count} articles")

    print(f"\n➡️  Prochaine étape: python processors/google_news/3_download_html.py")


if __name__ == "__main__":
    main()
