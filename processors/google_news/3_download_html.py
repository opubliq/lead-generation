#!/usr/bin/env python3
"""
Étape 3: Télécharge les HTMLs des articles filtrés
Input:  data/lake/google_news_filtered/<date>/articles_filtered.csv
Output: data/lake/google_news_html/<date>/article_*.html
"""

import csv
from pathlib import Path
from datetime import datetime
import requests
from time import sleep
from urllib.parse import urlparse


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
    """Télécharge les HTMLs des articles filtrés"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    input_file = Path("data/lake/google_news_filtered") / date_str / "articles_filtered.csv"

    if not input_file.exists():
        print(f"❌ Fichier introuvable: {input_file}")
        print(f"   Exécutez d'abord: python processors/google_news/2_filter_with_llm.py")
        return

    # Créer le dossier de sortie
    output_dir = Path("data/lake/google_news_html") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🌐 Téléchargement des HTMLs - {date_str}")
    print(f"📁 Destination: {output_dir}\n")

    # Lire les articles filtrés
    articles = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        articles = list(reader)

    print(f"📰 {len(articles)} articles à télécharger\n")

    # Télécharger chaque HTML
    success_count = 0
    failed_urls = []

    for i, article in enumerate(articles, 1):
        url = article['url']
        filename = sanitize_filename(url, i)
        output_file = output_dir / filename

        print(f"[{i}/{len(articles)}] {article['titre'][:50]}...")
        print(f"   URL: {url[:70]}...")

        # Télécharger
        success = download_html(url, output_file)

        if success:
            file_size = output_file.stat().st_size
            print(f"   ✅ Téléchargé: {filename} ({file_size:,} bytes)")
            success_count += 1

            # Ajouter le nom de fichier à l'article pour référence
            article['html_file'] = filename
        else:
            failed_urls.append({
                'titre': article['titre'],
                'url': url
            })

        # Rate limiting
        sleep(1)
        print()

    # Créer un mapping CSV pour référence
    mapping_file = output_dir / "articles_mapping.csv"
    with open(mapping_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['signal', 'titre', 'source', 'url', 'pertinence_llm', 'html_file']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([a for a in articles if 'html_file' in a])

    # Résumé
    print(f"{'='*60}")
    print(f"✅ Téléchargement terminé!")
    print(f"📊 Résultats:")
    print(f"   Succès: {success_count}/{len(articles)} ({success_count/len(articles)*100:.1f}%)")
    print(f"   Échecs: {len(failed_urls)}")
    print(f"   Fichiers: {output_dir}")
    print(f"   Mapping: {mapping_file}")

    if failed_urls:
        print(f"\n⚠️  URLs échouées:")
        for item in failed_urls[:5]:  # Montrer max 5
            print(f"   • {item['titre'][:60]}")
        if len(failed_urls) > 5:
            print(f"   ... et {len(failed_urls) - 5} autres")

    print(f"\n➡️  Prochaine étape: python processors/google_news/4_build_warehouse.py")


if __name__ == "__main__":
    main()
