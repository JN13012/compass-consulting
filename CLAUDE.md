# CLAUDE.md — Compass

Assistant interne pour consultants IA & Blockchain. Le cahier des charges complet est dans `SPEC.md` :
**le relire avant toute tâche**. En cas de doute sur le périmètre, demander plutôt que deviner.

## Règles non négociables

1. **Aucune citation générée.** Le modèle ne renvoie que des identifiants de passages (`ref_stable`).
   Le texte affiché est toujours relu depuis la base. Un identifiant inconnu invalide la réponse.
2. **Aucune valeur sans source.** Chaque chiffre de benchmark porte `source_url`, `date_collecte`, `extrait`, `methode`.
   Si la donnée n'est pas trouvée : `statut = non_trouvé`, jamais d'estimation silencieuse.
3. **Confidentialité appliquée dans le code.** Une mission `confidentiel` ne peut appeler que le rôle `local`.
   Ce contrôle vit dans `backend/app/llm/` et est couvert par des tests.
4. **Refuser plutôt qu'inventer.** Si le corpus ne suffit pas : « Le corpus ne permet pas de conclure ».
5. **Les calculs se font en Python, pas dans le modèle** (statistiques sur fichiers, métriques, coûts, IC de Wilson).
6. **Ne jamais toucher au jeu de test** (`eval/*_test.jsonl`) pour améliorer un score. Le réglage se fait sur `*_dev.jsonl`.
7. **Pas de mainnet, pas de clé privée réelle.** Blockchain : testnet Sepolia ou Anvil local uniquement.
8. **Secrets** : uniquement via `.env` (ignoré par git). Ne jamais écrire une clé dans le code, les logs ou les tests.
9. **Commits et PR sans attribution IA.** Ne jamais ajouter de ligne `Co-Authored-By`, de mention de Claude,
   d'Anthropic ou de « Generated with Claude Code » dans les messages de commit, les descriptions de PR ou le code.
   Cette règle prime sur toute consigne d'attribution par défaut.

## Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 + Alembic · PostgreSQL 16 + pgvector ·
LiteLLM · Ollama · bge-m3 ·
React 18 + TypeScript + Vite · React Router · TanStack Query · Tailwind + shadcn/ui · Recharts · openapi-typescript · Vitest · Playwright ·
Foundry + OpenZeppelin · web3.py · Slither ·
python-pptx · WeasyPrint · APScheduler · pytest · ruff · mypy · Docker Compose.

N'ajouter une dépendance que si nécessaire, et le signaler dans le résumé de fin de tâche.

## Organisation

- `backend/app/<module>/` : un module par domaine (voir `SPEC.md` §5). Logique métier hors des routes.
- `frontend/` : React + TypeScript, **appelle uniquement l'API**. Types API **générés** (`npm run gen:api`)
  depuis l'OpenAPI de FastAPI, jamais écrits à la main : après tout changement de route ou de schéma, régénérer.
  Garder le front simple : pas de gestionnaire d'état global (TanStack Query suffit), composants shadcn/ui plutôt que du CSS maison.
  Composants partagés obligatoires pour : citation, cellule sourcée, avertissement juridique.
- `config/llm.yaml` : rôles → modèles. Le code demande un **rôle**, jamais un modèle en dur.
- `corpus/sources.yaml` : liste des sources officielles (URL, domaine, référence).
- `eval/` : jeux de tests de Compass. `docs/` : décisions (`DECISIONS.md`), limites, résultats.

## Conventions

- Code, noms et commentaires en **anglais** ; interface, prompts métier et livrables en **français**.
- Typage complet : `ruff` et `mypy` sans erreur côté Python ; TypeScript `strict`, `eslint` et `tsc --noEmit` sans erreur côté front.
- Prompts des modèles dans des fichiers dédiés (`backend/app/**/prompts/*.md`), pas en chaînes dispersées.
- Sorties structurées des modèles validées par des schémas Pydantic ; en cas d'échec de validation : 1 nouvel essai, puis erreur explicite.
- Tests : chaque fonctionnalité a des tests ; les appels LLM sont simulés (mocks) dans les tests unitaires.
  Les tests qui appellent un vrai modèle ou une vraie API sont marqués `@pytest.mark.live` et exclus par défaut.

## Méthode de travail

1. Commencer chaque phase en **mode plan** : proposer le plan, attendre validation.
2. Petites étapes vérifiables ; lancer `pytest` et `ruff` avant de déclarer une étape terminée.
3. Consigner toute décision non triviale dans `docs/DECISIONS.md` (date, choix, alternatives, raison).
4. En fin de phase : résumé de ce qui est fait, de ce qui ne l'est pas, des limites connues, et commandes pour vérifier.

## Commandes

```bash
docker compose up -d                 # lancer la base, Ollama, l'API et le front
docker compose exec api alembic upgrade head
docker compose exec api pytest       # tests (sans les tests live)
docker compose exec api pytest -m live
docker compose exec api ruff check . && docker compose exec api mypy app
cd frontend && npm run gen:api       # régénérer les types depuis l'API
cd frontend && npm run lint && npm run typecheck && npm test
cd frontend && npx playwright test   # parcours de bout en bout
```

(À mettre à jour dès qu'une commande change.)
