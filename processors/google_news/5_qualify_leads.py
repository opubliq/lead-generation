#!/usr/bin/env python3
"""
Étape 5: Qualifie les organisations comme leads potentiels pour Opubliq
Input:  data/warehouse/google_news_organizations_<date>.json
Output: data/marts/google_news_leads_<date>.json
"""

import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


# Configuration Gemini
GEMINI_MODEL = "gemini-2.5-flash"
MAX_WORKERS = 4

# Prompt de qualification
QUALIFICATION_PROMPT = """Tu es un analyste en développement des affaires pour Opubliq, une firme québécoise spécialisée en:

**SERVICES OPUBLIQ:**
1. **Recherche d'opinion publique**: Sondages, analyse de sentiment, études personnalisées
2. **Affaires publiques**: Influence auprès des décideurs, évaluation d'acceptabilité sociale
3. **Communication stratégique**: Positionnement, stratégies de communication, tableaux de bord
4. **Levée de fonds**: Profilage de donateurs, stratégies personnalisées

**CLIENTS CIBLES D'OPUBLIQ:**
- Associations, fédérations, coalitions prenant position publiquement
- Syndicats en négociation ou conflit
- Ordres professionnels s'opposant à des réformes
- OBNL et groupes citoyens mobilisés sur des enjeux
- Organisations en consultation parlementaire
- Organismes cherchant à influencer l'opinion publique ou les décideurs

**CLIENTS À EXCLURE:**
- Partis politiques (déjà connus d'Opubliq)
- Gouvernement, ministères, organismes publics (processus d'appels d'offres)
- Grandes entreprises bien établies avec équipes internes

---

**ORGANISATION À ÉVALUER:**

NOM: {nom}
TYPE: {type}
MENTIONS: {mentions}

**CONTEXTE DES ACTIONS:**
{contexte_actions}

---

**TA TÂCHE:**
Évalue si cette organisation est un lead potentiel pour Opubliq.

**CRITÈRES D'ÉVALUATION:**
1. Est-ce un type d'organisation cible? (association, syndicat, OBNL, ordre pro, coalition, groupe citoyen)
2. Est-elle active publiquement? (prises de position, opposition, mobilisation)
3. A-t-elle un besoin potentiel des services d'Opubliq?
   - Mesurer l'opinion publique?
   - Influencer des décideurs?
   - Améliorer son acceptabilité sociale?
   - Stratégie de communication?
4. Est-ce un client accessible? (pas un parti, pas le gouvernement)

**SCORING:**
- 5: Lead prioritaire (besoin clair + contexte urgent + bonne cible)
- 4: Lead fort (besoin probable + contexte pertinent)
- 3: Lead moyen (besoin possible + contexte à valider)
- 2: Lead faible (besoin incertain)
- 1: Pas un lead (hors cible ou pas de besoin apparent)

**FORMAT JSON DE RÉPONSE:**
{{
  "lead_potentiel": true/false,
  "score": 1-5,
  "raison": "Explication concise en 1-2 phrases du pourquoi c'est/pas un lead",
  "besoin_anticipe": "sondage, affaires publiques, communication, levée de fonds, aucun",
  "urgence": "haute, moyenne, basse",
  "note_contextuelle": "Détail additionnel pertinent (1 phrase)"
}}

**IMPORTANT:**
- Réponds UNIQUEMENT en JSON valide
- Sois sélectif: seuls les vrais leads potentiels devraient avoir lead_potentiel=true
- Focus sur les organisations avec un besoin clair et immédiat
"""


def initialize_gemini():
    """Initialise l'API Gemini"""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("❌ Erreur: Variable d'environnement GEMINI_API_KEY non définie")
        print("   Exécutez: export GEMINI_API_KEY='votre_clé_api'")
        exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    return model


def qualify_organization(model, org: dict) -> dict:
    """Qualifie une organisation avec Gemini"""
    try:
        # Construire le contexte des actions (max 5 premiers articles)
        contexte_actions = []
        for i, article in enumerate(org['articles'][:5], 1):
            contexte_actions.append(
                f"{i}. Action: {article['action']}\n"
                f"   Enjeu: {article['enjeu']}\n"
                f"   Signal: {article['signal']}\n"
                f"   Résumé: {article['resume']}"
            )
        contexte = "\n\n".join(contexte_actions)

        prompt = QUALIFICATION_PROMPT.format(
            nom=org['nom'],
            type=org['type'],
            mentions=org['mentions'],
            contexte_actions=contexte
        )

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Nettoyer le markdown si présent
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parser le JSON
        try:
            qualification = json.loads(response_text)
        except json.JSONDecodeError as json_err:
            print(f"   ⚠️  JSON invalide pour {org['nom'][:30]}")
            return None

        return qualification

    except Exception as e:
        print(f"   ❌ Erreur qualification {org['nom'][:30]}: {str(e)[:100]}")
        return None


def process_organization(task_data):
    """Traite la qualification d'une organisation (pour parallélisation)"""
    i, total, org, model = task_data

    print(f"[{i}/{total}] {org['nom'][:60]}...")

    qualification = qualify_organization(model, org)

    if qualification and qualification.get('lead_potentiel', False):
        print(f"[{i}/{total}] ✅ LEAD (score {qualification['score']}/5): {qualification['raison'][:80]}")
        return {
            "organisation": org,
            "qualification": qualification
        }
    else:
        if qualification:
            print(f"[{i}/{total}] ⏭️  Pas un lead (score {qualification.get('score', 0)}/5)")
        return None


def main():
    """Qualifie les organisations comme leads potentiels"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    input_file = Path("data/warehouse") / f"google_news_organizations_{date_str}.json"

    # Créer le dossier marts
    marts_dir = Path("data/marts") / date_str
    marts_dir.mkdir(parents=True, exist_ok=True)
    output_file = marts_dir / "google_news_leads.json"

    if not input_file.exists():
        print(f"❌ Fichier introuvable: {input_file}")
        print(f"   Exécutez d'abord: python processors/google_news/4_extract_organizations.py")
        return

    print(f"🎯 Qualification des leads - {date_str}\n")

    # Initialiser Gemini
    model = initialize_gemini()
    print("✅ API Gemini initialisée")
    print(f"⚡ Traitement parallèle avec {MAX_WORKERS} workers\n")

    # Lire les organisations
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        organisations = data['organisations']

    print(f"📊 {len(organisations)} organisations à qualifier\n")

    # Préparer les tâches pour traitement parallèle
    tasks = [(i+1, len(organisations), org, model) for i, org in enumerate(organisations)]

    # Traiter en parallèle
    qualified_leads = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_org = {executor.submit(process_organization, task): task for task in tasks}

        for future in as_completed(future_to_org):
            result = future.result()
            if result:
                qualified_leads.append(result)

    print()

    # Trier par score décroissant
    qualified_leads.sort(key=lambda x: x['qualification']['score'], reverse=True)

    # Sauvegarder le JSON des leads qualifiés
    output_data = {
        "date": date_str,
        "total_organisations_analysees": len(organisations),
        "leads_qualifies": len(qualified_leads),
        "leads": qualified_leads
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Résumé
    print(f"{'='*60}")
    print(f"✅ Qualification terminée!")
    print(f"📊 Résultats:")
    print(f"   Organisations analysées: {len(organisations)}")
    print(f"   Leads qualifiés: {len(qualified_leads)}")
    print(f"   Taux de conversion: {len(qualified_leads)/len(organisations)*100:.1f}%")
    print(f"   Fichier: {output_file}")

    # Distribution des scores
    if qualified_leads:
        print(f"\n📈 Distribution des scores:")
        score_dist = {}
        for lead in qualified_leads:
            score = lead['qualification']['score']
            score_dist[score] = score_dist.get(score, 0) + 1

        for score in sorted(score_dist.keys(), reverse=True):
            count = score_dist[score]
            print(f"   Score {score}/5: {count} leads")

        # Top 10 leads
        print(f"\n🏆 Top 10 leads prioritaires:")
        for i, lead in enumerate(qualified_leads[:10], 1):
            org = lead['organisation']
            qual = lead['qualification']
            print(f"   {i}. {org['nom']} (score {qual['score']}/5)")
            print(f"      → {qual['raison']}")
            print(f"      → Besoin: {qual['besoin_anticipe']} | Urgence: {qual['urgence']}")

    print(f"\n✅ Prêt pour génération du rapport Markdown")


if __name__ == "__main__":
    main()
