#!/usr/bin/env python3
"""
Étape 2: Télécharge les HTMLs de tous les articles
Input:  data/lake/google_news_rss/<date>/articles_raw.csv
Output: data/lake/google_news_html/<date>/article_*.html
"""

import csv
from pathlib import Path
from datetime import datetime
import requests
from time import sleep
from urllib.parse import urlparse


# Domaines québécois/canadiens acceptés
ALLOWED_DOMAINS = {
    # Médias québécois
    'lapresse.ca', 'ledevoir.com', 'journaldemontreal.com', 'journaldequebec.com',
    'tvanouvelles.ca', 'radio-canada.ca', 'ici.radio-canada.ca', 'rcinet.ca',
    'lactualite.com', 'ledroit.com', 'lesoleil.com', 'latribune.ca',
    'nouvelliste.ca', 'lequotidien.com', 'lavoixdelest.ca',
    # Gouvernement et institutions québécoises
    'quebec.ca', 'gouv.qc.ca', 'assnat.qc.ca', 'dgeq.org',
    # Ordres professionnels et organisations québécoises
    'oiiq.org', 'cmq.org', 'barreau.qc.ca', 'opq.gouv.qc.ca',
    # Syndicats et associations québécoises
    'csn.qc.ca', 'ftq.qc.ca', 'fiq.qc.ca', 'scfp.qc.ca', 'sqees-298.qc.ca',
    # Municipalités et régions
    'ville.montreal.qc.ca', 'ville.quebec.qc.ca', 'stm.info',
    # Médias locaux et régionaux
    'monvicto.com', 'lienmultimedia.com', 'francopresse.ca',
    # Médias canadiens généralistes
    'cbc.ca', 'theglobeandmail.com', 'nationalpost.com', 'thestar.com',
    'globalnews.ca', 'ctv.ca', 'ctvnews.ca'
}


def is_quebec_canadian_domain(url: str) -> bool:
    """Vérifie si l'URL est d'un domaine québécois/canadien accepté"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Retirer 'www.' si présent
        if domain.startswith('www.'):
            domain = domain[4:]

        # Accepter tous les .ca (canadiens par défaut)
        if domain.endswith('.ca'):
            return True

        # Vérifier si le domaine exact est dans la liste
        if domain in ALLOWED_DOMAINS:
            return True

        # Vérifier si c'est un sous-domaine d'un domaine accepté
        for allowed in ALLOWED_DOMAINS:
            if domain.endswith('.' + allowed):
                return True

        return False
    except:
        return False


def download_html(url: str, output_file: Path, timeout: int = 30) -> bool:
    """Télécharge le HTML d'une URL"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        # Sauvegarder le HTML
        output_file.write_text(response.text, encoding='utf-8')
        return True

    except requests.exceptions.Timeout:
        print(f"   ⏱️  Timeout")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"   ❌ Erreur HTTP: {e.response.status_code}")
        return False
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False


def sanitize_filename(url: str, article_id: int) -> str:
    """Crée un nom de fichier sûr basé sur l'ID"""
    return f"article_{article_id:04d}.html"


def main():
    """Télécharge les HTMLs de tous les articles"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    input_file = Path("data/lake/google_news_rss") / date_str / "articles_raw.csv"

    if not input_file.exists():
        print(f"❌ Fichier introuvable: {input_file}")
        print(f"   Exécutez d'abord: python processors/google_news/1_parse_rss.py")
        return

    # Créer le dossier de sortie
    output_dir = Path("data/lake/google_news_html") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🌐 Téléchargement des HTMLs - {date_str}")
    print(f"📁 Destination: {output_dir}\n")

    # Lire tous les articles
    articles = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        articles = list(reader)

    print(f"📰 {len(articles)} articles à filtrer et télécharger\n")

    # Filtrer et télécharger chaque HTML
    success_count = 0
    skipped_count = 0
    failed_urls = []
    filtered_articles = []

    for i, article in enumerate(articles, 1):
        url = article['url']

        print(f"[{i}/{len(articles)}] {article['titre'][:50]}...")
        print(f"   URL: {url[:70]}...")

        # Filtrer par domaine
        if not is_quebec_canadian_domain(url):
            print(f"   ⏭️  Ignoré (domaine étranger)")
            skipped_count += 1
            print()
            continue

        filename = sanitize_filename(url, len(filtered_articles) + 1)
        output_file = output_dir / filename

        # Télécharger
        success = download_html(url, output_file)

        if success:
            file_size = output_file.stat().st_size
            print(f"   ✅ Téléchargé: {filename} ({file_size:,} bytes)")
            success_count += 1

            # Ajouter le nom de fichier à l'article pour référence
            article['html_file'] = filename
            filtered_articles.append(article)
        else:
            failed_urls.append({
                'titre': article['titre'],
                'url': url
            })

        # Rate limiting
        sleep(1)
        print()

    # Mettre à jour la liste des articles avec seulement ceux téléchargés
    articles = filtered_articles

    # Créer un mapping CSV pour référence
    mapping_file = output_dir / "articles_mapping.csv"
    with open(mapping_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['signal', 'titre', 'source', 'url', 'html_file']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(articles)

    # Résumé
    print(f"{'='*60}")
    print(f"✅ Téléchargement terminé!")
    print(f"📊 Téléchargés: {success_count} | Ignorés: {skipped_count} | Échecs: {len(failed_urls)}")
    print(f"➡️  Prochaine étape: python processors/google_news/3_build_warehouse.py")


if __name__ == "__main__":
    main()
