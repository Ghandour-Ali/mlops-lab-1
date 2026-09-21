# Lab 2 — Entraînement et suivi des expériences avec MLflow

Les quatre expériences ci-dessous ont été exécutées le 17 septembre 2026 et
vérifiées dans MLflow. Elles utilisent ResNet18 pré-entraîné, 11 classes,
le même mini-dataset, cinq époques, Adam et la graine 42, sur CPU (4 threads).
Le groupe MLflow est `lab2-completion-2026-09-17` dans l'expérience `food11`.

## Question 1 — Dépendances et verrouillage

`pyproject.toml` déclare MLflow, torch, torchvision et scikit-learn.
L'index explicite `pytorch-cpu` fournit torch et torchvision pour CPU.
Pillow est utilisé pour préparer les images ; NumPy et Matplotlib servent
à vérifier les modèles et produire le graphique comparatif.
`uv.lock` fixe les versions et les empreintes des dépendances directes et
transitives. L'environnement est réinstallable avec `uv sync --locked`.
Versions utilisées : MLflow 3.16.0, torch 2.14.0+cpu,
torchvision 0.29.0+cpu, scikit-learn 1.9.1.

## Question 2 — Serveur, métadonnées et artifacts

Le serveur est lancé depuis la racine du projet :

```powershell
uv run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --workers 1
```

`--backend-store-uri` désigne le stockage des métadonnées : expériences,
statuts, paramètres, métriques, tags et références des modèles. Ici, il s'agit
de SQLite dans `mlflow.db`. `--default-artifact-root` désigne le stockage des
fichiers produits : modèles, environnements et graphiques, ici sous `mlruns/`.
L'interface locale est http://127.0.0.1:5000.

## Question 3 — Exclusions de Git et DVC

`mlflow.db` et `mlruns/` sont des sorties de suivi modifiées à chaque exécution,
potentiellement volumineuses et liées à l'installation locale. Git conserve
le code et le compte rendu ; MLflow gère les expériences. Les suivre également
avec DVC dupliquerait cette responsabilité et mélangerait les expériences
avec les datasets de référence. Ces chemins sont ignorés par Git et ne sont
déclarés dans aucun fichier DVC. Les fichiers SQLite temporaires, `.venv/`
et `local_results/` sont également ignorés.

## Question 4 — Création de l'expérience

`mlflow.set_experiment("food11")` crée l'expérience si elle n'existe pas,
puis l'active pour les nouveaux runs. Sa création a été observée lors du
premier entraînement ; son identifiant dans ce serveur est `1`.

## Préparation et protocole

`src/food11/prepare_mini.py` sélectionne les 100 premiers noms triés par classe
et par split, ou tous les fichiers si la classe en contient moins. Il conserve
les splits officiels, convertit en RGB, redimensionne à 128×128 avec Lanczos,
et écrit les images JPEG (qualité 95) dans des dossiers portant les noms des
catégories. Le mini-dataset contient 1 100 images d'entraînement,
1 096 de validation et 1 096 d'évaluation. Les classes Rice de validation
et d'évaluation contiennent chacune 96 images.

Les 3 292 images régénérées ont été comparées octet par octet au mini-dataset
utilisé pour ces expériences : elles sont identiques. Empreinte du dataset
(chemins relatifs triés et SHA-256 des fichiers) :

```text
52c6203b8b36096e266cda5d2e129633733de8daae33aa3517f7f8fa30e6571c
```

Pendant l'entraînement, les transformations des poids pré-entraînés produisent
des tenseurs normalisés 224×224. `ImageFolder` et `DataLoader` chargent les images.
La dernière couche de ResNet18 est remplacée par une couche à 11 sorties et
tous les paramètres du réseau sont entraînés. La correspondance `class_to_idx`
est vérifiée entre les splits et enregistrée comme artifact.

## Question 5 — Paramètres, métriques et step

Un paramètre est une configuration fixe du run : `lr`, `batch_size`, `epochs`,
dataset, architecture, device ou seed. `mlflow.log_params` les enregistre au début.
Une métrique est une mesure : loss ou accuracy. Elle peut évoluer.
`mlflow.log_metrics(..., step=epoch)` enregistre `train_loss`, `val_loss`
et `val_accuracy` aux steps 0 à 4. Le step permet de tracer leur évolution
et de comparer les mêmes époques. `test_accuracy` et `test_loss` sont enregistrées
après l'entraînement, sur le split evaluation.

## Question 6 — Consulter et retrouver le modèle

Dans MLflow, ouvrir `food11`, puis le run pour voir ses paramètres et ses courbes.
Le modèle sauvegardé est lié au run et consultable dans les modèles/artifacts.
Avec cette version de MLflow, les modèles ont leur propre identifiant `m-...`.
Celui du meilleur run est `m-8e427b8761db489ab128445e3ea91675` et son emplacement réel est :

```text
file:///C:/Users/user/Documents/Mlopslab1/.verification/lab2-work/mlruns/1/models/m-8e427b8761db489ab128445e3ea91675/artifacts
```

La sauvegarde utilise `mlflow.pytorch.log_model` avec un exemple d'entrée
et `serialization_format="pickle"`. Chaque modèle de cette comparaison a été
rechargé et testé : sortie de forme `(1, 11)` et valeurs finies. Il faut conserver
la base `mlflow.db` et les fichiers `mlruns/` pour les retrouver au prochain lab.

## Question 7 — Comparaison des learning rates

Résultats finaux, triés par accuracy de validation (valeurs entre 0 et 1) :

| Run ID | lr | Batch size | val_accuracy | test_accuracy | Statut |
| --- | ---: | ---: | ---: | ---: | --- |
| `3acfe1a891994c78b89de31feb99ef30` | 0.0001 | 32 | 0.8102 | 0.8321 | FINISHED |
| `e8ad814f169b4992a7ad3c750a403e1b` | 0.001 | 64 | 0.5839 | 0.5976 | FINISHED |
| `106b40073a9346b1bd7384429f290a7b` | 0.001 | 32 | 0.5639 | 0.5721 | FINISHED |
| `dc69705a3a9046218fae6a7904851474` | 0.01 | 32 | 0.1414 | 0.1560 | FINISHED |

À batch size 32 et cinq époques, la meilleure learning rate testée est
**0.0001**, avec **81.02 %** de validation.
Une learning rate plus élevée n'est pas systématiquement meilleure : les
valeurs observées ci-dessus doivent être comparées à protocole identique.
Ces quatre runs ne permettent pas de conclure à un optimum général pour Food-11.

## Question 8 — Coordonnées parallèles

Le graphique `comparison/parallel_coordinates.png` est enregistré comme artifact
du meilleur run. Il relie `lr` (axe logarithmique), `batch_size` et `val_accuracy`,
avec chaque axe normalisé pour la visualisation. Les étiquettes donnent les
configurations réelles. On peut également sélectionner ces quatre runs dans
l'interface MLflow, cliquer sur **Compare** et choisir ces trois axes.

À `lr=0.001`, passer de batch size 32 à 64 fait passer `val_accuracy` de
**0.5639** à **0.5839**,
soit **+2.01 points de pourcentage**.
Les trois lignes à batch size 32 montrent séparément l'effet du learning rate.
La meilleure combinaison observée est `lr=0.0001`, `batch_size=32`.
Il s'agit d'une observation avec une seule graine et cinq époques, pas d'une
preuve que cette combinaison sera toujours la meilleure.

## Question 9 — Meilleur run pour le prochain lab

Après tri décroissant de la **val_accuracy finale** parmi les quatre runs
terminés de ce groupe :

```text
Run ID: 3acfe1a891994c78b89de31feb99ef30
Model URI: models:/m-8e427b8761db489ab128445e3ea91675
val_accuracy: 0.810219
test_accuracy: 0.832117
```

L'accuracy de test est rapportée après sélection ; elle ne sert pas à choisir
le meilleur modèle. Le fichier local `local_results/comparison.json` et son
artifact MLflow conservent les quatre identifiants et leurs résultats.

## Vérifications et reproduction

Les quatre runs ont le statut FINISHED, cinq points par métrique d'époque,
une accuracy finale de test et un modèle rechargé avec succès. Le premier
run avait terminé calcul et sauvegarde mais rencontré une erreur d'affichage
Unicode Windows au moment de sa clôture. Après vérification des métriques et
rechargement du modèle, son statut a été finalisé ; un tag documente cette
récupération. Le script corrige l'encodage pour les exécutions suivantes.

Pour refaire la comparaison, après préparation du dataset et démarrage du serveur :

```powershell
uv run python src/food11/compare_runs.py --group lab2-comparison --epochs 5 --run-missing
```

Le code et ce rapport sont versionnés dans Git. La base de suivi et les modèles restent dans MLflow. Des exports statiques des résultats et graphiques sont aussi publiés ci-dessous pour la correction à distance.


## Résultats consultables directement sur GitHub

- [Tableau des runs et scores (JSON)](reports/lab2/comparison.json)
- [Métriques des cinq époques (CSV)](reports/lab2/metrics.csv)

![Courbes d'apprentissage](reports/lab2/learning_curves.png)

![Coordonnées parallèles](reports/lab2/parallel_coordinates.png)

Ces exports proviennent de la base MLflow locale. Le professeur peut les consulter sans serveur MLflow ; les fichiers des modèles et la base SQLite restent locaux conformément à l'énoncé.
