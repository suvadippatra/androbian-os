#!/usr/bin/env python3
"""
community.py — AndrobianOS
════════════════════════════════════════════════════════════════════════
Community & Feedback panel.

Users can:
  • Submit a suggestion or bug report
  • The submission is saved as a GitHub Issue via the GitHub REST API
  • A local copy is also saved to ~/.config/androbian/feedback_log.json
  • Users can read existing suggestions (public Issues from the repo)

GitHub token is read from ~/.config/androbian/config.json
(set up by bootstrap.sh and github_sync.sh).

If no token is present, submissions are saved locally only.
════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
import json
import urllib.request
import urllib.error
import threading
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

CONFIG_FILE   = os.path.expanduser("~/.config/androbian/config.json")
FEEDBACK_LOG  = os.path.expanduser("~/.config/androbian/feedback_log.json")

# ── GitHub config helpers ──────────────────────────────────────────────────

def _read_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _read_feedback_log():
    try:
        with open(FEEDBACK_LOG) as f:
            return json.load(f)
    except Exception:
        return []


def _append_feedback_log(entry):
    log = _read_feedback_log()
    log.append(entry)
    os.makedirs(os.path.dirname(FEEDBACK_LOG), exist_ok=True)
    with open(FEEDBACK_LOG, "w") as f:
        json.dump(log, f, indent=2)


# ── Submit to GitHub Issues ────────────────────────────────────────────────

def submit_github_issue(title, body, token, owner, repo, label="community"):
    """
    POST a new GitHub Issue.
    Returns (True, issue_url) on success, (False, error_message) on failure.
    """
    url     = f"https://api.github.com/repos/{owner}/{repo}/issues"
    payload = json.dumps({
        "title":  title,
        "body":   body,
        "labels": [label],
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization":  f"token {token}",
            "Content-Type":   "application/json",
            "Accept":         "application/vnd.github.v3+json",
            "User-Agent":     "AndrobianOS-Community/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return True, data.get("html_url", "GitHub Issue created")
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as ex:
        return False, str(ex)


def fetch_github_issues(owner, repo, per_page=20):
    """
    Fetch recent public Issues (community feedback) from the repo.
    Returns list of dicts or empty list on failure.
    """
    url = (f"https://api.github.com/repos/{owner}/{repo}/issues"
           f"?state=open&per_page={per_page}&labels=community")
    req = urllib.request.Request(url, headers={"User-Agent": "AndrobianOS/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception:
        return []


# ── Main window ────────────────────────────────────────────────────────────

class CommunityApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Community & Feedback — AndrobianOS")
        self.geometry("740x560")
        self.minsize(600, 440)
        T.apply(self)
        self._centre()
        self._cfg = _read_config()
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"740x560+{(sw-740)//2}+{(sh-560)//2}")

    def _build(self):
        T.app_header(self, "Community & Feedback",
                     "Suggest features, report bugs, read community ideas", "💬")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        t1 = tk.Frame(nb, bg=T.BG)
        nb.add(t1, text="  ✏  Submit Feedback  ")
        self._build_submit(t1)

        t2 = tk.Frame(nb, bg=T.BG)
        nb.add(t2, text="  📋  Community Ideas  ")
        self._build_read(t2)

        t3 = tk.Frame(nb, bg=T.BG)
        nb.add(t3, text="  📁  My Submissions  ")
        self._build_local(t3)

        T.Divider(self).pack(fill="x")
        self.status = tk.Label(self, text="", bg=T.BG, fg=T.MUT, font=T.F(9))
        self.status.pack(anchor="w", padx=18, pady=6)

    # ── Submit tab ─────────────────────────────────────────────────────────
    def _build_submit(self, parent):
        body = tk.Frame(parent, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # GitHub token status
        cfg   = self._cfg
        has_t = bool(cfg.get("github_token") and
                     cfg.get("github_user") and
                     cfg.get("github_repo"))

        if has_t:
            note_text = (
                f"✓  Connected to github.com/{cfg['github_user']}/{cfg['github_repo']}\n"
                "   Your feedback will be submitted as a public GitHub Issue."
            )
            note_col = T.OK
        else:
            note_text = (
                "ℹ  GitHub not configured — feedback will be saved locally only.\n"
                "   To enable GitHub submission, run: bash /opt/androbian/github_sync.sh push"
            )
            note_col = T.WARN

        note = T.Card(body)
        note.pack(fill="x", pady=(0, 12))
        ni = tk.Frame(note, bg=T.SURF, padx=14, pady=10)
        ni.pack(fill="x")
        tk.Label(ni, text=note_text, bg=T.SURF, fg=note_col,
                 font=T.F(9), justify="left").pack(anchor="w")

        # Category
        cat_row = tk.Frame(body, bg=T.BG)
        cat_row.pack(fill="x", pady=(0, 8))
        tk.Label(cat_row, text="Category:", bg=T.BG, fg=T.MUT,
                 font=T.F(10), width=12, anchor="w").pack(side="left")
        self._cat = tk.StringVar(value="Suggestion")
        for c in ("Suggestion", "Bug Report", "Question", "Other"):
            tk.Radiobutton(cat_row, text=c, variable=self._cat, value=c,
                           bg=T.BG, fg=T.TXT, selectcolor=T.SURF2,
                           activebackground=T.BG, font=T.F(10)
                           ).pack(side="left", padx=6)

        # Title
        tk.Label(body, text="Title:", bg=T.BG, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 3))
        self._title_var = tk.StringVar()
        tk.Entry(body, textvariable=self._title_var, bg=T.SURF2, fg=T.TXT,
                 font=T.F(11), relief="flat", bd=0, insertbackground=T.TXT
                 ).pack(fill="x", ipady=6, pady=(0, 10))

        # Body
        tk.Label(body, text="Details (describe your suggestion or bug clearly):",
                 bg=T.BG, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 3))

        text_frame = tk.Frame(body, bg=T.SURF2)
        text_frame.pack(fill="both", expand=True, pady=(0, 10))
        sb = tk.Scrollbar(text_frame, bg=T.BDR, relief="flat", bd=0)
        self._body_text = tk.Text(
            text_frame, bg=T.SURF2, fg=T.TXT, font=T.F(10),
            insertbackground=T.TXT, relief="flat", bd=0, wrap="word",
            yscrollcommand=sb.set, padx=10, pady=8, height=7
        )
        sb.config(command=self._body_text.yview)
        sb.pack(side="right", fill="y")
        self._body_text.pack(fill="both", expand=True)

        btn_row = tk.Frame(body, bg=T.BG)
        btn_row.pack(fill="x")
        self._prog = ttk.Progressbar(btn_row, mode="indeterminate", length=200)
        self._prog.pack(side="left")
        T.Btn(btn_row, "Submit Feedback →",
              cmd=self._submit, style="primary",
              font=T.F(11, True)).pack(side="right")

    def _submit(self):
        title = self._title_var.get().strip()
        body  = self._body_text.get("1.0", "end-1c").strip()
        cat   = self._cat.get()

        if not title:
            T.popup(self, "Missing title", "Enter a short title.", "warning")
            return
        if not body:
            T.popup(self, "Missing details", "Add some details to your feedback.", "warning")
            return

        full_title = f"[{cat}] {title}"
        full_body  = (
            f"**Category:** {cat}\n\n"
            f"{body}\n\n"
            f"---\n*Submitted via AndrobianOS Community v1.0*"
        )
        timestamp = datetime.datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "category":  cat,
            "title":     full_title,
            "body":      full_body,
            "submitted_to_github": False,
        }

        cfg   = self._cfg
        has_t = bool(cfg.get("github_token") and
                     cfg.get("github_user") and
                     cfg.get("github_repo"))

        self._prog.start(10)
        self.status.config(text="Submitting…")

        def worker():
            if has_t:
                ok, result = submit_github_issue(
                    full_title, full_body,
                    cfg["github_token"], cfg["github_user"], cfg["github_repo"])
                if ok:
                    log_entry["submitted_to_github"] = True
                    log_entry["issue_url"] = result
                    _append_feedback_log(log_entry)
                    self._prog.stop()
                    self.status.config(
                        text=f"✓  Submitted to GitHub: {result}", fg=T.OK)
                    T.toast(self, "Feedback submitted to GitHub  ✓", "success")
                else:
                    _append_feedback_log(log_entry)
                    self._prog.stop()
                    self.status.config(
                        text=f"✗  GitHub failed ({result}) — saved locally.", fg=T.WARN)
            else:
                _append_feedback_log(log_entry)
                self._prog.stop()
                self.status.config(
                    text="✓  Saved locally (GitHub not configured).", fg=T.OK)
                T.toast(self, "Feedback saved locally  ✓", "info")

            # Clear form
            self._title_var.set("")
            self._body_text.delete("1.0", "end")

        threading.Thread(target=worker, daemon=True).start()

    # ── Community Ideas tab ─────────────────────────────────────────────────
    def _build_read(self, parent):
        body = tk.Frame(parent, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        top = tk.Frame(body, bg=T.BG)
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="Community suggestions from GitHub:",
                 bg=T.BG, fg=T.MUT, font=T.F(10)).pack(side="left")
        T.Btn(top, "Refresh",
              cmd=self._refresh_issues, style="secondary",
              font=T.F(9, True), padx=8, pady=3).pack(side="right")

        self._issues_log = T.LogBox(parent, height=16)
        self._issues_log.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self._issues_log.append("Click Refresh to load community feedback from GitHub.", T.MUT)

    def _refresh_issues(self):
        cfg  = self._cfg
        user = cfg.get("github_user", "")
        repo = cfg.get("github_repo", "")
        if not user or not repo:
            self._issues_log.clear()
            self._issues_log.append(
                "GitHub not configured. Run github_sync.sh push first.", T.WARN)
            return
        self._issues_log.clear()
        self._issues_log.append("Fetching from GitHub…")
        self.status.config(text="Loading community feedback…")

        def worker():
            issues = fetch_github_issues(user, repo)
            self._issues_log.clear()
            if not issues:
                self._issues_log.append(
                    "No community feedback found yet, or GitHub unavailable.", T.MUT)
            else:
                for iss in issues:
                    self._issues_log.append(
                        f"#{iss.get('number')}  {iss.get('title', '—')}", T.ACC)
                    self._issues_log.append(
                        f"  {iss.get('body','')[:120].strip()}…", T.MUT)
                    self._issues_log.append("")
            self.status.config(text=f"Loaded {len(issues)} item(s).", fg=T.OK)

        threading.Thread(target=worker, daemon=True).start()

    # ── Local submissions tab ──────────────────────────────────────────────
    def _build_local(self, parent):
        body = tk.Frame(parent, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=f"Locally saved feedback log:\n{FEEDBACK_LOG}",
                 bg=T.BG, fg=T.MUT, font=T.F(9)).pack(anchor="w", pady=(0, 8))
        self._local_log = T.LogBox(body, height=18)
        self._local_log.pack(fill="both", expand=True)
        self._load_local_log()

    def _load_local_log(self):
        entries = _read_feedback_log()
        self._local_log.clear()
        if not entries:
            self._local_log.append("No submissions yet.", T.MUT)
            return
        for e in reversed(entries):
            self._local_log.append(
                f"{e.get('timestamp','')[:16]}  {e.get('title','')}", T.ACC)
            if e.get("submitted_to_github"):
                self._local_log.append(
                    f"  ✓ GitHub: {e.get('issue_url','')}", T.OK)
            else:
                self._local_log.append("  (local only)", T.MUT)
            self._local_log.append("")


if __name__ == "__main__":
    CommunityApp().mainloop()
