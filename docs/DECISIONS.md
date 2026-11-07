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

## 2026-11-07 — Corpus : API de l'Office des publications plutôt que les pages EUR-Lex
- Alternatives : pages HTML EUR-Lex, téléchargement manuel.
- Raison : EUR-Lex bloque les clients automatiques (défi anti-robot, réponse 202 vide). L'Office des publications
  (éditeur du Journal officiel) sert le même texte en XHTML structuré, en français. Les liens affichés restent EUR-Lex.

## 2026-11-07 — Corpus : dernière version consolidée, considérants de l'acte d'origine
- Alternatives : versions d'origine uniquement ; consolidées uniquement.
- Raison : plusieurs textes ont été modifiés (MiFID II, directive 2011/16 qui intègre DAC8, AI Act…). On prend la
  version consolidée la plus récente datée au plus tard d'aujourd'hui (recherche via SPARQL) ; si elle n'existe pas en
  XHTML français, on essaie la précédente, puis l'acte d'origine. Les considérants ne figurent pas dans les
  consolidations et ne sont jamais modifiés : ils viennent de l'acte d'origine.
- Limite : seul le Journal officiel fait foi ; chaque passage garde le CELEX de sa version et le lien vers l'original.

## 2026-11-07 — Découpage : paragraphe, puis points si > 2 500 caractères
- Alternatives : découpage par taille fixe (chunks de N tokens).
- Raison : une citation doit correspondre à une unité juridique (article, paragraphe, point) que le consultant peut
  retrouver. Identifiants stables lisibles (`MICA-ART-3-1-5`). Annexes découpées sur les fins de ligne.
- `PARSER_VERSION` : tout changement des règles de découpage force un redécoupage à la prochaine ingestion, même si
  le texte source n'a pas changé (même SHA-256).

## 2026-11-07 — Embeddings reportés à la phase 1b
- Raison : Ollama (bge-m3) n'est pas installé pour l'instant. La colonne `embedding vector(1024)` existe ; la
  recherche plein texte (`tsvector` français + index GIN) fonctionne dès maintenant.

## 2026-11-07 — Routeur LLM par rôles (`config/llm.yaml`) au-dessus de LiteLLM
- Alternatives : appels directs aux SDK des fournisseurs.
- Raison : changer de fournisseur = modifier la config ; contrôle de confidentialité centralisé.
- Défauts : `reasoning` Claude Opus 5.5, `extraction` Claude Sonnet 5.5, `local` mistral-small (Ollama), `embedding` bge-m3.
