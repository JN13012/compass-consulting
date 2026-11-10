# Compass - assistant du consultant IA, Blockchain & Cybersécurité

Compass est un assistant d'IA pour le consultant en **IA, Blockchain et Cybersécurité**. Il accompagne une mission
complète, du premier entretien au livrable, en s'appuyant sur les **textes officiels européens** et des **données
publiques vérifiables**, jamais sur la mémoire du modèle.

## La méthode : une mission en 7 étapes

| # | Étape | Ce que fait Compass |
|---|---|---|
| 0 | **Entretiens** | grille de questions par domaine (« ce qu'on cherche »), relances proposées par l'IA, grille imprimable |
| 1 | **Diagnostic** | processus, irritants et maturité ; chaque irritant cite les notes d'entretien, citation vérifiée dans le code |
| 2 | **Solutions** | de la plus simple (digitaliser) à la plus complexe ; verdict « faut-il une blockchain ? » calculé par une grille |
| 3 | **Réglementation** | textes applicables et obligations, chacune appuyée sur le passage officiel exact |
| 4 | **Benchmark** | registre MiCA de l'ESMA et DefiLlama collectés en direct ; chaque cellule garde sa source |
| 5 | **POC** | cadrage avec critères chiffrés, dossier pour le développeur, évaluation sur un jeu de test gardé par Compass |
| 6 | **Livrables** | note de mission prête à imprimer, export PDF |

En parallèle : **Textes officiels** (questions-réponses citées) et **Veille** (nouvelles versions des textes,
comparaison article par article, missions concernées, calendrier des échéances).


## En bref

| | |
|---|---|
| **Corpus** | 13 textes européens en version consolidée (MiCA, AI Act, DORA, NIS2, RGPD…), ~7 000 passages citables, vérifiés contre EUR-Lex |
| **Réponses citées** | le modèle ne renvoie que des identifiants ; le texte affiché est relu depuis la base |
| **Évaluation** | 48 questions de test gelées avant mesure : 90 % de réponses justes avec gpt-5.1 (IC 95 % : 78-96 %), 79 % avec le modèle local qwen3.5 9B ; 11/12 refus corrects hors corpus |
| **IA au choix** | modèle local (Ollama, les données ne quittent pas la machine) ou modèle avancé via clé API (OpenAI, Anthropic, Mistral… via LiteLLM), sélectionnable dans l'interface |
| **Confidentialité** | une mission confidentielle ne peut appeler que le modèle local, quel que soit le choix (contrôle dans le code, testé) |
| **POC** | démo évaluée sur 30 cas jamais vus : 100 % de commandes justes, 5/6 cas ambigus refusés, verdict « pas encore » ([résultats](docs/RESULTATS.md)) |
| **Veille** | vérification des nouvelles versions sur EUR-Lex à la demande, alerte sur les missions dont un passage cité a changé |

## Démo

Trois missions fictives sont chargées en un clic (« Charger les missions de démo ») :

- **Maison Lumen** - prêt-à-porter haut de gamme : agent IA de lecture des commandes (POC évalué), contrefaçon et passeport numérique produit, faut-il vraiment une blockchain ?
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
- Phase 4 - POC & évaluation : cadrage (critères chiffrés, contraintes de la mission), dossier zip pour le développeur, banc d'évaluation sur un jeu de test gardé par Compass (IC de Wilson, verdict, corrections). POC de démo : agent de traitement des commandes (`poc_examples/commandes`, `docker compose --profile poc up -d`). Token ERC-3643 reporté.
- Phase 5 - livrables : note de mission imprimable, export PDF depuis le navigateur.
- Veille : vérification des nouvelles versions sur EUR-Lex, comparaison article par article, missions concernées, calendrier des échéances.
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
