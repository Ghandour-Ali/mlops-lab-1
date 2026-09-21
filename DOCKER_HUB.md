# Utiliser l'image Food-11 depuis Docker Hub

Dépôt : [ghandourali/food11-api](https://hub.docker.com/r/ghandourali/food11-api).

## Télécharger l'image

```powershell
docker pull ghandourali/food11-api:lab3-7ab74c2
```

Le tag `lab3-7ab74c2` identifie la livraison du lab 3 ; `latest` désigne la
dernière image publiée. La plateforme de cette image est **Linux AMD64**.

Les deux tags ont été vérifiés publiquement et correspondent à l'image testée
pendant le lab. Pour télécharger exactement cette livraison, indépendamment
de futurs changements de tags :

```powershell
docker pull ghandourali/food11-api@sha256:bdcc0239051d13ace6ef3be079a9e510cd8384ba86ae36c744c69caeac458a0f
```

[Preuve de publication et de vérification](reports/lab3/dockerhub.json).

## Préparer MLflow

L'image contient le code et les dépendances, pas les poids du modèle.
Elle charge `models:/food11@champion` au démarrage, ainsi que le fichier
`class_to_idx.json` du run associé. Le serveur doit servir ces artifacts par
HTTP ou par un stockage accessible depuis le conteneur ; un chemin Windows
`file:///C:/...` ne convient pas.

Sur la machine du lab, depuis la racine du projet, laisser ouvert :

```powershell
.\scripts\start_mlflow_serving.ps1
```

Sur une autre machine, configurer un serveur MLflow contenant le modèle
enregistré et adapter `MLFLOW_TRACKING_URI` à son adresse. Télécharger l'image
Docker ne télécharge pas la base MLflow de l'auteur.

## Démarrer et tester

Sur Windows ou macOS avec Docker Desktop :

```powershell
docker run -d --name food11-hub -p 127.0.0.1:8003:8000 -e MLFLOW_TRACKING_URI=http://host.docker.internal:5002 ghandourali/food11-api:lab3-7ab74c2
```

Ouvrir http://127.0.0.1:8003/docs, puis `POST /predict`, `Try it out`, choisir
une image et cliquer sur `Execute`. Le port 8003 évite le conteneur du lab
déjà disponible sur 8002. Pour arrêter cette instance :

```powershell
docker stop food11-hub
```

Sous Linux Engine, ajouter `--add-host=host.docker.internal:host-gateway`
si MLflow tourne sur l'hôte, et vérifier que son adresse et son port sont
accessibles depuis le réseau Docker.

Docker Hub distribue l'image ; il n'héberge pas une API de prédiction en direct.
Pour déployer un service public, il faut aussi une machine d'exécution et un
serveur MLflow accessible.
