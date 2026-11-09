# Décisions

Format : date - décision - alternatives - raison.

## 2026-11-07 - Front React + TypeScript (Vite) dès la phase 0
- Alternatives : Streamlit.
- Raison : standard du marché, cité dans les offres visées ; l'API reste séparée et typée.

## 2026-11-07 - Types API générés depuis l'OpenAPI de FastAPI (openapi-typescript + openapi-fetch)
- Alternatives : types écrits à la main, client généré complet (orval).
- Raison : front et back synchronisés sans duplication ; client minimal.

## 2026-11-07 - Le front appelle `/api/*`, proxifié par Vite vers l'API
- Alternatives : appels directs avec CORS.
- Raison : même origine en dev, pas de configuration CORS côté navigateur.

## 2026-11-07 - Ollama optionnel (profil Docker `local`)
- Alternatives : service toujours lancé.
- Raison : pas nécessaire avant les missions confidentielles ; évite un téléchargement lourd au démarrage.
  Le blocage « mission confidentielle → modèle local uniquement » est déjà appliqué et testé dans le routeur.

## 2026-11-07 - Corpus : API de l'Office des publications plutôt que les pages EUR-Lex
- Alternatives : pages HTML EUR-Lex, téléchargement manuel.
- Raison : EUR-Lex bloque les clients automatiques (défi anti-robot, réponse 202 vide). L'Office des publications
  (éditeur du Journal officiel) sert le même texte en XHTML structuré, en français. Les liens affichés restent EUR-Lex.

## 2026-11-07 - Corpus : dernière version consolidée, considérants de l'acte d'origine
- Alternatives : versions d'origine uniquement ; consolidées uniquement.
- Raison : plusieurs textes ont été modifiés (MiFID II, directive 2011/16 qui intègre DAC8, AI Act…). On prend la
  version consolidée la plus récente datée au plus tard d'aujourd'hui (recherche via SPARQL) ; si elle n'existe pas en
  XHTML français, on essaie la précédente, puis l'acte d'origine. Les considérants ne figurent pas dans les
  consolidations et ne sont jamais modifiés : ils viennent de l'acte d'origine.
- Limite : seul le Journal officiel fait foi ; chaque passage garde le CELEX de sa version et le lien vers l'original.

## 2026-11-07 - Découpage : paragraphe, puis points si > 2 500 caractères
- Alternatives : découpage par taille fixe (chunks de N tokens).
- Raison : une citation doit correspondre à une unité juridique (article, paragraphe, point) que le consultant peut
  retrouver. Identifiants stables lisibles (`MICA-ART-3-1-5`). Annexes découpées sur les fins de ligne.
- `PARSER_VERSION` : tout changement des règles de découpage force un redécoupage à la prochaine ingestion, même si
  le texte source n'a pas changé (même SHA-256).

## 2026-11-07 - Embeddings reportés à la phase 1b
- Raison : Ollama (bge-m3) n'est pas installé pour l'instant. La colonne `embedding vector(1024)` existe ; la
  recherche plein texte (`tsvector` français + index GIN) fonctionne dès maintenant.

## 2026-11-07 - Base de connaissances : réponses citées et refus en deux couches
- Le modèle renvoie un JSON `{statut, reponse, passages: [identifiants]}` ; le texte affiché est toujours relu
  depuis la base. Tout identifiant non fourni au modèle → refus (`citation_invalide`). Réponse sans citation → refus.
- Couche 1 (sans appel au modèle) : meilleur score plein texte < 0,30 → refus. Seuil provisoire, à régler en
  phase 1c sur le jeu de développement uniquement.
- Sortie mal formée : un nouvel essai, puis refus (`reponse_invalide`).

## 2026-11-07 - Recherche plein texte : requête OU + reclassement simple
- Une question naturelle en ET ne trouve presque rien ; on cherche en OU sur les mots porteurs de sens (mots
  interrogatifs retirés), puis on reclasse : considérants ×0,75, articles « Définitions » ×1,5 pour les questions de
  définition. Un texte nommé dans la question (MiCA, NIS 2, AI Act…) restreint la recherche à ce texte.
- Limite connue : sans embeddings, une question formulée autrement que le texte (« pratiques interdites » →
  art. 5 AI Act) peut rater le bon article. Le mode hybride (plein texte + vecteurs, fusion RRF) est prêt et
  s'active dès que les embeddings sont calculés.

## 2026-11-07 - Mode « Rechercher les passages » sans génération
- Toujours disponible, même sans fournisseur IA ; si le fournisseur est injoignable, `/kb/ask` renvoie 503 et
  l'interface propose ce mode.

## 2026-11-07 - Ollama côté Windows (GPU) plutôt que dans Docker
- Le poste a déjà Ollama sous Windows avec une RTX 4060 et `qwen3.5:9b`. L'URL est configurable
  (`OLLAMA_BASE_URL`) ; branchement et calcul des embeddings en fin de parcours. Tout est testé avec des appels
  simulés en attendant.

## 2026-11-07 - Routeur LLM par rôles (`config/llm.yaml`) au-dessus de LiteLLM
- Alternatives : appels directs aux SDK des fournisseurs.
- Raison : changer de fournisseur = modifier la config ; contrôle de confidentialité centralisé.
- Défauts : `reasoning` Claude Opus 5.5, `extraction` Claude Sonnet 5.5, `local` mistral-small (Ollama), `embedding` bge-m3.

## 2026-11-07 - Export de la note de mission : HTML imprimable plutôt que WeasyPrint

- **Choix** : l'API sert `GET /missions/{id}/note`, une page HTML A4 (styles `@page`) assemblée en Python à partir
  des résultats enregistrés et de la dernière collecte de benchmark ; le navigateur produit le PDF (« Exporter en PDF »).
- **Alternatives** : WeasyPrint (dépendances système Cairo/Pango dans l'image Docker), python-pptx (reporté).
- **Raison** : zéro dépendance ajoutée, rendu identique à l'écran et sur papier ; aucune citation générée, les extraits
  viennent de la base comme partout ailleurs. Export PPTX non fait.

## 2026-11-09 - Entretiens : grille écrite à la main, IA seulement pour les relances

- **Choix** : banque de questions dans `config/interview_guide.yaml` (tronc commun + modules IA, blockchain, cyber
  selon NIST CSF 2.0), chaque question avec « ce qu'on cherche ». Les réponses sont enregistrées par mission et
  « Envoyer vers les notes » les range par thème dans les notes, qui alimentent le diagnostic.
- **Alternatives** : questions entièrement générées par le modèle ; simple liste sans zone de réponse.
- **Raison** : une méthode d'entretien reproductible et relue vaut mieux qu'une liste variable d'une fois sur
  l'autre. Le modèle n'intervient que pour proposer des relances à partir des réponses déjà saisies.

## 2026-11-09 - Veille réglementaire : réelle, sans planificateur

- **Choix** : bouton « Vérifier les mises à jour » qui interroge l'Office des publications (SPARQL) et enregistre
  chaque vérification ; comparaison article par article entre la version en base et une version antérieure
  conservée (`python -m app.corpus archive`) ; missions qui citent le texte, avec les passages cités modifiés ;
  calendrier des échéances écrit à la main (`config/deadlines.yaml`), chaque date vérifiée par un test contre le
  passage qui la fixe.
- **Données de démonstration** : versions antérieures réelles archivées pour MiFID II (17/01/2025) et l'AI Act
  (12/07/2024), afin de montrer de vrais changements, pas des exemples inventés.
- **Non fait** : planification automatique (tâche hebdomadaire) et notifications, indiquées comme désactivées.
- **Raison** : tout ce qui est affiché est vrai et vérifiable ; seul l'automatisme est hors démonstration.

## 2026-11-09 - Phase 4 : Compass cadre et évalue le POC, il ne le code pas

- **Choix** : onglet « POC » en trois blocs. (1) Cadrage proposé par le modèle (solution, périmètre, user stories,
  critères chiffrés parmi 5 métriques fixes), contraintes de la mission ajoutées par le code (confidentialité,
  textes applicables, refus plutôt que deviner), seuils modifiables par le consultant. (2) Jeu de cas
  `{id, input, expected}` (`expected = null` : refus attendu), scindé de façon déterministe et stratifiée :
  40 % vont dans le dossier zip remis au développeur (CLAUDE.md, SPEC.md, ARCHITECTURE.md, INTERFACE.md, eval/),
  60 % restent dans Compass comme jeu de test. (3) Banc HTTP (`POST /run`) en tâche de fond : comparaison champ par
  champ, taux avec IC de Wilson, verdict par critère (« robuste » si tout l'intervalle respecte le seuil), échecs
  groupés par cause et liste de corrections, tout en Python.
- **Stockage** : colonne JSONB `missions.poc` (migration 0009) plutôt que les tables `PocDossier` / `EvalRun` de la
  spec : un seul POC par mission en v1, même modèle que diagnostic / solutions / réglementation.
- **Alternatives** : exécuter une commande CLI fournie par l'utilisateur (refusé : exécution arbitraire) ;
  transmettre tout le jeu au développeur (refusé : on réglerait le POC sur le test).
- **POC de démonstration** : `poc_examples/commandes/` (Maison Lumen), service Docker séparé (profil `poc`).
  Le modèle lit l'e-mail ; le code vérifie les références, prend les prix au catalogue, calcule le total.
  50 commandes fictives générées par script (`data/generate.py`), attendus calculés par le même script.
  « PDF » = texte extrait d'un bon de commande ; pas d'OCR d'images (dépendance lourde, hors v1).
- **Limite** : la liste de corrections cite des cas du jeu de test. Après une itération, ce jeu n'est plus vierge :
  chaque passage est donc publié avec son numéro d'itération (voir `RESULTATS.md`).
- **Reporté (phase 4b)** : POC token ERC-3643 (Foundry, Slither, Sepolia).
