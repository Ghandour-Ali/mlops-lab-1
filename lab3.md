# Lab 3 — Modèle Food-11, API et Docker

## Objectif et continuité

Le lab 1 prépare et versionne les images. Le lab 2 entraîne ResNet18 et compare
les expériences. Le lab 3 transforme le meilleur modèle en service HTTP,
chargeable depuis le registre MLflow, puis exécutable dans un conteneur Linux.

Le run d'entraînement retenu est `3acfe1a891994c78b89de31feb99ef30` :
validation **81,02 %**, test **83,21 %**. Les fichiers des modèles et les bases
MLflow restent hors Git ; le code, les réponses et les preuves de test sont publiés.

## Q1 — Modèle enregistré et artifact d'un run

Le premier enregistrement de `food11` a créé la **version 1**, statut READY.
L'artifact d'un run est le modèle sauvegardé par une exécution déterminée.
Le Model Registry lui donne un nom partagé, des versions, des descriptions,
des tags et des aliases, indépendamment de la liste des expériences.

La version 1 utilisait un chemin `file:///C:/...`, inaccessible à un conteneur
Linux. Le script `scripts/prepare_serving_model.py` a donc republié les mêmes
poids via le proxy HTTP MLflow et créé la **version 2**. Les tenseurs des deux
versions ont été comparés : ils sont identiques. Le run de publication est
distinct d'un entraînement et conserve le run source dans ses tags.
Voir [les preuves du registre](reports/lab3/registry.json).

## Q2 — Aliases et versions

Les anciens stages intégrés `Staging` et `Production` sont dépréciés.
Les aliases sont des noms définis par l'utilisateur, par exemple `champion`
ou `challenger` ; ce ne sont pas deux nouvelles étapes imposées par MLflow.
Ils pointent vers une version et peuvent être réaffectés sans modifier les poids
ni le numéro de version. Les tags fournissent des annotations supplémentaires.

`champion` a d'abord désigné la version 1, puis la version 2 publiée via HTTP.
Versionner séparément permet de gérer le modèle livré à l'API, tout en conservant
le lien vers le run qui a produit ses poids.

## Q3 — Charger une URI MLflow

`src/food11/serve.py` utilise
`mlflow.pyfunc.load_model("models:/food11@champion")` une fois au démarrage.
MLflow résout le registre et récupère le modèle et ses métadonnées ; aucun chemin
Windows ni fichier `.pth` n'est codé en dur. La correspondance des catégories
vient de `class_to_idx.json`, associé au run du modèle effectivement chargé.

Pour servir une nouvelle version compatible, on réaffecte `champion`, puis on
redémarre l'API : les processus déjà lancés conservent leur modèle en mémoire.
Aucune reconstruction de l'image n'est nécessaire si le prétraitement, la
signature et les dépendances restent compatibles. Un changement incompatible
nécessiterait une adaptation du code et une nouvelle image.

## Q4 — Ordre des couches et cache

Le Dockerfile copie `pyproject.toml` et `uv.lock`, puis installe les dépendances
avec `uv sync --frozen --no-dev --no-install-project`. Cette dernière option
permet d'installer les dépendances alors que les sources du projet ne sont pas
encore copiées. L'application est ensuite importée directement depuis `/app/src`.

Une modification de `serve.py` invalide la couche de copie des sources et les
étapes suivantes, mais pas l'installation des dépendances. Changer le lockfile
invalide cette installation. Le builder contient uv et l'environnement Python ;
le runtime ne récupère que l'environnement et le code. Le cache uv de BuildKit
n'est pas inclus dans l'image finale.

## Q5 — Taille des images et docker history

Les mesures réelles sont enregistrées dans [docker-images.json](reports/lab3/docker-images.json)
et les couches dans [history-multi.txt](reports/lab3/history-multi.txt) et
[history-single.txt](reports/lab3/history-single.txt).

| Image | Taille rapportée par `docker image inspect` | Mo décimaux |
| --- | ---: | ---: |
| Multi-stage | 443 411 589 octets | 443,41 |
| Single-stage | 467 166 498 octets | 467,17 |

Gain observé : **23 754 909 octets, soit environ 5,08 %**. Il s'agit des tailles
rapportées par le moteur Docker local, pas de l'espace disque supplémentaire
entre deux images partageant des couches.
`Dockerfile.single` sert de référence à une seule étape. Pour comparer le coût
du découpage, les deux recettes utilisent la même base Python slim et les mêmes
dépendances verrouillées. La référence conserve uv dans son image finale.
Les paquets scientifiques, notamment PyTorch, restent nécessaires dans les deux
images : le multi-stage ne supprime pas leur poids.
`docker history` montre notamment **1,49 Go pour la couche de l'environnement
Python** dans l'image finale. Les tailles des couches décompressées ne doivent
pas être confondues avec la valeur `.Size` ci-dessus rapportée par ce moteur.

```powershell
docker build -t food11-api:latest .
docker build -f Dockerfile.single -t food11-api:single .
docker image inspect food11-api:latest food11-api:single
docker history food11-api:latest
docker history food11-api:single
```

## Q6 — Rôle de .dockerignore

Le fichier utilise une liste d'inclusion : seuls les Dockerfiles, les deux fichiers
de dépendances et `src/` entrent dans le contexte ; les bytecodes Python sont exclus.
Ainsi `.venv`, `data`, `.git`, `.dvc`, `mlruns`, `mlartifacts` et les bases SQLite
ne sont pas transférés au builder.

Sans exclusions, le contexte peut devenir très volumineux et contenir des secrets
ou des fichiers verrouillés. Envoyer un fichier ne l'intègre pas automatiquement
à l'image : seules les instructions COPY/ADD le font. Avec `COPY . .`, copier
une `.venv` Windows sur l'environnement Linux peut casser ses exécutables et ses
bibliothèques. Les gros datasets ralentissent les transferts et peuvent remplir
le disque ; leur simple présence n'entraîne pas systématiquement un échec.

## Q7 — Réseau du conteneur et serveur MLflow

En réseau bridge, `127.0.0.1` désigne le conteneur lui-même. Sous Docker Desktop,
`host.docker.internal` résout vers une adresse de l'hôte accessible depuis le
conteneur. La variable `MLFLOW_TRACKING_URI` configure cette connexion.
Sous Linux Engine, on peut ajouter `--add-host=host.docker.internal:host-gateway`,
ou utiliser le réseau host lorsque c'est approprié.

Le serveur du lab 2 reste sur 5000. Un serveur partageant la même base de données
est lancé sur **5002**, avec accès réseau et proxy d'artifacts :

```powershell
.\scripts\start_mlflow_serving.ps1
```

Les nouveaux artifacts utilisent `mlflow-artifacts:/` et sont stockés dans
`mlartifacts/`. Le script de publication crée une nouvelle expérience avec ce
stockage ; changer seulement les options du serveur ne convertit pas les URIs
`file:///` déjà enregistrées. La liste des hôtes autorisés inclut explicitement
`host.docker.internal`, sans désactiver le middleware de sécurité.

Ce serveur est prévu pour le lab sur une machine de développement. Un déploiement
partagé nécessiterait notamment authentification, TLS et stockage persistant.

## Q8 — Nouveau conteneur, même image

L'image embarque Python, les dépendances et le code. Les poids et les catégories
sont téléchargés au démarrage depuis MLflow. Un nouveau conteneur peut donc
charger le champion sans reconstruire l'image, à condition que MLflow et les
artifacts restent accessibles. Ce n'est pas une application autonome hors ligne.

Le contrôle consiste à tester un premier conteneur, l'arrêter, en créer un
second depuis le même identifiant d'image, sans volume de modèle, puis refaire
les requêtes. Les fichiers `reports/lab3/container-*.json` conservent les résultats.
**Ce contrôle a réussi** : les deux conteneurs ont exactement le même identifiant
d'image, aucun montage, et les onze prédictions sont identiques après recréation.
La comparaison avec l'API Windows donne les mêmes catégories et un écart maximal
de confiance de **5,96 × 10⁻⁸**. Voir [restart-check.json](reports/lab3/restart-check.json).
Les prédictions doivent être comparables ; une prédiction n'est pas forcément
correcte et le score softmax n'est pas une garantie de justesse.

## Q9 — Partager exactement l'image construite

Git versionne la recette, pas les couches binaires. Il reste à pousser l'image
dans un registre tel que GHCR ou Docker Hub, à donner accès aux machines cibles
et à déployer une référence immuable `nom@sha256:...` plutôt que seulement `latest`.
L'architecture doit être compatible. Les machines cibles doivent aussi pouvoir
joindre MLflow et son stockage. Pour figer totalement le comportement, il faut
également figer la version du modèle : un alias mutable ne garantit pas le même
modèle lors d'un prochain démarrage.

Ce lab construit et teste les images localement ; aucune publication dans un
registre d'images n'est présentée comme réalisée.

## Reproduire sur la machine du lab

Depuis la racine du projet, avec Docker Desktop démarré :

```powershell
uv sync --locked
# Terminal 1 : laisser ouvert
.\scripts\start_mlflow_serving.ps1
```

Dans un deuxième terminal :

```powershell
uv run python scripts/prepare_serving_model.py
docker build -t food11-api:latest .
docker run -d --name food11-api -p 127.0.0.1:8002:8000 -e MLFLOW_TRACKING_URI=http://host.docker.internal:5002 food11-api:latest
uv run python scripts/test_serving.py --url http://127.0.0.1:8002
```

Ouvrir http://127.0.0.1:8002/docs pour envoyer une image à `/predict`.
`GET /health` retourne `{"status":"ok"}` après chargement réussi du modèle.
Le port hôte 8002 évite les services déjà présents sur 8000 et 8001 ; le port
interne demandé par le lab reste 8000. Ne pas relancer `docker run` avec le même
nom si le conteneur existe déjà ; utiliser `docker start food11-api`.

Sur une autre machine, un clone Git ne restaure pas le registre et ses modèles.
Il faut un serveur MLflow accessible qui contient `food11@champion`, ou refaire
le lab 2 puis enregistrer et publier son modèle. Les rapports et preuves exportées
restent lisibles sur GitHub sans exécuter ces services.

## Vérifications réalisées le 21 septembre 2026

| Contrôle | Résultat et preuve |
| --- | --- |
| Registre et poids | Versions 1 et 2 identiques, alias `champion` vers 2 : [registre](reports/lab3/registry.json) |
| API locale | `/health`, 11 images et 4 requêtes invalides : [résultats locaux](reports/lab3/local-api-tests.json) |
| Premier conteneur | Mêmes contrôles HTTP : [résultats](reports/lab3/container-first.json) |
| Nouveau conteneur | Même image, poids retéléchargés, mêmes réponses : [résultats](reports/lab3/container-restarted.json) |
| Comparaison | Même classement local/Docker, prédictions identiques entre conteneurs : [preuve](reports/lab3/restart-check.json) |
| Contenu de l'image | Aucun dataset, poids ou registre MLflow embarqué : [preuve](reports/lab3/image-content-check.json) |
| Cache | Après modification de `serve.py`, étape `uv sync` marquée CACHED : [journal](reports/lab3/build-multi.txt) |
| Images | Deux recettes construites, tailles et identifiants mesurés : [mesures](reports/lab3/docker-images.json) |

Les images d'aperçu servent à vérifier le fonctionnement de l'API ; ces onze
requêtes ne constituent pas une nouvelle mesure d'accuracy sur le jeu de test.
Le conteneur final `food11-api` est laissé actif et son healthcheck Docker est
`healthy`. Le script [verify_docker.py](scripts/verify_docker.py) conserve la
procédure de mesure et de recréation ; ses deux noms de conteneurs doivent être
libres pour relancer une vérification complète.

## Références

- [Construction Docker avec uv](https://docs.astral.sh/uv/guides/integration/docker/)
- [Serveur de suivi MLflow et proxy d'artifacts](https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/)
