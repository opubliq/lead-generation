#!/bin/bash
#
# Pipeline complet de collecte Google News
# Collecte les articles RSS, filtre avec LLM, télécharge HTMLs et construit le warehouse
#
# Usage: ./collect_google_news.sh
#
# Prérequis:
# - Variable d'environnement GEMINI_API_KEY définie
# - Python 3 avec dépendances installées (requests, google-generativeai)
#

set -e  # Arrêter si une commande échoue

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Pipeline Google News Lead Gen${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Vérifier que GEMINI_API_KEY est définie
if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}❌ Erreur: Variable GEMINI_API_KEY non définie${NC}"
    echo -e "${YELLOW}   Exécutez: export GEMINI_API_KEY='votre_clé'${NC}"
    exit 1
fi

# Étape 1: Collecte RSS
echo -e "${BLUE}[1/5]${NC} Collecte des flux RSS Google News..."
python3 scrapers/google_news/scraper.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Collecte RSS terminée${NC}"
else
    echo -e "${RED}❌ Échec de la collecte RSS${NC}"
    exit 1
fi
echo ""

# Étape 2: Parse RSS
echo -e "${BLUE}[2/5]${NC} Extraction des articles avec URLs..."
python3 processors/google_news/1_parse_rss.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Parse RSS terminé${NC}"
else
    echo -e "${RED}❌ Échec du parsing RSS${NC}"
    exit 1
fi
echo ""

# Étape 3: Filtrage LLM
echo -e "${BLUE}[3/5]${NC} Filtrage avec Gemini API (peut prendre quelques minutes)..."
python3 processors/google_news/2_filter_with_llm.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Filtrage LLM terminé${NC}"
else
    echo -e "${RED}❌ Échec du filtrage LLM${NC}"
    exit 1
fi
echo ""

# Étape 4: Téléchargement HTML
echo -e "${BLUE}[4/5]${NC} Téléchargement des HTMLs (peut prendre plusieurs minutes)..."
python3 processors/google_news/3_download_html.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Téléchargement HTML terminé${NC}"
else
    echo -e "${RED}❌ Échec du téléchargement HTML${NC}"
    exit 1
fi
echo ""

# Étape 5: Construction warehouse
echo -e "${BLUE}[5/5]${NC} Construction de la table warehouse..."
python3 processors/google_news/4_build_warehouse.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Warehouse construit${NC}"
else
    echo -e "${RED}❌ Échec de la construction warehouse${NC}"
    exit 1
fi
echo ""

# Résumé
DATE=$(date +%Y-%m-%d)
WAREHOUSE_FILE="data/warehouse/google_news_${DATE}.csv"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Pipeline terminé avec succès!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "📊 Résultats disponibles dans:"
echo -e "   ${YELLOW}${WAREHOUSE_FILE}${NC}"
echo ""
echo -e "📁 Données brutes dans:"
echo -e "   data/lake/google_news_rss/${DATE}/"
echo -e "   data/lake/google_news_filtered/${DATE}/"
echo -e "   data/lake/google_news_html/${DATE}/"
echo ""

# Afficher nombre d'articles si le fichier existe
if [ -f "$WAREHOUSE_FILE" ]; then
    ARTICLE_COUNT=$(tail -n +2 "$WAREHOUSE_FILE" | wc -l)
    echo -e "${GREEN}🎉 ${ARTICLE_COUNT} articles qualifiés collectés!${NC}"
fi
