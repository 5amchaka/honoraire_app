# Gestionnaire de Projets et Allocations

Une application Flask permettant de gérer des projets, leurs phases et leurs intervenants, avec un système automatique de calcul d'allocation de montants par phase et intervenant.

## Fonctionnalités

- Création et gestion de projets avec montant total
- Ajout de phases avec pourcentages du montant total
- Ajout d'intervenants avec montants "vérif" souhaités
- Calcul automatique de l'allocation des montants par phase et par intervenant
- Respect des contraintes :
  - Somme des pourcentages par phase = 100%
  - Respect des montants "vérif" avec une tolérance de ±5%
  - Utilisation d'un intervenant (MB) comme variable d'ajustement

## Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Étapes d'installation

1. Cloner le dépôt
```bash
git clone https://github.com/votre-username/gestionnaire-projets.git
cd gestionnaire-projets
```

2. Créer un environnement virtuel
```bash
python -m venv venv
```

3. Activer l'environnement virtuel
- Windows:
```bash
venv\Scripts\activate
```
- macOS/Linux:
```bash
source venv/bin/activate
```

4. Installer les dépendances
```bash
pip install -r requirements.txt
```

5. Initialiser la base de données
```bash
flask init-db
```

6. Générer des données de test (optionnel)
```bash
python generate_test_data.py
```

## Utilisation

1. Lancer l'application
```bash
python app.py
```

2. Accéder à l'application via votre navigateur à l'adresse `http://localhost:5001`

3. Workflow typique:
   - Créer un nouveau projet avec son montant total
   - Ajouter des phases avec leurs pourcentages (le total doit être 100%)
   - Ajouter des intervenants avec leurs montants "vérif" souhaités
   - Accéder à la page d'allocation et cliquer sur "Calculer l'allocation"
   - Vérifier les résultats et les écarts par rapport aux montants "vérif"

## Structure du Projet

```
gestionnaire-projets/
│
├── app.py              # Application principale Flask
├── models.py           # Modèles de données (ORM SQLAlchemy)
├── requirements.txt    # Dépendances Python
├── generate_test_data.py  # Script pour générer des données de test
│
├── static/             # Ressources statiques
│   └── css/
│       └── style.css   # Styles personnalisés
│
└── templates/          # Templates HTML
    ├── index.html            # Liste des projets
    ├── create_project.html   # Création de projet
    ├── project_detail.html   # Détail d'un projet avec phases et intervenants
    └── project_allocation.html # Tableau d'allocation
```

## Algorithme d'allocation

L'algorithme d'allocation fonctionne en plusieurs passes:

1. **Première passe**: Allocation proportionnelle des pourcentages pour chaque intervenant (sauf MB)
2. **Deuxième passe**: Allocation du pourcentage restant à MB
3. **Troisième passe**: Ajustement pour respecter la contrainte de ±5% sur les montants "vérif"

La variable d'ajustement (MB) permet de garantir que la somme des pourcentages reste toujours à 100%.

## Dépendances

- Flask: Framework web
- SQLAlchemy: ORM pour la gestion de la base de données
- Bootstrap: Framework CSS pour l'interface utilisateur

## Perspectives d'évolution

- Export des données en CSV ou PDF
- Ajout d'une gestion des factures
- Interface d'administration pour gérer les utilisateurs
- Système de validation des allocations

## Licence

MIT