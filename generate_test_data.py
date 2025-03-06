# generate_test_data.py
from app import app, db
from models import Project, Phase, Intervenant

def generate_test_data():
    # Créer un contexte d'application
    with app.app_context():
        # Vérifier si des données existent déjà
        if Project.query.count() > 0:
            print("Des données existent déjà dans la base de données.")
            return
        
        # Créer un projet de test
        projet1 = Project(name="Projet Résidentiel A", total_marche=1200000.0)
        db.session.add(projet1)
        db.session.flush()  # Pour obtenir l'ID du projet
        
        # Ajouter des phases
        phases = [
            Phase(name="Études", percentage=10.0, project_id=projet1.id),
            Phase(name="DCE", percentage=5.0, project_id=projet1.id),
            Phase(name="ACT", percentage=5.0, project_id=projet1.id),
            Phase(name="DET", percentage=65.0, project_id=projet1.id),
            Phase(name="AOR", percentage=15.0, project_id=projet1.id)
        ]
        db.session.add_all(phases)
        
        # Ajouter des intervenants
        intervenants = [
            Intervenant(name="Architecte", montant_verif=450000.0, project_id=projet1.id),
            Intervenant(name="BET Structure", montant_verif=230000.0, project_id=projet1.id),
            Intervenant(name="BET Fluides", montant_verif=280000.0, project_id=projet1.id),
            Intervenant(name="MB", montant_verif=240000.0, project_id=projet1.id)
        ]
        db.session.add_all(intervenants)
        
        # Créer un deuxième projet
        projet2 = Project(name="Projet Commercial B", total_marche=800000.0)
        db.session.add(projet2)
        db.session.flush()
        
        # Ajouter des phases pour le projet 2
        phases2 = [
            Phase(name="Études", percentage=12.0, project_id=projet2.id),
            Phase(name="DCE", percentage=8.0, project_id=projet2.id),
            Phase(name="DET", percentage=60.0, project_id=projet2.id),
            Phase(name="AOR", percentage=20.0, project_id=projet2.id)
        ]
        db.session.add_all(phases2)
        
        # Ajouter des intervenants pour le projet 2
        intervenants2 = [
            Intervenant(name="Architecte", montant_verif=320000.0, project_id=projet2.id),
            Intervenant(name="BET Structure", montant_verif=160000.0, project_id=projet2.id),
            Intervenant(name="BET Fluides", montant_verif=180000.0, project_id=projet2.id),
            Intervenant(name="MB", montant_verif=140000.0, project_id=projet2.id)
        ]
        db.session.add_all(intervenants2)
        
        # Enregistrer toutes les modifications
        db.session.commit()
        
        print("Données de test générées avec succès!")

if __name__ == "__main__":
    generate_test_data()