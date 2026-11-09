# Compass - assistant du consultant IA, Blockchain & Cybersécurité

Compass accompagne un consultant sur une mission complète, du premier entretien au livrable :
**diagnostic → solutions → réglementation → benchmark → POC & évaluation → livrables**.

Pensé pour des clients bancaires et industriels (licence PSCA, stablecoins, conformité MiCA / DORA / NIS2 / AI Act),
il s'appuie sur les **textes officiels européens** et des **données publiques vérifiables**, jamais sur la mémoire du modèle.

> Ceci n'est pas un conseil juridique. Toute conclusion réglementaire doit être validée par un juriste.

## En bref

| | |
|---|---|
| **Corpus** | 13 textes européens en version consolidée, ~7 000 passages citables, vérifiés 10/10 contre EUR-Lex |
| **Réponses citées** | le modèle ne renvoie que des identifiants ; le texte affiché est relu depuis la base |
| **Évaluation** | 80 questions, jeu de test gelé avant mesure : 79 % de réponses justes (IC 95 % : 66-88 %), 11/12 refus corrects hors corpus |
| **Benchmark** | DefiLlama + registre MiCA de l'ESMA en direct ; chaque cellule garde sa source et sa méthode |
| **Confidentialité** | une mission confidentielle ne peut appeler qu'un modèle local (contrôle dans le code, testé) |
| **Fournisseur IA** | au choix via LiteLLM (Claude, OpenAI, Mistral…) ou Ollama en local ; une seule variable `AI_API_KEY` |

## Démo

Trois missions fictives sont chargées en un clic (« Charger les missions de démo ») :

- **Maison Lumen** - PME du luxe : traçabilité, IA sur les processus Excel, faut-il vraiment une blockchain ?
- **Banque Azur** - banque régionale (confidentielle) : stablecoin euro, fonds monétaire tokenisé, MiCA.
- **Hexa Industrie** - ETI industrielle : diagnostic cyber NIST CSF 2.0, qualification NIS2 / CRA.

Cahier des charges : [`SPEC.md`](SPEC.md) · Décisions : [`docs/DECISIONS.md`](docs/DECISIONS.md) ·
Résultats : [`docs/RESULTATS.md`](docs/RESULTATS.md)

## État

- Phase 0 - squelette : API, base de données, front avec navigation, routeur LLM avec contrôle de confidentialité.
- Phase 1a - corpus : 13 textes officiels (MiCA, TFR, DAC/DAC8, régime pilote DLT, MiFID II, DORA, NIS2, CRA, AMLR, AI Act,
  RGPD, ESPR), dernière version consolidée, ~7 000 passages citables avec identifiants stables, empreintes SHA-256,
  versions conservées, recherche plein texte.

- Phase 1b - base de connaissances : recherche (plein texte, vectorielle, hybride), réponses citées avec refus en
  deux couches, page React avec citations exactes et liens EUR-Lex, mode « recherche seule » sans IA.
- Phase 1c - évaluation : 80 questions, jeu de test gelé, intervalles de Wilson (résultats dans `docs/RESULTATS.md`).
- Phase 2 - missions : diagnostic, solutions (verdict blockchain calculé), réglementation avec obligations citées.
- Phase 3 - benchmark sourcé : DefiLlama + registre MiCA de l'ESMA, chaque cellule garde sa source.
- Phase 5 - livrables : note de mission imprimable, export PDF depuis le navigateur.
- Entretiens : grille par domaine (questions + « ce qu'on cherche »), relances proposées par l'IA, réponses envoyées vers les notes, grille vierge imprimable.

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

Modèles locaux : Ollama sous Windows (GPU), voir [`docs/OLLAMA.md`](docs/OLLAMA.md) - lancement, modèles
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

Python 3.12 · FastAPI · PostgreSQL + pgvector · SQLAlchemy/Alembic · LiteLLM · React + TypeScript (Vite) · TanStack Query · Tailwind · Docker Compose.
