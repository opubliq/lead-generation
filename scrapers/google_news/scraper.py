#!/usr/bin/env python3
"""
Google News RSS Scraper for Lead Generation
Collecte les articles des 7 derniers jours selon 2 signaux optimisés
"""

import requests
from datetime import datetime
from pathlib import Path
import urllib.parse


# Configuration des 2 recherches par signal (élargies pour minimiser faux négatifs)
SEARCH_QUERIES = {
    "organisations_action_legislative": {
        "query": "(association OR fédération OR coalition OR ordre OR syndicat OR regroupement OR conseil OR collectif) (témoigne OR mémoire OR demande OR réclame OR appelle OR dénonce OR réagit OR s'oppose OR critique OR conteste OR interpelle OR exige) (Québec OR gouvernement québécois OR ministre) when:7d",
        "description": "Organisations en action législative - requête large"
    },
    "engagement_legislatif_organisationnel": {
        "query": "(projet de loi OR règlement OR consultation publique OR commission parlementaire) (association OR fédération OR coalition OR ordre OR syndicat OR regroupement) (présente OR dépose OR recommande OR propose OR appuie OR critique OR s'inquiète OR dénonce) Québec when:7d",
        "description": "Engagement législatif organisationnel - requête large"
    }
}

# Configuration Google News RSS
BASE_URL = "https://news.google.com/rss/search"
PARAMS = {
    "hl": "fr-CA",
    "gl": "CA",
    "ceid": "CA:fr"
}


def construct_rss_url(query: str) -> str:
    """Construit l'URL complète pour Google News RSS"""
    params = PARAMS.copy()
    params["q"] = query
    return f"{BASE_URL}?{urllib.parse.urlencode(params)}"


def fetch_rss_feed(url: str) -> str:
    """Récupère le contenu XML d'un flux RSS"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OpubliqLeadBot/1.0)"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def save_rss_content(content: str, signal_name: str, date_str: str) -> Path:
    """Sauvegarde le contenu RSS dans le data lake"""
    output_dir = Path("data/lake/google_news_rss") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{signal_name}.xml"
    output_file.write_text(content, encoding="utf-8")

    return output_file


def main():
    """Collecte tous les flux RSS et les sauvegarde"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"🔍 Collecte des flux Google News RSS - {date_str}")
    print(f"📁 Destination: data/lake/google_news_rss/{date_str}/\n")

    results = []

    for signal_name, config in SEARCH_QUERIES.items():
        print(f"📰 Signal: {signal_name}")
        print(f"   Description: {config['description']}")
        print(f"   Query: {config['query'][:80]}...")

        try:
            # Construire l'URL et récupérer le flux
            url = construct_rss_url(config["query"])
            print(f"   URL: {url[:100]}...")

            content = fetch_rss_feed(url)

            # Sauvegarder
            output_file = save_rss_content(content, signal_name, date_str)
            file_size = len(content)

            print(f"   ✅ Sauvegardé: {output_file} ({file_size:,} bytes)")
            results.append({
                "signal": signal_name,
                "file": output_file,
                "size": file_size,
                "success": True
            })

        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            results.append({
                "signal": signal_name,
                "success": False,
                "error": str(e)
            })

        print()

    # Résumé
    successful = sum(1 for r in results if r.get("success"))
    total = len(results)
    total_size = sum(r.get("size", 0) for r in results if r.get("success"))

    print(f"\n📊 Résumé:")
    print(f"   Réussis: {successful}/{total}")
    print(f"   Taille totale: {total_size:,} bytes")
    print(f"   Dossier: data/lake/google_news_rss/{date_str}/")


if __name__ == "__main__":
    main()
