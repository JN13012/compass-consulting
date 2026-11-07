# Décisions

Format : date — décision — alternatives — raison.

## 2026-11-07 — Front React + TypeScript (Vite) dès la phase 0
- Alternatives : Streamlit.
- Raison : standard du marché, cité dans les offres visées ; l'API reste séparée et typée.

## 2026-11-07 — Types API générés depuis l'OpenAPI de FastAPI (openapi-typescript + openapi-fetch)
- Alternatives : types écrits à la main, client généré complet (orval).
- Raison : front et back synchronisés sans duplication ; client minimal.

## 2026-11-07 — Le front appelle `/api/*`, proxifié par Vite vers l'API
- Alternatives : appels directs avec CORS.
- Raison : même origine en dev, pas de configuration CORS côté navigateur.

## 2026-11-07 — Ollama optionnel (profil Docker `local`)
- Alternatives : service toujours lancé.
- Raison : pas nécessaire avant les missions confidentielles ; évite un téléchargement lourd au démarrage.
  Le blocage « mission confidentielle → modèle local uniquement » est déjà appliqué et testé dans le routeur.

## 2026-11-07 — Routeur LLM par rôles (`config/llm.yaml`) au-dessus de LiteLLM
- Alternatives : appels directs aux SDK des fournisseurs.
- Raison : changer de fournisseur = modifier la config ; contrôle de confidentialité centralisé.
- Défauts : `reasoning` Claude Opus 5.5, `extraction` Claude Sonnet 5.5, `local` mistral-small (Ollama), `embedding` bge-m3.
