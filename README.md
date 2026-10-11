# WIKIPEDIA COUNTRY LEADERS SCRAPER

This project is a modular Python web scraping pipeline built in 3 days. It automatically collects data on political leaders by combining a custom REST API client with a BeautifulSoup scraper that extracts summaries directly from Wikipedia pages.

## KEY FEATURES

- **Dynamic File Exporter:** Built with the native argparse library, allowing the user to select the output format directly from the terminal using dedicated parameters. It can flatten nested data structures to generate a tabular .csv spreadsheet file ready for pandas, or export a standard structured .json database.
- **API Client with Cookie Refresh:** Automatically manages session cookies and refreshes them if they expire during execution.
- **HTML Scraper:** Grabs and cleans the first biographical paragraph of a leader's Wikipedia page using BeautifulSoup and regex.
- **OOP Architecture:** Clear separation of concerns between API requests (src/api_client.py), HTML processing (src/html_scraper.py), and the main orchestration (main.py).
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
│   └── html_scraper.py
├── .gitignore
├── README.md
├── main.py
└── requirements.txt
```

## HOW TO SETUP AND RUN

To set up the project locally inside a clean virtual environment, run `git clone https://github.com/Siegried81/Wikipedia_Scraper.git` and then go inside the folder using `cd Wikipedia_Scraper`. (This repository is a fork of [Max96H/Wikipedia_Scraper](https://github.com/Max96H/Wikipedia_Scraper), the team repository the exercise was built in.)

Create your virtual environment with python3 -m venv wikipedia_scraper_env. Activate it on Windows with source wikipedia_scraper_env/Scripts/activate (or on Linux/macOS with source wikipedia_scraper_env/bin/activate). 
Once activated, install the libraries with pip install -r requirements.txt.

To run the full scraper and generate the final data file, just execute python main.py. This will create a file named leaders.json at the root of the project.

If you want to test the components separately, you can run them individually. For the API connection and cookie checks, run python src/api_client.py. For the HTML extraction logic, run python src/html_scraper.py.

## HOW THE CODE WORKS

```
def main():
    """
    Main function of this wiki scraper project
    """

    #Create an ArgumentParser Object 
    parser = argparse.ArgumentParser(description="A wiki scraper to make json/csv file")
    #Add argument '--file'
    parser.add_argument('--file', type=str, default='json', help='The type of file to create (json|csv)')
    #Parse the command line arguments
    args = parser.parse_args()

    #Establish if we are gonna output a json file or a csv file depending on the command line arguments
    chose_csv = False
    file = "leaders.json"
    if args.file == "csv":
        chose_csv = True
        file = "leaders.csv"

    #Create a CountryLeadersAPI with our chosen api
    base_url = "https://country-leaders.onrender.com"
    country_leader_api = CountryLeadersAPI(base_url)

    #Getting a list of countries from the api
    countries = country_leader_api.get_countries()

    #Making a dictionary, keys = countries and values = leaders (list of dictionaries obtained from the api)
    leaders_per_countries = {}
    for country in countries:
        leaders = country_leader_api.get_leaders(country)

        leaders_per_countries[country] = leaders

    #Opening a Session Object to make the requests to wikipedia within one session (speeds things up)
    with requests.Session() as session:
        #Making the WikipediaScraper Object with the session
        wikipedia_scraper = WikipediaScraper(session)

        #Going through each leader to add a paragraph from their wikipedia page
        for country, leaders in leaders_per_countries.items():
            for i, leader in enumerate(leaders):
                html = wikipedia_scraper.fetch_html(leader["wikipedia_url"])

                leaders_per_countries[country][i]["first_paragraph"] = wikipedia_scraper.get_first_paragraph(html)

    #Creating either a csv or json file with the leaders per countries
    if chose_csv:
        wikipedia_scraper.to_csv_file(file, leaders_per_countries)
        print(1)
    else:
        wikipedia_scraper.to_json_file(file, leaders_per_countries)
        print(2)



if __name__ == "__main__":
    main()
```

We split the core logic into two tracks before plugging everything together in the main file:

### The API Part (src/api_client.py)
This file contains the CountryLeadersAPI class. Its main job is to fetch raw JSON data from the server. It handles security by checking for 401 and 403 HTTP status codes. If a token expires while looping through the data, the refresh_cookie method triggers automatically to get a new one. It uses get_countries to see which countries are supported and get_leaders to fetch the list of politicians for a specific country.

### The Scraping Part (src/html_scraper.py)
This file handles the WikipediaScraper class. To avoid overloading the network, it reuses the same requests.Session object created by the main script. The get_first_paragraph method uses BeautifulSoup to search the first 10 paragraphs of the page. It looks for a bold tag () which usually contains the leader's name, meaning it found the actual introduction. The clean_text method uses regex (re.sub) to strip out annoying Wikipedia artifacts like citation brackets (e.g., [1], [n 3]), extra newlines (\n), or the speaker icon (Écouterⓘ).

### Integration (main.py)
This is the central script. It coordinates the whole pipeline: it calls the API client to map out the target countries, fetches the leaders, loops through their Wikipedia URLs, uses the scraper to append the text summary to each leader, and finally saves everything into a JSON or csv file.

```
 {"fr": [{"id": "Q157", "first_name": "Fran\u00e7ois", "last_name": "Hollande", "birth_date": "1954-08-12", au 15 mai 2012............"}]
    },
```
```
fr
{'id': 'Q157', 'first_name': 'François', 'last_name': 'Hollande', 'birth_date': '1954-08-12',
us
{'id': 'Q23', 'first_name': 'George', 'last_name': 'Washington', 'birth_date': '1732-02-22', '
be
{'id': 'Q12978', 'first_name': 'Guy', 'last_name': 'Verhofstadt', 'birth_date': '1953-04-11',
ma
{'id': 'Q57553', 'first_name': 'Mohammed', 'last_name': 'None', 'birth_date': '1963-08-21', 'd
ru
{'id': 'Q7747', 'first_name': 'Vladimir', 'last_name': 'Putin', 'birth_date': '1952-10-07', 'd
```

## GIT FLOW & COLLABORATION

To simulate the real-world conditions of a data engineering pipeline in a company, any direct push to the main branch was strictly prohibited.
All phases of individual exploration and prototyping were restricted to the dev directory using the files max_sandbox_notebooook.ipynb and siegried_sandbox_notebooook.ipynb. The production code was developed on the branch Sieg for the api-client and on the branch Max for the html-scraper. Each feature integration required opening a formal Pull Request (PR) on GitHub, followed by a code review and manual approval from the partner before it could be merged.
