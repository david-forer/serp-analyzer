# SERP Analyzer

SERP Analyzer is a Windows desktop app for writers. Type in a search, and it reads the top 10 Google results, then tells you what kind of piece Google rewards for that search and who you'd be competing with. It was built for writers without an SEO background, so the answers come in plain language.

For the search "AI readiness assessment framework", it reported:

```
Explainer. 9 of 10 results are explainers.
Competition: Crowded. Big names hold 4 and established brands hold 1 of the top 10.
Big names: undp.org, cisco.com, microsoft.com, aiforgood.itu.int
```

## What the app shows

The left side of the window holds the search box, a competition scale (Open, Mixed or Crowded) and a meter showing how clear the format is, meaning how strongly the top results agree on one format.

The right side reads top to bottom:

- The format Google rewards, with a count of the results behind it and the angle to take. When courses, products, directories or tools lead the results, a "Heads up" note says an article will struggle to rank.
- Competition, with a line on what the rating means for your site, then the counts and names behind it.
- What to include, the People Also Ask questions readers have, other signals from the page, and related searches. Click a related search to check it.
- The details: what searchers want, a breakdown of page types in the top 10, what else Google shows on the page, and the full top 10 with links.

"See all 10 results" opens every result with its snippet, and "Save as file" exports the analysis as JSON, CSV and a plain-text summary.

## How it works

The app fetches the top 10 results for your search. An OpenAI model then labels each one with a page type, such as how-to guide, explainer, service page, forum thread or course page, and with how well known the site behind it is. The format recommendation comes from counting the page types. If 4 results are how-to guides and 3 are service pages, it suggests a how-to guide that also covers cost and timeline.

The competition rating comes from counting who ranks. Big names are organizations most people in the US would recognize, plus any .gov, .edu or .int site. Established brands are well known within their industry. With 4 or more big names, or 7 or more big names and established brands combined, competition is Crowded. With 3 or fewer combined, it's Open. Anything in between is Mixed. Forum and community posts in the top 10 are noted, since they usually mean good content is scarce.

People Also Ask questions become a starting outline, after a second check removes questions about a different meaning of the search.

The app describes the competition. It does not predict whether you can rank, because that depends mostly on your own site, which the app can't see. It also reads only titles, snippets and the results page, so it has no word counts or backlink data.

## What you need

- Windows 10 or 11
- Python 3.10 or newer
- An OpenAI API key
- Search data from Serper, or from DataForSEO if you want AI Overviews

Each analysis costs well under a cent in API fees.

## Setup

1. Install Python from python.org. On the first screen of the installer, tick **Add python.exe to PATH**.
2. Download this project. Click the green Code button on this page, choose Download ZIP, and unzip it wherever you like. If you use Git, you can clone the repository instead.
3. Open PowerShell in the project folder. In File Explorer, open the `serp-analyzer` folder, click the address bar, type `powershell` and press Enter.
4. Create a private Python environment for the app:
   ```powershell
   python -m venv venv
   ```
   This makes a `venv` folder that holds the app's libraries, separate from the rest of your computer. It takes a few seconds and prints nothing when it works.
5. Install the libraries:
   ```powershell
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   You'll see download progress, ending with a line that starts with "Successfully installed".
6. Create your settings file and open it:
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```
   Fill in your keys (see the next section), save, and close Notepad.
7. Double-click `launch.bat` to open the app.

## API keys

The `.env` file holds your keys. It stays on your computer and is excluded from Git, so it will not be uploaded if you publish your own copy.

### OpenAI (required)

Create a key at platform.openai.com under API keys. The account needs billing set up. Paste the key after `OPENAI_API_KEY=`.

### Serper

Sign up at serper.dev and copy the API key from the dashboard into `SERPER_API_KEY=`.

### DataForSEO (optional)

DataForSEO returns Google's AI Overviews and the sites they cite. Serper does not. Sign up at app.dataforseo.com, open API Access, and copy your API login and API password into `DATAFORSEO_LOGIN=` and `DATAFORSEO_PASSWORD=`. The API password is a separate generated password, not the one you sign in with. New accounts get a small trial credit. After that, DataForSEO requires a $50 minimum deposit.

When both DataForSEO lines are filled in, the app uses DataForSEO. When either one is empty, it uses Serper. The last line of the Overview tab shows which one ran.

## Where files are saved

Everything goes in the `outputs` folder inside the project. The Export tab saves each analysis to its own folder, named with the date and the search. The app also saves the untouched search data from every run to `outputs/raw`, which is useful for checking exactly what Google returned. The `outputs` folder is excluded from Git.

## Changing the country or language

Results are for Google in the United States, in English. To change that, edit `gl` and `hl` in `src/serper_search.py`, or `location_code` and `language_code` in `src/dataforseo_search.py`.

## Search API decisions

A running log of which search API this tool uses and why. Newest first.

### 2026-09-25: Switched to DataForSEO, with Serper kept as a fallback

The raw Serper responses settled the question. Two searches were tested: "ai audit for small business" and "how does compound interest work", a search that almost always shows an AI Overview in Google. Both Serper responses contained only organic results, People Also Ask and related searches. Neither contained an AI Overview or a featured snippet, so Serper's standard search does not pass these through. DataForSEO's Live Advanced endpoint returns every SERP element as its own item, including AI Overviews with the sources they cite, featured snippets, and Discussions and forums blocks. Those are the signals that tell a writer what format Google prefers, so the switch was worth the extra setup. Cost is about $0.002 per search, plus $0.002 for the AI Overview option, which DataForSEO refunds when no AI Overview appears. It needs a $50 minimum deposit and a login and API password instead of a single key. The app uses DataForSEO whenever `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` are set in `.env`, and falls back to Serper otherwise.

### 2026-09-25: Tested whether Serper returns AI Overviews

Serper was the search source at this point. It needs a single API key, which keeps setup simple for writers trying the tool. Published comparisons disagreed on whether Serper returns Google's AI Overview, and the AI Overview is one of the most useful signals for deciding what to write. To settle it with real data, the app was changed to save every raw search response to `outputs/raw/` and to show on the Overview tab whether an AI Overview was found. DataForSEO was lined up as the replacement if Serper failed the test, because its documentation confirms AI Overview support through the `load_async_ai_overview` option.

### Earlier: Google Custom Search API replaced by Serper

The first version of this tool used Google's Custom Search JSON API. It was replaced by Serper, but the reason was not recorded at the time.

## License

MIT License
