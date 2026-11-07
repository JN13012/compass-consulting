# Compass — assistant du consultant IA & Blockchain

Outil interne qui accompagne une mission de conseil de bout en bout :
**diagnostic → solutions → réglementation → benchmark → POC & évaluation → livrables**,
avec des citations toujours vérifiables, des données on-chain réelles et des modèles locaux pour les missions confidentielles.

> Ceci n'est pas un conseil juridique. Toute conclusion réglementaire doit être validée par un juriste.

Cahier des charges : [`SPEC.md`](SPEC.md) · Décisions : [`docs/DECISIONS.md`](docs/DECISIONS.md)

## État

- Phase 0 — squelette : API, base de données, front avec navigation, routeur LLM avec contrôle de confidentialité.
- Phase 1a — corpus : 11 textes officiels (MiCA, TFR, DAC/DAC8, régime pilote DLT, MiFID II, DORA, AMLR, AI Act,
  RGPD, ESPR), dernière version consolidée, ~6 000 passages citables avec identifiants stables, empreintes SHA-256,
  versions conservées, recherche plein texte.

- Phase 1b — base de connaissances : recherche (plein texte, vectorielle, hybride), réponses citées avec refus en
  deux couches, page React avec citations exactes et liens EUR-Lex, mode « recherche seule » sans IA.
- Phase 1c — évaluation : 80 questions, jeu de test gelé, intervalles de Wilson (résultats dans `docs/RESULTATS.md`).
- Phase 2 — missions : diagnostic, solutions (verdict blockchain calculé), réglementation avec obligations citées.
- Phase 3 — benchmark sourcé : DefiLlama + registre MiCA de l'ESMA, chaque cellule garde sa source.
- Phase 5 — livrables : note de mission imprimable, export PDF depuis le navigateur.

```bash
docker compose exec api python -m app.corpus ingest            # tout le corpus
docker compose exec api python -m app.corpus ingest --source MICA
```

## Lancer

Prérequis : Docker (avec Compose).

```bash
cp .env.example .env          # clés API facultatives pour l'instant
docker compose up -d --build
```

- Front : http://localhost:5180 (port modifiable via `FRONT_PORT` dans `.env`)
- API : http://localhost:8000/docs

Modèles locaux : Ollama sous Windows (GPU), voir [`docs/OLLAMA.md`](docs/OLLAMA.md) — lancement, modèles
(`qwen3.5:9b`, `bge-m3`), adresse vue depuis WSL, calcul des embeddings (`python -m app.corpus embed`).

## Développer

```bash
# API
docker compose exec api pytest
docker compose exec api ruff check .
docker compose exec api mypy app

# Front (dans frontend/)
npm run gen:api      # régénère les types depuis l'API en cours d'exécution
npm run lint && npm run typecheck && npm test
```

## Stack

FastAPI · PostgreSQL + pgvector · SQLAlchemy/Alembic · LiteLLM · React + TypeScript (Vite) · TanStack Query · Tailwind · Docker Compose.
