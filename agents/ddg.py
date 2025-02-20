from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import re

# load environment variables from .env file
_ = load_dotenv()

ddg = DDGS()

# choose location (try to change to your own city!)
city = "Singapore"

query = f"""
    what is the current weather in {city}?
    Should I travel there today?
    "weather.com"
"""

def search(query, max_results=6):
    try:
        results = ddg.text(query, max_results=max_results)
        return [i["href"] for i in results]
    except Exception as e:
        print(f"returning previous results due to exception reaching ddg.")
        results = [ # cover case where DDG rate limits due to high deeplearning.ai volume
        ]
        return results  

def scrape_weather_info(url):
    """Scrape content from the given URL"""
    if not url:
        return "Weather information could not be found."
    # fetch data
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return "Failed to retrieve the webpage."
    # parse result
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

def ddg_search_and_scrape(query):
    url = search(query)[0]
    # scrape first website
    soup = scrape_weather_info(url)
    print(f"Website: {url}\n\n")
    # extract text
    weather_data = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
        text = tag.get_text(" ", strip=True)
        weather_data.append(text)
    # combine all elements into a single string
    weather_data = "\n".join(weather_data)
    # remove all spaces from the combined text
    weather_data = re.sub(r'\s+', ' ', weather_data)
    print(f"Website: {url}\n\n")
    print(weather_data)

ddg_search_and_scrape(query)
# import json
# from pygments import highlight, lexers, formatters

# # parse JSON
# parsed_json = json.loads(data.replace("'", '"'))

# # pretty print JSON with syntax highlighting
# formatted_json = json.dumps(parsed_json, indent=4)
# colorful_json = highlight(formatted_json,
#                           lexers.JsonLexer(),
#                           formatters.TerminalFormatter())

# print(colorful_json)