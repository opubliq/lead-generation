#!/usr/bin/env python3
"""
Google News RSS Scraper for Lead Generation
Collecte les articles des 7 derniers jours selon différents signaux
"""

import requests
from datetime import datetime
from pathlib import Path
import urllib.parse


# Configuration des 5 recherches par signal
SEARCH_QUERIES = {
    "organisations_reactives": {
        "query": "(association OR fédération OR coalition) (dénonce OR réagit OR demande OR s'oppose OR appelle) Québec when:7d",
        "description": "Organisations prenant position publiquement"
    },
    "enjeux_legislatifs": {
        "query": "(projet de loi OR règlement OR consultation publique OR mémoire OR commission parlementaire) (industrie OR secteur OR entreprise OR organisation) Québec when:7d",
        "description": "Organisations engagées dans processus législatifs"
    },
    "financement_gouvernemental": {
        "query": "(subvention OR financement OR aide gouvernementale OR investissement public) (annonce OR obtient OR reçoit) Québec when:7d",
        "description": "Relations financières avec le gouvernement"
    },
    "recrutement_affaires_publiques": {
        "query": "(embauche OR recherche OR recrutement) (affaires publiques OR relations gouvernementales OR lobbying OR communications) Québec when:7d",
        "description": "Besoins directs en services d'affaires publiques"
    },
    "gestion_crise": {
        "query": "(controverse OR critique OR enquête OR scandale) (organisation OR entreprise OR association) Québec when:7d",
        "description": "Organisations en situation de crise potentielle"
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
    output_dir = Path("data/lake/google_news") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{signal_name}.xml"
    output_file.write_text(content, encoding="utf-8")

    return output_file


def main():
    """Collecte tous les flux RSS et les sauvegarde"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"🔍 Collecte des flux Google News RSS - {date_str}")
    print(f"📁 Destination: data/lake/google_news/{date_str}/\n")

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
    print(f"   Dossier: data/lake/google_news/{date_str}/")


if __name__ == "__main__":
    main()
