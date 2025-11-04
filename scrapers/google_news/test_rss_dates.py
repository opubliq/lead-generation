#!/usr/bin/env python3
"""
Script de test pour vérifier le filtrage par date de Google News RSS
Teste différentes configurations d'URL pour obtenir seulement les 7 derniers jours
"""

import requests
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import pytz


def test_rss_url(query: str, description: str, extra_params: dict = None) -> dict:
    """
    Teste une URL Google News RSS et analyse les dates des articles
    """
    print(f"\n{'=' * 80}")
    print(f"Test: {description}")
    print(f"Query: {query}")
    print(f"{'=' * 80}")

    # Construire l'URL
    base_url = "https://news.google.com/rss/search"
    params = {
        "hl": "fr-CA",
        "gl": "CA",
        "ceid": "CA:fr",
        "q": query
    }

    # Ajouter les paramètres extra si fournis
    if extra_params:
        params.update(extra_params)

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"URL: {url}\n")

    try:
        # Récupérer le flux RSS
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OpubliqLeadBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parser le XML
        root = ET.fromstring(response.content)

        # Extraire les articles
        articles = []
        now = datetime.now(pytz.UTC)
        seven_days_ago = now - timedelta(days=7)

        for item in root.findall('.//item'):
            title_elem = item.find('title')
            pub_date_elem = item.find('pubDate')
            link_elem = item.find('link')

            if title_elem is not None and pub_date_elem is not None:
                title = title_elem.text
                pub_date_str = pub_date_elem.text
                link = link_elem.text if link_elem is not None else "N/A"

                # Parser la date
                try:
                    pub_date = date_parser.parse(pub_date_str)
                    days_ago = (now - pub_date).days

                    articles.append({
                        'title': title,
                        'pub_date': pub_date,
                        'pub_date_str': pub_date_str,
                        'days_ago': days_ago,
                        'link': link,
                        'within_7_days': pub_date >= seven_days_ago
                    })
                except Exception as e:
                    print(f"Erreur parsing date: {pub_date_str} - {e}")

        # Trier par date (plus récent d'abord)
        articles.sort(key=lambda x: x['pub_date'], reverse=True)

        # Afficher les résultats
        print(f"Nombre d'articles trouvés: {len(articles)}\n")

        within_7_days = [a for a in articles if a['within_7_days']]
        outside_7_days = [a for a in articles if not a['within_7_days']]

        print(f"✅ Dans les 7 derniers jours: {len(within_7_days)}")
        print(f"❌ Plus de 7 jours: {len(outside_7_days)}\n")

        if outside_7_days:
            print("⚠️  ARTICLES TROP VIEUX DÉTECTÉS:")
            for article in outside_7_days[:5]:  # Montrer les 5 plus vieux
                print(f"  - {article['days_ago']} jours: {article['title'][:80]}")
                print(f"    Date: {article['pub_date_str']}")
                print(f"    Link: {article['link'][:100]}")
                print()

        if within_7_days:
            print("✅ Exemples d'articles récents:")
            for article in within_7_days[:3]:
                print(f"  - {article['days_ago']} jours: {article['title'][:80]}")
                print(f"    Date: {article['pub_date_str']}")
                print()

        return {
            'success': True,
            'total_articles': len(articles),
            'within_7_days': len(within_7_days),
            'outside_7_days': len(outside_7_days),
            'articles': articles
        }

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """
    Teste différentes configurations de query pour trouver celle qui filtre correctement
    """
    print("🧪 Test du filtrage par date de Google News RSS")
    print(f"📅 Date actuelle: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 7 jours avant: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')}")

    # Différentes variations à tester
    test_queries = [
        {
            "query": "(association OR fédération) (dénonce OR réagit) Québec when:7d",
            "description": "Version actuelle - when:7d (avec deux-points)"
        },
        {
            "query": "(association OR fédération) (dénonce OR réagit) Québec",
            "description": "Pas de filtre de date - baseline",
            "params": {"when": "7d"}
        },
        {
            "query": "(association OR fédération) (dénonce OR réagit) Québec after:{}".format(
                (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            ),
            "description": "Utiliser after:YYYY-MM-DD"
        }
    ]

    results = []
    for test_config in test_queries:
        extra_params = test_config.get("params", None)
        result = test_rss_url(test_config["query"], test_config["description"], extra_params)
        results.append({
            'config': test_config,
            'result': result
        })

    # Résumé comparatif
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ COMPARATIF")
    print("=" * 80)

    for i, r in enumerate(results, 1):
        if r['result']['success']:
            print(f"\n{i}. {r['config']['description']}")
            print(f"   Total: {r['result']['total_articles']}")
            print(f"   ✅ Dans les 7 jours: {r['result']['within_7_days']}")
            print(f"   ❌ Plus de 7 jours: {r['result']['outside_7_days']}")

            if r['result']['outside_7_days'] == 0:
                print("   🎯 CETTE CONFIGURATION FONCTIONNE!")
        else:
            print(f"\n{i}. {r['config']['description']}")
            print(f"   ❌ Erreur: {r['result']['error']}")

    print("\n" + "=" * 80)
    print("💡 RECOMMANDATION:")

    # Trouver la meilleure configuration
    valid_results = [r for r in results if r['result']['success']]
    if valid_results:
        best = min(valid_results, key=lambda x: x['result']['outside_7_days'])
        if best['result']['outside_7_days'] == 0:
            print(f"✅ Utiliser: {best['config']['description']}")
            print(f"   Query: {best['config']['query']}")
        else:
            print("⚠️  Aucune configuration ne filtre parfaitement les 7 derniers jours")
            print("   Google News RSS peut inclure des articles plus anciens")
            print("   Solution: Filtrer les dates côté application après réception")
    else:
        print("❌ Toutes les configurations ont échoué")


if __name__ == "__main__":
    main()
