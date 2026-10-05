from src.api_client import CountryLeadersAPI
from src.html_scraper import WikipediaScraper
from src.http_session import build_session
import argparse
import time

#Pause between two Wikipedia fetches. Scraping etiquette: the loop walks every
#leader of every country, so without it we would hit the site as fast as the
#network allows.
REQUEST_DELAY_SECONDS = 0.5

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

    #Opening a Session Object to make the requests to wikipedia within one session
    #(speeds things up, and retries the transient failures with a backoff)
    with build_session() as session:
        #Making the WikipediaScraper Object with the session
        wikipedia_scraper = WikipediaScraper(session)

        #Going through each leader to add a paragraph from their wikipedia page
        for country, leaders in leaders_per_countries.items():
            for i, leader in enumerate(leaders):
                html = wikipedia_scraper.fetch_html(leader["wikipedia_url"])

                leaders_per_countries[country][i]["first_paragraph"] = wikipedia_scraper.get_first_paragraph(html)

                #Wait before the next page so we don't hammer Wikipedia
                time.sleep(REQUEST_DELAY_SECONDS)

    #Creating either a csv or json file with the leaders per countries
    if chose_csv:
        wikipedia_scraper.to_csv_file(file, leaders_per_countries)
    else:
        wikipedia_scraper.to_json_file(file, leaders_per_countries)
    print(f"Saved {file}")



if __name__ == "__main__":
    main()