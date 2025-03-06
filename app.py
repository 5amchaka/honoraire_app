# app.py
from flask import Flask, render_template, request, redirect, url_for, flash

from models import db, Project, Phase, Intervenant, PhaseIntervenant, PhaseIntervenantVerif

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'votre_clé_secrète'  # Nécessaire pour flash messages

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

@app.route('/project/<int:project_id>/allocation')
def project_allocation(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Vérifier si nous avons des phases et des intervenants
    if not project.phases:
        flash("Veuillez d'abord ajouter des phases au projet", "warning")
        return redirect(url_for('project_detail', project_id=project.id))
    
    if not project.intervenants:
        flash("Veuillez d'abord ajouter des intervenants au projet", "warning")
        return redirect(url_for('project_detail', project_id=project.id))
    
    # Calculer le total des pourcentages et montants des phases
    phases_total_percent = sum(phase.percentage for phase in project.phases)
    phases_total_amount = sum(project.total_marche * phase.percentage / 100 for phase in project.phases)
    
    # Récupérer toutes les allocations existantes
    allocations = PhaseIntervenant.query.filter(
        PhaseIntervenant.phase_id.in_([phase.id for phase in project.phases])
    ).all()
    
    # Créer un dictionnaire pour accéder facilement aux allocations
    allocation_data = {}
    for allocation in allocations:
        allocation_data[(allocation.phase_id, allocation.intervenant_id)] = allocation
    
    # Calculer les totaux par intervenant
    intervenant_totals = {}
    for intervenant in project.intervenants:
        total_amount = sum(
            alloc.final_amount for alloc in allocations 
            if alloc.intervenant_id == intervenant.id and alloc.final_amount is not None
        )
        
        intervenant_totals[intervenant.id] = {
            'amount': total_amount,
            'verif': intervenant.montant_verif,
            'ecart': total_amount - intervenant.montant_verif if intervenant.montant_verif else 0
        }
    
    return render_template('project_allocation.html', 
                          project=project,
                          phases_total_percent=phases_total_percent,
                          phases_total_amount=phases_total_amount,
                          allocation_data=allocation_data,
                          intervenant_totals=intervenant_totals)

# Route modifiée pour le calcul d'allocation
@app.route('/project/<int:project_id>/allocation/calculate', methods=['POST'])
def calculate_allocation(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Vérifier si nous avons des phases et des intervenants
    if not project.phases or not project.intervenants:
        flash("Le projet doit avoir des phases et des intervenants pour calculer l'allocation", "danger")
        return redirect(url_for('project_allocation', project_id=project.id))
    
    # Identifier l'intervenant MB (s'il existe) qui servira de variable d'ajustement par défaut
    mb_intervenant = next((i for i in project.intervenants if i.name.lower() == 'mb'), None)
    
    # Si MB n'existe pas, prendre le dernier intervenant comme variable d'ajustement
    if not mb_intervenant and project.intervenants:
        mb_intervenant = project.intervenants[-1]
        flash(f"Aucun intervenant 'MB' trouvé, '{mb_intervenant.name}' sera utilisé comme variable d'ajustement par défaut", "warning")
    
    # Récupérer les montants vérif détaillés
    verifs = PhaseIntervenantVerif.query.filter(
        PhaseIntervenantVerif.phase_id.in_([phase.id for phase in project.phases])
    ).all()
    
    # Créer un dictionnaire pour accéder facilement aux verifs
    verif_data = {}
    for verif in verifs:
        verif_data[(verif.phase_id, verif.intervenant_id)] = verif.montant_verif
    
    # Supprimer les allocations existantes
    PhaseIntervenant.query.filter(
        PhaseIntervenant.phase_id.in_([phase.id for phase in project.phases])
    ).delete(synchronize_session=False)
    
    # Initialiser le dictionnaire d'allocations
    allocation_by_phase_intervenant = {}
    
    # Première passe : traiter les phases une par une
    for phase in project.phases:
        phase_amount = project.total_marche * phase.percentage / 100
        remaining_percent = 100.0  # Pourcentage restant pour cette phase
        remaining_amount = phase_amount  # Montant restant pour cette phase
        phase_allocations = {}
        
        # Identifier les intervenants avec des montants vérif définis pour cette phase
        fixed_intervenants = []
        adjustable_intervenants = []
        zero_intervenants = []
        
        for intervenant in project.intervenants:
            verif_montant = verif_data.get((phase.id, intervenant.id))
            
            if verif_montant is not None:
                if verif_montant > 0:
                    fixed_intervenants.append(intervenant)
                elif verif_montant == 0:
                    zero_intervenants.append(intervenant)
            else:
                # Si pas de montant vérif défini, l'intervenant est ajustable
                adjustable_intervenants.append(intervenant)
        
        # Traiter d'abord les intervenants avec des montants vérif fixes
        total_fixed_amount = 0
        for intervenant in fixed_intervenants:
            verif_montant = verif_data.get((phase.id, intervenant.id), 0)
            
            # Calculer le pourcentage que cela représente de la phase
            alloc_percent = (verif_montant / phase_amount) * 100
            
            # Limiter le pourcentage au restant disponible si nécessaire
            if alloc_percent > remaining_percent:
                alloc_percent = remaining_percent
                verif_montant = phase_amount * (alloc_percent / 100)
            
            # Stocker l'allocation
            phase_allocations[(phase.id, intervenant.id)] = {
                'percent': alloc_percent,
                'amount': verif_montant
            }
            
            # Mettre à jour les pourcentages et montants restants
            remaining_percent -= alloc_percent
            remaining_amount -= verif_montant
            total_fixed_amount += verif_montant
        
        # Déterminer quel intervenant sert de tampon pour cette phase
        # Si MB a un montant vérif défini pour cette phase, c'est un autre intervenant qui sera le tampon
        buffer_intervenant = None
        
        # Vérifier si MB est dans les fixed_intervenants
        if mb_intervenant and mb_intervenant in fixed_intervenants:
            # MB a un montant fixe pour cette phase, choisir un autre tampon parmi les ajustables
            if adjustable_intervenants:
                buffer_intervenant = adjustable_intervenants[0]
                adjustable_intervenants.remove(buffer_intervenant)
        else:
            # MB n'a pas de montant fixe, il est le tampon par défaut
            buffer_intervenant = mb_intervenant
            if buffer_intervenant in adjustable_intervenants:
                adjustable_intervenants.remove(buffer_intervenant)
        
        # Répartir le pourcentage restant équitablement entre les intervenants ajustables (hors tampon)
        if adjustable_intervenants and remaining_percent > 0:
            per_adjustable_percent = remaining_percent / len(adjustable_intervenants)
            
            for intervenant in adjustable_intervenants:
                alloc_percent = per_adjustable_percent
                alloc_amount = phase_amount * (alloc_percent / 100)
                
                # Stocker l'allocation
                phase_allocations[(phase.id, intervenant.id)] = {
                    'percent': alloc_percent,
                    'amount': alloc_amount
                }
                
                # Mettre à jour le pourcentage restant
                remaining_percent -= alloc_percent
                remaining_amount -= alloc_amount
        
        # Attribuer le reste au tampon (si défini)
        if buffer_intervenant and remaining_percent > 0:
            phase_allocations[(phase.id, buffer_intervenant.id)] = {
                'percent': remaining_percent,
                'amount': remaining_amount
            }
        
        # Ajouter les allocations de cette phase au dictionnaire global
        allocation_by_phase_intervenant.update(phase_allocations)
    
    # Deuxième passe : vérifier les écarts par rapport aux montants vérif totaux
    intervenant_totals = {}
    for intervenant in project.intervenants:
        # Calculer le total pour cet intervenant sur toutes les phases
        total_amount = sum(
            allocation_by_phase_intervenant.get((phase.id, intervenant.id), {}).get('amount', 0)
            for phase in project.phases
        )
        
        # Calculer l'écart par rapport à la vérif globale
        if intervenant.montant_verif:
            ecart = total_amount - intervenant.montant_verif
            ecart_percent = (ecart / intervenant.montant_verif) * 100
        else:
            ecart = 0
            ecart_percent = 0
        
        intervenant_totals[intervenant.id] = {
            'amount': total_amount,
            'verif': intervenant.montant_verif,
            'ecart': ecart,
            'ecart_percent': ecart_percent
        }
    
    # Troisième passe : ajuster les phases où les intervenants sont ajustables
    # pour respecter la contrainte de ±5% sur les montants vérif globaux
    adjustments_needed = []
    
    for intervenant in project.intervenants:
        if intervenant == mb_intervenant:
            continue  # On ne fait pas d'ajustements sur MB qui est notre tampon principal
            
        if intervenant.montant_verif and abs(intervenant_totals[intervenant.id]['ecart_percent']) > 5:
            # Cet intervenant a besoin d'un ajustement
            ecart = intervenant_totals[intervenant.id]['ecart']
            adjustments_needed.append((intervenant, ecart))
    
    # Trier les ajustements par écart absolu décroissant (traiter d'abord les plus grands écarts)
    adjustments_needed.sort(key=lambda x: abs(x[1]), reverse=True)
    
    # Pour chaque intervenant nécessitant un ajustement
    for intervenant, ecart in adjustments_needed:
        # Identifier les phases où l'intervenant est ajustable
        adjustable_phases = []
        for phase in project.phases:
            if (phase.id, intervenant.id) not in verif_data or verif_data[(phase.id, intervenant.id)] is None:
                adjustable_phases.append(phase)
        
        # Si pas de phases ajustables, on ne peut rien faire
        if not adjustable_phases:
            continue
        
        # Répartir l'ajustement entre les phases ajustables
        adjustment_per_phase = ecart / len(adjustable_phases)
        
        for phase in adjustable_phases:
            phase_amount = project.total_marche * phase.percentage / 100
            
            # Récupérer l'allocation actuelle
            current_allocation = allocation_by_phase_intervenant.get((phase.id, intervenant.id), {'percent': 0, 'amount': 0})
            buffer_allocation = allocation_by_phase_intervenant.get((phase.id, mb_intervenant.id), {'percent': 0, 'amount': 0})
            
            # Calculer le nouvel amount après ajustement
            new_amount = current_allocation['amount'] - adjustment_per_phase
            
            # Vérifier que le nouveau montant est positif
            if new_amount < 0:
                new_amount = 0
            
            # Calculer le nouveau pourcentage
            new_percent = (new_amount / phase_amount) * 100
            delta_percent = current_allocation['percent'] - new_percent
            
            # Mettre à jour l'allocation
            allocation_by_phase_intervenant[(phase.id, intervenant.id)] = {
                'percent': new_percent,
                'amount': new_amount
            }
            
            # Transférer la différence au tampon (MB)
            if mb_intervenant:
                buffer_allocation['percent'] += delta_percent
                buffer_allocation['amount'] += adjustment_per_phase
                allocation_by_phase_intervenant[(phase.id, mb_intervenant.id)] = buffer_allocation
    
    # Enregistrer toutes les allocations dans la base de données
    for (phase_id, intervenant_id), allocation in allocation_by_phase_intervenant.items():
        if allocation['percent'] > 0:  # Ne pas créer d'allocation à 0%
            alloc = PhaseIntervenant(
                phase_id=phase_id,
                intervenant_id=intervenant_id,
                final_percent=allocation['percent'],
                final_amount=allocation['amount']
            )
            db.session.add(alloc)
    
    db.session.commit()
    
    flash("L'allocation a été calculée avec succès", "success")
    return redirect(url_for('project_allocation', project_id=project.id))

# Dans app.py, ajouter ces nouvelles routes

@app.route('/project/<int:project_id>/verif-detail')
def project_verif_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Vérifier que le projet a des phases et des intervenants
    if not project.phases:
        flash("Veuillez d'abord ajouter des phases au projet", "warning")
        return redirect(url_for('project_detail', project_id=project.id))
    
    if not project.intervenants:
        flash("Veuillez d'abord ajouter des intervenants au projet", "warning")
        return redirect(url_for('project_detail', project_id=project.id))
    
    # Récupérer les montants vérif existants
    verifs = PhaseIntervenantVerif.query.filter(
        PhaseIntervenantVerif.phase_id.in_([phase.id for phase in project.phases])
    ).all()
    
    # Créer un dictionnaire pour accéder facilement aux verifs
    verif_data = {}
    for verif in verifs:
        verif_data[(verif.phase_id, verif.intervenant_id)] = verif
    
    # Calculer les totaux par intervenant
    intervenant_verif_totals = {}
    for intervenant in project.intervenants:
        total_verif = sum(
            verif.montant_verif for verif in verifs 
            if verif.intervenant_id == intervenant.id and verif.montant_verif is not None
        )
        intervenant_verif_totals[intervenant.id] = total_verif
    
    # Calculer le total des pourcentages et montants des phases
    phases_total_percent = sum(phase.percentage for phase in project.phases)
    phases_total_amount = sum(project.total_marche * phase.percentage / 100 for phase in project.phases)
    
    return render_template('project_verif_detail.html', 
                           project=project,
                           verif_data=verif_data,
                           intervenant_verif_totals=intervenant_verif_totals,
                           phases_total_percent=phases_total_percent,
                           phases_total_amount=phases_total_amount)

@app.route('/project/<int:project_id>/verif-detail/save', methods=['POST'])
def save_verif_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Supprimer les verifs existants
    PhaseIntervenantVerif.query.filter(
        PhaseIntervenantVerif.phase_id.in_([phase.id for phase in project.phases])
    ).delete(synchronize_session=False)
    
    # Récupérer les données du formulaire et créer de nouveaux verifs
    for phase in project.phases:
        for intervenant in project.intervenants:
            field_name = f"verif_{phase.id}_{intervenant.id}"
            verif_value = request.form.get(field_name, '')
            
            # Convertir en float si non vide
            if verif_value.strip():
                try:
                    montant_verif = float(verif_value)
                    # Créer un nouvel enregistrement PhaseIntervenantVerif
                    verif = PhaseIntervenantVerif(
                        phase_id=phase.id,
                        intervenant_id=intervenant.id,
                        montant_verif=montant_verif
                    )
                    db.session.add(verif)
                except ValueError:
                    flash(f"Valeur invalide pour {phase.name} - {intervenant.name}: {verif_value}", "danger")
                    return redirect(url_for('project_verif_detail', project_id=project.id))
    
    db.session.commit()
    flash("Les montants vérif ont été enregistrés avec succès", "success")
    return redirect(url_for('project_verif_detail', project_id=project.id))

@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Supprimer toutes les allocations liées au projet
    PhaseIntervenant.query.filter(
        PhaseIntervenant.phase_id.in_([phase.id for phase in project.phases])
    ).delete(synchronize_session=False)
    
    # Supprimer toutes les vérifications liées au projet
    if 'PhaseIntervenantVerif' in globals():  # Vérification si le modèle existe
        PhaseIntervenantVerif.query.filter(
            PhaseIntervenantVerif.phase_id.in_([phase.id for phase in project.phases])
        ).delete(synchronize_session=False)
    
    # Supprimer toutes les phases et intervenants du projet
    for phase in project.phases:
        db.session.delete(phase)
    
    for intervenant in project.intervenants:
        db.session.delete(intervenant)
    
    # Supprimer le projet lui-même
    db.session.delete(project)
    db.session.commit()
    
    flash(f"Le projet '{project.name}' a été supprimé avec succès", "success")
    return redirect(url_for('index'))

@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        # Récupérer les infos du formulaire
        project_name = request.form.get('project_name')
        total_marche = request.form.get('total_marche')
        
        # Mettre à jour le projet
        project.name = project_name
        project.total_marche = float(total_marche)
        db.session.commit()
        
        flash("Les modifications ont été enregistrées avec succès", "success")
        return redirect(url_for('project_detail', project_id=project.id))
    else:
        # Afficher le formulaire d'édition
        return render_template('edit_project.html', project=project)

@app.route('/project/<int:project_id>/phases/edit', methods=['GET', 'POST'])
def edit_phases(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        # Récupérer les pourcentages modifiés
        for phase in project.phases:
            percentage_key = f'percentage_{phase.id}'
            if percentage_key in request.form:
                try:
                    phase.percentage = float(request.form[percentage_key])
                except ValueError:
                    flash(f"Valeur invalide pour la phase {phase.name}", "danger")
                    return redirect(url_for('edit_phases', project_id=project.id))
        
        # Vérifier que la somme des pourcentages est égale à 100%
        total_percentage = sum(phase.percentage for phase in project.phases)
        if abs(total_percentage - 100.0) > 0.01:  # Tolérance de 0.01% pour les erreurs d'arrondi
            flash(f"La somme des pourcentages doit être égale à 100% (actuellement {total_percentage:.2f}%)", "danger")
            return redirect(url_for('edit_phases', project_id=project.id))
        
        db.session.commit()
        flash("Les pourcentages des phases ont été modifiés avec succès", "success")
        return redirect(url_for('project_detail', project_id=project.id))
    else:
        # Afficher le formulaire d'édition des phases
        return render_template('edit_phases.html', project=project)

# -- Lancement serveur -------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)