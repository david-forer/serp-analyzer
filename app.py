#!/usr/bin/env python3
"""
SERP Analyzer desktop app.
Dark reading-pane layout: a left rail with the search, the competition scale and a
"format agreement" meter, and a scrolling right pane that reads like a short note.
"""

import sys
import os
import json
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, font as tkfont
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Add src directory to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from content_strategy_analyzer import PAGE_TYPE_PROFILES

# Names for what a ranking result IS. PAGE_TYPE_PROFILES labels describe what a writer should BUILD,
# which reads wrong for a few types (a Reddit thread is not a "discussion-style article").
RESULT_NAMES = {
    "forum_thread": "Forum thread", "tool": "Tool", "news_article": "News article",
    "research_paper": "Research paper", "other": "Other",
}


def result_name(page_type):
    if page_type in RESULT_NAMES:
        return RESULT_NAMES[page_type]
    return PAGE_TYPE_PROFILES.get(page_type, {}).get("label", (page_type or "").replace("_", " ").capitalize())

# Plain names for the SERP features each search service reports
FEATURE_NAMES = {
    "peopleAlsoAsk": "People Also Ask", "people_also_ask": "People Also Ask",
    "relatedSearches": "Related searches", "related_searches": "Related searches",
    "people_also_search": "People also search for",
    "answerBox": "Featured snippet", "answer_box": "Answer box", "featured_snippet": "Featured snippet",
    "knowledgeGraph": "Knowledge panel", "knowledge_graph": "Knowledge panel",
    "topStories": "Top stories", "top_stories": "Top stories",
    "videos": "Videos", "video": "Videos", "short_videos": "Short videos",
    "ai_overview": "AI Overview", "discussions_and_forums": "Discussions and forums",
    "perspectives": "Perspectives", "images": "Images", "local_pack": "Local map pack",
    "shopping": "Shopping results", "paid": "Ads", "popular_products": "Popular products",
}


# Palette and type
RAIL_BG = "#1b1d24"
MAIN_BG = "#16171c"
CARD_BG = "#23262f"
INPUT_BG = "#131419"
BORDER = "#2f333d"
TEXT = "#e8e8ea"
MUTED = "#9a9ca6"
FAINT = "#62656f"
LINK = "#8fb3e8"
METER_OFF = "#3a3e48"
COMPETITION_COLORS = {
    "Open": "#8fd19e",
    "Mixed": "#e5c07b",
    "Crowded": "#e8a194",
}
WARNING_COLOR = "#e8a194"
SERIF = "Georgia"
SANS = "Segoe UI"
NUM_RESULTS = 10
PAD_X = 48

LOADING_LINES = [
    "Reading the top 10 so you don't have to...",
    "Asking Google what it really thinks...",
    "Politely eavesdropping on Reddit...",
    "Counting how-to guides. There are always more than you'd expect...",
    "Sorting the listicles from the lookalikes...",
    "Checking whether an AI already answered this one...",
    "Judging ten websites by their covers...",
    "Squinting at the search results...",
]


class SerpAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SERP Analyzer")
        self.root.geometry("900x700")
        self.root.minsize(800, 560)
        self.root.configure(bg=MAIN_BG)

        self._last_analysis = None
        self._busy = False
        self._loading_step = 0
        self._current_view = ("empty",)
        self._last_width = 0
        self._resize_job = None
        self.loading_label = None
        self.results_win = None

        self._build_rail()
        self._build_main()
        self._render_empty()

    # ------------------------------------------------------------------ left rail

    def _build_rail(self):
        rail = tk.Frame(self.root, bg=RAIL_BG, width=250)
        rail.pack(side=tk.LEFT, fill=tk.Y)
        rail.pack_propagate(False)
        tk.Frame(self.root, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(rail, bg=RAIL_BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=24, pady=(28, 24))

        tk.Label(inner, text="SERP Analyzer", font=(SERIF, 16, "bold"),
                 fg=TEXT, bg=RAIL_BG).pack(anchor="w")

        self._rail_label(inner, "Your search", pady=(28, 8))
        box = tk.Frame(inner, bg=BORDER)
        box.pack(fill=tk.X)
        self.search = tk.Text(box, height=2, wrap="word", font=(SANS, 11), bg=INPUT_BG, fg=TEXT,
                              insertbackground=TEXT, relief="flat", padx=12, pady=10,
                              highlightthickness=0)
        self.search.pack(fill=tk.X, padx=1, pady=1)
        self.search.bind("<Return>", self._on_enter)
        self.search.focus_set()

        self.check_btn = tk.Button(inner, text="Check", command=self._run_analysis,
                                   font=(SANS, 11, "bold"), bg=CARD_BG, fg=TEXT,
                                   activebackground=BORDER, activeforeground=TEXT,
                                   disabledforeground=MUTED, relief="flat", bd=0, pady=10,
                                   cursor="hand2", highlightthickness=1,
                                   highlightbackground=BORDER)
        self.check_btn.pack(fill=tk.X, pady=(10, 0))

        self._rail_label(inner, "Competition", pady=(30, 8))
        self.scale_rows = {}
        for name in ("Open", "Mixed", "Crowded"):
            row = tk.Frame(inner, bg=RAIL_BG)
            row.pack(fill=tk.X, pady=1)
            dot = tk.Canvas(row, width=14, height=14, bg=RAIL_BG, highlightthickness=0)
            dot.pack(side=tk.LEFT, padx=(12, 10), pady=10)
            lbl = tk.Label(row, text=name, font=(SANS, 10), fg=MUTED, bg=RAIL_BG)
            lbl.pack(side=tk.LEFT)
            self.scale_rows[name] = (row, dot, lbl)
        self._set_scale(None)

        self._rail_label(inner, "How clear the format is", pady=(24, 8))
        sure = tk.Frame(inner, bg=RAIL_BG)
        sure.pack(fill=tk.X)
        self.meter = tk.Canvas(sure, width=108, height=8, bg=RAIL_BG, highlightthickness=0)
        self.meter.pack(anchor="w")
        self.sure_label = tk.Label(sure, text="", font=(SANS, 10), fg=MUTED, bg=RAIL_BG)
        self.sure_label.pack(anchor="w", pady=(6, 0))
        self._set_meter(None)

        # Quiet links at the bottom of the rail
        bottom = tk.Frame(inner, bg=RAIL_BG)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.results_link = self._link(bottom, "See all 10 results", self._show_all_results)
        self.save_link = self._link(bottom, "Save as file", self._export)
        self.checked_label = tk.Label(bottom, text="", font=(SANS, 9), fg=FAINT, bg=RAIL_BG,
                                      anchor="w", justify="left", wraplength=200)
        self.checked_label.pack(anchor="w", pady=(10, 0))
        self._set_links_enabled(False)

    def _rail_label(self, parent, text, pady):
        tk.Label(parent, text=text, font=(SANS, 9, "bold"), fg=MUTED,
                 bg=RAIL_BG).pack(anchor="w", pady=pady)

    def _link(self, parent, text, command):
        lbl = tk.Label(parent, text=text, font=(SANS, 10, "underline"), fg=LINK,
                       bg=parent["bg"], cursor="hand2")
        lbl.pack(anchor="w", pady=2)
        lbl.enabled = True
        lbl.bind("<Button-1>", lambda e: command() if lbl.enabled else None)
        return lbl

    def _set_links_enabled(self, enabled):
        for lbl in (self.results_link, self.save_link):
            lbl.enabled = enabled
            lbl.configure(fg=LINK if enabled else FAINT, cursor="hand2" if enabled else "arrow")

    def _set_scale(self, level):
        """Highlight the current competition level on the three-step scale"""
        for name, (row, dot, lbl) in self.scale_rows.items():
            active = name == level
            bg = CARD_BG if active else RAIL_BG
            for w in (row, dot, lbl):
                w.configure(bg=bg)
            lbl.configure(fg=TEXT if active else MUTED,
                          font=(SANS, 10, "bold" if active else "normal"))
            dot.delete("all")
            if active:
                color = COMPETITION_COLORS[name]
                dot.create_oval(2, 2, 12, 12, fill=color, outline=color)
            else:
                dot.create_oval(2, 2, 12, 12, outline=FAINT, width=1.5)

    def _set_meter(self, confidence):
        """Five-segment format agreement meter"""
        self.meter.delete("all")
        filled = 0 if confidence is None else max(1, min(5, round(confidence * 5)))
        for i in range(5):
            x = i * 22
            self.meter.create_rectangle(x, 1, x + 18, 7, outline="",
                                        fill=TEXT if i < filled else METER_OFF)
        self.sure_label.configure(
            text="" if confidence is None else f"{self._sure_words(confidence)} ({round(confidence * 100)}%)"
        )

    @staticmethod
    def _sure_words(confidence):
        """How strongly the top results agree on one format"""
        if confidence >= 0.8:
            return "Very clear"
        if confidence >= 0.6:
            return "Clear"
        if confidence >= 0.4:
            return "Somewhat mixed"
        return "Mixed"

    # ------------------------------------------------------------------ main pane

    def _build_main(self):
        # Dark scrollbar to match the theme (the default Windows one is light gray)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Vertical.TScrollbar", background=CARD_BG, troughcolor=MAIN_BG,
                        bordercolor=MAIN_BG, lightcolor=CARD_BG, darkcolor=CARD_BG,
                        arrowcolor=MUTED, gripcount=0)
        style.map("Dark.Vertical.TScrollbar", background=[("active", BORDER)])

        wrap = tk.Frame(self.root, bg=MAIN_BG)
        wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(wrap, bg=MAIN_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview,
                                  style="Dark.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.page = tk.Frame(self.canvas, bg=MAIN_BG)
        self.page_id = self.canvas.create_window(0, 0, window=self.page, anchor="nw")
        self.page.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.page_id, width=event.width)
        if abs(event.width - self._last_width) > 30:
            self._last_width = event.width
            if self._resize_job:
                self.root.after_cancel(self._resize_job)
            self._resize_job = self.root.after(150, self._rerender)

    def _on_mousewheel(self, event):
        # Only scroll the main pane, and only when its content is taller than the window
        if event.widget.winfo_toplevel() != self.root:
            return
        bbox = self.canvas.bbox("all")
        if bbox and bbox[3] > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _text_width(self):
        return max(360, self.canvas.winfo_width() - PAD_X * 2 - 10)

    def _new_body(self):
        for child in self.page.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)
        body = tk.Frame(self.page, bg=MAIN_BG)
        body.pack(fill=tk.X, padx=PAD_X, pady=(36, 40))
        return body

    def _rerender(self):
        view = self._current_view
        if view[0] == "results":
            self._render_results(view[1])
        elif view[0] == "error":
            self._render_error(view[1])
        elif view[0] == "loading":
            self._render_loading()
        else:
            self._render_empty()

    # Small building blocks for the note
    def _eyebrow(self, parent, text):
        tk.Label(parent, text=text, font=(SANS, 9), fg=MUTED, bg=MAIN_BG).pack(anchor="w")

    def _para(self, parent, text, size=11, fg=TEXT, pady=(0, 0), bold=False):
        lbl = tk.Label(parent, text=text, font=(SANS, size, "bold" if bold else "normal"), fg=fg,
                       bg=MAIN_BG, wraplength=self._text_width(), justify="left", anchor="w")
        lbl.pack(anchor="w", fill=tk.X, pady=pady)
        return lbl

    def _rule(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=22)

    def _section_label(self, parent, text):
        tk.Label(parent, text=text.upper(), font=(SANS, 9, "bold"), fg=MUTED,
                 bg=MAIN_BG).pack(anchor="w", pady=(0, 10))

    def _bullets(self, parent, items):
        for item in items:
            row = tk.Frame(parent, bg=MAIN_BG)
            row.pack(fill=tk.X, anchor="w", pady=2)
            tk.Label(row, text="\u2022", font=(SANS, 11), fg=TEXT, bg=MAIN_BG).pack(side=tk.LEFT, anchor="n", padx=(4, 10))
            tk.Label(row, text=item, font=(SANS, 11), fg=TEXT, bg=MAIN_BG, justify="left", anchor="w",
                     wraplength=self._text_width() - 30).pack(side=tk.LEFT, fill=tk.X)

    def _question_cards(self, parent, questions):
        grid = tk.Frame(parent, bg=MAIN_BG)
        grid.pack(fill=tk.X)
        grid.columnconfigure(0, weight=1, uniform="q")
        grid.columnconfigure(1, weight=1, uniform="q")
        card_wrap = max(150, self._text_width() // 2 - 40)
        for i, q in enumerate(questions):
            card = tk.Frame(grid, bg=CARD_BG)
            card.grid(row=i // 2, column=i % 2, sticky="nsew",
                      padx=(0, 10) if i % 2 == 0 else (0, 0), pady=(0, 10))
            tk.Label(card, text=q, font=(SANS, 10), fg=TEXT, bg=CARD_BG, justify="left",
                     anchor="nw", wraplength=card_wrap).pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

    def _gap(self, parent, height=20):
        tk.Frame(parent, bg=MAIN_BG, height=height).pack(fill=tk.X)

    def _type_bars(self, parent, counts, total):
        """One row per page type: name, a bar showing its share of the top results, and the count"""
        bar_width = max(120, self._text_width() - 290)
        for page_type, n in sorted(counts.items(), key=lambda x: -x[1]):
            row = tk.Frame(parent, bg=MAIN_BG)
            row.pack(fill=tk.X, pady=3)
            label = result_name(page_type)
            tk.Label(row, text=label, font=(SANS, 10), fg=TEXT, bg=MAIN_BG, width=26,
                     anchor="w").pack(side=tk.LEFT)
            bar = tk.Canvas(row, width=bar_width, height=10, bg=MAIN_BG, highlightthickness=0)
            bar.pack(side=tk.LEFT, padx=(8, 10))
            bar.create_rectangle(0, 1, bar_width, 9, fill=CARD_BG, outline="")
            bar.create_rectangle(0, 1, max(4, int(bar_width * n / max(total, 1))), 9, fill=MUTED, outline="")
            tk.Label(row, text=str(n), font=(SANS, 10), fg=MUTED, bg=MAIN_BG).pack(side=tk.LEFT)

    def _top_list(self, parent, results):
        """The top results inline: number, clickable title, then site, page type and date"""
        for r in results:
            row = tk.Frame(parent, bg=MAIN_BG)
            row.pack(fill=tk.X, pady=(0, 12))
            tk.Label(row, text=str(r.get("position", "")), font=(SANS, 10), fg=FAINT, bg=MAIN_BG,
                     width=3, anchor="nw").pack(side=tk.LEFT, anchor="n")
            col = tk.Frame(row, bg=MAIN_BG)
            col.pack(side=tk.LEFT, fill=tk.X, expand=True)

            title = tk.Label(col, text=r.get("title", ""), font=(SANS, 10, "bold"), fg=TEXT, bg=MAIN_BG,
                             justify="left", anchor="w", wraplength=self._text_width() - 40, cursor="hand2")
            title.pack(anchor="w")
            url = r.get("url", "")
            title.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
            title.bind("<Enter>", lambda e, w=title: w.configure(fg=LINK))
            title.bind("<Leave>", lambda e, w=title: w.configure(fg=TEXT))

            domain = urlparse(url).netloc.replace("www.", "")
            page_type = r.get("classification", {}).get("page_type", "")
            type_label = result_name(page_type) if page_type else ""
            date = (r.get("date") or "").strip()
            if len(date) > 10 and date[4:5] == "-":
                date = date[:10]  # DataForSEO sends "2026-01-10 00:00:00 +00:00", keep the day
            meta = "   ".join(part for part in (domain, type_label, date) if part)
            tk.Label(col, text=meta, font=(SANS, 9), fg=MUTED, bg=MAIN_BG, anchor="w").pack(anchor="w")

    def _chips(self, parent, items):
        """Related searches as chips that wrap onto new rows. Clicking one checks it."""
        chip_font = tkfont.Font(family=SANS, size=10)
        max_width = self._text_width()
        row, used = None, 0
        for text in items:
            width = chip_font.measure(text) + 38
            if row is None or used + width > max_width:
                row = tk.Frame(parent, bg=MAIN_BG)
                row.pack(anchor="w", pady=(0, 8))
                used = 0
            chip = tk.Label(row, text=text, font=chip_font, fg=LINK, bg=MAIN_BG, padx=14, pady=5,
                            highlightthickness=1, highlightbackground=BORDER, cursor="hand2")
            chip.pack(side=tk.LEFT, padx=(0, 8))
            chip.bind("<Button-1>", lambda e, t=text: self._check_related(t))
            used += width

    # ------------------------------------------------------------------ views

    def _render_empty(self):
        self._current_view = ("empty",)
        body = self._new_body()
        self._eyebrow(body, "Our read on this search")
        tk.Label(body, text="Type a search to begin.", font=(SERIF, 30), fg=FAINT,
                 bg=MAIN_BG).pack(anchor="w", pady=(6, 12))
        self._para(body, "Enter the search you're thinking of writing about and press Check. "
                         "You'll see what kind of piece Google rewards and who you'd be up against.", fg=MUTED)

    def _render_loading(self):
        self._current_view = ("loading",)
        body = self._new_body()
        self._eyebrow(body, "Our read on this search")
        tk.Label(body, text="Working on it.", font=(SERIF, 34), fg=TEXT,
                 bg=MAIN_BG).pack(anchor="w", pady=(6, 12))
        line = LOADING_LINES[self._loading_step % len(LOADING_LINES)]
        self.loading_label = self._para(body, line, size=13, fg=MUTED)

    def _tick_loading(self):
        """Swap in the next loading line every 2.5 seconds until the analysis finishes"""
        if not self._busy:
            return
        self._loading_step += 1
        if self.loading_label is not None and self.loading_label.winfo_exists():
            self.loading_label.configure(text=LOADING_LINES[self._loading_step % len(LOADING_LINES)])
        self.root.after(2500, self._tick_loading)

    def _render_error(self, message):
        self._current_view = ("error", message)
        body = self._new_body()
        self._eyebrow(body, "Our read on this search")
        tk.Label(body, text="Something went wrong.", font=(SERIF, 30), fg=WARNING_COLOR,
                 bg=MAIN_BG).pack(anchor="w", pady=(6, 12))
        self._para(body, message, fg=MUTED)
        self._para(body, "Check your API keys in the .env file, then try again.", fg=MUTED, pady=(12, 0))

    def _render_results(self, data):
        self._current_view = ("results", data)
        rec = data.get("content_strategy", {}).get("recommendation", {})
        competition = rec.get("competition", {})
        level = competition.get("level", "")
        warning = rec.get("format_warning", "")
        features = data.get("serp_features") or {}

        body = self._new_body()

        # Headline: the format Google rewards for this search
        self._eyebrow(body, "What Google rewards for this search")
        headline = rec.get("headline") or rec.get("content_type", "Article")
        tk.Label(body, text=f"{headline}.", font=(SERIF, 34), fg=TEXT,
                 bg=MAIN_BG, justify="left", anchor="w",
                 wraplength=self._text_width()).pack(anchor="w", fill=tk.X, pady=(4, 10))
        if rec.get("format_summary"):
            self._para(body, rec["format_summary"] + ".", size=13)
        if warning:
            self._para(body, "Heads up: " + warning, size=11, fg=WARNING_COLOR, pady=(10, 0))
        elif rec.get("angle"):
            self._para(body, rec["angle"], size=11, fg=MUTED, pady=(8, 0))

        # Competition: who ranks, described rather than predicted
        if level:
            self._rule(body)
            self._section_label(body, "Competition")
            tk.Label(body, text=level, font=(SERIF, 20), fg=COMPETITION_COLORS.get(level, TEXT),
                     bg=MAIN_BG).pack(anchor="w", pady=(0, 6))
            if competition.get("meaning"):
                self._para(body, competition["meaning"], size=12)
            self._para(body, competition.get("summary", ""), size=10, fg=MUTED, pady=(6, 0))
            domains = competition.get("big_name_domains") or []
            if domains:
                self._para(body, "Big names: " + ", ".join(domains), size=9, fg=MUTED, pady=(8, 0))
            est_domains = competition.get("established_domains") or []
            if est_domains:
                self._para(body, "Established brands: " + ", ".join(est_domains), size=9, fg=MUTED,
                           pady=(4 if domains else 8, 0))

        # What to include
        if rec.get("required_elements"):
            self._rule(body)
            self._section_label(body, "What to include")
            self._bullets(body, rec["required_elements"])

        # Questions
        questions = rec.get("questions_to_answer") or []
        if questions:
            self._rule(body)
            self._section_label(body, "Questions readers ask")
            self._question_cards(body, questions)
        removed = features.get("people_also_ask_removed") or []
        if removed:
            self._para(body, "Left out as off-topic: " + "  |  ".join(removed), size=9, fg=FAINT, pady=(4, 0))

        # Other signals from the page
        reasons = [r for r in rec.get("reasoning", [])
                   if r and r != rec.get("format_summary") and r != warning]
        if reasons:
            self._rule(body)
            self._section_label(body, "Also on this page")
            self._bullets(body, reasons)

        # AI Overview sources (DataForSEO only)
        sources = rec.get("ai_overview_sources") or []
        if sources:
            self._rule(body)
            self._section_label(body, "Google's AI Overview cites")
            self._bullets(body, [f"{s.get('title') or s.get('domain')} ({s.get('domain', '')})"
                                 for s in sources[:8]])

        # Related searches
        related = rec.get("related_searches") or []
        if related:
            self._rule(body)
            self._section_label(body, "Related searches")
            self._para(body, "Click one to check it.", size=9, fg=FAINT, pady=(0, 10))
            self._chips(body, related)

        # ---- The details: the evidence behind the recommendation
        self._rule(body)
        tk.Label(body, text="The details", font=(SERIF, 20), fg=TEXT, bg=MAIN_BG).pack(anchor="w", pady=(0, 18))

        intent = data.get("intent") or {}
        if intent.get("user_intent"):
            self._section_label(body, "What searchers want")
            self._para(body, intent["user_intent"])
            self._gap(body)

        counts = rec.get("page_type_counts") or {}
        if counts:
            self._section_label(body, "What's ranking")
            self._type_bars(body, counts, data.get("total_results", 10))
            mix = data.get("classification_summary") or {}
            if mix:
                parts = [f"{n} {cat}" for cat, n in sorted(mix.items(), key=lambda x: -x[1])]
                self._para(body, "By purpose: " + ", ".join(parts), size=9, fg=MUTED, pady=(8, 0))
            self._gap(body)

        self._section_label(body, "What else Google shows")
        names = []
        for key in features.get("present") or []:
            name = FEATURE_NAMES.get(key, key.replace("_", " ").capitalize())
            if name not in names:
                names.append(name)
        self._para(body, ", ".join(names) if names else "Nothing beyond the regular results.")
        if features.get("ai_overview"):
            aio_note = "An AI Overview appears above the results."
        elif data.get("search_source") == "DataForSEO":
            aio_note = "No AI Overview for this search."
        else:
            aio_note = "AI Overviews can't be checked with Serper. Add DataForSEO to see them."
        self._para(body, aio_note, size=10, fg=MUTED, pady=(4, 0))
        self._gap(body)

        self._section_label(body, f"The top {len(data.get('results', []))}")
        self._para(body, "Click a title to open the page.", size=9, fg=FAINT, pady=(0, 10))
        self._top_list(body, data.get("results", []))

    # ------------------------------------------------------------------ actions

    def _on_enter(self, event):
        self._run_analysis()
        return "break"  # stop the Enter key from adding a new line to the search box

    def _check_related(self, text):
        if self._busy:
            return
        self.search.delete("1.0", tk.END)
        self.search.insert("1.0", text)
        self._run_analysis()

    def _run_analysis(self):
        if self._busy:
            return
        query = self.search.get("1.0", tk.END).strip()
        if not query:
            self.search.focus_set()
            return

        self._busy = True
        self._loading_step = 0
        self.check_btn.config(state=tk.DISABLED, text="Checking...")
        self._set_scale(None)
        self._set_meter(None)
        self._set_links_enabled(False)
        self.checked_label.configure(text="")
        self._render_loading()
        self.root.after(2500, self._tick_loading)

        thread = threading.Thread(target=self._do_analysis, args=(query,))
        thread.daemon = True
        thread.start()

    def _do_analysis(self, query):
        try:
            from dataforseo_search import get_search_client
            from classifier import ResultClassifier
            from content_strategy_analyzer import ContentStrategyAnalyzer

            search_client = get_search_client()
            results = search_client.search(query, num_results=NUM_RESULTS)
            if not results:
                self.root.after(0, lambda: self._show_error("Google returned no results for this search."))
                return

            analysis = {
                "query": query,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "total_results": len(results),
                "results": results,
                "serp_features": search_client.last_features,
                "search_source": "DataForSEO" if type(search_client).__name__ == "DataForSEOClient" else "Serper",
            }

            # Save the full search response so every SERP feature can be checked later
            self._save_raw_response(query, search_client.last_raw)

            # What the person searching most likely wants (shown under The details)
            try:
                from intent_detector import IntentDetector
                analysis["intent"] = IntentDetector().detect_intent(query, results)
            except Exception:
                pass  # the recommendation does not depend on this, so carry on without it

            # Label each result with its purpose and page type
            classifier = ResultClassifier()
            for result in analysis["results"]:
                result["classification"] = classifier.classify_result(result)

            summary = {}
            for r in analysis["results"]:
                cat = r.get("classification", {}).get("category", "unknown")
                summary[cat] = summary.get(cat, 0) + 1
            analysis["classification_summary"] = summary

            # Drop People Also Ask questions that belong to a different meaning of the search
            features = analysis.get("serp_features") or {}
            if features.get("people_also_ask"):
                filtered = classifier.filter_questions(
                    query, features["people_also_ask"], [r.get("title", "") for r in results]
                )
                features["people_also_ask"] = filtered["keep"]
                features["people_also_ask_removed"] = filtered["removed"]

            analysis["content_strategy"] = ContentStrategyAnalyzer().analyze(
                query=query,
                results=analysis["results"],
                serp_features=analysis.get("serp_features"),
            )

            self._last_analysis = analysis
            self.root.after(0, lambda: self._display_results(analysis))

        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda: self._show_error(msg))

    def _save_raw_response(self, query, raw):
        """Write the untouched search response to outputs/raw for inspection"""
        if not raw:
            return
        try:
            raw_dir = Path(__file__).parent / "outputs" / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()[:50].replace(' ', '_')
            path = raw_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_query}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
        except Exception:
            # A failed debug save should never stop the analysis
            pass

    def _show_error(self, message):
        self._busy = False
        self.check_btn.config(state=tk.NORMAL, text="Check")
        self._render_error(message)

    def _display_results(self, data):
        self._busy = False
        self.check_btn.config(state=tk.NORMAL, text="Check again")

        rec = data.get("content_strategy", {}).get("recommendation", {})
        self._set_scale(rec.get("competition", {}).get("level"))
        self._set_meter(rec.get("confidence"))

        self.results_link.configure(text=f"See all {data['total_results']} results")
        self._set_links_enabled(True)
        checked = datetime.fromisoformat(data["timestamp"])
        self.checked_label.configure(
            text=f"Checked {checked:%B} {checked.day}, {checked.year}\nSearch data: {data.get('search_source', 'Serper')}"
        )
        self._render_results(data)

    def _show_all_results(self):
        """Open the full top 10 in a second window"""
        if not self._last_analysis:
            return
        if self.results_win is not None and self.results_win.winfo_exists():
            self.results_win.destroy()

        win = tk.Toplevel(self.root)
        self.results_win = win
        win.title(f"All results: {self._last_analysis['query']}")
        win.geometry("760x620")
        win.configure(bg=MAIN_BG)

        text = tk.Text(win, wrap="word", bg=MAIN_BG, fg=TEXT, font=(SANS, 10), relief="flat",
                       padx=32, pady=24, highlightthickness=0, spacing1=2, spacing3=2)
        scrollbar = ttk.Scrollbar(win, command=text.yview, style="Dark.Vertical.TScrollbar")
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(fill=tk.BOTH, expand=True)

        text.tag_configure("meta", foreground=MUTED, font=(SANS, 9, "bold"))
        text.tag_configure("title", foreground=TEXT, font=(SANS, 11, "bold"))
        text.tag_configure("url", foreground=LINK, font=(SANS, 9))
        text.tag_configure("snippet", foreground=MUTED, font=(SANS, 10))

        for r in self._last_analysis["results"]:
            c = r.get("classification", {})
            page_type = (c.get("page_type") or "").replace("_", " ")
            meta = f"#{r['position']}   {page_type}   {c.get('category', '')}".upper()
            text.insert(tk.END, meta + "\n", "meta")
            text.insert(tk.END, r.get("title", "") + "\n", "title")
            text.insert(tk.END, r.get("url", "") + "\n", "url")
            text.insert(tk.END, (r.get("snippet") or "") + "\n\n", "snippet")
        text.configure(state=tk.DISABLED)

    def _export(self):
        """Save JSON, CSV and a text summary, then open the folder"""
        if not self._last_analysis:
            return
        try:
            from output_writer import OutputWriter

            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            query = self._last_analysis.get("query", "analysis")
            safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()[:50].replace(' ', '_')
            output_dir = Path(__file__).parent / "outputs" / f"{timestamp_str}_{safe_query}"
            output_dir.mkdir(parents=True, exist_ok=True)

            OutputWriter(base_dir=str(output_dir)).write_all_formats(self._last_analysis, "analysis")
            self.save_link.configure(text="Saved. Opening folder...")
            self.root.after(2500, lambda: self.save_link.configure(text="Save as file"))
            os.startfile(str(output_dir))
        except Exception as e:
            self.save_link.configure(text="Save failed")
            self.root.after(3000, lambda: self.save_link.configure(text="Save as file"))
            print(f"Export error: {e}")


def main():
    root = tk.Tk()
    SerpAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
