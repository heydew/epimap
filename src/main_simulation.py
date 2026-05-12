import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from pathlib import Path
from io_data import get_pop
from model import ConfigMaladie, MoteurSEIRDV
from scenarios import (
    Confinement, Vaccination, NouveauVariant,
    MesuresSanitaires, LeveeRestrictions, FermetureFrontieres
)
from scenarios_predefinis import SCENARIOS
import viz_curves
import viz_map
import threading

OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(exist_ok=True)
GEO = Path(__file__).resolve().parents[1] / "data" / "world-countries.geojson"
POP = Path(__file__).resolve().parents[1] / "data" / "population.csv"


def lbl(parent, text, row, col, **kw):
    tk.Label(parent, text=text, anchor="w", **kw).grid(row=row, column=col, sticky="w", padx=6, pady=3)

def entry(parent, var, row, col, width=14):
    tk.Entry(parent, textvariable=var, width=width).grid(row=row, column=col, padx=6, pady=3)

def slider(parent, var, from_, to, row, col, resolution=0.01):
    tk.Scale(parent, variable=var, from_=from_, to=to, orient="horizontal",
             resolution=resolution, length=220).grid(row=row, column=col, padx=6, pady=2, sticky="w")

#événement

class FenetreEvenement(tk.Toplevel):
    def __init__(self, parent, pays_valides, callback):
        super().__init__(parent)
        self.title("Ajouter un événement")
        self.resizable(False, False)
        self.pays_valides = sorted(pays_valides)
        self.callback = callback
        self.result = None
        self._build()
        self.grab_set()

    def _build(self):
        f = tk.Frame(self, padx=12, pady=8)
        f.pack(fill="both", expand=True)


        lbl(f, "Type :", 0, 0)
        self.type_var = tk.StringVar(value="Confinement")
        types = ["Confinement", "Vaccination", "Nouveau variant",
                 "Mesures sanitaires", "Levée des restrictions", "Fermeture des frontières"]
        cb = ttk.Combobox(f, textvariable=self.type_var, values=types, state="readonly", width=24)
        cb.grid(row=0, column=1, padx=6, pady=3, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda _: self._refresh_champs())


        # date
        lbl(f, "Date (YYYY-MM-DD) :", 1, 0)
        self.date_var = tk.StringVar(value="2020-01-01")
        entry(f, self.date_var, 1, 1, width=14)

        # pays (tous ou un seul)
        lbl(f, "Pays (vide = tous) :", 2, 0)
        self.pays_var = tk.StringVar()
        self.pays_cb = ttk.Combobox(f, textvariable=self.pays_var,
                                    values=[""] + self.pays_valides, width=22)
        self.pays_cb.grid(row=2, column=1, padx=6, pady=3, sticky="w")




        # cadre champs dynamiques
        self.champs_frame = tk.LabelFrame(f, text="Paramètres", padx=8, pady=6)
        self.champs_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=6)
        self._refresh_champs()

        tk.Button(f, text="Ajouter", command=self._valider, bg="#4A90D9", fg="white",
                  width=12).grid(row=4, column=0, columnspan=2, pady=8)

    def _clear_champs(self):
        for w in self.champs_frame.winfo_children():
            w.destroy()

    def _refresh_champs(self):
        self._clear_champs()
        t = self.type_var.get()
        cf = self.champs_frame

        if t == "Confinement":
            lbl(cf, "Réduction contagiosité (0-1) :", 0, 0)
            self.red_var = tk.DoubleVar(value=0.6)
            slider(cf, self.red_var, 0, 1, 0, 1)
            lbl(cf, "Durée (jours) :", 1, 0)
            self.duree_var = tk.IntVar(value=90)
            tk.Spinbox(cf, from_=1, to=730, textvariable=self.duree_var, width=8).grid(row=1, column=1, padx=6)

        elif t == "Vaccination":
            lbl(cf, "Taux quotidien (0-1) :", 0, 0)
            self.taux_var = tk.DoubleVar(value=0.005)
            slider(cf, self.taux_var, 0, 0.05, 0, 1, resolution=0.001)

        elif t == "Nouveau variant":
            self.modif_r0 = tk.BooleanVar(value=True)
            tk.Checkbutton(cf, text="Modifier R0", variable=self.modif_r0).grid(row=0, column=0, sticky="w")
            self.new_r0 = tk.DoubleVar(value=5.0)
            slider(cf, self.new_r0, 0.5, 20, 0, 1, resolution=0.1)

            self.modif_ifr = tk.BooleanVar(value=False)
            tk.Checkbutton(cf, text="Modifier mortalité", variable=self.modif_ifr).grid(row=1, column=0, sticky="w")
            self.new_ifr = tk.DoubleVar(value=0.01)
            slider(cf, self.new_ifr, 0, 1, 1, 1)

        elif t == "Mesures sanitaires":
            lbl(cf, "Réduction permanente (0-1) :", 0, 0)
            self.red_var = tk.DoubleVar(value=0.3)
            slider(cf, self.red_var, 0, 1, 0, 1)

        elif t == "Fermeture des frontières":
            lbl(cf, "Durée (jours) :", 0, 0)
            self.duree_var = tk.IntVar(value=90)
            tk.Spinbox(cf, from_=1, to=730, textvariable=self.duree_var, width=8).grid(row=0, column=1, padx=6)

        # ban les restrictions

    def _valider(self):
        date = self.date_var.get().strip()
        try:
            pd.Timestamp(date)
        except Exception:
            messagebox.showerror("Erreur", "Date invalide (YYYY-MM-DD)")
            return

        pays_raw = self.pays_var.get().strip()
        pays = pays_raw if pays_raw else None
        if pays and pays not in self.pays_valides:
            messagebox.showerror("Erreur", f"Pays introuvable : {pays}")
            return

        t = self.type_var.get()
        try:
            if t == "Confinement":
                ev = Confinement(date, self.red_var.get(), self.duree_var.get(), pays)
            elif t == "Vaccination":
                ev = Vaccination(date, self.taux_var.get(), pays)
            elif t == "Nouveau variant":
                r0  = self.new_r0.get()  if self.modif_r0.get()  else None
                ifr = self.new_ifr.get() if self.modif_ifr.get() else None
                ev = NouveauVariant(date, r0, ifr, pays)
            elif t == "Mesures sanitaires":
                ev = MesuresSanitaires(date, self.red_var.get(), pays)
            elif t == "Levée des restrictions":
                ev = LeveeRestrictions(date, pays)
            elif t == "Fermeture des frontières":
                ev = FermetureFrontieres(date, self.duree_var.get(), pays)
            else:
                return
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return

        self.callback(ev, t, date, pays)
        self.destroy()


#interface de base

class AppSimulation(tk.Tk):
    def __init__(self, pop, pays_valides):
        super().__init__()
        self.title("EpiMap — Simulation")
        self.resizable(False, False)
        self.pop = pop
        self.pays_valides = sorted(pays_valides)
        self.evenements = []
        self._build()

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_scenario = tk.Frame(nb, padx=10, pady=8)
        self.tab_maladie  = tk.Frame(nb, padx=10, pady=8)
        self.tab_evs      = tk.Frame(nb, padx=10, pady=8)

        nb.add(self.tab_scenario, text="  Scénario  ")
        nb.add(self.tab_maladie,  text="  Maladie   ")
        nb.add(self.tab_evs,      text="  Événements")

        self._build_scenario()
        self._build_maladie()
        self._build_evenements()

        # barre du bas
        bas = tk.Frame(self, pady=6)
        bas.pack(fill="x", padx=10)
        self.log_var = tk.StringVar(value="Prêt.")
        tk.Label(bas, textvariable=self.log_var, anchor="w", fg="#555").pack(side="left", fill="x", expand=True)
        tk.Button(bas, text="▶  Lancer la simulation", command=self._lancer,
                  bg="#27ae60", fg="white", font=("", 11, "bold"),
                  padx=16, pady=6).pack(side="right")

    #scénario
    def _build_scenario(self):
        f = self.tab_scenario
        tk.Label(f, text="Choisir un scénario prédéfini :", anchor="w",
                 font=("", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.scenario_var = tk.StringVar(value="0")
        options = [("0", "Personnalisé (configurer onglet Maladie)")]
        for k, (nom, _) in SCENARIOS.items():
            options.append((k, nom))

        for i, (val, label) in enumerate(options):
            tk.Radiobutton(f, text=label, variable=self.scenario_var,
                           value=val, anchor="w").grid(row=i+1, column=0, sticky="w", pady=2)

    # maladie custom
    def _build_maladie(self):
        f = self.tab_maladie

        champs = [
            ("Nom de la maladie :",              "nom",        "str",   "Ma maladie"),
            ("R0  (grippe≈1.3 · covid≈2.5) :",  "r0",         "slide", (0.5, 20, 2.5, 0.1)),
            ("Incubation (jours) :",             "incub",      "slide", (1, 30, 5, 0.5)),
            ("Contagiosité (jours) :",           "contag",     "slide", (1, 30, 10, 0.5)),
            ("Mortalité (0–1) :",                "mortalite",  "slide", (0, 1, 0.01, 0.001)),
            ("Pays d'origine :",                 "origine",    "combo", None),
            ("Date début (YYYY-MM-DD) :",        "date_debut", "str",   "2020-01-01"),
            ("Date fin   (YYYY-MM-DD) :",        "date_fin",   "str",   "2022-01-01"),
            ("Infectés initiaux :",              "infectes0",  "spin",  (1, 100000, 67)),
            ("Vitesse propagation (0–1) :",      "vitesse",    "slide", (0, 1, 0.3, 0.01)),
        ]

        self.vars = {}
        for row, (label, key, typ, opt) in enumerate(champs):
            lbl(f, label, row, 0)
            if typ == "str":
                v = tk.StringVar(value=opt)
                entry(f, v, row, 1, width=18)
            elif typ == "slide":
                from_, to, default, res = opt
                v = tk.DoubleVar(value=default)
                slider(f, v, from_, to, row, 1, resolution=res)
            elif typ == "combo":
                v = tk.StringVar(value="China")
                cb = ttk.Combobox(f, textvariable=v, values=self.pays_valides,
                                  width=22, state="normal")
                cb.grid(row=row, column=1, padx=6, pady=3, sticky="w")
            elif typ == "spin":
                from_, to, default = opt
                v = tk.IntVar(value=default)
                tk.Spinbox(f, from_=from_, to=to, textvariable=v, width=10).grid(
                    row=row, column=1, padx=6, pady=3, sticky="w")
            self.vars[key] = v

    # événements
    def _build_evenements(self):
        f = self.tab_evs

        tk.Button(f, text="+ Ajouter un événement", command=self._ajouter_ev,
                  bg="#4A90D9", fg="white").pack(anchor="w", pady=(0, 8))

        cols = ("Type", "Date", "Pays")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160)
        self.tree.pack(fill="both", expand=True)

        tk.Button(f, text="Supprimer sélection", command=self._suppr_ev,
                  fg="red").pack(anchor="w", pady=4)

    def _ajouter_ev(self):
        FenetreEvenement(self, self.pays_valides, self._on_ev_ajout)

    def _on_ev_ajout(self, ev, type_label, date, pays):
        self.evenements.append(ev)
        self.tree.insert("", "end", values=(type_label, date, pays or "Tous"))

    def _suppr_ev(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self.tree.delete(sel[0])
        self.evenements.pop(idx)

    # lancer
    def _lancer(self):
        choix = self.scenario_var.get()

        if choix in SCENARIOS:
            _, fn = SCENARIOS[choix]
            maladie, date_fin, evenements = fn()
        else:
            # validation maladie custom
            try:
                nom       = self.vars["nom"].get().strip() or "Maladie"
                r0        = float(self.vars["r0"].get())
                incub     = float(self.vars["incub"].get())
                contag    = float(self.vars["contag"].get())
                mortalite = float(self.vars["mortalite"].get())
                origine   = self.vars["origine"].get().strip()
                date_deb  = self.vars["date_debut"].get().strip()
                date_fin  = self.vars["date_fin"].get().strip()
                infectes0 = int(self.vars["infectes0"].get())
                vitesse   = float(self.vars["vitesse"].get())

                pd.Timestamp(date_deb)
                pd.Timestamp(date_fin)
                if origine not in self.pays_valides:
                    raise ValueError(f"Pays d'origine introuvable : {origine}")
            except Exception as e:
                messagebox.showerror("Paramètres invalides", str(e))
                return

            maladie = ConfigMaladie(
                nom=nom, r0=r0, jours_incubation=incub, jours_contagieux=contag,
                taux_mortalite=mortalite, pays_origine=origine, date_debut=date_deb,
                infectes_initiaux=infectes0, vitesse_propagation=vitesse,
            )
            evenements = self.evenements

        self.log_var.set("Simulation en cours…")
        self.update()

        def run():
            try:
                plage = pd.date_range(start=maladie.date_debut, end=date_fin, freq="D")
                moteur = MoteurSEIRDV(maladie, self.pop, str(GEO))
                data = moteur.simuler(plage, evenements)

                world = data.groupby("date")[["S", "E", "I", "R", "D", "V"]].sum().reset_index()

                f_courbes = str(OUT / "simulation_courbes.html")
                f_carte   = str(OUT / "simulation_carte.html")
                viz_curves.tracer_seirdv(world, maladie.nom, f_courbes)
                viz_map.carte_simulation(data, str(GEO), f_carte, maladie.nom)

                self.log_var.set(
                    f"Terminé — pic infectés : {world['I'].max():,.0f} · "
                    f"décès : {world['D'].iloc[-1]:,.0f}"
                )
                viz_curves.out(f_courbes)
                viz_map.out(f_carte)
            except Exception as e:
                self.log_var.set(f"Erreur : {e}")
                messagebox.showerror("Erreur simulation", str(e))

        threading.Thread(target=run, daemon=True).start()


# ─── main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pop = get_pop(p=str(POP))
    pop = pop[pop["pop"] > 100_000].copy()
    pays_valides = set(pop["pays"].unique())

    app = AppSimulation(pop, pays_valides)
    app.mainloop()