# app.py
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

# -- Lancement serveur -------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)
