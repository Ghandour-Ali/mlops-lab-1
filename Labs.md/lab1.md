# Lab 1 - DVC

## Question 1
Après `uv init`, quels fichiers ont été créés et à quoi servent-ils ?

Réponse :

`uv init` crée les fichiers de base du projet Python :

- `pyproject.toml` : contient les informations du projet et les dépendances.
- `.python-version` : indique la version de Python utilisée.
- `README.md` : décrit le projet.
- `.gitignore` : indique à Git quels fichiers ne doivent pas être suivis.

## Question 2
Après `dvc init`, quels fichiers ont été créés ? À quoi servent-ils ? Lesquels doivent être envoyés sur Git ?

Réponse :

Après `dvc init`, DVC crée principalement :

- `.dvc/` et `.dvc/config` : configuration DVC du dépôt.
- `.dvc/.gitignore` : fichiers internes ignorés par Git.
- `.dvcignore` : fichiers ignorés par DVC.

La configuration non sensible et `.dvcignore` doivent être versionnés avec Git. Les credentials ne doivent jamais être ajoutés au dépôt.

## Question 3
Lorsqu'on ajoute DagsHub comme remote DVC, où sont stockés les credentials ? Quelles sont les autres options que `--global` ? Faut-il les envoyer sur Git ?

Réponse :

Les credentials configurés avec `--local` sont stockés dans `.dvc/config.local`, qui reste local au poste et ne doit pas être committé. Sans option, DVC écrit dans `.dvc/config`; avec `--global`, il écrit dans la configuration utilisateur. Des variables d'environnement ou un gestionnaire de secrets sont aussi possibles.

Les credentials ne doivent jamais être envoyés sur Git.

## Question 4
Après avoir exécuté `dvc add data`, regardez le fichier `.gitignore`. Qu'est-ce qui a changé ?

Réponse :

DVC a ajouté `/data` à `.gitignore`. Git ne suit donc pas les fichiers volumineux du dataset ; il suit le pointeur `data.dvc`, tandis que les données sont gérées par DVC.

## Question 5
Est-ce qu'un fichier `data.dvc` a été créé ? Que contient-il ?

Réponse :

Oui. `data.dvc` contient le hash MD5 du dossier, sa taille, le nombre de fichiers et le chemin suivi. La première version contenait notamment :

```yaml
outs:
- md5: a3a457d03c51ff8b037a833440f6ad13.dir
  size: 1188442712
  nfiles: 16643
  hash: md5
  path: data
```

## Question 6
Après avoir fait le commit et le push, regardez GitHub et DagsHub.

Réponse :

Le code et les pointeurs DVC sont présents sur GitHub. Les fichiers volumineux ne sont pas stockés dans Git ; ils sont transférés vers le remote DVC DagsHub avec `dvc push`. Le fichier `data.dvc` fait le lien entre Git et les objets stockés par DVC.

## Question 7
Clonez le repository dans un autre dossier. Le dossier `data` est-il directement présent après le clone ? Quelle commande DVC faut-il utiliser ?

Réponse :

Après `git clone`, le dossier `data` n'est pas forcément présent, car il est ignoré par Git. Le dépôt contient le pointeur `data.dvc`. Pour restaurer les données :

```powershell
git clone https://github.com/Ghandour-Ali/mlops-lab-1.git
cd mlops-lab-1
.\.venv\Scripts\dvc.exe pull -r origin
```

Les credentials du remote doivent être configurés localement avant le `pull` si nécessaire.

## Question 8
Après être revenu sur un ancien commit avec `git checkout <old-commit>`, puis `dvc checkout`, que se passe-t-il ?

Réponse :

`git checkout` change les pointeurs versionnés par Git. Ensuite, `dvc checkout` restaure dans le workspace les données correspondant à ces pointeurs, si elles sont disponibles dans le cache local. Sinon, `dvc pull` doit être exécuté avant `dvc checkout`.

Les dossiers n'apparaissent que s'ils sont référencés par le commit sélectionné.
