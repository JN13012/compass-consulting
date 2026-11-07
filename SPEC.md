# Compass — Assistant du consultant IA, Blockchain & Cybersécurité

> Cahier des charges. Version 0.2 — 2026-11-07 (ajout du volet cybersécurité, plan recentré sur un démonstrateur).
> Statut : document de référence pour le développement. Toute évolution de périmètre se fait ici d'abord.

**Finalité du projet : un démonstrateur de portfolio** (captures, vidéo, publication LinkedIn, CV). Les choix
privilégient ce qui se montre et se vérifie : parcours de démonstration complets, résultats chiffrés honnêtes,
code propre. Pas d'exploitation en production.

---

## 1. Contexte et objectif

Les consultants en IA générative, en blockchain et en cybersécurité passent une grande partie de leur temps à :
diagnostiquer les processus d'un client, choisir la bonne technologie, vérifier la réglementation,
faire des benchmarks, cadrer et évaluer des POC, puis produire des livrables.

**Compass** est un outil interne qui assiste le consultant sur toute la mission, en suivant la méthode
**Diagnostic → Cadrage → Pilote → Passage à l'échelle**.

### Ce qui le distingue d'un assistant généraliste (ChatGPT, Claude)

1. **Citations vérifiables** : le modèle ne renvoie que des identifiants de passages ; le texte affiché est toujours relu depuis la base. Une citation affichée est toujours réelle.
2. **Données réelles et datées** : données on-chain et registres officiels, pas la mémoire d'un modèle.
3. **Reproductibilité** : un benchmark ou une évaluation peut être relancé à l'identique.
4. **Format cabinet** : livrables (note, slides) prêts à retravailler, chaque chiffre sourcé.
5. **Confidentialité** : les missions marquées confidentielles n'utilisent que des modèles locaux.
6. **Savoir dire non** : l'outil refuse quand le corpus ne permet pas de répondre, et peut recommander *de ne pas* utiliser l'IA ou la blockchain.

### Avertissement permanent (affiché dans l'interface)

> Compass est une aide au travail du consultant. Il ne constitue pas un conseil juridique et ne qualifie
> définitivement aucune situation. Toute conclusion réglementaire doit être validée par un juriste.

---

## 2. Utilisateurs

- **Consultant** (utilisateur principal) : crée des missions, lance les analyses, valide et exporte.
- **Pas d'authentification multi-utilisateurs en v1** (outil local, mono-utilisateur).

---

## 3. Périmètre fonctionnel

### 3.1 Navigation

```
Compass
├── Missions                 liste + création
│   └── Mission <client>
│       ├── 1. Diagnostic
│       ├── 2. Solutions
│       ├── 3. Réglementation
│       ├── 4. Benchmark
│       ├── 5. POC & évaluation
│       └── 6. Livrables
├── Veille
├── Base de connaissances    questions-réponses citées
└── Paramètres               fournisseurs IA, clés API, sources
```

### 3.2 Missions

- Champs : client (nom fictif ou réel), secteur, description du contexte, **niveau de confidentialité** (`public` | `confidentiel`), date de création, statut.
- Une mission `confidentiel` **ne peut utiliser que des modèles locaux** (contrôle appliqué dans le code, pas seulement dans l'interface).
- Documents de mission : import de fichiers (PDF, DOCX, XLSX, CSV, TXT, EML) stockés et indexés **dans le périmètre de la mission uniquement**.

### 3.3 Onglet Diagnostic

Entrées : description libre des processus, notes d'entretien, fichiers d'exemple (ex. tableur Excel des commandes).

Sorties :
- **Cartographie des processus** : étapes, acteurs, outils actuels, volumes estimés.
- **Analyse des fichiers** (tableurs) : structure des colonnes, doublons, ressaisies, champs vides, incohérences — calculés en Python (pandas), pas devinés par le modèle.
- **Irritants** : liste priorisée (temps perdu, erreurs, risques), chacun relié à sa source (passage des notes ou constat sur fichier).
- **Maturité** : grille sur 5 axes (données, outils/ERP, intégrations/API, compétences, gouvernance), note 1-3 justifiée.

### 3.4 Onglet Solutions

Pour chaque irritant, l'outil propose des solutions classées par **niveau de complexité croissante** :

1. **Digitaliser** (remplacer un outil manuel) — sans IA
2. **Automatiser** (connecter, supprimer les ressaisies) — sans IA
3. **IA** (extraction de documents, recherche sémantique, agents, prévision, assistant RAG)
4. **Blockchain** (tokenisation, stablecoin, traçabilité, passeport produit)

Règles :
- Toujours proposer la solution **la plus simple qui résout le problème** en premier.
- Pour toute solution blockchain, appliquer la **grille « Faut-il une blockchain ? »** (plusieurs parties sans confiance mutuelle ? besoin d'un registre partagé infalsifiable ? actif programmable ou transférable ? un intermédiaire de confiance suffirait-il ?). Si la grille échoue, l'outil **recommande de ne pas utiliser de blockchain** et explique pourquoi.
- Chaque solution porte : gain estimé (heures/mois, erreurs évitées), coût estimé (build + run, avec hypothèses explicites), délai, risques, prérequis de maturité.
- Sortie : **matrice valeur / faisabilité** et **feuille de route en 3 temps** (quick wins, 3-6 mois, 6-18 mois).

### 3.5 Onglet Réglementation

- Pour la mission et ses solutions retenues : liste des **textes applicables**, avec pour chacun le raisonnement et **les passages cités**.
- Qualifications prises en charge en v1 :
  - **Crypto** : le jeton est-il un instrument financier (MiFID II / régime pilote DLT), un EMT, un ART, un autre crypto-actif, ou hors champ MiCA ? L'activité nécessite-t-elle un agrément PSCA ? TFR applicable ? DAC8 ?
  - **IA** : niveau de risque AI Act (interdit, haut risque, transparence, minimal) ; données personnelles → RGPD (base légale, AIPD probable ?).
  - **Résilience** : entité financière → DORA.
  - **Cybersécurité** : l'entité relève-t-elle de NIS 2 (entité essentielle ou importante selon secteur — annexes I/II — et taille) ? Ses produits sont-ils des « produits comportant des éléments numériques » au sens du Cyber Resilience Act (catégorie par défaut, importante, critique) ? Obligations de notification d'incident (NIS 2, DORA, RGPD art. 33).
- Pour chaque obligation : statut `couvert` / `manquant` / `à vérifier` selon les informations de la mission.
- Toute affirmation sans passage cité est **interdite** à l'affichage ; si le corpus ne suffit pas : « Le corpus ne permet pas de conclure ».

### 3.6 Base de connaissances (questions-réponses)

- Question en français → réponse courte + passages cités (texte exact, référence article, lien officiel, date de consultation).
- **Refus en deux couches** :
  1. seuil de pertinence sur la recherche (aucun passage suffisant → refus sans appeler le modèle) ;
  2. le modèle peut répondre `INSUFFISANT` ; tout identifiant de passage renvoyé qui n'existe pas en base invalide la réponse.
- Filtres : domaine (crypto, IA, données, résilience), texte, date.

### 3.7 Onglet Benchmark

1. Le consultant saisit un sujet (ex. « stablecoins euro utilisables par une banque »).
2. L'outil propose des **acteurs** et des **critères** à partir de gabarits (`stablecoins`, `fonds_tokenises`, `psca`, `fournisseurs_llm`) ; le consultant les modifie.
3. Collecte depuis trois types de sources :
   - **On-chain** : offre en circulation, nombre de détenteurs, blockchains, historique (DefiLlama, Etherscan, RPC).
   - **Registres officiels** : registre intérimaire MiCA de l'ESMA, listes AMF.
   - **Documents** : prospectus, rapports de réserves, pages officielles — extraction par le modèle **avec l'extrait source**.
4. Chaque cellule = `{valeur, unité, source_url, date_collecte, extrait, méthode, statut}` où `statut ∈ {trouvé, non_trouvé, validé, corrigé}`. **Jamais de valeur sans source.**
5. Le consultant valide/corrige chaque cellule. Le benchmark est **relançable** (mêmes acteurs, mêmes critères, nouvelles données) avec historique des versions.
6. Graphiques simples (évolution d'offre, comparaison) et synthèse rédigée à partir des seules cellules validées.

### 3.8 Onglet POC & évaluation

**L'outil ne code pas le POC.** Il le cadre, puis l'évalue.

**a) Générateur de dossier POC** — produit un dossier zip prêt pour Claude Code :
```
poc-<nom>/
├── CLAUDE.md            contexte, règles, contraintes (confidentialité, RGPD, AI Act…)
├── SPEC.md              objectif, périmètre, user stories, critères d'acceptation chiffrés
├── ARCHITECTURE.md      stack et briques recommandées
├── data/                échantillons anonymisés
├── eval/
│   ├── cases.jsonl      entrées + sorties attendues
│   └── README.md        métriques, seuils, protocole
└── INTERFACE.md         contrat que le POC doit respecter pour être évalué
```

**b) Contrat d'évaluation** — un POC est évaluable s'il expose soit :
- une commande CLI : `run --input <fichier>` → JSON sur stdout ; soit
- une route HTTP : `POST /run` `{input}` → `{output}`.

**c) Banc d'évaluation** — lance les cas du jeu de tests, compare aux attendus, calcule :
- justesse (exacte ou par champ), taux de refus, faux refus, latence, coût estimé ;
- **intervalle de confiance à 95 % (Wilson)** sur chaque taux ;
- pour un smart contract : résultat des tests Foundry + rapport Slither (nb de findings par sévérité).

**d) Rapport** — résultats vs seuils, échecs regroupés par cause, liste de corrections à renvoyer à Claude Code.

**e) Deux POC de démonstration livrés avec le projet** (dans `poc_examples/`) :
- **Agent de traitement des commandes** : lit des commandes reçues par email/PDF, extrait les champs (client, produits, quantités, prix, date de livraison), remplit une base, prépare une facture. Jeu de 50 commandes fictives variées (dont scans et cas ambigus).
- **Token de part de fonds à transferts restreints** (inspiré d'ERC-3643, version simplifiée) sur testnet Sepolia : liste blanche KYC, gel de compte, transfert forcé, pause, souscription/rachat contre un stablecoin EUR de test, NAV mise à jour par un rôle oracle. Tests Foundry + analyse Slither.

### 3.9 Onglet Livrables

- **Note de mission** (PDF, 5-15 pages) : contexte, diagnostic, solutions, réglementation, benchmark, POC, feuille de route, limites.
- **Slides** (PPTX via python-pptx) : gabarit sobre, 1 idée par slide, sources en note de bas de page.
- N'inclut que des éléments **validés** par le consultant.

### 3.10 Veille

- Sources surveillées (configurables dans `corpus/sources.yaml`) : EUR-Lex, ESMA, EBA, AMF, CNIL, Commission européenne (AI Office).
- Tâche planifiée (quotidienne) : détecte les nouveaux documents ou les changements (hash), les ingère dans le corpus avec version, génère un **résumé du changement** et indique **quelles missions sont concernées**.
- Un document modifié ne remplace jamais silencieusement l'ancien : versions conservées, date de consultation tracée.

### 3.11 Paramètres — fournisseurs IA

- Couche d'abstraction **LiteLLM** : Anthropic, OpenAI, Mistral, Google, Ollama (local).
- Configuration par **rôle** dans `config/llm.yaml` :
  - `reasoning` (agents, qualification, rédaction) — défaut : Claude
  - `extraction` (champs structurés) — défaut : Claude
  - `local` (missions confidentielles) — défaut : modèle Ollama
  - `embedding` — défaut : `bge-m3` en local
- Journal de chaque appel : rôle, modèle, tokens, coût estimé, durée, mission.

---

## 4. Corpus réglementaire initial

Chaque document est enregistré avec : identifiant, titre, URL officielle, date de consultation, version, **hash SHA-256**, langue (FR prioritaire).

| Domaine | Texte | Référence |
|---|---|---|
| Crypto | MiCA | Règlement (UE) 2023/1114 |
| Crypto | Transferts de fonds et crypto-actifs (TFR, « travel rule ») | Règlement (UE) 2023/1113 |
| Crypto / fiscal | DAC8 | Directive (UE) 2023/2226 |
| Tokenisation | Régime pilote DLT | Règlement (UE) 2022/858 |
| Tokenisation | MiFID II | Directive 2014/65/UE |
| Résilience | DORA | Règlement (UE) 2022/2554 |
| LCB-FT | AMLR | Règlement (UE) 2024/1624 |
| IA | AI Act | Règlement (UE) 2024/1689 |
| Données | RGPD | Règlement (UE) 2016/679 |
| Produits | ESPR (passeport numérique des produits) | Règlement (UE) 2024/1781 |
| Cybersécurité | NIS 2 | Directive (UE) 2022/2555 |
| Cybersécurité | Cyber Resilience Act | Règlement (UE) 2024/2847 |
| Compléments | Orientations ESMA/EBA, positions AMF, ressources CNIL | à sélectionner en phase 1 |

**Découpage** : par article (et par paragraphe pour les articles longs), considérants séparés, annexes par point. Chaque passage a un identifiant stable (`MICA-ART-3-1-5`, etc.).

---

## 5. Architecture technique

```
compass/
├── backend/
│   └── app/
│       ├── api/            routes FastAPI
│       ├── core/           config, base de données, journalisation
│       ├── llm/            routeur LiteLLM, règles de confidentialité, coût
│       ├── corpus/         ingestion, découpage, hash, versions
│       ├── retrieval/      recherche vectorielle + plein texte, seuils
│       ├── answering/      réponses citées, validation des identifiants, refus
│       ├── missions/       diagnostic, solutions, réglementation
│       ├── benchmark/      gabarits, collecte, cellules sourcées
│       ├── connectors/     defillama, etherscan, rpc, esma, fichiers
│       ├── poc/            générateur de dossier, banc d'évaluation, rapport
│       ├── export/         pdf, pptx
│       └── watch/          veille planifiée
├── frontend/               React + TypeScript (Vite), appelle uniquement l'API
│   └── src/
│       ├── api/            client généré depuis l'OpenAPI de FastAPI
│       ├── pages/          Missions, Mission (onglets), Veille, Base de connaissances, Paramètres
│       ├── components/     composants partagés (Citation, SourcedCell, Disclaimer…)
│       └── lib/
├── contracts/              Foundry (POC token)
├── poc_examples/           POC de démonstration
├── corpus/
│   ├── sources.yaml
│   └── raw/                fichiers téléchargés (non versionnés si volumineux)
├── eval/                   jeux de tests de Compass lui-même
├── config/                 llm.yaml, benchmark_templates/
├── docs/                   décisions, limites, résultats d'évaluation
├── tests/
└── docker-compose.yml
```

| Brique | Choix | Raison |
|---|---|---|
| Langage | Python 3.12 | écosystème IA/data |
| API | FastAPI + Pydantic | typage, OpenAPI |
| Base | PostgreSQL 16 + pgvector | données + vecteurs au même endroit |
| ORM / migrations | SQLAlchemy 2 + Alembic | standard |
| Plein texte | PostgreSQL `tsvector` (français) | recherche hybride sans service en plus |
| IA | LiteLLM, Ollama, bge-m3 | multi-fournisseur, local possible |
| Front | React 18 + TypeScript + Vite | standard du marché, cité dans les offres Doors3 |
| Routage / données | React Router + TanStack Query | navigation par onglets, cache et états de chargement |
| UI | Tailwind CSS + shadcn/ui | composants sobres prêts à l'emploi, peu de CSS à écrire |
| Graphiques | Recharts | matrice valeur/faisabilité, évolutions on-chain |
| Client API | openapi-typescript (types générés depuis FastAPI) | front et back toujours synchronisés |
| Tests front | Vitest + Testing Library ; Playwright pour 2-3 parcours | |
| Blockchain | Foundry, OpenZeppelin, web3.py, Sepolia, Slither | standard du métier |
| Export | python-pptx, WeasyPrint (PDF) | |
| Planification | APScheduler | veille quotidienne |
| Qualité | pytest, ruff, mypy | |
| Lancement | Docker Compose | une commande |

---

## 6. Modèle de données (principal)

- `Mission(id, client, secteur, contexte, confidentialite, statut, created_at)`
- `MissionFile(id, mission_id, nom, type, hash, chemin)`
- `SourceDocument(id, code, titre, url, domaine, version, date_consultation, sha256, langue)`
- `Passage(id, document_id, ref_stable, texte, embedding, tsv)`
- `Finding(id, mission_id, type[irritant|maturite|obligation], contenu, statut, source_refs[])`
- `Solution(id, mission_id, finding_id, niveau[digitaliser|automatiser|ia|blockchain], description, gain, cout, delai, risques, hypotheses, retenue)`
- `Citation(id, objet_type, objet_id, passage_id)`
- `Benchmark(id, mission_id, sujet, gabarit, version)`
- `BenchmarkCell(id, benchmark_id, acteur, critere, valeur, unite, source_url, date_collecte, extrait, methode, statut)`
- `PocDossier(id, mission_id, nom, spec, seuils, chemin_zip)`
- `EvalRun(id, cible, config, date, metriques, ic95)` / `EvalCaseResult(...)`
- `WatchItem(id, source, url, detecte_le, sha256, resume, missions_concernees[])`
- `LlmCall(id, mission_id, role, modele, tokens_in, tokens_out, cout, duree)`

---

## 7. Évaluation de Compass lui-même

Objectif : chiffrer la fiabilité honnêtement, sans sur-ajuster.

- **Jeu de questions** (`eval/qa.jsonl`) : 60 questions minimum, validées une par une à la main.
  - 75 % répondables (réponse attendue + **identifiant(s) du passage attendu**), 25 % non répondables (le corpus ne contient pas la réponse).
  - Réparties sur tous les domaines du corpus.
- **Séparation dev / test** : 40 % dev, 60 % test. **La configuration (modèle, seuils, mode de recherche) est figée sur le dev avant de lancer le test.** Le test n'est lancé qu'une fois par configuration figée ; tout relancement est documenté.
- **Métriques** : bonne réponse avec bon passage cité, refus corrects, faux refus, réponses sourcées mais fausses ; IC 95 % (Wilson).
- **Comparaisons** : recherche vectorielle seule / plein texte seul / hybride ; au moins deux fournisseurs de modèle (un cloud, un local).
- **Jeu de qualifications** (`eval/qualifications.jsonl`) : 20 cas de missions fictives avec qualification attendue (catégorie MiCA, niveau AI Act…).
- **Résultats et limites** publiés dans `docs/RESULTATS.md`, y compris ce qui ne marche pas.

---

## 8. Exigences non fonctionnelles

- **Lancement** : `docker compose up` suffit (hors clés API).
- **Secrets** : uniquement via `.env` (jamais commité) ; `.env.example` fourni.
- **Confidentialité** : routeur LLM bloque tout fournisseur cloud pour une mission `confidentiel` (testé).
- **Traçabilité** : tout contenu affiché peut remonter à sa source (passage, URL, fichier, appel on-chain).
- **Langue** : interface et livrables en français ; code et commentaires en anglais.
- **Performance indicative** : réponse de la base de connaissances < 15 s avec un modèle cloud.

---

## 9. Hors périmètre v1

- Multi-utilisateurs, authentification, droits.
- Construction automatique des POC (option future : lancement via Claude Agent SDK dans un environnement isolé).
- Déploiement mainnet, gestion de fonds réels.
- Design soigné / charte graphique : interface sobre et fonctionnelle uniquement en v1.

---

## 10. Cas de démonstration

Trois missions fictives complètes, préchargées :

1. **« Maison Lumen »**, distributeur de prêt-à-porter haut de gamme : commandes et factures sur Excel, demandes de suivi de livraison, contrefaçon. → Solutions : digitalisation des commandes, agent de traitement des commandes (IA), passeport numérique produit (blockchain, avec grille de pertinence). → Réglementation : RGPD, AI Act, ESPR, vérification hors champ MiCA.
2. **« Banque Azur »**, banque régionale : projet de fonds monétaire tokenisé réglé en stablecoin EUR, contrôle KYC des investisseurs par IA. → Réglementation : MiFID II / régime pilote DLT, MiCA (EMT), DORA, AMLR, AI Act. → Benchmark : stablecoins EUR et fonds monétaires tokenisés. → POC : token à transferts restreints + évaluation (audit Slither).
3. **« Hexa Industrie »**, ETI (450 salariés) fabriquant des capteurs connectés pour l'industrie : Active Directory vieillissant, pas de plan de réponse à incident, sauvegardes non testées, firmware mis à jour à la main. → Diagnostic de maturité cyber (grille NIST CSF 2.0 : Gouverner, Identifier, Protéger, Détecter, Répondre, Rétablir). → Réglementation : NIS 2 (fabrication — annexe II, entité importante ?), Cyber Resilience Act (capteurs = produits comportant des éléments numériques), RGPD art. 32-33. → Solutions : quick wins (MFA, sauvegardes hors ligne testées, inventaire), feuille de route, et un usage IA encadré (tri des alertes) avec qualification AI Act.

---

## 3.12 Volet cybersécurité (transverse)

- **Diagnostic de maturité** : grille NIST CSF 2.0 (6 fonctions), notée 1-3 par fonction avec justification reliée aux notes d'entretien ; mesures d'hygiène prioritaires.
- **Qualification réglementaire** : NIS 2, CRA, DORA, RGPD (voir §3.5), avec citations.
- **Solutions** : classées comme les autres (quick wins → projets), chaque mesure reliée au risque et à l'obligation qu'elle couvre.
- **POC** : l'audit de smart contract (Slither) et le banc d'évaluation couvrent la partie technique ; pas d'outil offensif.

---

## 11. Plan de réalisation — recentré « démonstrateur »

| Phase | Contenu | Statut |
|---|---|---|
| 0 | Squelette, Docker, config | ✅ |
| 1a | Corpus (13 textes, versions consolidées), vérification EUR-Lex | ✅ |
| 1b | Recherche, réponses citées, refus, page Base de connaissances | |
| 1c | Évaluation (jeu de questions validé, IC 95 %) | |
| 2 | Missions, Diagnostic, Solutions, Réglementation (IA, blockchain, cyber) + 3 missions de démo | |
| 3 | Benchmark sourcé (données on-chain + registres) | |
| 4 | Dossier POC + banc d'évaluation ; 1 POC démontré de bout en bout | |
| 5 | Export livrables (PDF/PPTX) ; veille simplifiée (bouton « vérifier les mises à jour ») | |
| 6 | Finitions, captures, vidéo, README orienté recruteur | |

Fournisseurs IA : Ollama (Windows, GPU local) branché en fin de parcours ; tout est développé et testé avec des
appels simulés, puis validé avec le vrai modèle avant les captures.
