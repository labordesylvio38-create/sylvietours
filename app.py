from flask import Flask, flash, render_template, request, redirect, url_for, send_file
import sqlite3
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import socket

app = Flask(__name__)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sylvietours.db')

def fix_decimal(val):
    try:
        return float(str(val).replace(',', '.'))
    except:
        return 0.0

def format_date(date_str):
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        return d.strftime('%d.%m.%y')
    except:
        return date_str

def nombre_en_lettres(n):
    units = ['', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf',
             'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept',
             'dix-huit', 'dix-neuf']
    tens = ['', 'dix', 'vingt', 'trente', 'quarante', 'cinquante', 'soixante',
            'soixante', 'quatre-vingt', 'quatre-vingt']
    n = int(n)
    if n == 0: return 'zéro'
    if n < 0: return 'moins ' + nombre_en_lettres(-n)
    result = ''
    if n >= 1000:
        result += nombre_en_lettres(n // 1000) + ' mille '
        n %= 1000
    if n >= 100:
        if n // 100 == 1:
            result += 'cent '
        else:
            result += units[n // 100] + ' cent '
        n %= 100
    if n >= 20:
        t = n // 10
        u = n % 10
        if t == 7 or t == 9:
            result += tens[t] + '-' + units[10 + u] + ' '
        elif t == 8:
            result += 'quatre-vingt' + (('-' + units[u]) if u else 's') + ' '
        else:
            result += tens[t] + (('-' + units[u]) if u else '') + ' '
    elif n > 0:
        result += units[n] + ' '
    return result.strip()

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        client TEXT,
        nb_personnes INTEGER,
        date_arrivee TEXT,
        date_depart TEXT,
        statut TEXT DEFAULT 'en cours',
        numero_facture TEXT,
        notes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hebergements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id INTEGER,
        hotel TEXT,
        nb_nuits INTEGER,
        designation TEXT,
        nb_chambres TEXT,
        tarif_nuit REAL,
        FOREIGN KEY(mission_id) REFERENCES missions(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS vehicules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id INTEGER,
        itineraire TEXT,
        type_voiture TEXT,
        nb_voitures INTEGER,
        nb_jours INTEGER,
        tarif_jour REAL,
        noms_chauffeurs TEXT,
        nb_chauffeurs INTEGER DEFAULT 0,
        FOREIGN KEY(mission_id) REFERENCES missions(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS cartes_sim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id INTEGER,
        date_debut TEXT,
        date_fin TEXT,
        nb_sim INTEGER,
        prix_sim REAL,
        nb_forfait INTEGER,
        prix_forfait REAL,
        client TEXT,
        numero_devis TEXT,
        statut_paiement TEXT DEFAULT 'non payé',
        FOREIGN KEY(mission_id) REFERENCES missions(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS packs_eau (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id INTEGER,
        date_debut TEXT,
        date_fin TEXT,
        designation TEXT,
        prix_unitaire REAL,
        nb_paquets INTEGER,
        client TEXT,
        numero_facture TEXT,
        statut_paiement TEXT DEFAULT 'non payé',
        FOREIGN KEY(mission_id) REFERENCES missions(id)
    )''')
    migrations = [
        "ALTER TABLE vehicules ADD COLUMN noms_chauffeurs TEXT",
        "ALTER TABLE vehicules ADD COLUMN nb_chauffeurs INTEGER DEFAULT 0",
        "ALTER TABLE cartes_sim ADD COLUMN statut_paiement TEXT DEFAULT 'non payé'",
        "ALTER TABLE packs_eau ADD COLUMN statut_paiement TEXT DEFAULT 'non payé'",
    ]
    for m in migrations:
        try:
            c.execute(m)
        except:
            pass
    conn.commit()
    conn.close()

def get_mission(mission_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM missions WHERE id=?", (mission_id,))
    m = c.fetchone()
    c.execute("SELECT * FROM hebergements WHERE mission_id=?", (mission_id,))
    hebs = c.fetchall()
    c.execute("SELECT * FROM vehicules WHERE mission_id=?", (mission_id,))
    vehs = c.fetchall()
    conn.close()
    return m, hebs, vehs

def make_footer(contact_style, contact_blue):
    def footer(canvas, doc):
        canvas.saveState()
        items = [
            Paragraph("<b>(+261) 34 64 900 10 - (+261) 34 65 188 85 –(+261) 32 41 101 29</b>", contact_style),
            Paragraph("<u>Messenger: Diamant Ngyavo</u>", contact_blue),
            Paragraph("<u>WatsApp: 034 64 900 10</u>", contact_blue),
            Paragraph("<u>Siteweb : www.sylvie-tours.com</u>", contact_blue),
        ]
        y = 1*cm
        for item in items:
            w, h = item.wrap(doc.width, 1*cm)
            item.drawOn(canvas, doc.leftMargin, y)
            y += h + 2
        canvas.restoreState()
    return footer

@app.route('/')
def accueil():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM missions ORDER BY id DESC")
    missions = c.fetchall()
    conn.close()

    missions_en_cours = len([m for m in missions if len(m) > 6 and str(m[6]).strip().lower() == 'en cours'])
    missions_terminees = len([m for m in missions if len(m) > 6 and str(m[6]).strip().lower() == 'terminée'])
    missions_annulees = len([m for m in missions if len(m) > 6 and str(m[6]).strip().lower() == 'annulée'])

    return render_template(
        'accueil.html',
        missions=missions,
        missions_en_cours=missions_en_cours,
        missions_terminees=missions_terminees,
        missions_annulees=missions_annulees
    )

@app.route('/nouvelle_mission', methods=['GET', 'POST'])
def nouvelle_mission():
    if request.method == 'POST':
        nom = request.form['nom']
        client = request.form['client']
        nb = request.form['nb_personnes']
        arrivee = request.form['date_arrivee']
        depart = request.form['date_depart']
        num_facture = request.form['numero_facture']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO missions (nom, client, nb_personnes, date_arrivee, date_depart, numero_facture) VALUES (?,?,?,?,?,?)",
                  (nom, client, nb, arrivee, depart, num_facture))
        conn.commit()
        mission_id = c.lastrowid
        conn.close()
        return redirect(url_for('detail_mission', mission_id=mission_id))
    return render_template('nouvelle_mission.html')

@app.route('/mission/<int:mission_id>')
def detail_mission(mission_id):
    m, hebs, vehs = get_mission(mission_id)
    total_heb = sum(fix_decimal(h[6]) * h[3] for h in hebs)
    total_veh = sum(fix_decimal(v[6]) * v[4] * v[5] for v in vehs)
    total = total_heb + total_veh
    return render_template('detail_mission.html',
        mission=m, hebergements=hebs, vehicules=vehs,
        total_heb=total_heb, total_veh=total_veh, total=total)

@app.route('/modifier_mission/<int:mission_id>', methods=['GET', 'POST'])
def modifier_mission(mission_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if request.method == 'POST':
        nom = request.form['nom']
        client = request.form['client']
        nb = request.form['nb_personnes']
        arrivee = request.form['date_arrivee']
        depart = request.form['date_depart']
        num_facture = request.form['numero_facture']
        statut = request.form['statut']
        c.execute("""UPDATE missions SET nom=?, client=?, nb_personnes=?,
                  date_arrivee=?, date_depart=?, numero_facture=?, statut=?
                  WHERE id=?""",
                  (nom, client, nb, arrivee, depart, num_facture, statut, mission_id))
        conn.commit()
        conn.close()
        return redirect(url_for('detail_mission', mission_id=mission_id))
    c.execute("SELECT * FROM missions WHERE id=?", (mission_id,))
    mission = c.fetchone()
    conn.close()
    return render_template('modifier_mission.html', mission=mission)

@app.route('/supprimer_mission/<int:mission_id>')
def supprimer_mission(mission_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM hebergements WHERE mission_id=?", (mission_id,))
    c.execute("DELETE FROM vehicules WHERE mission_id=?", (mission_id,))
    c.execute("DELETE FROM cartes_sim WHERE mission_id=?", (mission_id,))
    c.execute("DELETE FROM packs_eau WHERE mission_id=?", (mission_id,))
    c.execute("DELETE FROM missions WHERE id=?", (mission_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('accueil'))

@app.route('/ajouter_hebergement/<int:mission_id>', methods=['POST'])
def ajouter_hebergement(mission_id):
    hotel = request.form['hotel']
    nb_nuits = request.form['nb_nuits']
    designation = request.form['designation']
    nb_chambres = request.form['nb_chambres']
    tarif = fix_decimal(request.form['tarif_nuit'])
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO hebergements (mission_id, hotel, nb_nuits, designation, nb_chambres, tarif_nuit) VALUES (?,?,?,?,?,?)",
              (mission_id, hotel, nb_nuits, designation, nb_chambres, tarif))
    conn.commit()
    conn.close()
    return redirect(url_for('detail_mission', mission_id=mission_id))

@app.route('/modifier_hebergement/<int:heb_id>', methods=['GET', 'POST'])
def modifier_hebergement(heb_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if request.method == 'POST':
        hotel = request.form['hotel']
        nb_nuits = request.form['nb_nuits']
        designation = request.form['designation']
        nb_chambres = request.form['nb_chambres']
        tarif = fix_decimal(request.form['tarif_nuit'])
        c.execute("UPDATE hebergements SET hotel=?, nb_nuits=?, designation=?, nb_chambres=?, tarif_nuit=? WHERE id=?",
                  (hotel, nb_nuits, designation, nb_chambres, tarif, heb_id))
        conn.commit()
        c.execute("SELECT mission_id FROM hebergements WHERE id=?", (heb_id,))
        mission_id = c.fetchone()[0]
        conn.close()
        return redirect(url_for('detail_mission', mission_id=mission_id))
    c.execute("SELECT * FROM hebergements WHERE id=?", (heb_id,))
    heb = c.fetchone()
    conn.close()
    return render_template('modifier_hebergement.html', heb=heb)

@app.route('/supprimer_hebergement/<int:heb_id>/<int:mission_id>')
def supprimer_hebergement(heb_id, mission_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM hebergements WHERE id=?", (heb_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('detail_mission', mission_id=mission_id))

@app.route('/ajouter_vehicule/<int:mission_id>', methods=['POST'])
def ajouter_vehicule(mission_id):
    itineraire = request.form['itineraire']
    type_v = request.form['type_voiture']
    nb_v = request.form['nb_voitures']
    nb_j = request.form['nb_jours']
    tarif = fix_decimal(request.form['tarif_jour'])
    noms_chauffeurs = request.form.get('noms_chauffeurs', '')
    nb_chauffeurs = request.form.get('nb_chauffeurs', 0)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO vehicules (mission_id, itineraire, type_voiture, nb_voitures, nb_jours, tarif_jour, noms_chauffeurs, nb_chauffeurs) VALUES (?,?,?,?,?,?,?,?)",
              (mission_id, itineraire, type_v, nb_v, nb_j, tarif, noms_chauffeurs, nb_chauffeurs))
    conn.commit()
    conn.close()
    return redirect(url_for('detail_mission', mission_id=mission_id))

@app.route('/modifier_vehicule/<int:veh_id>', methods=['GET', 'POST'])
def modifier_vehicule(veh_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if request.method == 'POST':
        itineraire = request.form['itineraire']
        type_v = request.form['type_voiture']
        nb_v = request.form['nb_voitures']
        nb_j = request.form['nb_jours']
        tarif = fix_decimal(request.form['tarif_jour'])
        noms_chauffeurs = request.form.get('noms_chauffeurs', '')
        nb_chauffeurs = request.form.get('nb_chauffeurs', 0)
        c.execute("UPDATE vehicules SET itineraire=?, type_voiture=?, nb_voitures=?, nb_jours=?, tarif_jour=?, noms_chauffeurs=?, nb_chauffeurs=? WHERE id=?",
                  (itineraire, type_v, nb_v, nb_j, tarif, noms_chauffeurs, nb_chauffeurs, veh_id))
        conn.commit()
        c.execute("SELECT mission_id FROM vehicules WHERE id=?", (veh_id,))
        mission_id = c.fetchone()[0]
        conn.close()
        return redirect(url_for('detail_mission', mission_id=mission_id))
    c.execute("SELECT * FROM vehicules WHERE id=?", (veh_id,))
    veh = c.fetchone()
    conn.close()
    return render_template('modifier_vehicule.html', veh=veh)

@app.route('/supprimer_vehicule/<int:veh_id>/<int:mission_id>')
def supprimer_vehicule(veh_id, mission_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM vehicules WHERE id=?", (veh_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('detail_mission', mission_id=mission_id))

@app.route('/cartes_sim')
def cartes_sim():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT cs.*, m.nom FROM cartes_sim cs JOIN missions m ON cs.mission_id = m.id ORDER BY cs.id DESC")
    sims = c.fetchall()
    c.execute("SELECT id, nom FROM missions ORDER BY nom")
    missions = c.fetchall()
    conn.close()
    return render_template('cartes_sim.html', sims=sims, missions=missions)

@app.route('/ajouter_sim', methods=['POST'])
def ajouter_sim():
    mission_id = request.form['mission_id']
    date_debut = request.form['date_debut']
    date_fin = request.form['date_fin']
    nb_sim = request.form['nb_sim']
    prix_sim = fix_decimal(request.form['prix_sim'])
    nb_forfait = request.form['nb_forfait']
    prix_forfait = fix_decimal(request.form['prix_forfait'])
    client = request.form['client']
    numero_devis = request.form['numero_devis']
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO cartes_sim (mission_id, date_debut, date_fin, nb_sim, prix_sim, nb_forfait, prix_forfait, client, numero_devis) VALUES (?,?,?,?,?,?,?,?,?)",
              (mission_id, date_debut, date_fin, nb_sim, prix_sim, nb_forfait, prix_forfait, client, numero_devis))
    conn.commit()
    conn.close()
    return redirect(url_for('cartes_sim'))

@app.route('/payer_sim/<int:sim_id>')
def payer_sim(sim_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT statut_paiement FROM cartes_sim WHERE id=?", (sim_id,))
    row = c.fetchone()
    nouveau = 'payé' if row[0] == 'non payé' else 'non payé'
    c.execute("UPDATE cartes_sim SET statut_paiement=? WHERE id=?", (nouveau, sim_id))
    conn.commit()
    conn.close()
    return redirect(url_for('cartes_sim'))

@app.route('/supprimer_sim/<int:sim_id>')
def supprimer_sim(sim_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM cartes_sim WHERE id=?", (sim_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('cartes_sim'))

@app.route('/devis_sim/<int:sim_id>')
def devis_sim(sim_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT cs.*, m.nom FROM cartes_sim cs JOIN missions m ON cs.mission_id = m.id WHERE cs.id=?", (sim_id,))
    sim = c.fetchone()
    conn.close()

    total_sim = fix_decimal(sim[5]) * int(sim[4])
    total_forfait = fix_decimal(sim[7]) * int(sim[6])
    total = total_sim + total_forfait

    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    fichier = os.path.join(static_dir, f"devis_sim_{sim_id}.pdf")

    contact_style = ParagraphStyle('cs', alignment=TA_CENTER, fontSize=8, fontName='Helvetica')
    contact_blue = ParagraphStyle('cb', alignment=TA_CENTER, fontSize=8, fontName='Helvetica', textColor=colors.blue)
    footer = make_footer(contact_style, contact_blue)

    doc = SimpleDocTemplate(fichier, pagesize=A4,
                            topMargin=0.5*cm, bottomMargin=3.5*cm,
                            leftMargin=1.5*cm, rightMargin=1.5*cm)

    center = ParagraphStyle('center', alignment=TA_CENTER, fontSize=12, fontName='Helvetica-Bold')
    right = ParagraphStyle('right', alignment=TA_RIGHT, fontSize=10, fontName='Helvetica')
    elements = []

    logo_path = os.path.join(static_dir, 'logo.jpg')
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=17*cm, height=2.5*cm))
    elements.append(Spacer(1, 20))

    num = sim[9] if sim[9] else f"SIM-00{sim[0]}"
    elements.append(Paragraph("<u>DEVIS</u>", center))
    elements.append(Paragraph(f"<u>SIM/Recharge TELEPHONE N° {num}</u>", center))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Doit :", right))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("A", right))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"<b>{sim[8]}</b>", right))
    elements.append(Spacer(1, 25))

    date_arr = format_date(sim[2])
    date_dep = format_date(sim[3])

    data = [
        ['Date', 'Nbre de SIM', 'Total SIM en\nEuros', 'Nbres de\nforfait', 'Total forfait\nen Euros', 'Total général\nen Euros'],
        [f"{date_arr}\nau\n{date_dep}", str(sim[4]), f"{total_sim:,.2f}", str(sim[6]), f"{total_forfait:,.2f}", f"{total:,.2f}"],
        ['', '', '', '', 'TOTAL', f"{total:,.2f}"]
    ]

    t = Table(data, colWidths=[2.8*cm, 2.5*cm, 3*cm, 2.5*cm, 3*cm, 3.2*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('SPAN', (0,-1), (3,-1)),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 25))

    lettres = nombre_en_lettres(total).capitalize()
    elements.append(Paragraph(
        f"Arrêté la présente facture à la somme de : <b>{lettres} euros ({total:,.2f} €)</b>",
        ParagraphStyle('lettres', fontSize=9, fontName='Helvetica')
    ))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Le responsable", ParagraphStyle('resp', alignment=TA_RIGHT, fontSize=10, fontName='Helvetica')))

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    return send_file(fichier, as_attachment=True)

@app.route('/packs_eau')
def packs_eau():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT pe.*, m.nom FROM packs_eau pe JOIN missions m ON pe.mission_id = m.id ORDER BY pe.id DESC")
    eaux = c.fetchall()
    c.execute("SELECT id, nom FROM missions ORDER BY nom")
    missions = c.fetchall()
    conn.close()
    return render_template('packs_eau.html', eaux=eaux, missions=missions)

@app.route('/ajouter_eau', methods=['POST'])
def ajouter_eau():
    mission_id = request.form['mission_id']
    date_debut = request.form['date_debut']
    date_fin = request.form['date_fin']
    designation = request.form['designation']
    prix_unitaire = fix_decimal(request.form['prix_unitaire'])
    nb_paquets = request.form['nb_paquets']
    client = request.form['client']
    numero_facture = request.form['numero_facture']
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO packs_eau (mission_id, date_debut, date_fin, designation, prix_unitaire, nb_paquets, client, numero_facture) VALUES (?,?,?,?,?,?,?,?)",
              (mission_id, date_debut, date_fin, designation, prix_unitaire, nb_paquets, client, numero_facture))
    conn.commit()
    conn.close()
    return redirect(url_for('packs_eau'))

@app.route('/payer_eau/<int:eau_id>')
def payer_eau(eau_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT statut_paiement FROM packs_eau WHERE id=?", (eau_id,))
    row = c.fetchone()
    nouveau = 'payé' if row[0] == 'non payé' else 'non payé'
    c.execute("UPDATE packs_eau SET statut_paiement=? WHERE id=?", (nouveau, eau_id))
    conn.commit()
    conn.close()
    return redirect(url_for('packs_eau'))

@app.route('/supprimer_eau/<int:eau_id>')
def supprimer_eau(eau_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM packs_eau WHERE id=?", (eau_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('packs_eau'))

@app.route('/facture_eau/<int:eau_id>')
def facture_eau(eau_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT pe.*, m.nom FROM packs_eau pe JOIN missions m ON pe.mission_id = m.id WHERE pe.id=?", (eau_id,))
    eau = c.fetchone()
    conn.close()

    total = fix_decimal(eau[5]) * int(eau[6])
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    fichier = os.path.join(static_dir, f"facture_eau_{eau_id}.pdf")

    contact_style = ParagraphStyle('cs', alignment=TA_CENTER, fontSize=8, fontName='Helvetica')
    contact_blue = ParagraphStyle('cb', alignment=TA_CENTER, fontSize=8, fontName='Helvetica', textColor=colors.blue)
    footer = make_footer(contact_style, contact_blue)

    doc = SimpleDocTemplate(fichier, pagesize=A4,
                            topMargin=0.5*cm, bottomMargin=3.5*cm,
                            leftMargin=1.5*cm, rightMargin=1.5*cm)

    center = ParagraphStyle('center', alignment=TA_CENTER, fontSize=12, fontName='Helvetica-Bold')
    right = ParagraphStyle('right', alignment=TA_RIGHT, fontSize=10, fontName='Helvetica')
    right_bold = ParagraphStyle('rightb', alignment=TA_RIGHT, fontSize=10, fontName='Helvetica-Bold')
    elements = []

    logo_path = os.path.join(static_dir, 'logo.jpg')
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=17*cm, height=2.5*cm))
    elements.append(Spacer(1, 20))

    num = eau[8] if eau[8] else f"EAU-00{eau[0]}"
    elements.append(Paragraph(f"<u>FACTURE EAU VIVE N° {num}</u>", center))
    elements.append(Spacer(1, 25))
    elements.append(Paragraph("<u><b>DOIT :</b></u>", right_bold))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"<b>{eau[7]}</b>", right))
    elements.append(Spacer(1, 25))

    date_arr = format_date(eau[2])
    date_dep = format_date(eau[3])

    data = [
        ['Date', 'Désignation', 'Prix Unitaire\nen Euros', 'Nbre Pqts', 'Montant\nen Euros'],
        [f"{date_arr}\nau\n{date_dep}", eau[4], f"{fix_decimal(eau[5]):,.2f}", str(eau[6]), f"{total:,.2f}"],
        ['', '', '', 'TOTAL', f"{total:,.2f} €"]
    ]

    t = Table(data, colWidths=[3*cm, 4.5*cm, 3.5*cm, 2.5*cm, 3*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('SPAN', (0,-1), (2,-1)),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 25))

    lettres = nombre_en_lettres(total).capitalize()
    elements.append(Paragraph(
        f"Arrêté la présente facture à la somme de : <b>{lettres} euros ({total:,.2f} €)</b>",
        ParagraphStyle('lettres', fontSize=9, fontName='Helvetica')
    ))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Le responsable", ParagraphStyle('resp', alignment=TA_RIGHT, fontSize=10, fontName='Helvetica')))

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    return send_file(fichier, as_attachment=True)

@app.route('/facture/<int:mission_id>')
def generer_facture(mission_id):
    m, hebs, vehs = get_mission(mission_id)
    total_heb = sum(fix_decimal(h[6]) * h[3] for h in hebs)
    total_veh = sum(fix_decimal(v[6]) * v[4] * v[5] for v in vehs)
    total = total_heb + total_veh

    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    fichier = os.path.join(static_dir, f"facture_mission_{mission_id}.pdf")

    contact_style = ParagraphStyle('cs', alignment=TA_CENTER, fontSize=8, fontName='Helvetica')
    contact_blue = ParagraphStyle('cb', alignment=TA_CENTER, fontSize=8, fontName='Helvetica', textColor=colors.blue)
    footer = make_footer(contact_style, contact_blue)

    doc = SimpleDocTemplate(fichier, pagesize=A4,
                            topMargin=0.5*cm, bottomMargin=3.5*cm,
                            leftMargin=1.5*cm, rightMargin=1.5*cm)

    center = ParagraphStyle('center', alignment=TA_CENTER, fontSize=11, fontName='Helvetica-Bold')
    normal_c = ParagraphStyle('normalc', alignment=TA_CENTER, fontSize=10, fontName='Helvetica')
    right = ParagraphStyle('right', alignment=TA_RIGHT, fontSize=10, fontName='Helvetica')
    style_note = ParagraphStyle('note', fontSize=9, fontName='Helvetica-BoldOblique', leftIndent=20)
    rib_style = ParagraphStyle('rib', alignment=TA_CENTER, fontSize=8, fontName='Helvetica')

    elements = []

    logo_path = os.path.join(static_dir, 'logo.jpg')
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=17*cm, height=2.5*cm))
    elements.append(Spacer(1, 8))

    num = m[7] if m[7] else f"00{m[0]}"
    date_arr = format_date(m[4])
    date_dep = format_date(m[5])

    elements.append(Paragraph(f"<u>FACTURE PROFORMA N° {num}</u>", center))
    elements.append(Paragraph(f"Du {date_arr} au {date_dep}", normal_c))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("A", right))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"<b>{m[2]}</b>", right))
    elements.append(Spacer(1, 10))

    if hebs:
        heb_data = [['DATE', 'HOTEL', 'Nbre\n/nuitées', 'Désignation', 'Nbres\nchambre',
                     'Tarif/nuitée\n*Vignette\ntouristique\n*Taxe de\nséjour\nen Euros', 'TOTAL']]
        for h in hebs:
            total_h = fix_decimal(h[6]) * h[3]
            heb_data.append([f"{date_arr}\nau\n{date_dep}", h[2], f"{h[3]:02d} nuits",
                              h[4], h[5], f"{fix_decimal(h[6]):,.2f} €", f"{total_h:,.2f} €"])
        heb_data.append(['', '', '', 'Sous total', '', '', f"{total_heb:,.2f} €"])
        t_heb = Table(heb_data, colWidths=[2*cm, 3*cm, 1.5*cm, 3.2*cm, 2.2*cm, 2.3*cm, 2.3*cm])
        t_heb.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('SPAN', (3,-1), (5,-1)),
        ]))
        elements.append(t_heb)
        elements.append(Spacer(1, 8))

    if vehs:
        veh_data = [['DATE', 'ITINERAIRE', 'TYPE\nDE VOITURE', 'Nbres de\nvoiture',
                     'Nbres\nde jour', 'Tarif/jour\nen Euros', 'TOTAL']]
        for v in vehs:
            total_v = fix_decimal(v[6]) * v[4] * v[5]
            veh_data.append([f"{date_arr}\nau\n{date_dep}", v[2], v[3],
                              f"{v[4]:02d}", f"{v[5]:02d} jours",
                              f"{fix_decimal(v[6]):,.2f}", f"{total_v:,.2f} €"])
        veh_data.append(['', '', '', '', 'Sous total', '', f"{total_veh:,.2f} €"])
        t_veh = Table(veh_data, colWidths=[2*cm, 2.5*cm, 2.5*cm, 1.8*cm, 2*cm, 2.5*cm, 2.2*cm])
        t_veh.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('SPAN', (4,-1), (5,-1)),
        ]))
        elements.append(t_veh)
        elements.append(Spacer(1, 4))

    total_data = [['', '', '', '', '', 'Total\ngénéral', f"{total:,.2f} €"]]
    t_total = Table(total_data, colWidths=[2*cm, 2.5*cm, 2.5*cm, 1.8*cm, 2*cm, 2.5*cm, 2.2*cm])
    t_total.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))
    elements.append(t_total)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b><i>• Carburant à la charge du client selon le trajet</i></b>", style_note))
    elements.append(Spacer(1, 8))

    lettres = nombre_en_lettres(total).capitalize()
    elements.append(Paragraph(
        f"Arrêtée à la somme de : <b>{lettres} euros ({total:,.2f} €)</b>",
        ParagraphStyle('lettres', fontSize=9, fontName='Helvetica')
    ))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Compte : Mr LABORDE Joseph Rolland, Lot VO 3 A Miandrarivo Ambanidia", rib_style))
    elements.append(Paragraph("Antananarivo 101 MADAGASCAR", rib_style))
    elements.append(Paragraph("Code Banque : 00009 ; Code guichet : 05500 ; N° compte : 23002400009 ; Clé rib : 93 ; Domiciliation : BOA MADAGASCAR", rib_style))
    elements.append(Paragraph("IBAN : MG46 0000 9055 0023 0024 0000 993 ; SWIFT : AFRIMGMGXXX", rib_style))

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    return send_file(fichier, as_attachment=True)

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js')

@app.route('/enregistrer_mission/<int:mission_id>', methods=['POST'])
def enregistrer_mission(mission_id):

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE missions
        SET statut = 'Terminée'
        WHERE id = ?
    """, (mission_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('accueil'))


conn = sqlite3.connect(DB)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE missions ADD COLUMN statut TEXT DEFAULT 'En cours'")
    conn.commit()
except:
    pass

conn.close()



@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    init_db()
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    try:
        hostname = socket.gethostbyname(socket.gethostname())
        print(f"\n✅ Application accessible sur : http://{hostname}:5000\n")
    except:
        pass
    app.run(debug=True, host='0.0.0.0', port=5000)

    