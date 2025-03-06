# app.py
from flask import Flask, render_template, request, redirect, url_for
from models import db, Project, Phase, Intervenant, PhaseIntervenant  # Importation des modèles

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/app.db'  # Préciser le chemin vers la BD
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialiser l'instance de db avec l'application
db.init_app(app)

# Remplacer @app.before_first_request qui est déprécié
@app.cli.command("init-db")
def create_tables():
    db.create_all()
    print("Base de données initialisée !")

# -- Modèles -----------------------------------------------------
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_marche = db.Column(db.Float, nullable=False)

    phases = db.relationship('Phase', backref='project', lazy=True)
    intervenants = db.relationship('Intervenant', backref='project', lazy=True)


class Phase(db.Model):
    __tablename__ = 'phases'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    allocations = db.relationship('PhaseIntervenant', backref='phase', lazy=True)


class Intervenant(db.Model):
    __tablename__ = 'intervenants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    montant_verif = db.Column(db.Float, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    allocations = db.relationship('PhaseIntervenant', backref='intervenant', lazy=True)


class PhaseIntervenant(db.Model):
    __tablename__ = 'phase_intervenants'
    
    id = db.Column(db.Integer, primary_key=True)
    phase_id = db.Column(db.Integer, db.ForeignKey('phases.id'), nullable=False)
    intervenant_id = db.Column(db.Integer, db.ForeignKey('intervenants.id'), nullable=False)
    final_percent = db.Column(db.Float, nullable=True)
    # final_amount = db.Column(db.Float, nullable=True)  # Optionnel

# -- Création des tables si nécessaire ---------------------------
@app.before_first_request
def create_tables():
    db.create_all()

# -- Routes ------------------------------------------------------

@app.route('/')
def index():
    # Page d’accueil : liste des projets
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
    
    return render_template('project_detail.html', 
                           project=project,
                           phases_total_percent=phases_total_percent,
                           phases_total_amount=phases_total_amount)

@app.route('/project/<int:project_id>/phase/add', methods=['POST'])
def add_phase(project_id):
    project = Project.query.get_or_404(project_id)
    
    phase_name = request.form.get('phase_name')
    percentage = float(request.form.get('percentage'))
    
    new_phase = Phase(name=phase_name, percentage=percentage, project_id=project.id)
    db.session.add(new_phase)
    db.session.commit()
    
    return redirect(url_for('project_detail', project_id=project.id))

# -- Lancement serveur -------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)
