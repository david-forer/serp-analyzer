# SERP Analyzer

SERP Analyzer is a Windows desktop app for writers. Type in a search, and it reads the top 10 Google results, then tells you whether the topic is worth writing about and what kind of piece to write. It was built for writers without an SEO background, so the answers come in plain language.

For the search "ai audit for small business", the verdict was:

```
VERDICT: Write it. How-to guide with service page elements. Competition looks
beatable: 3 of 10 top results are forum, community or self-published posts.
```

## What the app shows

Results appear on 5 tabs.

- Overview has the verdict, the mix of result types, and anything else Google shows on the page, such as People Also Ask questions or an AI Overview.
- Intent describes what the person searching most likely wants.
- Strategy has the full recommendation: the type of piece, its format and angle, what to include, and the reasons behind each call. It also lists People Also Ask questions to answer, off-topic questions it removed, and related searches to check next.
- SERP Results lists each of the top 10 with its purpose and page type.
- Export saves the analysis as JSON, CSV and a plain-text summary.

## How it works

The app fetches the top 10 results for your search. An OpenAI model then labels each one with a page type, such as how-to guide, explainer, service page, forum thread or course page. The recommendation comes from counting those labels. If 4 results are how-to guides and 3 are service pages, it suggests a how-to guide that also covers cost and timeline.

Next it reads the rest of the results page. People Also Ask questions become a starting outline, after a second check removes questions about a different meaning of the search. Forum threads and self-published posts in the top 10 suggest the competition is beatable. When course, product or directory pages lead the results, an article will struggle to rank, and the verdict says so.

The app reads titles, snippets and the results page. It does not open the ranking pages, so it has no word counts or backlink data. Treat the verdict as a well-informed starting point.

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
