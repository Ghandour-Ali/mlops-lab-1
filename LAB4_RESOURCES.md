# Isolation et retrait du Lab 4

Le Lab 4 a été développé et testé séparément, puis fusionné dans `main` à la demande de l'utilisateur (commit de fusion `3462623`). Les quatre labs sont maintenant réunis dans `.verification/lab2-work`. Les conteneurs et le volume du Lab 4 gardent les mêmes noms ; le modèle original reste préservé.

## Ressources propres au lab

| Ressource | Nom |
| --- | --- |
| Projet Compose | `food11-lab4` |
| Conteneurs | `food11-lab4-mlflow-1`, `food11-lab4-inference-1`, `food11-lab4-frontend-1` |
| Réseau | `food11-lab4_default` |
| Volume persistant | `food11-lab4_mlflow-data` |
| Images locales | `food11-lab4-mlflow:local`, `food11-lab4-inference:local`, `food11-lab4-frontend:local` |
| Ports hôte | `127.0.0.1:5500`, `127.0.0.1:8501` |
| Ressources temporaires de test | `food11-lab4-no-volume-check`, `food11-lab4-startup-failure-check`, projet `food11-lab4-persistence-check`, port 5501 ; supprimées après les tests |
| Fichiers ajoutés | `docker-compose.yml`, `frontend/`, `mlflow/`, `lab4.md`, `Labs.md/lab4.md`, `start-lab4.cmd`, ce document, `scripts/bootstrap_lab4.ps1`, `scripts/seed_lab4.py`, `scripts/verify_lab4.py`, `scripts/capture_lab4.py`, `reports/lab4/` |
| Fichiers adaptés sur cette branche | `README.md`, `src/food11/serve.py` (version chargée observable) |

## Arrêter sans perdre les modèles

Depuis le dossier du Lab 4 :

```powershell
docker compose down
```

Pour reprendre : `docker compose up -d --wait`.

## Supprimer le Lab 4, seulement si cela est demandé

Ces commandes sont documentées ; elles ne sont pas exécutées pour livrer le lab.

1. Dans le worktree Lab 4, `docker compose down -v` supprime ses trois conteneurs, son réseau et **son seul volume**. Les copies du modèle et les versions créées dans ce volume sont alors perdues.
2. Supprimer uniquement les trois tags `food11-lab4-*:local` avec `docker image rm` ; ne pas utiliser `docker system prune` ou `docker volume prune`.
3. Depuis le dépôt d'origine, vérifier et retirer le worktree `../lab4-work` avec `git worktree remove ../lab4-work`. Si des fichiers locaux ignorés subsistent, les examiner avant tout retrait forcé.
4. Retirer la branche locale `lab4` et, si elle a été publiée, la branche distante `lab4`. Aucune réécriture de `main` n'est nécessaire.

Les images Docker Hub `ghandourali/food11-api`, le conteneur `food11-api`, la base `lab2-work/mlflow.db`, ses dossiers d'artefacts et les données DVC ne font pas partie des ressources à supprimer. Le cache de construction Docker peut contenir des couches partagées ; il n'est pas purgé automatiquement.
