# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Project, Phase, Intervenant, PhaseIntervenant

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

@app.route('/project/<int:project_id>/allocation/calculate', methods=['POST'])
def calculate_allocation(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Vérifier si nous avons des phases et des intervenants
    if not project.phases or not project.intervenants:
        flash("Le projet doit avoir des phases et des intervenants pour calculer l'allocation", "danger")
        return redirect(url_for('project_allocation', project_id=project.id))
    
    # Identifier l'intervenant MB (s'il existe) qui servira de variable d'ajustement
    mb_intervenant = next((i for i in project.intervenants if i.name.lower() == 'mb'), None)
    
    # Si MB n'existe pas, prendre le dernier intervenant comme variable d'ajustement
    if not mb_intervenant and project.intervenants:
        mb_intervenant = project.intervenants[-1]
        flash(f"Aucun intervenant 'MB' trouvé, '{mb_intervenant.name}' sera utilisé comme variable d'ajustement", "warning")
    
    # Supprimer les allocations existantes
    PhaseIntervenant.query.filter(
        PhaseIntervenant.phase_id.in_([phase.id for phase in project.phases])
    ).delete(synchronize_session=False)
    
    # Liste des intervenants sans l'ajusteur (MB ou autre)
    regular_intervenants = [i for i in project.intervenants if i != mb_intervenant]
    
    # Calculer les pourcentages cibles globaux pour chaque intervenant
    # Ces pourcentages représentent ce que chaque intervenant devrait obtenir au total
    target_percentages = {}
    for intervenant in project.intervenants:
        if intervenant.montant_verif:
            target_percentages[intervenant.id] = (intervenant.montant_verif / project.total_marche) * 100
        else:
            # Si pas de montant vérif, valeur par défaut
            target_percentages[intervenant.id] = 0
    
    # Première passe : allouer selon les pourcentages cibles pour les intervenants réguliers
    allocation_by_phase_intervenant = {}
    remaining_by_phase = {}
    
    for phase in project.phases:
        phase_amount = project.total_marche * phase.percentage / 100
        remaining_percent = 100.0  # Pourcentage restant pour cette phase
        phase_allocations = {}
        
        # Allouer proportionnellement à chaque intervenant régulier
        total_target_percent = sum(target_percentages[i.id] for i in regular_intervenants)
        
        if total_target_percent > 0:
            for intervenant in regular_intervenants:
                # Pourcentage calculé proportionnellement au poids de l'intervenant
                if total_target_percent > 0:
                    alloc_percent = (target_percentages[intervenant.id] / total_target_percent) * 100
                else:
                    alloc_percent = 0
                
                # Limiter le pourcentage au restant disponible
                if alloc_percent > remaining_percent:
                    alloc_percent = remaining_percent
                
                # Calculer le montant
                alloc_amount = phase_amount * (alloc_percent / 100)
                
                # Stocker l'allocation
                phase_allocations[(phase.id, intervenant.id)] = {
                    'percent': alloc_percent,
                    'amount': alloc_amount
                }
                
                # Mettre à jour le pourcentage restant
                remaining_percent -= alloc_percent
        
        # Stocker le pourcentage restant pour MB
        remaining_by_phase[phase.id] = remaining_percent
        allocation_by_phase_intervenant.update(phase_allocations)
    
    # Deuxième passe : allouer le reste à MB et vérifier les écarts
    if mb_intervenant:
        for phase in project.phases:
            phase_amount = project.total_marche * phase.percentage / 100
            remaining_percent = remaining_by_phase[phase.id]
            
            # Allouer le reste à MB
            mb_amount = phase_amount * (remaining_percent / 100)
            
            allocation_by_phase_intervenant[(phase.id, mb_intervenant.id)] = {
                'percent': remaining_percent,
                'amount': mb_amount
            }
    
    # Vérifier les écarts par rapport aux montants vérif
    intervenant_totals = {}
    for intervenant in project.intervenants:
        # Calculer le total pour cet intervenant sur toutes les phases
        total_amount = sum(
            allocation_by_phase_intervenant.get((phase.id, intervenant.id), {}).get('amount', 0)
            for phase in project.phases
        )
        
        # Calculer l'écart par rapport à la vérif
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
    
    # Troisième passe : ajuster pour minimiser les écarts (si MB est présent)
    if mb_intervenant:
        # Identifier les intervenants qui ont un écart > 5%
        intervenants_to_adjust = []
        for intervenant in regular_intervenants:
            if intervenant_totals[intervenant.id]['ecart_percent'] > 5:
                intervenants_to_adjust.append(intervenant)
        
        # Ajuster pour chaque intervenant qui dépasse l'écart
        for intervenant in intervenants_to_adjust:
            target_amount = intervenant.montant_verif * 1.05  # +5% max
            excess_amount = intervenant_totals[intervenant.id]['amount'] - target_amount
            
            if excess_amount <= 0:
                continue  # Pas besoin d'ajuster
            
            # Répartir l'excès entre les phases
            for phase in project.phases:
                phase_key = (phase.id, intervenant.id)
                mb_key = (phase.id, mb_intervenant.id)
                
                if phase_key not in allocation_by_phase_intervenant:
                    continue
                
                phase_amount = project.total_marche * phase.percentage / 100
                current_allocation = allocation_by_phase_intervenant[phase_key]
                
                # Calculer l'ajustement proportionnel pour cette phase
                phase_proportion = current_allocation['amount'] / intervenant_totals[intervenant.id]['amount']
                amount_to_reduce = excess_amount * phase_proportion
                
                # Limiter la réduction au montant actuel
                if amount_to_reduce > current_allocation['amount']:
                    amount_to_reduce = current_allocation['amount']
                
                # Calculer les nouveaux pourcentages
                percent_to_reduce = (amount_to_reduce / phase_amount) * 100
                new_percent = current_allocation['percent'] - percent_to_reduce
                new_amount = current_allocation['amount'] - amount_to_reduce
                
                # Mettre à jour l'allocation
                allocation_by_phase_intervenant[phase_key] = {
                    'percent': new_percent,
                    'amount': new_amount
                }
                
                # Transférer le pourcentage à MB
                mb_allocation = allocation_by_phase_intervenant.get(mb_key, {'percent': 0, 'amount': 0})
                mb_allocation['percent'] += percent_to_reduce
                mb_allocation['amount'] += amount_to_reduce
                allocation_by_phase_intervenant[mb_key] = mb_allocation
    
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

# -- Lancement serveur -------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)