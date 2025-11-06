#!/usr/bin/env python3
"""
Google News RSS Scraper for Lead Generation
Collecte les articles des 7 derniers jours selon 2 signaux optimisés
"""

import requests
from datetime import datetime, timedelta
from pathlib import Path
import urllib.parse
import xml.etree.ElementTree as ET
from dateutil import parser as date_parser
import pytz


# Configuration des queries multiples - simplifiées et ciblées
SEARCH_QUERIES = {
    # Organisations qui réagissent
    "orgs_denoncent": {
        "query": "(association OR fédération OR coalition) dénonce Québec when:14d",
        "description": "Organisations qui dénoncent"
    },
    "orgs_reclament": {
        "query": "(association OR fédération OR syndicat) réclame Québec when:14d",
        "description": "Organisations qui réclament"
    },
    "orgs_demandent": {
        "query": "(ordre OR syndicat OR coalition) demande gouvernement when:14d",
        "description": "Organisations qui demandent"
    },
    "orgs_critiquent": {
        "query": "(association OR fédération OR ordre) critique (gouvernement OR ministre) when:14d",
        "description": "Organisations qui critiquent"
    },

    # Processus législatifs
    "projet_loi_memoire": {
        "query": "\"projet de loi\" mémoire when:14d",
        "description": "Mémoires sur projets de loi"
    },
    "commission_parlementaire": {
        "query": "commission parlementaire (présente OR témoigne) when:14d",
        "description": "Témoignages en commission"
    },
    "consultation_publique": {
        "query": "consultation publique (association OR fédération) when:14d",
        "description": "Consultations publiques"
    },

    # Actions organisationnelles
    "coalition_appelle": {
        "query": "(coalition OR regroupement) appelle Québec when:14d",
        "description": "Coalitions qui appellent à l'action"
    },
    "syndicat_action": {
        "query": "syndicat (critique OR dénonce OR réagit) gouvernement when:14d",
        "description": "Syndicats en action"
    },
    "ordre_professionnel": {
        "query": "ordre professionnel (recommande OR propose OR s'inquiète) when:14d",
        "description": "Ordres professionnels actifs"
    },

    # Interpellations et oppositions
    "orgs_interpellent": {
        "query": "(association OR fédération) (interpelle OR s'oppose) ministre when:14d",
        "description": "Organisations interpellent ministres"
    },
    "orgs_exigent": {
        "query": "(syndicat OR coalition OR regroupement) exige Québec when:14d",
        "description": "Organisations qui exigent"
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


def filter_rss_by_date(xml_content: str, days: int = 14) -> tuple[str, dict]:
    """
    Filtre le XML RSS pour garder seulement les articles des X derniers jours
    Retourne le XML filtré et des stats
    """
    root = ET.fromstring(xml_content)
    channel = root.find('channel')

    if channel is None:
        return xml_content, {"error": "No channel found"}

    now = datetime.now(pytz.UTC)
    cutoff_date = now - timedelta(days=days)

    stats = {
        "total": 0,
        "kept": 0,
        "removed": 0,
        "oldest_kept": None,
        "newest_kept": None
    }

    items_to_remove = []
    kept_dates = []

    for item in channel.findall('item'):
        stats["total"] += 1
        pub_date_elem = item.find('pubDate')

        if pub_date_elem is None or not pub_date_elem.text:
            items_to_remove.append(item)
            stats["removed"] += 1
            continue

        try:
            pub_date = date_parser.parse(pub_date_elem.text)

            if pub_date < cutoff_date or pub_date > now:
                items_to_remove.append(item)
                stats["removed"] += 1
            else:
                stats["kept"] += 1
                kept_dates.append(pub_date)
        except:
            items_to_remove.append(item)
            stats["removed"] += 1

    # Supprimer les items filtrés
    for item in items_to_remove:
        channel.remove(item)

    if kept_dates:
        stats["oldest_kept"] = min(kept_dates)
        stats["newest_kept"] = max(kept_dates)

    # Retourner le XML filtré
    filtered_xml = ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')
    return filtered_xml, stats


def save_rss_content(content: str, signal_name: str, date_str: str) -> Path:
    """Filtre et sauvegarde le contenu RSS dans le data lake"""
    # Filtrer pour garder seulement les 14 derniers jours
    filtered_content, stats = filter_rss_by_date(content, days=14)

    output_dir = Path("data/lake/google_news_rss") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{signal_name}.xml"
    output_file.write_text(filtered_content, encoding="utf-8")

    return output_file, stats


def deduplicate_articles(all_items: list) -> tuple[list, dict]:
    """
    Déduplique les articles par URL
    Retourne les articles uniques et des stats
    """
    seen_urls = {}
    unique_items = []

    for item in all_items:
        link_elem = item.find('link')
        if link_elem is not None and link_elem.text:
            url = link_elem.text
            if url not in seen_urls:
                seen_urls[url] = True
                unique_items.append(item)

    stats = {
        'total': len(all_items),
        'unique': len(unique_items),
        'duplicates': len(all_items) - len(unique_items)
    }

    return unique_items, stats


def main():
    """Collecte tous les flux RSS, déduplique et sauvegarde"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"🔍 Collecte des flux Google News RSS - {date_str}")
    print(f"📁 Destination: data/lake/google_news_rss/{date_str}/\n")

    all_items = []
    query_results = []

    for signal_name, config in SEARCH_QUERIES.items():
        print(f"📰 Query: {signal_name}")
        print(f"   Description: {config['description']}")
        print(f"   Query: {config['query']}")

        try:
            # Construire l'URL et récupérer le flux
            url = construct_rss_url(config["query"])

            content = fetch_rss_feed(url)

            # Filtrer par date
            filtered_content, filter_stats = filter_rss_by_date(content, days=14)

            # Parser le XML filtré et extraire les items
            root = ET.fromstring(filtered_content)
            channel = root.find('channel')
            if channel is not None:
                items = channel.findall('item')
                all_items.extend(items)

                print(f"   📊 Articles: {filter_stats['total']} → {filter_stats['kept']} gardés")
                if filter_stats.get('oldest_kept'):
                    days_old = (datetime.now(pytz.UTC) - filter_stats['oldest_kept']).days
                    print(f"   📅 Plus ancien: {days_old} jours")

                query_results.append({
                    "signal": signal_name,
                    "kept": filter_stats['kept'],
                    "success": True
                })
            else:
                print(f"   ⚠️  Pas de channel trouvé")
                query_results.append({
                    "signal": signal_name,
                    "kept": 0,
                    "success": False
                })

        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            query_results.append({
                "signal": signal_name,
                "success": False,
                "error": str(e)
            })

        print()

    # Déduplication
    print(f"🔄 Déduplication des articles...")
    unique_items, dedup_stats = deduplicate_articles(all_items)
    print(f"   Total collecté: {dedup_stats['total']}")
    print(f"   Doublons: {dedup_stats['duplicates']}")
    print(f"   Uniques: {dedup_stats['unique']}\n")

    # Créer un XML consolidé avec les articles uniques
    if unique_items:
        # Créer une structure RSS valide
        rss_root = ET.Element('rss', version='2.0')
        rss_root.set('xmlns:media', 'http://search.yahoo.com/mrss/')
        channel = ET.SubElement(rss_root, 'channel')

        ET.SubElement(channel, 'title').text = f'Google News - Lead Generation - {date_str}'
        ET.SubElement(channel, 'description').text = 'Articles consolidés et dédupliqués'
        ET.SubElement(channel, 'language').text = 'fr-CA'

        # Ajouter tous les items uniques
        for item in unique_items:
            channel.append(item)

        # Sauvegarder
        output_dir = Path("data/lake/google_news_rss") / date_str
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "articles_consolidated.xml"
        xml_string = ET.tostring(rss_root, encoding='utf-8', xml_declaration=True).decode('utf-8')
        output_file.write_text(xml_string, encoding='utf-8')

        file_size = output_file.stat().st_size
        print(f"✅ Fichier consolidé créé: {output_file}")
        print(f"   Taille: {file_size:,} bytes")
        print(f"   Articles uniques: {dedup_stats['unique']}")
    else:
        print(f"⚠️  Aucun article à sauvegarder")

    # Résumé
    print(f"\n📊 Résumé:")
    successful = sum(1 for r in query_results if r.get("success"))
    total_kept = sum(r.get("kept", 0) for r in query_results if r.get("success"))
    print(f"   Queries réussies: {successful}/{len(query_results)}")
    print(f"   Articles collectés (avant dédup): {dedup_stats['total']}")
    print(f"   Articles uniques: {dedup_stats['unique']}")
    print(f"   Dossier: data/lake/google_news_rss/{date_str}/")


if __name__ == "__main__":
    main()
