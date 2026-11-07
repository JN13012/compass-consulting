# Modèles locaux avec Ollama (Windows + WSL)

Compass tourne dans Docker sous WSL ; Ollama tourne sous Windows pour profiter du GPU.

## 1. Lancer Ollama sous Windows, accessible depuis WSL

Par défaut Ollama n'écoute que `127.0.0.1` (invisible depuis WSL). Dans PowerShell :

```powershell
$env:OLLAMA_HOST = "0.0.0.0:11434"; ollama serve
```

(Fermer d'abord l'icône Ollama de la barre des tâches si elle est lancée. Windows peut demander d'autoriser
Ollama dans le pare-feu : réseaux privés uniquement.)

## 2. Modèles

```powershell
ollama pull qwen3.5:9b   # réponses (≈ 6,6 Go)
ollama pull bge-m3       # embeddings, recherche par le sens (≈ 1,2 Go)
```

## 3. Adresse vue depuis WSL

```bash
ip route | awk '/default/{print $3}'      # ex. 172.26.48.1 (peut changer après un redémarrage)
curl http://172.26.48.1:11434/api/version
```

Reporter l'adresse dans `.env` :

```
KB_ROLE=local
OLLAMA_BASE_URL=http://172.26.48.1:11434
```

puis `docker compose up -d api`.

## 4. Calculer les embeddings (une fois, puis après chaque ingestion)

```bash
docker compose exec api python -m app.corpus embed
```

Seuls les passages sans vecteur sont calculés : la commande peut être relancée sans risque.
La recherche passe automatiquement en mode hybride dès que des vecteurs existent.
