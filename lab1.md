# Lab 1 - DVC

## Question 1
Après `uv init`, quels fichiers ont été créés et à quoi servent-ils ?

Réponse :
Réponse:

- J'ai ajouté le remote `origin` pointant vers `https://dagshub.com/Ghandour-Ali/mlops-lab-1.dvc` et configuré l'authentification en mode `basic` en local.
- Où sont stockées les credentials ? -> Elles sont stockées localement dans `.dvc/config.local` (fichier non versionné par défaut). C'est l'option `--local` que nous avons utilisée.
- Options autres que `--global` :
	- `--local` : écrit les paramètres dans `.dvc/config.local` (recommandé pour secrets locaux).
	- sans flag : écrit dans `.dvc/config` au niveau du dépôt (repo-level).
	- `--global` : écrit dans la config DVC de l'utilisateur (ex: `~/.config/dvc/config`).
- Faut-il pousser les credentials sur Git ? -> Non. Ne jamais committer ou pousser les mots de passe/jetons. Utilisez `.dvc/config.local`, variables d'environnement, ou un secret manager.

Remarque opérationnelle : j'ai vérifié que le remote `origin` est présent (`dvc remote list`) et que `.dvc/config.local` contient les clés (`auth`, `user`, `password`) — le mot de passe est conservé localement et n'a pas été ajouté au dépôt Git.

`uv init` crée les fichiers de base du projet Python.

- `pyproject.toml` : contient les informations du projet et les dépendances.
- `.python-version` : indique la version de Python utilisée.
- `main.py` : fichier Python principal créé au départ.
- `README.md` : sert à décrire le projet.
- `.gitignore` : indique à Git quels fichiers il ne doit pas suivre.


## Question 2
Après `dvc init`, quels fichiers ont été créés ? À quoi servent-ils ? Lesquels doivent être envoyés sur Git ?

Réponse :

Après `dvc init`, DVC crée principalement :

- `.dvc/`
- `.dvc/config`
- `.dvc/.gitignore`
- `.dvcignore`

Le dossier `.dvc` contient la configuration nécessaire pour utiliser DVC dans le projet.

Le fichier `.dvcignore` permet d'indiquer à DVC les fichiers ou dossiers qu'il doit ignorer, un peu comme `.gitignore` pour Git.

Ces fichiers doivent être ajoutés au dépôt Git afin que les autres personnes qui clonent le projet puissent aussi utiliser la même configuration DVC.

Par contre, les mots de passe, tokens ou autres credentials ne doivent jamais être poussés sur Git.


## Question 3
Lorsqu'on ajoute DagsHub comme remote DVC, où sont stockés les credentials ? Quelles sont les autres options que `--global` ? Faut-il les envoyer sur Git ?


Réponse :

- Où sont stockés les credentials ?
	- Ils peuvent être stockés à trois endroits selon l'option choisie :
		- **Global** (utilisateur) : `~/.config/dvc/config` (option `--global`).
		- **Repo** (niveau dépôt) : `.dvc/config` (par défaut, sans flag).
		- **Local** (non versionné) : `.dvc/config.local` (option `--local`) — recommandé pour les secrets.

- Quelles sont les autres options que `--global` ?
	- `--local` : écriture dans `.dvc/config.local` (garder les credentials hors du dépôt).
	- Sans flag : écriture dans `.dvc/config` (repo-level).
	- Alternatives : variables d'environnement, keyring/secret manager, ou providers d'authentification (tokens, OAuth) selon le remote.

- Faut‑il les envoyer sur Git ?
	- Non. Ne commitez jamais de mots de passe ou tokens. Commitez uniquement la configuration non sensible (`.dvc/config`, `.dvcignore`).
	- Pour les credentials, utilisez `.dvc/config.local`, variables d'environnement, ou un gestionnaire de secrets.




## Question 4
Après avoir exécuté `dvc add data`, regardez le fichier `.gitignore`. Qu'est-ce qui a changé ?

Réponse :

- DVC a ajouté une entrée pour exclure le dossier de données brutes de Git.
- Le fichier `.gitignore` contient désormais `/data`, empêchant Git de suivre le contenu du dossier `data` (les fichiers réels sont gérés par DVC).



## Question 5
Est-ce qu'un fichier `data.dvc` a été créé ? Que contient-il ?

Réponse :

- Oui — un fichier `data.dvc` a été créé par `dvc add`.
- Il contient les métadonnées DVC pointant vers le dossier `data` : hash (md5), taille totale, nombre de fichiers et le chemin suivi. Exemple de contenu :

```
outs:
- md5: a3a457d03c51ff8b037a833440f6ad13.dir
	size: 1188442712
	nfiles: 16643
	hash: md5
	path: data
```



## Question 6
Après avoir fait le commit et le push, regardez GitHub et DagsHub.

Le code est-il présent sur GitHub ?
Les données sont-elles présentes ?
Quel fichier permet de faire le lien avec les données ?
Que voit-on sur DagsHub ?

Réponse :

- **Le code sur GitHub :** Oui. Le commit contenant les pointeurs DVC (notamment `data.dvc`) a été poussé sur GitHub et est visible dans le dépôt.
- **Les données :** Les fichiers de données bruts ne sont pas stockés dans Git (ils sont listés dans `.gitignore`). Les données elles‑mêmes sont sur le remote DVC (DagsHub) — `dvc push` a renvoyé « Everything is up to date », donc les objets sont disponibles sur le remote.
- **Fichier de liaison :** `data.dvc` fait le lien entre le dépôt Git et les objets de données versionnés par DVC. Les configurations de remote sont dans `.dvc/config` ou `.dvc/config.local`.
- **Ce qu'on voit sur DagsHub :** dans l'onglet *Data* (ou la section Storage) on voit l'artefact poussé, sa taille totale (~1.1 GB), le nombre de fichiers (16643), le hash/ID (md5) et la possibilité de télécharger les fichiers ou consulter les métadonnées.




## Question 7
Clonez le repository dans un autre dossier.

Le dossier `data` est-il directement présent après le clone ?

Quelle commande DVC faut-il utiliser pour récupérer les données ?

Réponse :




## Question 8
Après être revenu sur un ancien commit avec :

`git checkout <old-commit>`

puis :

`dvc checkout`

Est-ce que les dossiers `food11_processed` et `food11_processed_mini` apparaissent ?

Réponse :