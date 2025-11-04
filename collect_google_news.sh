#!/bin/bash
#
# Pipeline complet de collecte Google News
# Collecte les articles RSS, télécharge HTMLs, construit le warehouse et extrait les organisations
#
# Usage: ./collect_google_news.sh
#
# Prérequis:
# - Virtual environment 'venv' avec dépendances installées
# - Variable d'environnement GEMINI_API_KEY définie
#

set -e  # Arrêter si une commande échoue

# Activer le virtual environment
source venv/bin/activate

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
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}❌ Erreur: Variable GEMINI_API_KEY non définie${NC}"
    echo -e "${YELLOW}   Ajoutez-la dans .env ou: export GEMINI_API_KEY='votre_clé'${NC}"
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

# Étape 3: Téléchargement HTML
echo -e "${BLUE}[3/5]${NC} Téléchargement des HTMLs (peut prendre plusieurs minutes)..."
python3 processors/google_news/2_download_html.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Téléchargement HTML terminé${NC}"
else
    echo -e "${RED}❌ Échec du téléchargement HTML${NC}"
    exit 1
fi
echo ""

# Étape 4: Construction warehouse
echo -e "${BLUE}[4/5]${NC} Construction de la table warehouse..."
python3 processors/google_news/3_build_warehouse.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Warehouse construit${NC}"
else
    echo -e "${RED}❌ Échec de la construction warehouse${NC}"
    exit 1
fi
echo ""

# Étape 5: Extraction des organisations
echo -e "${BLUE}[5/6]${NC} Extraction des organisations avec Gemini (peut prendre quelques minutes)..."
python3 processors/google_news/4_extract_organizations.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Organisations extraites${NC}"
else
    echo -e "${RED}❌ Échec de l'extraction des organisations${NC}"
    exit 1
fi
echo ""

# Étape 6: Qualification des leads
echo -e "${BLUE}[6/6]${NC} Qualification des leads avec Gemini (peut prendre quelques minutes)..."
python3 processors/google_news/5_qualify_leads.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Leads qualifiés${NC}"
else
    echo -e "${RED}❌ Échec de la qualification des leads${NC}"
    exit 1
fi
echo ""

# Résumé
DATE=$(date +%Y-%m-%d)
WAREHOUSE_FILE="data/warehouse/google_news_${DATE}.csv"
ORGANIZATIONS_FILE="data/warehouse/google_news_organizations_${DATE}.json"
LEADS_FILE="data/marts/${DATE}/google_news_leads.json"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Pipeline terminé avec succès!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "📊 Résultats disponibles:"
echo -e "   ${YELLOW}${WAREHOUSE_FILE}${NC}"
echo -e "   ${YELLOW}${ORGANIZATIONS_FILE}${NC}"
echo -e "   ${YELLOW}${LEADS_FILE}${NC}"
echo ""

# Afficher statistiques
if [ -f "$WAREHOUSE_FILE" ]; then
    ARTICLE_COUNT=$(tail -n +2 "$WAREHOUSE_FILE" | wc -l)
    echo -e "${GREEN}📰 ${ARTICLE_COUNT} articles collectés${NC}"
fi

if [ -f "$ORGANIZATIONS_FILE" ]; then
    ORG_COUNT=$(grep -o '"nom":' "$ORGANIZATIONS_FILE" | wc -l)
    echo -e "${GREEN}🏢 ${ORG_COUNT} organisations identifiées${NC}"
fi

if [ -f "$LEADS_FILE" ]; then
    LEAD_COUNT=$(grep -o '"lead_potentiel": true' "$LEADS_FILE" | wc -l)
    echo -e "${GREEN}🎯 ${LEAD_COUNT} leads qualifiés${NC}"
fi

echo ""
echo -e "➡️  Prochaine étape: Générer le rapport avec /generate-lead-report"
