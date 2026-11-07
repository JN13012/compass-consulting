# Prompts par phase — Compass

Mode d'emploi :
- **Une phase = une session Claude Code** (ou plusieurs si la phase est longue). Ouvrir une nouvelle session entre deux phases.
- Coller le prompt de la phase. Claude Code commence en mode plan : **lire et valider son plan** avant qu'il code.
- À la fin de chaque phase : faire toi-même la section **« À vérifier par toi »**, puis commit.
- Les tâches marquées 👤 sont **les tiennes** : ne pas les déléguer, c'est ce qui rend le projet crédible.

---

## Phase 0 — Squelette du projet

```
Lis SPEC.md et CLAUDE.md en entier. Nous démarrons la phase 0 (SPEC §11).

Objectif : un squelette qui démarre, sans fonctionnalité métier.

À livrer :
- Arborescence de SPEC §5 (modules vides avec __init__.py).
- docker-compose.yml : postgres+pgvector, ollama, api (FastAPI), front (React + Vite, serveur de dev).
- frontend/ : Vite + React + TypeScript strict, Tailwind + shadcn/ui, React Router, TanStack Query,
  eslint, Vitest ; script `gen:api` (openapi-typescript) qui génère les types depuis /openapi.json.
- Mise en page : barre latérale (Missions, Veille, Base de connaissances, Paramètres),
  page Mission avec les 6 onglets en placeholders, composant Disclaimer affiché partout.
- Configuration (pydantic-settings), .env.example, .gitignore.
- SQLAlchemy + Alembic avec une première migration (tables Mission et SourceDocument uniquement).
- Route GET /health (vérifie la base) et une page d'accueil React qui l'affiche via le client généré.
- config/llm.yaml avec les rôles reasoning, extraction, local, embedding (SPEC §3.11).
- Routeur LLM minimal dans backend/app/llm/ : choisit le modèle selon le rôle,
  refuse tout rôle non local pour une mission confidentielle (exception dédiée), journalise l'appel.
- Tests : /health, routeur (choix du modèle, blocage confidentialité, appels simulés).
- pytest, ruff, mypy configurés côté API ; lint, typecheck et Vitest côté front.
  README.md avec les commandes de lancement.
- docs/DECISIONS.md initialisé.

Critères de fin : `docker compose up` démarre tout, /health répond OK, la page d'accueil React l'affiche,
la navigation entre les pages fonctionne, tous les contrôles (API et front) passent.

Commence par me proposer ton plan.
```

**À vérifier par toi :** lancer `docker compose up`, ouvrir le front, lire le routeur LLM (le blocage confidentiel est-il vraiment impossible à contourner ?).

---

## Phase 1a — Corpus et ingestion

👤 **Avant de lancer :** relire la liste du corpus (SPEC §4) et ajouter 3-5 compléments (orientations ESMA/EBA, positions AMF, CNIL) avec leur URL officielle.

```
Lis SPEC.md (§3.6, §4, §6) et CLAUDE.md. Phase 1a : ingestion du corpus.

À livrer :
- corpus/sources.yaml rempli avec les textes de SPEC §4 (URL EUR-Lex en français, domaine, référence).
  Si tu n'es pas sûr d'une URL, marque-la `a_verifier: true` au lieu de l'inventer.
- Téléchargement des sources (HTML EUR-Lex de préférence), stockage dans corpus/raw/,
  enregistrement SourceDocument avec date de consultation et SHA-256.
- Découpage en passages : articles, paragraphes pour les articles longs, considérants, annexes.
  Identifiants stables lisibles (ex. MICA-ART-3-1-5). Même entrée → mêmes identifiants (test).
- Embeddings bge-m3 (via Ollama ou sentence-transformers, à justifier dans DECISIONS.md) + tsvector français.
- Commande CLI : `python -m app.corpus ingest [--source CODE]`, idempotente (hash inchangé → rien à refaire).
- Rapport d'ingestion : nb de passages par document, documents en échec.
- Tests sur un extrait HTML fixe (pas de réseau dans les tests unitaires).

Critères de fin : tout le corpus ingéré, relance sans doublon, rapport lisible.
Commence par me proposer ton plan.
```

**À vérifier par toi :** ouvrir 10 passages au hasard et les comparer au texte officiel (découpage, numérotation, pas de texte coupé). Vérifier chaque URL marquée `a_verifier`.

---

## Phase 1b — Recherche, réponses citées, Base de connaissances

```
Lis SPEC.md (§3.6, §7) et CLAUDE.md. Phase 1b.

À livrer :
- backend/app/retrieval : recherche vectorielle, plein texte, et hybride (fusion RRF), mode configurable.
- backend/app/answering :
  - prompt qui impose au modèle de répondre en JSON {reponse, passages: [ref_stable], statut: OK|INSUFFISANT} ;
  - couche 1 de refus : aucun passage au-dessus du seuil → refus sans appel au modèle ;
  - couche 2 : statut INSUFFISANT, ou ref_stable inconnu/hors des passages fournis → refus ;
  - le texte cité affiché est relu depuis la base.
- Route POST /kb/ask et page React « Base de connaissances » (composant Citation réutilisable) (question, réponse, passages cités
  avec texte exact, référence, lien officiel, date de consultation ; avertissement juridique visible ; filtres par domaine).
- Tests : refus couche 1, refus couche 2, identifiant inventé rejeté, rendu des citations.

Critères de fin : une question répondable obtient une réponse citée ; une question hors corpus est refusée.
Commence par me proposer ton plan.
```

---

## Phase 1c — Évaluation de la Base de connaissances

👤 **Avant de lancer :** c'est la tâche la plus importante du projet.
1. Faire générer un brouillon de 80 questions (par Claude, à part), réparties par domaine, 75 % répondables / 25 % non.
2. **Valider chaque question à la main** : garder les 60 meilleures, écrire la réponse attendue et l'identifiant du passage attendu en lisant le texte officiel.
3. Séparer : `eval/qa_dev.jsonl` (24) et `eval/qa_test.jsonl` (36). Ne plus jamais modifier le fichier test après ça.

```
Lis SPEC.md (§7) et CLAUDE.md. Phase 1c : évaluation.

Les jeux eval/qa_dev.jsonl et eval/qa_test.jsonl existent et ne doivent pas être modifiés.

À livrer :
- backend/app/poc/evaluation (réutilisable plus tard pour les POC) : exécution d'un jeu de cas,
  métriques (bonne réponse + bon passage, refus corrects, faux refus, sourcé-mais-faux à marquer manuellement),
  IC 95 % de Wilson, latence, coût.
- CLI : `python -m app.eval kb --split dev|test --mode vector|fulltext|hybrid --role reasoning|local`.
- Enregistrement des runs (EvalRun) et export Markdown.
- Procédure : régler seuils et mode sur dev uniquement, figer la config dans config/eval_frozen.yaml,
  puis lancer test UNE fois par configuration figée.
- docs/RESULTATS.md : tableau comparatif (3 modes × 2 fournisseurs), IC 95 %, limites.

Critères de fin : RESULTATS.md complet et honnête, y compris les échecs.
Commence par me proposer ton plan.
```

**À vérifier par toi :** relire chaque échec du test et le classer (recherche ratée, mauvais raisonnement, question ambiguë). Ajouter ton analyse dans RESULTATS.md.

---

## Phase 2a — Missions et Diagnostic

```
Lis SPEC.md (§3.2, §3.3, §6) et CLAUDE.md. Phase 2a.

À livrer :
- CRUD missions (API + page React « Missions »), niveau de confidentialité, import de fichiers de mission.
- Indexation des fichiers de mission dans un espace propre à la mission.
- Onglet Diagnostic :
  - analyse de tableurs en pandas (colonnes, types, doublons, champs vides, incohérences) — aucun calcul par le modèle ;
  - extraction par le modèle : processus, acteurs, outils, irritants (chaque irritant relié à sa source) ;
  - grille de maturité 5 axes notée 1-3 avec justification ;
  - le consultant peut valider / modifier / supprimer chaque élément.
- Respect de la confidentialité de la mission dans tous les appels.
- Fichiers de démonstration pour « Maison Lumen » (SPEC §10) : tableur de commandes réaliste avec défauts, notes d'entretien.
- Tests.

Commence par me proposer ton plan.
```

---

## Phase 2b — Solutions et Réglementation

```
Lis SPEC.md (§3.4, §3.5) et CLAUDE.md. Phase 2b.

À livrer :
- Onglet Solutions :
  - pour chaque irritant validé : propositions classées digitaliser → automatiser → IA → blockchain ;
  - grille « Faut-il une blockchain ? » codée explicitement (questions + réponses + verdict), capable de dire non ;
  - gain, coût (hypothèses explicites, calcul en Python), délai, risques, prérequis ;
  - matrice valeur/faisabilité (graphique) et feuille de route en 3 temps.
- Onglet Réglementation :
  - textes applicables à la mission et aux solutions retenues, avec raisonnement et passages cités (moteur de la phase 1) ;
  - qualifications : crypto (instrument financier / EMT / ART / autre / hors champ ; PSCA ; TFR ; DAC8),
    IA (niveau AI Act ; RGPD), DORA ;
  - obligations avec statut couvert / manquant / à vérifier ;
  - affirmation sans citation = non affichée.
- Mission de démonstration « Banque Azur » (SPEC §10).
- Tests, dont : un cas où la grille blockchain doit répondre non.

Commence par me proposer ton plan.
```

👤 **Avant / après :** écrire `eval/qualifications_dev.jsonl` et `_test.jsonl` (20 cas fictifs avec la qualification attendue, vérifiée dans les textes). Après la phase : lancer l'évaluation des qualifications et compléter RESULTATS.md.

**Jalon : version minimale présentable atteinte.**

---

## Phase 3 — Benchmark

```
Lis SPEC.md (§3.7) et CLAUDE.md. Phase 3.

À livrer :
- Gabarits dans config/benchmark_templates/ : stablecoins, fonds_tokenises, psca, fournisseurs_llm
  (acteurs suggérés, critères, méthode de collecte par critère).
- Connecteurs (backend/app/connectors) avec cache et gestion des erreurs : DefiLlama (stablecoins),
  Etherscan (clé via .env), lecture RPC (totalSupply, rôles du contrat si possible), registre intérimaire MiCA de l'ESMA,
  extraction depuis documents/URL avec extrait source.
- Cellules sourcées (BenchmarkCell), statuts, validation/correction dans l'interface.
- Relance d'un benchmark avec versions et comparaison avant/après.
- Graphiques simples et synthèse rédigée à partir des seules cellules validées.
- Tests avec réponses d'API enregistrées (pas de réseau en tests unitaires).

Commence par me proposer ton plan.
```

**À vérifier par toi :** contrôler 10 cellules à la main contre leur source.

---

## Phase 4a — Dossier POC et banc d'évaluation

```
Lis SPEC.md (§3.8) et CLAUDE.md. Phase 4a.

À livrer :
- Générateur de dossier POC (zip) : CLAUDE.md, SPEC.md, ARCHITECTURE.md, data/, eval/cases.jsonl, eval/README.md,
  INTERFACE.md — rempli depuis la mission (solution retenue, contraintes réglementaires citées, confidentialité).
- Contrat d'évaluation : CLI `run --input` → JSON, ou HTTP POST /run.
- Banc d'évaluation générique (réutilise le module de la phase 1c) : justesse par champ, refus, latence, coût, IC 95 %.
- Évaluation smart contract : lancement des tests Foundry + Slither, synthèse des findings par sévérité.
- Rapport : résultats vs seuils, échecs groupés par cause, liste de corrections prête à renvoyer à Claude Code.
- Onglet « POC & évaluation » dans le front React.

Commence par me proposer ton plan.
```

## Phase 4b — POC de démonstration

Lancer **chaque POC dans sa propre session**, à partir du dossier généré par Compass (c'est la démonstration de la boucle complète).

1. Générer le dossier POC « agent de commandes » depuis la mission Maison Lumen.
2. Ouvrir une session Claude Code dans ce dossier : « Lis CLAUDE.md et SPEC.md, construis le POC, respecte INTERFACE.md. »
3. Évaluer avec Compass, renvoyer la liste de corrections, itérer jusqu'au seuil (ou documenter pourquoi on n'y arrive pas).
4. Même chose pour le token à transferts restreints (mission Banque Azur), sur Anvil puis Sepolia.

👤 Construire les 50 commandes fictives de test (dont scans et cas ambigus) et vérifier les sorties attendues.

---

## Phase 5 — Livrables et veille

```
Lis SPEC.md (§3.9, §3.10) et CLAUDE.md. Phase 5.

À livrer :
- Export note de mission (PDF) et slides (PPTX) à partir des seuls éléments validés, sources en notes.
- Veille : APScheduler quotidien, détection par hash des nouveaux documents/changements sur les sources de sources.yaml,
  ingestion versionnée (jamais d'écrasement silencieux), résumé du changement, missions concernées.
- Page « Veille » dans le front React.
- Tests.

Commence par me proposer ton plan.
```

---

## Phase 6 — Finitions (surtout 👤)

- Rejouer les deux missions de démonstration de bout en bout, corriger ce qui accroche.
- Tests Playwright des 3 parcours clés : question à la Base de connaissances, mission de bout en bout, export.
- README orienté recruteur : le problème, ce que fait l'outil, captures, résultats chiffrés, limites.
- `docs/LIMITES.md` : ce que l'outil ne sait pas faire.
- Vidéo de 3 minutes : une mission, du diagnostic au livrable.
- Note de synthèse de 3-4 pages type cabinet (ex. sur les stablecoins euro ou les fonds tokenisés) produite avec Compass et relue par toi.
