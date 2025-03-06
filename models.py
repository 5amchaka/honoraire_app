from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Nom du projet
    total_marche = db.Column(db.Float, nullable=False) # Montant total du marché

    # Relation : un projet possede plusieurs phases
    phases = db.relationship('Phase', backref='project', lazy=True)

    # Relation : un projet possede plusieurs intervenants
    intervenants = db.relationship('Intervenant', backref='project', lazy=True)

    def __repr__(self):
        return f"<Project(id={self.name}, name='{self.name}')>"
    
class Phase(db.Model):
    __tablename__ = 'phases'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Nom de la phase (Ex : Études, Travaux, etc.)
    percentage = db.Column(db.Float, nullable=False)  # Pourcentage de la phase par rapport au total du projet
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # Relation : une phase peut avoir plusieurs associations à des intervenants
    allocations = db.relationship('PhaseIntervenant', backref='phase', lazy=True)
    
    def __repr__(self):
        return f"<Phase(id={self.id}, name='{self.name}', percentage={self.percentage})>"


class Intervenant(db.Model):
    __tablename__ = 'intervenants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Nom ou rôle de l’intervenant (ex : Architecte, MB, etc.)
    montant_verif = db.Column(db.Float, nullable=True)  # Montant 'vérif' souhaité sur l'ensemble du projet
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # Relation : un intervenant peut être associé à plusieurs phases
    allocations = db.relationship('PhaseIntervenant', backref='intervenant', lazy=True)
    
    def __repr__(self):
        return f"<Intervenant(id={self.id}, name='{self.name}', montant_verif={self.montant_verif})>"


class PhaseIntervenant(db.Model):
    __tablename__ = 'phase_intervenants'
    
    id = db.Column(db.Integer, primary_key=True)
    phase_id = db.Column(db.Integer, db.ForeignKey('phases.id'), nullable=False)
    intervenant_id = db.Column(db.Integer, db.ForeignKey('intervenants.id'), nullable=False)
    
    # Pourcentage finalement attribué à l'intervenant dans cette phase (calculé)
    final_percent = db.Column(db.Float, nullable=True)  
    
    # Optionnel : on peut également stocker un montant calculé directement :
    # final_amount = db.Column(db.Float, nullable=True)
    
    def __repr__(self):
        return (f"<PhaseIntervenant("
                f"phase_id={self.phase_id}, "
                f"intervenant_id={self.intervenant_id}, "
                f"final_percent={self.final_percent})>")
    
