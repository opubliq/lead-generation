#!/usr/bin/env python3
"""
Étape 2: Télécharge les HTMLs de tous les articles via Selenium (pour suivre les redirections Google News)
Input:  data/lake/google_news_rss/<date>/articles_raw.csv
Output: data/lake/google_news_html/<date>/article_*.html
"""

import csv
from pathlib import Path
from datetime import datetime
from time import sleep
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# Configuration
MAX_WORKERS = 4  # Nombre de navigateurs parallèles

# Domaines québécois/canadiens acceptés
ALLOWED_DOMAINS = {
    # Médias québécois
    'lapresse.ca', 'ledevoir.com', 'journaldemontreal.com', 'journaldequebec.com',
    'tvanouvelles.ca', 'radio-canada.ca', 'ici.radio-canada.ca', 'rcinet.ca',
    'lactualite.com', 'ledroit.com', 'lesoleil.com', 'latribune.ca',
    'nouvelliste.ca', 'lequotidien.com', 'lavoixdelest.ca', 'noovo.info',
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


def create_driver():
    """Crée un driver Chrome headless"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.page_load_strategy = 'eager'  # Ne pas attendre toutes les ressources, juste le DOM
    return webdriver.Chrome(options=chrome_options)


def download_html_selenium(driver, url: str, output_file: Path, timeout: int = 15) -> tuple[bool, str]:
    """Télécharge le HTML d'une URL Google News avec Selenium (suit la redirection JS)"""
    try:
        # Définir un timeout de page
        driver.set_page_load_timeout(timeout)

        # Charger l'URL Google News
        driver.get(url)

        # Attendre que la redirection JavaScript se fasse
        sleep(2)

        # Récupérer l'URL finale et le contenu
        final_url = driver.current_url
        html_content = driver.page_source

        # Sauvegarder le HTML
        output_file.write_text(html_content, encoding='utf-8')

        return True, final_url

    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            print(f"   ⏱️  Timeout ({timeout}s)")
        else:
            print(f"   ❌ Erreur: {error_msg[:100]}")
        return False, ""


def process_article_download(task_data):
    """Traite le téléchargement d'un article (pour parallélisation)"""
    i, total, article, output_dir, article_counter = task_data

    # Créer un driver pour ce thread
    driver = create_driver()

    try:
        url = article['url']

        print(f"[{i}/{total}] {article['titre'][:50]}...")

        filename = sanitize_filename(url, article_counter)
        output_file = output_dir / filename

        # Télécharger avec Selenium (pas de retry, on skip si trop lent)
        success, final_url = download_html_selenium(driver, url, output_file, timeout=15)

        if success:
            # Vérifier si le domaine final est québécois/canadien
            if is_quebec_canadian_domain(final_url):
                file_size = output_file.stat().st_size
                print(f"[{i}/{total}] ✅ {filename} ({file_size:,} bytes)")
                print(f"[{i}/{total}] 🔗 {final_url[:80]}...")

                return {
                    'success': True,
                    'article': article,
                    'filename': filename,
                    'final_url': final_url
                }
            else:
                print(f"[{i}/{total}] ⏭️  Ignoré (domaine étranger: {final_url.split('/')[2]})")
                output_file.unlink()  # Supprimer le fichier
                return {'success': False, 'skipped': True}
        else:
            return {'success': False, 'skipped': False}

    finally:
        driver.quit()


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

    print(f"🌐 Téléchargement des HTMLs avec Selenium - {date_str}")
    print(f"📁 Destination: {output_dir}")
    print(f"⚡ Traitement parallèle avec {MAX_WORKERS} navigateurs\n")

    # Lire tous les articles
    articles = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        articles = list(reader)

    print(f"📰 {len(articles)} articles à télécharger\n")

    # Préparer les tâches pour traitement parallèle
    article_counter = threading.Lock()
    counter = [0]  # Compteur partagé pour numérotation des fichiers

    def get_counter():
        with article_counter:
            counter[0] += 1
            return counter[0]

    tasks = [(i+1, len(articles), article, output_dir, get_counter()) for i, article in enumerate(articles)]

    # Télécharger en parallèle
    success_count = 0
    skipped_count = 0
    failed_count = 0
    filtered_articles = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Soumettre toutes les tâches
        future_to_article = {executor.submit(process_article_download, task): task for task in tasks}

        # Récupérer les résultats au fur et à mesure
        for future in as_completed(future_to_article):
            result = future.result()

            if result['success']:
                success_count += 1
                article = result['article']
                article['html_file'] = result['filename']
                article['final_url'] = result['final_url']
                filtered_articles.append(article)
            elif result.get('skipped'):
                skipped_count += 1
            else:
                failed_count += 1

    print()

    # Mettre à jour la liste des articles avec seulement ceux téléchargés
    articles = filtered_articles

    # Créer un mapping CSV pour référence
    mapping_file = output_dir / "articles_mapping.csv"
    with open(mapping_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['signal', 'titre', 'source', 'url', 'date', 'final_url', 'html_file']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(articles)

    # Résumé
    print(f"\n{'='*60}")
    print(f"✅ Téléchargement terminé!")
    print(f"📊 Téléchargés: {success_count} | Ignorés: {skipped_count} | Échecs: {failed_count}")
    print(f"➡️  Prochaine étape: python processors/google_news/3_build_warehouse.py")


if __name__ == "__main__":
    main()
