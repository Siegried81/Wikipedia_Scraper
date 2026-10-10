from src.api_client import ApiError, CountryLeadersAPI
from src.html_scraper import WikipediaScraper
import argparse
import sys
import requests

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

    #Create a CountryLeadersAPI with our chosen api. A failing API stops the
    #run with a message instead of producing an empty file that looks complete.
    base_url = "https://country-leaders.onrender.com"
    try:
        country_leader_api = CountryLeadersAPI(base_url)

        #Getting a list of countries from the api
        countries = country_leader_api.get_countries()

        #Making a dictionary, keys = countries and values = leaders (list of dictionaries obtained from the api)
        leaders_per_countries = {}
        for country in countries:
            leaders_per_countries[country] = country_leader_api.get_leaders(country)
    except (ApiError, requests.RequestException) as exc:
        print(f"The country-leaders API is unavailable, nothing written: {exc}", file=sys.stderr)
        sys.exit(1)

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
    else:
        wikipedia_scraper.to_json_file(file, leaders_per_countries)
    total = sum(len(leaders) for leaders in leaders_per_countries.values())
    print(f"Wrote {total} leaders from {len(leaders_per_countries)} countries to {file}")



if __name__ == "__main__":
    main()