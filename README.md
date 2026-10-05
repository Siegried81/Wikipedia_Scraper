# WIKIPEDIA COUNTRY LEADERS SCRAPER

This project is a modular Python web scraping pipeline built in 3 days. It automatically collects data on political leaders by combining a custom REST API client with a BeautifulSoup scraper that extracts summaries directly from Wikipedia pages.

## KEY FEATURES

- **Dynamic File Exporter:** Built with the native argparse library, allowing the user to select the output format directly from the terminal using dedicated parameters. It flattens the nested `{country: [leaders]}` structure into one row per leader (with the country as an extra column) and writes it with `csv.DictWriter`, so the .csv is properly quoted and readable by pandas, or exports a standard structured .json database. Both files are written in UTF-8 with unescaped accents.
- **API Client with Cookie Refresh:** Automatically manages session cookies and refreshes them if they expire during execution. The cookie is only kept when the server answers 200.
- **HTML Scraper:** Grabs and cleans the first biographical paragraph of a leader's Wikipedia page using BeautifulSoup and regex.
- **Resilient HTTP:** A single shared `requests.Session` (src/http_session.py) retries 429/5xx answers and timeouts with an exponential backoff, and sends one descriptive User-Agent with a contact address on every request. The main loop also waits 0.5 s between two Wikipedia pages as scraping etiquette.
- **OOP Architecture:** Clear separation of concerns between API requests (src/api_client.py), HTML processing (src/html_scraper.py), and the main orchestration (main.py).
- **Tests:** A pytest suite (tests/) covering the fetch error paths, the text cleaning, the CSV writer and the UTF-8 output. Every request is mocked, so the suite never hits Wikipedia or the API.
- **Playgrounds:** A dev/ folder where we tested our endpoints and selectors in Jupyter Notebooks before writing production code.

## PROJECT STRUCTURE

```
wikipedia-scraper/
├── dev/
│   ├── max_sandbox_notebooook.ipynb
│   └── siegried_sandbox_notebooook.ipynb
├── src/
│   ├── __init__.py
│   ├── api_client.py
│   ├── html_scraper.py
│   └── http_session.py
├── tests/
│   ├── test_api_client.py
│   ├── test_html_scraper.py
│   └── test_main.py
├── .gitignore
├── conftest.py
├── README.md
├── main.py
└── requirements.txt
```

## HOW TO SETUP AND RUN

To set up the project locally inside a clean virtual environment, run `git clone https://github.com/Max96H/Wikipedia_Scraper.git` and then go inside the folder using `cd Wikipedia_Scraper`.

Create your virtual environment with `python3 -m venv wikipedia_scraper_env`, then activate it:

```
# Windows (PowerShell)
wikipedia_scraper_env\Scripts\Activate.ps1
# Windows (Git Bash)
source wikipedia_scraper_env/Scripts/activate
# Linux, WSL or macOS
source wikipedia_scraper_env/bin/activate
```

Once activated, install the libraries with `pip install -r requirements.txt`.

To run the full scraper and generate the final data file, execute `python main.py`. This will create a file named leaders.json at the root of the project. Use `python main.py --file csv` to get leaders.csv instead. The run takes a few minutes: it pauses 0.5 s between Wikipedia pages on purpose.

If you want to test the components separately, you can run them individually. For the API connection and cookie checks, run `python -m src.api_client`. For the HTML extraction logic, run `python -m src.html_scraper`. Both reach the real servers, unlike the test suite.

To run the test suite, execute `python -m pytest` from the project root. All network calls are mocked, so no request is sent.

## HOW THE CODE WORKS

```
def main():

    parser = argparse.ArgumentParser(description="A wiki scraper to make json/csv file")
    parser.add_argument('--file', type=str, default='json', help='The type of file to create (json|csv)')
    args = parser.parse_args()

    chose_csv = False
    file = "leaders.json"
    if args.file == "csv":
        chose_csv = True
        file = "leaders.csv"

    base_url = "https://country-leaders.onrender.com"
    country_leader_api = CountryLeadersAPI(base_url)

    countries = country_leader_api.get_countries()

    leaders_per_countries = {}
    for country in countries:
        leaders = country_leader_api.get_leaders(country)

        leaders_per_countries[country] = leaders

    with build_session() as session:
        wikipedia_scraper = WikipediaScraper(session)

        for country, leaders in leaders_per_countries.items():
            for i, leader in enumerate(leaders):
                html = wikipedia_scraper.fetch_html(leader["wikipedia_url"])

                leaders_per_countries[country][i]["first_paragraph"] = wikipedia_scraper.get_first_paragraph(html)

                time.sleep(REQUEST_DELAY_SECONDS)


    if chose_csv:
        wikipedia_scraper.to_csv_file(file, leaders_per_countries)
    else:
        wikipedia_scraper.to_json_file(file, leaders_per_countries)
    print(f"Saved {file}")



if __name__ == "__main__":
    main()
```

We split the core logic into two tracks before plugging everything together in the main file:

### The API Part (src/api_client.py)
This file contains the CountryLeadersAPI class. Its main job is to fetch raw JSON data from the server. It handles security by checking for 401 and 403 HTTP status codes. If a token expires while looping through the data, the refresh_cookie method triggers automatically to get a new one, and it only stores the cookie when the answer is a 200 (an error page carries no usable token). It uses get_countries to see which countries are supported and get_leaders to fetch the list of politicians for a specific country. All of its calls go through the shared retrying session.

### The Session Part (src/http_session.py)
This small module holds the two things every request needs: the USER_AGENT constant (tool name plus a contact address, as Wikipedia's robot policy asks for) and build_session, which returns a requests.Session with an HTTPAdapter/Retry mounted on it. The API runs on free hosting and cold-starts with 503s or timeouts, so three retries with an exponential backoff are what make the first run of the day work.

### The Scraping Part (src/html_scraper.py)
This file handles the WikipediaScraper class. To avoid overloading the network, it reuses the same requests.Session object created by the main script. fetch_html always returns a string: the page's HTML, or "" when the request fails or the status is not 200, so a failed fetch cannot crash the caller. The get_first_paragraph method uses BeautifulSoup to search the first 10 paragraphs of the page. It looks for a bold tag (`<b>`) which usually contains the leader's name, meaning it found the actual introduction. The clean_text method uses regex (re.sub) to strip out Wikipedia artifacts: one generic pattern removes any bracketed note (`[1]`, `[12]`, `[n 3]`, `[citation needed]`), a second removes the audio markers (Écouterⓘ, (uitspraakⓘ)), and the whitespace left behind is collapsed into single spaces.

### Integration (main.py)
This is the central script. It coordinates the whole pipeline: it calls the API client to map out the target countries, fetches the leaders, loops through their Wikipedia URLs, uses the scraper to append the text summary to each leader, waits REQUEST_DELAY_SECONDS between two pages, and finally saves everything into a JSON or csv file.

leaders.json (`python main.py`), grouped by country, accents kept as is:

```
{"fr": [{"id": "Q157", "first_name": "François", "last_name": "Hollande", "birth_date": "1954-08-12", "first_paragraph": "François Hollande, né le 12 août 1954 à Rouen..."}],
 "us": [{"id": "Q23", "first_name": "George", "last_name": "Washington", "birth_date": "1732-02-22", "first_paragraph": "George Washington was an American..."}]}
```

leaders.csv (`python main.py --file csv`), one header row then one row per leader, commas inside the text quoted:

```
country,id,first_name,last_name,birth_date,death_date,place_of_birth,wikipedia_url,start_mandate,end_mandate,first_paragraph
fr,Q157,François,Hollande,1954-08-12,,Rouen,https://fr.wikipedia.org/wiki/François_Hollande,2012-05-15,2017-05-14,"François Hollande, né le 12 août 1954 à Rouen (Seine-Inférieure), est un haut fonctionnaire et homme d'État français."
us,Q23,George,Washington,1732-02-22,1799-12-14,Westmoreland County,https://en.wikipedia.org/wiki/George_Washington,1789-04-30,1797-03-04,"George Washington was an American Founding Father..."
```

## GIT FLOW & COLLABORATION

To simulate the real-world conditions of a data engineering pipeline in a company, any direct push to the main branch was strictly prohibited.
All phases of individual exploration and prototyping were restricted to the dev directory using the files max_sandbox_notebooook.ipynb and siegried_sandbox_notebooook.ipynb. The production code was developed on the branch Sieg for the api-client and on the branch Max for the html-scraper. Each feature integration required opening a formal Pull Request (PR) on GitHub, followed by a code review and manual approval from the partner before it could be merged.
