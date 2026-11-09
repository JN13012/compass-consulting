"""Generates the 50 fictitious B2B orders of the Maison Lumen demo (deterministic).

Expected values are computed here, from the same random draw that writes the e-mail: they are never typed by hand
nor produced by a model. 40 orders are complete; 10 are ambiguous and must be refused (expected = null).

    python poc_examples/commandes/data/generate.py   ->  poc_examples/commandes/data/commandes.jsonl
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
CATALOG = json.loads((HERE.parent / "catalog.json").read_text("utf-8"))
SENT = date(2026, 11, 20)  # every e-mail is dated 20/11/2026

CLIENTS = [
    ("Atelier Neuf", "Lyon", "Claire Moreau"), ("Maison Berthe", "Bordeaux", "Julien Petit"),
    ("Le Comptoir des Lices", "Rennes", "Sophie Lambert"), ("Galerie Sainte-Anne", "Nantes", "Marc Fontaine"),
    ("Boutique Odette", "Lille", "Inès Garnier"), ("Concept Riviera", "Nice", "Thomas Roux"),
    ("La Malle d'Hugo", "Strasbourg", "Hugo Vidal"), ("Studio Capucine", "Toulouse", "Léa Mercier"),
    ("Les Arcades", "Annecy", "Paul Girard"), ("Comptoir Garonne", "Agen", "Nadia Benali"),
]
WORDS = {1: "une", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq", 6: "six", 8: "huit", 10: "dix"}
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre"]
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def fmt_date(d: date, style: int) -> str:
    return [
        d.strftime("%d/%m/%Y"),
        f"le {d.day} {MONTHS[d.month - 1]}",
        f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}",
        d.isoformat(),
    ][style]


def qty(n: int, rng: random.Random) -> str:
    return WORDS[n] if n in WORDS and rng.random() < 0.3 else str(n)


def product(p: dict[str, object], rng: random.Random) -> str:
    r = rng.random()
    if r < 0.4:
        return str(p["reference"])
    if r < 0.8:
        return str(p["designation"])
    return f"{p['designation']} (réf. {p['reference']})"


def render(client: tuple[str, str, str], lines: list[tuple[dict[str, object], int]], due: date,
           rng: random.Random) -> str:
    name, city, contact = client
    head = f"De : {contact} <commandes@{name.lower().replace(' ', '').replace(chr(39), '')}.fr>\n" \
           f"Date : {SENT.strftime('%d/%m/%Y')}\nObjet : "
    d = fmt_date(due, rng.randrange(4))
    style = rng.randrange(4)
    if style == 0:  # formal e-mail
        body = "\n".join(f"- {qty(q, rng)} x {product(p, rng)}" for p, q in lines)
        return (f"{head}Commande {name}\n\nBonjour,\n\nPour notre boutique {name} ({city}), merci de bien vouloir "
                f"enregistrer la commande suivante :\n{body}\n\nLivraison souhaitée : {d}.\n\n"
                f"Bien cordialement,\n{contact}")
    if style == 1:  # short e-mail, inline
        body = ", ".join(f"{qty(q, rng)} {product(p, rng)}" for p, q in lines)
        return f"{head}réassort\n\nSalut, pour {name} il nous faudrait {body}. Livraison {d} si possible. " \
               f"Merci !\n{contact.split()[0]}"
    if style == 2:  # text extracted from a PDF order form
        rows = "\n".join(f"{p['reference']:<18}| {p['designation']:<28}| {q}" for p, q in lines)
        return (f"{head}Bon de commande\n\nVeuillez trouver ci-joint notre bon de commande.\n\n"
                f"[Pièce jointe : bon_de_commande.pdf - texte extrait]\nBON DE COMMANDE N° BC-{rng.randint(1000, 9999)}"
                f"\nClient : {name} - {city}\nDate de livraison : {d}\n\nRéférence         | Désignation"
                f"                 | Qté\n{rows}\n\nSignature : {contact}")
    body = "\n".join(f"{product(p, rng)} : {qty(q, rng)}" for p, q in lines)  # list with a note in between
    return (f"{head}Commande pour la saison\n\nBonjour l'équipe Lumen,\n\nNos clientes adorent la collection ! "
            f"Voici ce que {name} souhaite recevoir :\n{body}\n\nÀ livrer {d} au plus tard, à l'adresse "
            f"habituelle de {city}.\n\nMerci, {contact}")


def clear_case(i: int, rng: random.Random) -> dict[str, object]:
    client = rng.choice(CLIENTS)
    items = rng.sample(CATALOG, rng.randint(1, 4))
    lines = [(p, rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 12])) for p in items]
    due = SENT + timedelta(days=rng.randint(5, 70))
    return {
        "id": f"CMD-{i:02d}",
        "input": render(client, lines, due, rng),
        "expected": {
            "client": client[0],
            "date_livraison": due.isoformat(),
            "lignes": sorted(({"reference": p["reference"], "quantite": q} for p, q in lines),
                             key=lambda x: str(x["reference"])),
            "total_ht": round(sum(float(p["prix_ht"]) * q for p, q in lines), 2),  # type: ignore[arg-type]
        },
    }


AMBIGUOUS = [  # (reason, e-mail) - a human must be asked; the agent must refuse
    ("quantité absente", "Bonjour, pour Atelier Neuf merci de nous envoyer des Pochettes Nova et des foulards "
                         "soie imprimés, livraison le 4 décembre. Claire"),
    ("couleur du sac Iris non précisée", "Bonjour, Maison Berthe souhaite 3 sacs Iris et 2 ceintures Lin, "
                                         "livraison 10/12/2026. Merci, Julien Petit"),
    ("produit hors catalogue", "Bonjour, pour Studio Capucine : 4 x Bottines Lumen cuir velours, 2 x Pull "
                               "cachemire col rond. Livraison le 8 décembre. Léa"),
    ("renvoi à une commande précédente", "Salut, même commande que le mois dernier pour Les Arcades, livraison "
                                         "début décembre. Paul"),
    ("quantités contradictoires", "Bonjour, Galerie Sainte-Anne : 6 Écharpes cachemire. Finalement non, mettez-en "
                                  "4... ou 5, je vous confirme demain. Livraison le 15/12/2026. Marc"),
    ("client non identifiable", "Bonjour, merci d'envoyer 2 Manteaux laine double face et 3 Gants agneau pour le "
                                "12 décembre. Bonne journée"),
    ("date de livraison absente", "Bonjour, pour Boutique Odette : 5 LUM-POR-CART et 2 LUM-CAB-ALBA. "
                                  "Merci, Inès Garnier"),
    ("commande annulée", "Bonjour, Concept Riviera annule la commande de 3 Sacs Iris cuir camel prévue le "
                         "9 décembre. Thomas Roux"),
    ("simple question, pas une commande", "Bonjour, avez-vous encore des Chemises popeline blanches en stock pour "
                                          "La Malle d'Hugo ? Merci, Hugo Vidal"),
    ("référence illisible", "[Pièce jointe : bon_de_commande.pdf - texte extrait]\nBON DE COMMANDE\nClient : Comptoir "
                            "Garonne - Agen\nDate de livraison : 03/12/2026\nLUM-???-?  | ill1s1ble | 4\n"
                            "LUM-GAN-AGN | Gants agneau | 2\nSignature : Nadia Benali"),
]


def main() -> None:
    rng = random.Random(20261109)
    cases = [clear_case(i + 1, rng) for i in range(40)]
    for j, (reason, text) in enumerate(AMBIGUOUS, start=41):
        head = f"De : client\nDate : {SENT.strftime('%d/%m/%Y')}\nObjet : commande\n\n"
        cases.append({"id": f"CMD-{j:02d}", "input": head + text, "expected": None, "note": reason})
    out = HERE / "commandes.jsonl"
    out.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), "utf-8")
    print(f"{len(cases)} cas -> {out}")


if __name__ == "__main__":
    main()
