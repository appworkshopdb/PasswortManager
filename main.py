"""
main.py - Eigener lokaler Passwort-Manager.

Start:  python3 main.py

Beim ersten Start wird ein Master-Passwort festgelegt. Alle Passwörter
werden lokal in vault.db verschlüsselt gespeichert (AES via Fernet,
Schlüssel abgeleitet aus dem Master-Passwort mit PBKDF2).
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import secrets
import string

from vault import Vault, WrongMasterPassword
import import_bitwarden


# ---------------------------------------------------------------- Login ----

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Passwort-Manager - Anmelden")
        self.geometry("380x220")
        self.resizable(False, False)
        self.vault = Vault()
        self.result_vault = None

        first_time = not self.vault.is_initialized()

        label_text = (
            "Willkommen! Lege ein neues Master-Passwort fest.\n"
            "Merke es dir gut - es kann NICHT wiederhergestellt werden."
            if first_time else
            "Bitte Master-Passwort eingeben:"
        )

        tk.Label(self, text=label_text, wraplength=340, justify="center").pack(pady=15)

        self.pw_var = tk.StringVar()
        entry = tk.Entry(self, textvariable=self.pw_var, show="*", width=30)
        entry.pack(pady=5)
        entry.focus()

        if first_time:
            self.pw2_var = tk.StringVar()
            tk.Label(self, text="Wiederholen:").pack()
            entry2 = tk.Entry(self, textvariable=self.pw2_var, show="*", width=30)
            entry2.pack(pady=5)

        self.first_time = first_time

        btn_text = "Master-Passwort festlegen" if first_time else "Entsperren"
        tk.Button(self, text=btn_text, command=self._submit).pack(pady=15)
        entry.bind("<Return>", lambda e: self._submit())

    def _submit(self):
        pw = self.pw_var.get()
        if not pw:
            messagebox.showerror("Fehler", "Passwort darf nicht leer sein.")
            return

        if self.first_time:
            if pw != self.pw2_var.get():
                messagebox.showerror("Fehler", "Passwörter stimmen nicht überein.")
                return
            if len(pw) < 8:
                if not messagebox.askyesno(
                    "Schwaches Passwort",
                    "Das Passwort ist kürzer als 8 Zeichen. Trotzdem fortfahren?"
                ):
                    return
            self.vault.setup_master_password(pw)
            self.result_vault = self.vault
            self.destroy()
        else:
            try:
                self.vault.unlock(pw)
                self.result_vault = self.vault
                self.destroy()
            except WrongMasterPassword:
                messagebox.showerror("Fehler", "Master-Passwort ist falsch.")
                self.pw_var.set("")


# ------------------------------------------------------------ Main App -----

class PasswordManagerApp(tk.Tk):
    def __init__(self, vault: Vault):
        super().__init__()
        self.vault = vault
        self.title("Mein Passwort-Manager")
        self.geometry("820x480")
        self.selected_id = None

        self._build_menu()
        self._build_layout()
        self._refresh_list()

    # ---- Menu ----

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Aus Bitwarden importieren...", command=self._import_bitwarden)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self._on_close)
        menubar.add_cascade(label="Datei", menu=file_menu)
        self.config(menu=menubar)

    # ---- Layout ----

    def _build_layout(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Suche:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=self.search_var, width=40)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._refresh_list())

        tk.Button(top, text="+ Neu", command=self._new_entry).pack(side="right", padx=3)

        main = tk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # Liste links
        columns = ("name", "username", "url")
        self.tree = ttk.Treeview(main, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Name")
        self.tree.heading("username", text="Benutzername")
        self.tree.heading("url", text="URL")
        self.tree.column("name", width=180)
        self.tree.column("username", width=180)
        self.tree.column("url", width=220)
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        scrollbar = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="left", fill="y")

        # Detailbereich rechts
        detail = tk.Frame(main, padx=15)
        detail.pack(side="left", fill="both", expand=True)

        self.name_var = tk.StringVar()
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        self.url_var = tk.StringVar()

        self._labeled_entry(detail, "Name", self.name_var, 0)
        self._labeled_entry(detail, "Benutzername", self.user_var, 1)

        tk.Label(detail, text="Passwort").grid(row=2, column=0, sticky="w", pady=4)
        pw_frame = tk.Frame(detail)
        pw_frame.grid(row=2, column=1, sticky="ew", pady=4)
        self.pass_entry = tk.Entry(pw_frame, textvariable=self.pass_var, show="*", width=25)
        self.pass_entry.pack(side="left")
        tk.Button(pw_frame, text="👁", width=3, command=self._toggle_pw).pack(side="left", padx=2)
        tk.Button(pw_frame, text="🎲", width=3, command=self._generate_pw).pack(side="left", padx=2)
        tk.Button(pw_frame, text="Kopieren", command=self._copy_pw).pack(side="left", padx=2)

        self._labeled_entry(detail, "URL", self.url_var, 3)

        tk.Label(detail, text="Notizen").grid(row=4, column=0, sticky="nw", pady=4)
        self.notes_text = tk.Text(detail, width=30, height=6)
        self.notes_text.grid(row=4, column=1, sticky="ew", pady=4)

        btn_frame = tk.Frame(detail)
        btn_frame.grid(row=5, column=1, sticky="w", pady=15)
        tk.Button(btn_frame, text="Speichern", command=self._save_entry).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Löschen", command=self._delete_entry, fg="red").pack(side="left", padx=3)

        detail.columnconfigure(1, weight=1)

    def _labeled_entry(self, parent, label, var, row):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        tk.Entry(parent, textvariable=var, width=30).grid(row=row, column=1, sticky="ew", pady=4)

    # ---- Actions ----

    def _refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for entry in self.vault.list_entries(self.search_var.get()):
            self.tree.insert("", "end", iid=str(entry["id"]),
                              values=(entry["name"], entry["username"] or "", entry["url"] or ""))

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        entry_id = int(sel[0])
        entry = self.vault.get_entry_decrypted(entry_id)
        self.selected_id = entry_id
        self.name_var.set(entry["name"] or "")
        self.user_var.set(entry["username"] or "")
        self.pass_var.set(entry["password"] or "")
        self.url_var.set(entry["url"] or "")
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", entry["notes"] or "")

    def _new_entry(self):
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())
        self.name_var.set("")
        self.user_var.set("")
        self.pass_var.set("")
        self.url_var.set("")
        self.notes_text.delete("1.0", "end")

    def _save_entry(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Fehler", "Name darf nicht leer sein.")
            return
        username = self.user_var.get().strip() or None
        password = self.pass_var.get() or None
        url = self.url_var.get().strip() or None
        notes = self.notes_text.get("1.0", "end").strip() or None

        if self.selected_id is None:
            self.vault.add_entry(name, username, password, url, notes)
        else:
            self.vault.update_entry(self.selected_id, name, username, password, url, notes)
        self._refresh_list()
        messagebox.showinfo("Gespeichert", f"'{name}' wurde gespeichert.")

    def _delete_entry(self):
        if self.selected_id is None:
            return
        if messagebox.askyesno("Löschen", "Diesen Eintrag wirklich löschen?"):
            self.vault.delete_entry(self.selected_id)
            self._new_entry()
            self._refresh_list()

    def _toggle_pw(self):
        current = self.pass_entry.cget("show")
        self.pass_entry.config(show="" if current == "*" else "*")

    def _generate_pw(self):
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        pw = "".join(secrets.choice(alphabet) for _ in range(16))
        self.pass_var.set(pw)
        self.pass_entry.config(show="")

    def _copy_pw(self):
        self.clipboard_clear()
        self.clipboard_append(self.pass_var.get())
        messagebox.showinfo("Kopiert", "Passwort wurde in die Zwischenablage kopiert.")

    def _import_bitwarden(self):
        filepath = filedialog.askopenfilename(
            title="Bitwarden-Export auswählen",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not filepath:
            return
        try:
            stats = import_bitwarden.import_file(self.vault, filepath)
        except Exception as e:
            messagebox.showerror("Fehler beim Import", str(e))
            return
        self._refresh_list()
        messagebox.showinfo(
            "Import abgeschlossen",
            f"{stats['imported']} von {stats['total']} Einträgen importiert "
            f"({stats['skipped']} übersprungen)."
        )

    def _on_close(self):
        self.vault.close()
        self.destroy()


def main():
    login = LoginWindow()
    login.mainloop()

    if login.result_vault is None:
        return  # Fenster wurde geschlossen ohne Login

    app = PasswordManagerApp(login.result_vault)
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
