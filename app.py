# app.py
from flask import Flask, render_template, request, redirect, url_for
from models import db, Project, Phase, Intervenant, PhaseIntervenant  # Importation des modèles

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/app.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialiser l'instance de db avec l'application
db.init_app(app)

# Fonction pour créer les tables
@app.cli.command("init-db")
def create_tables():
    with app.app_context():
        db.create_all()
        print("Base de données initialisée !")

# -- Routes ------------------------------------------------------

@app.route('/')
def index():
    # Page d'accueil : liste des projets
    all_projects = Project.query.all()
    return render_template('index.html', projects=all_projects)

@app.route('/project/new', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        # Récupérer les infos du formulaire
        project_name = request.form.get('project_name')
        total_marche = request.form.get('total_marche')

        # Créer l'objet Project
        new_project = Project(name=project_name, total_marche=float(total_marche))
        db.session.add(new_project)
        db.session.commit()

        # Rediriger vers l'accueil ou la page de détail
        return redirect(url_for('index'))
    else:
        # Simplement afficher le formulaire
        return render_template('create_project.html')

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Calculer le total des pourcentages et montants des phases
    phases_total_percent = sum(phase.percentage for phase in project.phases)
    phases_total_amount = sum(project.total_marche * phase.percentage / 100 for phase in project.phases)
    
    # Calculer le total des montants vérif des intervenants
    intervenants_total_verif = sum(intervenant.montant_verif for intervenant in project.intervenants)
    intervenants_total_percent = (intervenants_total_verif / project.total_marche * 100) if project.total_marche else 0
    
    return render_template('project_detail.html', 
                           project=project,
                           phases_total_percent=phases_total_percent,
                           phases_total_amount=phases_total_amount,
                           intervenants_total_verif=intervenants_total_verif,
                           intervenants_total_percent=intervenants_total_percent)

@app.route('/project/<int:project_id>/phase/add', methods=['POST'])
def add_phase(project_id):
    project = Project.query.get_or_404(project_id)
    
    phase_name = request.form.get('phase_name')
    percentage = float(request.form.get('percentage'))
    
    new_phase = Phase(name=phase_name, percentage=percentage, project_id=project.id)
    db.session.add(new_phase)
    db.session.commit()
    
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/project/<int:project_id>/intervenant/add', methods=['POST'])
def add_intervenant(project_id):
    project = Project.query.get_or_404(project_id)
    
    intervenant_name = request.form.get('intervenant_name')
    montant_verif = float(request.form.get('montant_verif'))
    
    new_intervenant = Intervenant(name=intervenant_name, 
                                  montant_verif=montant_verif, 
                                  project_id=project.id)
    db.session.add(new_intervenant)
    db.session.commit()
    
    return redirect(url_for('project_detail', project_id=project.id))

# -- Lancement serveur -------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)