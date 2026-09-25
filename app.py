#!/usr/bin/env python3
"""
SERP Analyzer Desktop App
Simple tkinter GUI for SERP analysis.
"""

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path
from datetime import datetime

# Add src directory to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Set up environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


class SerpAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SERP Analyzer")
        self.root.geometry("900x700")
        self.root.minsize(700, 500)

        # Dark theme colors
        self.bg = "#1a1b26"
        self.bg2 = "#24283b"
        self.fg = "#c0caf5"
        self.fg2 = "#9aa5ce"
        self.accent = "#7aa2f7"
        self.success = "#9ece6a"
        self.error = "#f7768e"

        self.root.configure(bg=self.bg)

        # Configure styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_styles()

        self._last_analysis = None
        self._create_widgets()

    def _configure_styles(self):
        self.style.configure(".", background=self.bg, foreground=self.fg)
        self.style.configure("TFrame", background=self.bg)
        self.style.configure("TLabel", background=self.bg, foreground=self.fg, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground=self.accent)
        self.style.configure("TButton", font=("Segoe UI", 10), padding=8)
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("TCheckbutton", background=self.bg, foreground=self.fg)
        self.style.configure("TEntry", fieldbackground=self.bg2, foreground=self.fg)
        self.style.configure("TCombobox", fieldbackground=self.bg2, foreground=self.fg)
        self.style.map("TCheckbutton", background=[("active", self.bg)])

        # Notebook tab styling - white text for dark background
        self.style.configure("TNotebook", background=self.bg)
        self.style.configure("TNotebook.Tab",
                            background=self.bg2,
                            foreground="#ffffff",  # White
                            font=("Segoe UI", 10, "bold"),
                            padding=[12, 6])
        self.style.map("TNotebook.Tab",
                      background=[("selected", self.accent)],
                      foreground=[("selected", "#ffffff")])

    def _create_widgets(self):
        # Main container
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Label(main, text="SERP Analyzer", style="Header.TLabel")
        header.pack(pady=(0, 5))

        subtitle = ttk.Label(main, text="Analyze search results for content strategy insights", foreground=self.fg2)
        subtitle.pack(pady=(0, 20))

        # Search frame
        search_frame = ttk.Frame(main)
        search_frame.pack(fill=tk.X, pady=(0, 15))

        # Query entry
        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(search_frame, textvariable=self.query_var, font=("Segoe UI", 11), width=50)
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.query_entry.bind("<Return>", lambda e: self._run_analysis())

        # Analyze button
        self.analyze_btn = ttk.Button(search_frame, text="Analyze", style="Accent.TButton", command=self._run_analysis)
        self.analyze_btn.pack(side=tk.LEFT)

        # Options frame
        options_frame = ttk.Frame(main)
        options_frame.pack(fill=tk.X, pady=(0, 15))

        # Number of results
        ttk.Label(options_frame, text="Results:").pack(side=tk.LEFT, padx=(0, 5))
        self.num_results_var = tk.StringVar(value="10")
        num_combo = ttk.Combobox(options_frame, textvariable=self.num_results_var, values=["5", "10", "15", "20"], width=5, state="readonly")
        num_combo.pack(side=tk.LEFT, padx=(0, 20))

        # Checkboxes
        self.intent_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Intent Detection", variable=self.intent_var).pack(side=tk.LEFT, padx=(0, 15))

        self.classify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Classification", variable=self.classify_var).pack(side=tk.LEFT, padx=(0, 15))

        self.strategy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Content Strategy", variable=self.strategy_var).pack(side=tk.LEFT)

        # Notebook for tabs
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 10))

        # Create tabs
        self._create_overview_tab()
        self._create_intent_tab()
        self._create_strategy_tab()
        self._create_results_tab()
        self._create_export_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main, textvariable=self.status_var, foreground=self.fg2)
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def _create_text_widget(self, parent):
        text = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg=self.bg2,
            fg=self.fg,
            insertbackground=self.fg,
            selectbackground=self.accent,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        return text

    def _create_overview_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Overview")
        self.overview_text = self._create_text_widget(frame)
        self.overview_text.pack(fill=tk.BOTH, expand=True)
        self.overview_text.insert(tk.END, "Enter a search query and click Analyze to get started.")
        self.overview_text.config(state=tk.DISABLED)

    def _create_intent_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Intent")
        self.intent_text = self._create_text_widget(frame)
        self.intent_text.pack(fill=tk.BOTH, expand=True)
        self.intent_text.config(state=tk.DISABLED)

    def _create_strategy_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Strategy")
        self.strategy_text = self._create_text_widget(frame)
        self.strategy_text.pack(fill=tk.BOTH, expand=True)
        self.strategy_text.config(state=tk.DISABLED)

    def _create_results_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="SERP Results")
        self.results_text = self._create_text_widget(frame)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        self.results_text.config(state=tk.DISABLED)

    def _create_export_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Export")

        ttk.Label(frame, text="Export Analysis", style="Header.TLabel").pack(pady=(20, 10))
        ttk.Label(frame, text="Save your analysis results to files.", foreground=self.fg2).pack(pady=(0, 30))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        ttk.Button(btn_frame, text="Export JSON", command=lambda: self._export("json")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export CSV", command=lambda: self._export("csv")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export All", command=lambda: self._export("all"), style="Accent.TButton").pack(side=tk.LEFT, padx=5)

        self.export_status = ttk.Label(frame, text="", foreground=self.fg2)
        self.export_status.pack(pady=(20, 0))

    def _update_text(self, widget, content):
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, content)
        widget.config(state=tk.DISABLED)

    def _run_analysis(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showwarning("Input Required", "Please enter a search query.")
            return

        self.analyze_btn.config(state=tk.DISABLED)
        self.status_var.set("Analyzing...")

        # Show a rotating loading message on the Overview tab while the analysis runs
        self._busy = True
        self._loading_step = 0
        self.notebook.select(0)
        self._show_loading_message()

        # Run in background thread
        thread = threading.Thread(target=self._do_analysis, args=(query,))
        thread.daemon = True
        thread.start()

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

    def _show_loading_message(self):
        """Swap in the next loading line every 2.5 seconds until the analysis finishes"""
        if not getattr(self, "_busy", False):
            return
        line = self.LOADING_LINES[self._loading_step % len(self.LOADING_LINES)]
        self._update_text(self.overview_text, f"We're analyzing your search.\n\n{line}")
        self._loading_step += 1
        self.root.after(2500, self._show_loading_message)

    def _do_analysis(self, query):
        try:
            from dataforseo_search import get_search_client
            from intent_detector import IntentDetector
            from classifier import ResultClassifier
            from content_strategy_analyzer import ContentStrategyAnalyzer

            num_results = int(self.num_results_var.get())

            # Fetch results
            self.root.after(0, lambda: self.status_var.set("Fetching search results..."))
            search_client = get_search_client()
            results = search_client.search(query, num_results=num_results)

            if not results:
                self.root.after(0, lambda: self._show_error("No results found"))
                return

            timestamp = datetime.now().isoformat(timespec="seconds")
            analysis = {
                "query": query,
                "timestamp": timestamp,
                "total_results": len(results),
                "results": results,
                "serp_features": search_client.last_features,
                "search_source": "DataForSEO" if type(search_client).__name__ == "DataForSEOClient" else "Serper"
            }

            # Save the full Serper response so we can see every SERP feature it returns
            self._save_raw_response(query, search_client.last_raw)

            # Intent detection
            if self.intent_var.get():
                self.root.after(0, lambda: self.status_var.set("Detecting intent..."))
                intent_detector = IntentDetector()
                analysis["intent"] = intent_detector.detect_intent(query, results)

            # Classification
            if self.classify_var.get():
                self.root.after(0, lambda: self.status_var.set("Classifying results..."))
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
                    self.root.after(0, lambda: self.status_var.set("Checking questions..."))
                    filtered = classifier.filter_questions(
                        query, features["people_also_ask"], [r.get("title", "") for r in results]
                    )
                    features["people_also_ask"] = filtered["keep"]
                    features["people_also_ask_removed"] = filtered["removed"]

            # Content strategy
            if self.strategy_var.get():
                self.root.after(0, lambda: self.status_var.set("Analyzing content strategy..."))
                strategy_analyzer = ContentStrategyAnalyzer()
                analysis["content_strategy"] = strategy_analyzer.analyze(
                    query=query,
                    results=analysis["results"],
                    user_intent=analysis.get("intent"),
                    serp_features=analysis.get("serp_features")
                )

            self._last_analysis = analysis
            self.root.after(0, lambda: self._display_results(analysis))

        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda: self._show_error(msg))

    def _save_raw_response(self, query, raw):
        """Write the untouched Serper response to outputs/raw for inspection"""
        if not raw:
            return
        try:
            import json
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
        self._update_text(self.overview_text, "Something went wrong. Check the message and try again.")
        self.status_var.set("Error")
        self.analyze_btn.config(state=tk.NORMAL)
        messagebox.showerror("Error", message)

    def _display_results(self, data):
        self._busy = False
        self.status_var.set("Analysis complete!")
        self.analyze_btn.config(state=tk.NORMAL)

        # Overview
        overview = ""
        verdict = data.get("content_strategy", {}).get("recommendation", {}).get("verdict")
        if verdict:
            overview += f"VERDICT: {verdict['summary']}\n\n"
        overview += f"Query: {data['query']}\n"
        overview += f"Results: {data['total_results']}\n"
        overview += f"Timestamp: {data['timestamp']}\n\n"

        if "classification_summary" in data:
            overview += "=== Result Type Distribution ===\n"
            total = sum(data["classification_summary"].values())
            for cat, count in sorted(data["classification_summary"].items(), key=lambda x: -x[1]):
                pct = count / total * 100
                bar = "█" * int(pct / 5)
                overview += f"{cat:15} {count:2} ({pct:5.1f}%) {bar}\n"

        if "content_strategy" in data:
            rec = data["content_strategy"].get("recommendation", {})
            overview += f"\n=== Recommended Content ===\n"
            overview += f"Type: {rec.get('content_type', 'N/A')}\n"
            overview += f"Format: {rec.get('format', 'N/A')}\n"

        features = data.get("serp_features") or {}
        if features.get("present"):
            overview += f"\n=== What Else Is On The Page ===\n"
            overview += ", ".join(features["present"]) + "\n"
            aio = features.get("ai_overview")
            overview += f"AI Overview found: {'yes' if aio else 'no'}\n"
            if isinstance(aio, dict) and aio.get("sources"):
                overview += "AI Overview cites:\n"
                for s in aio["sources"][:8]:
                    overview += f"  • {s.get('title') or s.get('domain')}  ({s.get('domain', '')})\n"

        overview += f"\nSearch data from: {data.get('search_source', 'Serper')}\n"

        self._update_text(self.overview_text, overview)

        # Intent
        if "intent" in data:
            intent = data["intent"]
            intent_text = f"=== User Intent ===\n\n"
            intent_text += f"{intent.get('user_intent', 'N/A')}\n\n"
            intent_text += f"Type: {intent.get('intent_type', 'N/A')}\n"
            intent_text += f"Confidence: {intent.get('confidence', 0):.0%}\n\n"
            if intent.get("key_signals"):
                intent_text += f"Key Signals: {', '.join(intent['key_signals'])}\n\n"
            intent_text += f"Reasoning:\n{intent.get('reasoning', 'N/A')}\n"
            self._update_text(self.intent_text, intent_text)
        else:
            self._update_text(self.intent_text, "Intent detection was skipped.")

        # Strategy
        if "content_strategy" in data:
            strategy = data["content_strategy"]
            rec = strategy.get("recommendation", {})

            strat_text = "=== Content Strategy Recommendation ===\n\n"
            if rec.get("verdict"):
                strat_text += f"VERDICT:\n  {rec['verdict']['summary']}\n\n"
            strat_text += f"CONTENT TYPE:\n  {rec.get('content_type', 'N/A')}\n\n"
            strat_text += f"FORMAT:\n  {rec.get('format', 'N/A')}\n\n"
            strat_text += f"ANGLE:\n  {rec.get('angle', 'N/A')}\n\n"

            strat_text += "REQUIRED ELEMENTS:\n"
            for elem in rec.get("required_elements", []):
                strat_text += f"  • {elem}\n"

            strat_text += f"\nCONFIDENCE: {rec.get('confidence', 0):.0%}\n\n"

            strat_text += "WHY THIS APPROACH:\n"
            for reason in rec.get("reasoning", []):
                strat_text += f"  • {reason}\n"

            if rec.get("questions_to_answer"):
                strat_text += "\nQUESTIONS TO ANSWER (People Also Ask):\n"
                for q in rec["questions_to_answer"]:
                    strat_text += f"  • {q}\n"

            removed = (data.get("serp_features") or {}).get("people_also_ask_removed") or []
            if removed:
                strat_text += "\nOFF-TOPIC QUESTIONS REMOVED:\n"
                for q in removed:
                    strat_text += f"  • {q}\n"

            if rec.get("related_searches"):
                strat_text += "\nSEARCHES TO CHECK NEXT:\n"
                for q in rec["related_searches"]:
                    strat_text += f"  • {q}\n"

            self._update_text(self.strategy_text, strat_text)
        else:
            self._update_text(self.strategy_text, "Content strategy analysis was skipped.")

        # SERP Results
        results_text = ""
        for r in data["results"]:
            cat = r.get("classification", {}).get("category", "unknown") if "classification" in r else "N/A"
            page_type = r.get("classification", {}).get("page_type", "")
            label = f"{cat.upper()} | {page_type.replace('_', ' ')}" if page_type else cat.upper()
            results_text += f"#{r['position']} [{label}]\n"
            results_text += f"  {r['title']}\n"
            results_text += f"  {r['url']}\n"
            results_text += f"  {r.get('snippet', '')[:200]}...\n\n"

        self._update_text(self.results_text, results_text)

        # Switch to overview tab
        self.notebook.select(0)

    def _export(self, format_type):
        if not self._last_analysis:
            messagebox.showwarning("No Data", "Run an analysis first before exporting.")
            return

        try:
            from output_writer import OutputWriter

            # Create output directory
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            query = self._last_analysis.get("query", "analysis")
            safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
            safe_query = safe_query.replace(' ', '_')

            output_dir = Path(__file__).parent / "outputs" / f"{timestamp_str}_{safe_query}"
            output_dir.mkdir(parents=True, exist_ok=True)

            writer = OutputWriter(base_dir=str(output_dir))

            if format_type == "json":
                path = writer.write_json(self._last_analysis, "analysis.json")
            elif format_type == "csv":
                path = writer.write_csv(
                    self._last_analysis.get("results", []),
                    filename="analysis.csv",
                    query_intent=self._last_analysis.get("intent"),
                    content_strategy=self._last_analysis.get("content_strategy")
                )
            else:
                paths = writer.write_all_formats(self._last_analysis, "analysis")
                path = str(output_dir)

            self.export_status.config(text=f"Exported to: {path}", foreground=self.success)

        except Exception as e:
            self.export_status.config(text=f"Error: {e}", foreground=self.error)


def main():
    root = tk.Tk()
    app = SerpAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
