# Résultats - Base de connaissances

Mesure unique sur le **jeu de test** (48 questions jamais utilisées pour le réglage), configuration figée
au préalable sur le jeu de réglage ([`config/eval_frozen.yaml`](../config/eval_frozen.yaml), commitée avant le test).

Modèle local : `qwen3.5:9b` (Ollama, RTX 4060) · embeddings `bge-m3` · recherche vectorielle · 13 textes, 6 994 passages.

| Indicateur | Résultat | IC 95 % (Wilson) |
|---|---|---|
| Répond en citant le bon article | **27 / 36** (75 %) | 59 - 86 % |
| … et la réponse contient le fait attendu | 26 / 36 (72 %) | 56 - 84 % |
| Refus à tort (réponse pourtant dans les textes) | 7 / 36 (19 %) | 10 - 35 % |
| Répond en citant un mauvais article | 2 / 36 (6 %) | 2 - 18 % |
| Refuse les questions hors corpus | **11 / 12** (92 %) | 65 - 99 % |
| Score global (bonnes réponses + bons refus) | **38 / 48** (79 %) | 66 - 88 % |
| Recherche : bon passage dans les 8 premiers | 32 / 36 (89 %) | 75 - 96 % |

Jeu de réglage, pour comparaison : 30/32 (94 %). L'écart avec le test est attendu (réglage sur le réglage) et
montre pourquoi on ne publie que le chiffre du test.

## Comparaison des modes de recherche (jeu de réglage, bon passage dans les 8 premiers)

| Plein texte | Hybride (RRF) | Vectoriel |
|---|---|---|
| 10 / 24 | 17 / 24 | **23 / 24** |

Comme dans d'autres retours d'expérience, l'hybride ne bat pas le vectoriel seul sur ce corpus.

## Limites

- Échantillon petit : les intervalles de confiance sont larges.
- Questions rédigées par IA puis vérifiées automatiquement contre les passages attendus ; contrôle humain partiel.
- « Fait attendu » vérifié par simple présence d'une expression : une paraphrase correcte peut être comptée fausse.
- Le principal défaut est la **prudence** du modèle local (19 % de refus à tort), pas l'invention : 1 seule
  réponse donnée sur 12 questions hors corpus. Un modèle plus grand (Claude, via le même routeur) réduirait
  vraisemblablement les refus à tort - non mesuré.
- Le détail question par question est dans `eval/runs/`.

## 2026-11-09 - Modèle via clé API (openai/gpt-5.1)

Configuration figée avant la mesure (`config/eval_frozen_api.yaml`) : mêmes réglages de recherche que la
configuration locale (vectorielle, bge-m3, 8 passages, seuil 0,45), seul le modèle qui rédige change.
Jeu de réglage : 30/32. Mesure unique sur le jeu de test (48 questions) :

| Indicateur | Local (qwen3.5 9B) | Clé API (gpt-5.1) |
|---|---|---|
| Global | 38/48 - 79 % (IC 95 % : 66-88 %) | **43/48 - 90 % (IC 95 % : 78-96 %)** |
| Bonne source citée | 27/36 | 32/36 - 89 % |
| Faux refus | 7/36 | 1/36 - 3 % |
| Mauvaise source | - | 3/36 - 8 % |
| Refus corrects hors corpus | 11/12 | 11/12 - 92 % |
| Temps moyen par question | - | 3,1 s |

Lecture : le gain vient surtout des faux refus (7 → 1) ; le grand modèle exploite mieux les passages retrouvés.
Les intervalles se recouvrent : l'amélioration est probable, pas démontrée avec 48 questions.
Les missions confidentielles restent sur le modèle local, quel que soit ce résultat.
