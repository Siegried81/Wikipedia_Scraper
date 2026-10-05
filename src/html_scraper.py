from bs4 import BeautifulSoup
from src.http_session import USER_AGENT, build_session
import csv
import json
import re

# Wikipedia citation and audio artifacts, compiled once and reused by clean_text.
# One generic bracket pattern replaces a hand-written list of cases: it matches
# any bracketed note ([1], [n 3], [citation needed]) and not only single chars.
CITATION_PATTERN = re.compile(r"\[[^\]]*\]")
AUDIO_PATTERN = re.compile(r"\(?\s*(?:Écouter|uitspraak)?\s*ⓘ\s*\)?")
WHITESPACE_PATTERN = re.compile(r"\s+")


class WikipediaScraper():
    def __init__(self, session):
        """
        Constructor with one parameter
        :param: a requests.Session() object put into self.session attribute
        """
        self.session = session
    
    def fetch_html(self, url: str) -> str:
        """
        Method to fetch a web page's html
        :param: string of an url
        Returns the html text, or an empty string if unsuccessfull
        Always a string (never a Response), so the caller can feed the result
        straight to get_first_paragraph whether the request worked or not.
        """
        try:
            #Using the opened session to scrape a wikipedia page.
            #The User-Agent is passed explicitly because the session comes from
            #the caller and may not carry the project's identification header.
            response = self.session.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            #Any non-success status means there is no page to parse
            if response.status_code != 200:
                raise Exception(f"Request failed with status {response.status_code}")
            return response.text
        #Handling of errors
        except Exception as ex:
            print(f"Something went wrong: {ex}")
            return ""

    def get_first_paragraph(self, html: str):
        """
        Method to get the first paragraph of someone's biography on wikipedia
        :param: a string of a web page's html
        Returns a string of the first paragraph or 'failed' if unsuccessfull
        """
        first_paragraph = "failed"
        try:
            #Loading the content (html tree) in a BeautifulSoup Object
            soup = BeautifulSoup(html, features="html.parser")
            #Making a list of all the paragraphs and checking there was at least one
            paragraphs = soup.find_all("p")
            if not paragraphs:
                raise Exception("Couldn't find any paragraphs.")
            #Going throug the first ten and finding the first with an emboldened part and checking if there was at least one
            for p in paragraphs[:10]:
                if p.find("b"):
                    first_paragraph = self.clean_text(str(p.text))
                    break
            if first_paragraph == "failed":
                raise Exception(f"Couldn't find a paragraph containing <bold> within : {paragraphs[:10]}")
        #Handling of errors
        except Exception as ex:
            print("Something went wrong", ex)
        except BaseException as ex:
            print("Something went wrong", ex)
        # Whatever happens, return a string
        finally:
            return first_paragraph
    
    def clean_text(self, text: str) -> str:
        """
        Method to clean a string with re library
        :param: a string to parse
        Returns the parsed string
        """
        #Drop any bracketed citation, then the audio-sample markers
        text = CITATION_PATTERN.sub("", text)
        text = AUDIO_PATTERN.sub("", text)
        #Collapse the newlines and double spaces left behind by the removals
        return WHITESPACE_PATTERN.sub(" ", text).strip()

    def to_json_file(self, filepath: str, leaders) -> None:
        """
        Method to create or overwrite a json file
        :param: string of the filepath
        :param: Python object to put in the file
        """
        #encoding and ensure_ascii are explicit: the default encoding follows the
        #OS codepage (ANSI on Windows) and json would escape every accent, which
        #turns names like François into mojibake or ç sequences
        with open(filepath, "w", encoding="utf-8") as js_file:
            #Transform the python object in a json string
            js_str = json.dumps(leaders, ensure_ascii=False)
            js_file.write(js_str)

    def to_csv_file(self, filepath: str, leaders: dict) -> None:
        """
        Method to create or overwrite a csv file
        :param: string of the filepath
        :param: Python dictionary to put in the file
        One row per leader with the country as an extra column, written by
        csv.DictWriter so quoting and commas inside the text are escaped and the
        file can really be read back by pandas or a spreadsheet.
        """
        #Flatten {country: [leader, ...]} into one row per leader
        rows = []
        fieldnames = ["country"]
        for country, leads in leaders.items():
            for leader in leads:
                rows.append({"country": country, **leader})
                #Collect the columns in order of first appearance, as the API
                #does not guarantee the same keys for every leader
                for key in leader:
                    if key not in fieldnames:
                        fieldnames.append(key)

        #newline="" is required by the csv module to avoid blank lines on Windows
        with open(filepath, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    #Some testing of the class and it's methods if this file is directly executed in a command line
    with build_session() as session:
        wiki = WikipediaScraper(session)

        html = wiki.fetch_html("https://fr.wikipedia.org/wiki/Fran%C3%A7ois_Hollande")

        fp = wiki.get_first_paragraph(html)

        print(fp)