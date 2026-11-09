"""Three fictitious demo missions (SPEC §10). Companies, people and figures are invented."""

from __future__ import annotations

from typing import Any

DEMO_MISSIONS: list[dict[str, Any]] = [
    {
        "client": "Maison Lumen",
        "sector": "Distribution - prêt-à-porter haut de gamme",
        "focus": ["ia", "blockchain"],
        "confidentiality": "public",
        "context": (
            "Distributeur de prêt-à-porter haut de gamme (120 salariés, 14 boutiques en France, e-shop). "
            "Souhaite réduire les tâches manuelles et lutter contre la contrefaçon."
        ),
        "notes": """Entretien avec la directrice des opérations et le responsable logistique.

Commandes B2B (revendeurs multimarques) : environ 900 commandes par mois, reçues par e-mail, souvent en PDF ou en
photo de bon de commande. Deux assistantes ressaisissent chaque commande dans un tableur Excel partagé, puis dans
l'ERP (Sage). Ressaisie estimée à 6 minutes par commande. Environ 4 % d'erreurs (références, quantités), découvertes
à la livraison, avec avoirs et retours coûteux.

Facturation : factures générées depuis l'ERP mais rapprochement manuel avec les bons de livraison, chaque fin de mois,
3 jours de travail pour la comptable.

Service client : 40 % des appels et e-mails concernent « où en est ma livraison ? ». Les numéros de suivi des
transporteurs sont copiés à la main dans le tableur.

Contrefaçon : des copies des sacs iconiques circulent sur les plateformes de revente. Les clients du marché de la
seconde main demandent une preuve d'authenticité. La marque aimerait aussi préparer le passeport numérique des
produits demandé par la réglementation européenne sur l'écoconception.

Données : les fichiers clients (35 000 contacts) sont dans l'ERP et dans le CRM de l'e-shop, avec des doublons.
Pas de responsable data. Le DSI externalisé est favorable à une API ERP mais n'a jamais connecté d'outils.
La direction veut des résultats visibles en moins de 6 mois et un budget maîtrisé.""",
    },
    {
        "client": "Banque Azur",
        "sector": "Banque régionale",
        "focus": ["blockchain", "ia"],
        "confidentiality": "confidentiel",
        "context": (
            "Banque régionale (2 300 salariés, 600 000 clients). Étudie le lancement d'un fonds monétaire tokenisé "
            "réglé en stablecoin euro et l'automatisation du contrôle KYC des investisseurs."
        ),
        "notes": """Entretien avec le directeur de l'innovation, la directrice de la conformité et le RSSI.

Projet 1 - Fonds monétaire tokenisé : la filiale de gestion d'actifs voudrait émettre les parts d'un fonds monétaire
sous forme de jetons sur une blockchain publique, accessibles à des investisseurs professionnels. Les souscriptions
et rachats seraient réglés dans un stablecoin euro émis par un établissement de crédit partenaire. La banque se
demande si les parts tokenisées relèvent de MiCA ou de la réglementation des instruments financiers, et si elle doit
obtenir un agrément supplémentaire. Elle veut pouvoir geler des jetons sur décision de justice et restreindre les
transferts aux investisseurs dont le KYC est validé.

Projet 2 - Contrôle KYC par IA : 1 200 dossiers d'investisseurs professionnels par an, contrôlés à la main
(extraits Kbis, pièces d'identité des dirigeants, bénéficiaires effectifs). La conformité veut un outil qui lit les
pièces, détecte les incohérences et prépare la décision, l'analyste gardant la décision finale.

Contraintes : données clients strictement confidentielles, hébergement en France, la banque est soumise à DORA.
Le RSSI rappelle que tout nouveau prestataire TIC doit entrer dans le registre des contrats et être testé.
La direction veut une feuille de route et un premier pilote en 9 mois.""",
    },
    {
        "client": "Hexa Industrie",
        "sector": "Industrie - fabricant de capteurs connectés",
        "focus": ["cyber", "ia"],
        "confidentiality": "public",
        "context": (
            "ETI industrielle (450 salariés, 95 M€ de chiffre d'affaires) qui conçoit et fabrique des capteurs "
            "connectés pour l'industrie (vibrations, température), vendus dans toute l'Union européenne."
        ),
        "notes": """Entretien avec le directeur général, le DSI et le responsable produit.

Système d'information : Active Directory vieillissant (serveurs de 2014), comptes administrateurs partagés,
pas d'authentification multifacteur, y compris pour l'accès VPN des commerciaux. Sauvegardes quotidiennes sur un NAS
dans la même salle serveur, jamais testées en restauration. Pas d'inventaire à jour des postes et serveurs.

Incidents : une tentative de rançongiciel il y a 18 mois, bloquée par chance. Aucun plan de réponse à incident,
personne ne sait qui prévenir ni dans quel délai. La direction découvre qu'elle pourrait être concernée par NIS 2.

Produits : les capteurs embarquent un firmware et communiquent avec une plateforme cloud. Les mises à jour du
firmware sont faites à la main par les techniciens chez les clients. Pas de processus pour recevoir ou traiter les
signalements de vulnérabilités. Les clients industriels commencent à exiger des preuves de sécurité dans les
appels d'offres.

Équipe : 4 personnes à la DSI, pas de RSSI, budget sécurité non identifié. Le SOC est envisagé mais jugé trop cher.
Le DSI aimerait utiliser l'IA pour trier les alertes de sécurité, trop nombreuses pour l'équipe.
La direction demande une feuille de route réaliste sur 12 mois et les obligations réglementaires prioritaires.""",
    },
]


# Interview grids already filled for the demo missions (question id -> client answer), consistent with the notes.
DEMO_INTERVIEWS: dict[str, dict[str, Any]] = {
    "Maison Lumen": {
        "checked": [
            "Organigramme et interlocuteurs clés",
            "Exemples réels de fichiers Excel, documents ou formulaires traités"],
        "answers": {
            "C1": "Distributeur de prêt-à-porter haut de gamme, 120 salariés, 14 boutiques en France et un e-shop.",
            "C2": "La directrice des opérations porte le projet, la direction générale valide le budget.",
            "C3": "Les erreurs de commande coûtent cher et des "
                  "copies de nos sacs circulent sur les sites de revente.",
            "C4": "Plus de ressaisie des commandes, moins de 1 % d'erreurs "
                  "et une preuve d'authenticité pour nos clients.",
            "C5": "Les commandes B2B arrivent par e-mail, souvent en PDF ou en photo. Deux assistantes "
                  "les ressaisissent "
                  "dans un tableur Excel partagé, puis dans l'ERP (Sage).",
            "C6": "Environ 900 commandes par mois, 6 minutes de ressaisie par commande. La comptable passe 3 jours "
                  "chaque fin de mois sur le rapprochement des factures.",
            "C7": "Environ 4 % d'erreurs (références, quantités), découvertes à la livraison, avec avoirs et retours "
                  "coûteux. 40 % des appels concernent « où en est ma livraison ? ».",
            "C8": "Sage pour l'ERP, le CRM de l'e-shop, Excel partagé. Rien n'est connecté.",
            "C9": "35 000 contacts clients entre l'ERP et le CRM, avec des doublons. Pas de responsable data.",
            "C10": "Résultats visibles en moins de 6 mois, budget maîtrisé. "
                   "Le DSI externalisé est favorable à une API ERP.",
            "IA1": "La ressaisie des commandes et les réponses sur le suivi des livraisons.",
            "IA2": "Des bons de commande en PDF ou en photo, environ 900 par mois.",
            "IA3": "Une assistante validerait chaque commande avant l'envoi dans l'ERP.",
            "B1": "Les revendeurs, les clients de seconde main et la marque doivent pouvoir vérifier l'authenticité.",
            "B3": "Des produits physiques (sacs) avec un certificat d'authenticité, et le passeport numérique produit.",
        },
    },
    "Banque Azur": {
        "checked": ["Schéma des flux (qui envoie quoi à qui)", "Agréments et autorisations en vigueur"],
        "answers": {
            "C1": "Banque régionale, 2 300 salariés, 600 000 clients, avec une filiale de gestion d'actifs.",
            "C2": "Le directeur de l'innovation porte le projet, avec la directrice de la conformité et le RSSI.",
            "C3": "Les grandes banques lancent des fonds tokenisés et le contrôle KYC manuel ne suit plus.",
            "C4": "Un premier pilote en 9 mois et une feuille de route validée par la conformité.",
            "C5": "Chaque dossier d'investisseur professionnel est contrôlé à la main : Kbis, pièces d'identité des "
                  "dirigeants, bénéficiaires effectifs.",
            "C6": "1 200 dossiers d'investisseurs professionnels par an.",
            "C11": "La banque est soumise à DORA. Elle se demande si les parts tokenisées relèvent de MiCA ou de la "
                   "réglementation des instruments financiers.",
            "IA3": "L'outil prépare la décision, l'analyste garde la décision finale.",
            "IA4": "Données clients strictement confidentielles, hébergement en France obligatoire.",
            "B3": "Des parts d'un fonds monétaire émises sous forme de jetons, réglées dans un stablecoin euro émis "
                  "par un établissement de crédit partenaire.",
            "B4": "La filiale de gestion émet les parts ; le stablecoin est émis par un partenaire.",
            "B5": "Uniquement des investisseurs professionnels.",
            "B7": "Oui : geler des jetons sur décision de justice et restreindre les transferts aux investisseurs dont "
                  "le KYC est validé.",
        },
    },
    "Hexa Industrie": {
        "checked": ["Configuration des accès à distance et de la messagerie (MFA)"],
        "answers": {
            "C1": "ETI de 450 salariés, 95 M€ de chiffre d'affaires, capteurs connectés vendus dans toute l'UE.",
            "C3": "Une tentative de rançongiciel il y a 18 mois, et les clients exigent des preuves de sécurité dans "
                  "les appels d'offres.",
            "C4": "Une feuille de route réaliste sur 12 mois et les obligations réglementaires prioritaires.",
            "C10": "4 personnes à la DSI, pas de RSSI, budget sécurité non identifié. Un SOC est jugé trop cher.",
            "S1": "Pas de RSSI ni de politique de sécurité écrite.",
            "S2": "Pas d'inventaire à jour des postes et serveurs. Active Directory vieillissant (serveurs de 2014).",
            "S3": "Comptes administrateurs partagés, pas d'authentification multifacteur, y compris pour le VPN des "
                  "commerciaux.",
            "S4": "Sauvegardes quotidiennes sur un NAS dans la même salle serveur, jamais testées en restauration.",
            "S5": "Les alertes sont trop nombreuses pour l'équipe, personne ne les trie vraiment.",
            "S6": "Aucun plan de réponse à incident, personne ne sait qui prévenir ni dans quel délai.",
            "S7": "Industrie manufacturière, 450 salariés, 95 M€ de chiffre d'affaires. "
                  "La direction découvre NIS 2.",
            "S8": "Oui : les capteurs embarquent un firmware et communiquent avec une plateforme cloud. "
                  "Les mises à jour "
                  "sont faites à la main chez les clients, pas de processus pour les signalements de vulnérabilités.",
            "IA1": "Le tri des alertes de sécurité, trop nombreuses pour l'équipe.",
        },
    },
}
