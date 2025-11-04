#!/usr/bin/env python3
"""
Étape 1: Parse les fichiers XML RSS et extrait les articles avec URLs
Input:  data/lake/google_news_rss/<date>/*.xml
Output: data/lake/google_news_rss/<date>/articles_raw.csv
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import csv


def extract_articles_from_xml(xml_file: Path, signal_name: str) -> list[dict]:
    """Extrait les articles d'un fichier XML RSS avec URL"""
    articles = []

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Les items sont dans <channel><item>
        items = root.findall('.//item')

        for item in items:
            title_elem = item.find('title')
            source_elem = item.find('source')
            link_elem = item.find('link')
            pub_date_elem = item.find('pubDate')

            title = title_elem.text if title_elem is not None else "N/A"
            source = source_elem.text if source_elem is not None else "N/A"

            # Extraire l'URL de l'article depuis <link> (URL Google News qui redirige vers l'article)
            url = link_elem.text if link_elem is not None else "N/A"

            # Extraire la date de publication
            pub_date = pub_date_elem.text if pub_date_elem is not None else "N/A"

            articles.append({
                "signal": signal_name,
                "titre": title,
                "source": source,
                "url": url,
                "date": pub_date
            })

    except Exception as e:
        print(f"   ❌ Erreur lors du parsing de {xml_file.name}: {e}")

    return articles


def main():
    """Parse le fichier XML consolidé et crée un CSV avec URLs"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    data_dir = Path("data/lake/google_news_rss") / date_str

    if not data_dir.exists():
        print(f"❌ Le dossier {data_dir} n'existe pas")
        print(f"   Exécutez d'abord: python scrapers/google_news/scraper.py")
        return

    print(f"📊 Extraction des articles RSS - {date_str}\n")

    # Chercher le fichier consolidé
    consolidated_file = data_dir / "articles_consolidated.xml"

    if not consolidated_file.exists():
        print(f"❌ Fichier consolidé non trouvé: {consolidated_file}")
        print(f"   Exécutez d'abord: python scrapers/google_news/scraper.py")
        return

    all_articles = []

    print(f"📰 Traitement: {consolidated_file.name}")
    articles = extract_articles_from_xml(consolidated_file, "consolidated")
    all_articles.extend(articles)
    print(f"   ✅ {len(articles)} articles extraits")

    # Créer le CSV avec URLs
    csv_file = data_dir / "articles_raw.csv"

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['signal', 'titre', 'source', 'url', 'date'])
        writer.writeheader()
        writer.writerows(all_articles)

    print(f"\n{'='*60}")
    print(f"✅ CSV créé: {csv_file}")
    print(f"📊 Total: {len(all_articles)} articles")

    # Statistiques par signal
    signal_counts = {}
    for article in all_articles:
        signal = article['signal']
        signal_counts[signal] = signal_counts.get(signal, 0) + 1

    print(f"\n📁 Répartition par signal:")
    for signal, count in sorted(signal_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(all_articles) * 100) if len(all_articles) > 0 else 0
        print(f"   • {signal}: {count} articles ({percentage:.1f}%)")

    print(f"\n➡️  Prochaine étape: python processors/google_news/2_filter_with_llm.py")


if __name__ == "__main__":
    main()
