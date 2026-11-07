# Compass — assistant du consultant IA & Blockchain

Outil interne qui accompagne une mission de conseil de bout en bout :
**diagnostic → solutions → réglementation → benchmark → POC & évaluation → livrables**,
avec des citations toujours vérifiables, des données on-chain réelles et des modèles locaux pour les missions confidentielles.

> Ceci n'est pas un conseil juridique. Toute conclusion réglementaire doit être validée par un juriste.

Cahier des charges : [`SPEC.md`](SPEC.md) · Décisions : [`docs/DECISIONS.md`](docs/DECISIONS.md)

## État

Phase 0 — squelette : API, base de données, front avec navigation, routeur LLM avec contrôle de confidentialité.

## Lancer

Prérequis : Docker (avec Compose).

```bash
cp .env.example .env          # clés API facultatives pour l'instant
docker compose up -d --build
```

- Front : http://localhost:5180 (port modifiable via `FRONT_PORT` dans `.env`)
- API : http://localhost:8000/docs

Modèles locaux (optionnel) : `docker compose --profile local up -d`.

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
