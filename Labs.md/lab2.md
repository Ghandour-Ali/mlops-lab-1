# Lab 2 - Entraînement et suivi des expériences avec MLflow

## Mise en place de l'environnement

Les dépendances suivantes ont été ajoutées au projet avec `uv` :

- `mlflow`
- `torch`
- `torchvision`
- `scikit-learn`

Comme l'entraînement est réalisé sur CPU, `torch` et `torchvision` utilisent l'index CPU de PyTorch. La configuration correspondante se trouve dans `pyproject.toml`. Docker et Docker Compose sont également installés et disponibles.

## Question 1
**En regardant `pyproject.toml` et `uv.lock`, qu'est-ce qui a changé ?**

Réponse :

`pyproject.toml` contient maintenant les quatre dépendances nécessaires au lab, avec leurs contraintes de version. Il contient aussi une source explicite `pytorch-cpu` pour éviter l'installation de la version CUDA.

`uv.lock` a été généré ou mis à jour par `uv`. Il enregistre les versions exactes des dépendances directes et transitives afin que l'environnement soit reproductible sur une autre machine.

Les imports ont été vérifiés avec les versions suivantes :

```text
mlflow      3.16.0
torch       2.14.0+cpu
torchvision 0.29.0+cpu
scikit-learn 1.9.1
```

## Serveur de suivi MLflow

Le serveur local a été lancé avec :

```powershell
uv run mlflow server --host 127.0.0.1 --port 5000 `
  --backend-store-uri sqlite:///mlflow.db `
  --default-artifact-root ./mlruns
```

L'interface est accessible à l'adresse : `http://127.0.0.1:5000`.

## Question 2
**À quoi servent `--backend-store-uri` et `--default-artifact-root` ? Quelle est la différence entre les métadonnées et les artifacts ?**

Réponse :

`--backend-store-uri` indique où MLflow stocke les métadonnées de suivi : expériences, runs, paramètres, métriques, tags et références vers les artifacts. Dans ce lab, ces métadonnées sont stockées dans la base SQLite `mlflow.db`.

`--default-artifact-root` indique l'emplacement où MLflow stocke les fichiers produits par les runs. Ici, les artifacts sont placés dans le dossier local `mlruns/`.

Les métadonnées décrivent l'exécution et ses résultats sous forme structurée. Les artifacts sont les fichiers associés au run, par exemple un modèle entraîné, un fichier de configuration ou un rapport.

## Question 3
**Pourquoi `mlflow.db` et `mlruns/` ne doivent-ils être suivis ni par Git ni par DVC ?**

Réponse :

Ces éléments sont des sorties locales du serveur MLflow. Ils peuvent devenir volumineux, être modifiés automatiquement à chaque run et contenir des chemins ou des informations propres à la machine utilisée.

Ils ne font pas partie du code source ni du dataset de référence. Les versionner avec Git créerait du bruit dans l'historique et des conflits fréquents. Les suivre avec DVC mélangerait les résultats d'expériences avec les données d'entraînement. Ils sont donc exclus de Git avec :

```text
mlflow.db
mlruns/
```

## Question 4
**Que se passe-t-il lors du premier appel à `mlflow.set_experiment` avec un nom inexistant ?**

Réponse :

MLflow crée automatiquement une nouvelle expérience portant ce nom. Dans ce lab, l'appel :

```python
mlflow.set_experiment("food11")
```

a créé l'expérience `food11`, visible ensuite dans l'interface MLflow. Les runs suivants sont associés à cette expérience au lieu de l'expérience `Default`.

## Préparation des données

Le dataset disponible était organisé sous forme de fichiers nommés, par exemple `0_0.jpg`, directement dans les dossiers `training`, `validation` et `evaluation`. Cette structure n'est pas suffisante pour `torchvision.datasets.ImageFolder`, qui attend un dossier par classe.

Le script `src/food11/prepare_mini.py` prépare donc une version réduite sous la forme :

```text
data/food11_processed_mini/
├── training/0 ... training/10
├── validation/0 ... validation/10
└── evaluation/0 ... evaluation/10
```

Le script utilise des hardlinks lorsque le système le permet, afin d'éviter une copie inutile des images. Le mini-dataset préparé contient 11 classes et environ 100 images par classe et par split.

## Entraînement

Le script `src/food11/train.py` :

- charge les données avec `ImageFolder` et `DataLoader` ;
- utilise un `resnet18` pré-entraîné ;
- remplace sa dernière couche pour produire 11 classes ;
- accepte `--dataset`, `--epochs`, `--lr` et `--batch-size` ;
- utilise le CPU lorsqu'aucun GPU CUDA n'est disponible ;
- enregistre les paramètres et les métriques dans MLflow ;
- enregistre le modèle final comme artifact MLflow.

Exemple d'exécution :

```powershell
uv run python src/food11/train.py `
  --dataset mini --epochs 5 --lr 0.001 --batch-size 32
```

## Question 5
**Quelle est la différence entre `mlflow.log_param` et `mlflow.log_metric` ? Pourquoi `log_metric` utilise-t-il `step` ?**

Réponse :

Un paramètre est une valeur fixée pour une exécution, par exemple le learning rate, la taille des batches ou le nombre d'époques. Il est enregistré avec `mlflow.log_param` ou `mlflow.log_params`.

Une métrique est une valeur mesurée pendant ou après l'entraînement, par exemple la loss ou l'accuracy. Elle peut être enregistrée plusieurs fois avec `mlflow.log_metric`.

Le paramètre `step` indique la position de la mesure dans le temps, ici le numéro de l'époque. MLflow peut ainsi afficher l'évolution de `train_loss`, `val_loss` et `val_accuracy` sous forme de courbes. Un paramètre n'évolue pas au cours du run, donc il n'a pas besoin de `step`.

## Question 6
**Où trouve-t-on les paramètres, les courbes de métriques et le modèle ? Où le modèle est-il stocké ?**

Réponse :

Dans MLflow, il faut ouvrir l'expérience `food11`, puis l'onglet **Training runs** et sélectionner un run. La page du run affiche :

- les paramètres : dataset, epochs, learning rate, batch size et device ;
- les métriques : `train_loss`, `val_loss`, `val_accuracy`, `test_loss` et `test_accuracy` ;
- le modèle enregistré dans la section des artifacts du run.

Avec MLflow 3.16, l'artifact de modèle est géré dans le stockage local de l'expérience sous `mlruns/1/models/`. Les métadonnées du run restent référencées par `mlflow.db`.

Un run réussi utilisé pendant le lab est :

```text
Run ID: 05211f2bf57a46bc9cb56d383dd5cf18
```

## Question 7
**Quelle learning rate a donné la meilleure `val_accuracy` ? Est-ce que plus élevé est toujours meilleur ?**

Réponse :

Les trois premiers essais ont permis de comparer plusieurs valeurs. Les métriques enregistrées étaient :

```text
lr=0.001   val_accuracy=0.4352  run interrompu lors du premier log du modèle
lr=0.001   val_accuracy=0.3714  run interrompu lors du second test de logging
lr=0.001   val_accuracy=0.2527  run terminé avec modèle enregistré
```

Ces essais ne constituent pas encore une comparaison propre de plusieurs learning rates, car les deux premières exécutions ont échoué pendant l'enregistrement du modèle et utilisaient la même valeur de `lr`. La valeur `0.001` est celle testée avec succès, mais il faut lancer les essais `0.01`, `0.001` et `0.0001` prévus par l'énoncé pour tirer une conclusion fiable.

Une learning rate plus élevée n'est donc pas toujours meilleure. Une valeur trop élevée peut rendre l'optimisation instable, tandis qu'une valeur trop faible peut ralentir l'apprentissage.

## Question 8
**Quel motif observe-t-on avec `lr`, `batch_size` et `val_accuracy` dans le graphique de coordonnées parallèles ?**

Réponse :

Le graphique permet de relier les choix d'hyperparamètres aux résultats. Il faut comparer des runs terminés avec le même dataset et le même nombre d'époques. En général, le meilleur compromis est celui qui relie une learning rate stable et une taille de batch adaptée à la quantité de données disponible.

Sur ce mini-dataset, il ne faut pas conclure qu'un seul hyperparamètre explique toujours le résultat : l'interaction entre learning rate, batch size et durée d'entraînement peut modifier fortement la validation.

## Question 9
**Quel est le meilleur run après un tri décroissant par `val_accuracy` ?**

Réponse :

Dans l'état actuel, le meilleur score de validation enregistré est `0.4352`, associé au run :

```text
e9b8e1e9ac044eda9f559745f2ec146c
```

Cependant, ce run est marqué comme échoué parce qu'il a été créé avant la correction du format de sauvegarde MLflow. Le meilleur run terminé correctement est :

```text
Run ID: 05211f2bf57a46bc9cb56d383dd5cf18
val_accuracy: 0.2527
test_accuracy: 0.2673
```

Pour répondre définitivement à la question, il faut comparer les quatre exécutions complètes recommandées dans l'énoncé après la correction du logging du modèle.

## Versionnement du code

Le code et les dépendances du lab ont été commités et poussés avec :

```text
6eccf89 Start Lab 2 MLflow training
```

Les runs, métriques et artifacts restent dans MLflow. Le code reste versionné par Git, tandis que les datasets restent gérés par DVC.
