#!/usr/bin/env python3
"""
Étape 4: Construit la table finale du warehouse
Input:  data/lake/google_news_html/<date>/articles_mapping.csv
Output: data/warehouse/<date>.csv
"""

import csv
from pathlib import Path
from datetime import datetime


def main():
    """Construit la table finale du warehouse"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Lire le mapping des articles
    mapping_file = Path("data/lake/google_news_html") / date_str / "articles_mapping.csv"

    if not mapping_file.exists():
        print(f"❌ Fichier introuvable: {mapping_file}")
        print(f"   Exécutez d'abord: python processors/google_news/3_download_html.py")
        return

    # Créer le dossier warehouse
    warehouse_dir = Path("data/warehouse")
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    output_file = warehouse_dir / f"google_news_{date_str}.csv"

    print(f"🏭 Construction de la table warehouse - {date_str}\n")

    # Lire les articles
    articles = []
    with open(mapping_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        articles = list(reader)

    print(f"📰 {len(articles)} articles à intégrer\n")

    # Pour l'instant, on copie simplement signal, titre, source, url
    # Dans les étapes futures, on pourra parser les HTMLs pour extraire plus de données
    warehouse_data = []

    for article in articles:
        warehouse_data.append({
            'signal': article['signal'],
            'titre': article['titre'],
            'source': article['source'],
            'url': article['url']
        })

    # Sauvegarder dans le warehouse
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['signal', 'titre', 'source', 'url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(warehouse_data)

    # Résumé
    print(f"{'='*60}")
    print(f"✅ Table warehouse créée!")
    print(f"📊 Résultats:")
    print(f"   Articles: {len(warehouse_data)}")
    print(f"   Fichier: {output_file}")

    # Statistiques par signal
    signal_counts = {}
    for article in warehouse_data:
        signal = article['signal']
        signal_counts[signal] = signal_counts.get(signal, 0) + 1

    print(f"\n📁 Répartition par signal:")
    for signal, count in sorted(signal_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(warehouse_data) * 100) if len(warehouse_data) > 0 else 0
        print(f"   • {signal}: {count} articles ({percentage:.1f}%)")

    print(f"\n✅ Pipeline terminé! Données prêtes pour analyse.")


if __name__ == "__main__":
    main()
