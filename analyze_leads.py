#!/usr/bin/env python3
"""
Script to analyze leads JSON and extract top candidates for the report.
"""
import json

def load_and_analyze_leads(leads_file):
    """Load leads and return top candidates with their data."""
    with open(leads_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total organisations: {data['total_organisations_analysees']}")
    print(f"Leads qualifiés: {data['leads_qualifies']}")
    print(f"\nTop 15 leads by score and mentions:")

    # Sort by score, then by mentions
    sorted_leads = sorted(data['leads'],
                         key=lambda x: (x['qualification']['score'], x['organisation']['mentions']),
                         reverse=True)

    for i, lead in enumerate(sorted_leads[:15], 1):
        org = lead['organisation']
        qual = lead['qualification']
        print(f"\n{i}. {org['nom']}")
        print(f"   Score: {qual['score']}/10 | Type: {qual['type']} | Urgence: {qual['urgence']}")
        print(f"   Mentions: {org['mentions']} | Articles: {len(org['articles'])}")
        print(f"   Contexte: {qual['contexte'][:100]}...")

    # Save top 15 to a separate file for detailed analysis
    output = {
        'metadata': {
            'date': data['date'],
            'total_organisations': data['total_organisations_analysees'],
            'leads_qualifies': data['leads_qualifies']
        },
        'top_leads': sorted_leads[:15]
    }

    output_file = leads_file.replace('google_news_leads.json', 'top_15_leads.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved top 15 leads to: {output_file}")
    return output_file

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        leads_file = sys.argv[1]
    else:
        leads_file = '/home/hubcad25/opubliq/repos/lead-generation/data/marts/2025-11-06/google_news_leads.json'

    output_file = load_and_analyze_leads(leads_file)
