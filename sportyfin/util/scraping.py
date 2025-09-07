import time
import regex
import datetime
import json
import sys
from . import event_info
from .pretty_print import *
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup

load_dotenv()

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

FOOTBALL = "football"
F1 = "f1"
NFL = "nfl"
NBA = "nba"
NHL = "nhl"
UFC = "ufc"
BOXING = "boxing"
RUGBY = "rugby"


def flatten_json(y: dict) -> dict:
    """
    Function capable of flattening an object.
    """
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            ix = 0
            for a in x:
                flatten(a, name + str(ix) + '_')
                ix += 1
        else:
            out[name[:-1]] = x
    flatten(y)
    return out


# Helper Functions
def selenium_find(link: str) -> list:
    """
    Looks for possible m3u8 links in network traffic from a streaming site.
    """
    pind(f"Trying to find m3u8 in network traffic - {link}", colours.OKCYAN, otype.DEBUG)
    res = []
    try:
        try:

            caps = DesiredCapabilities.CHROME
            caps['goog:loggingPrefs'] = {'performance': 'ALL'}
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
        except Exception as e:
            print(e.with_traceback())
        driver.get(link)
        time.sleep(1)  # wait for all the data to arrive.
        perf = driver.get_log('performance')
        for j in perf:
            try:
                if "m3u8" in json.dumps(j):
                    obj = flatten_json(json.loads(j["message"]))
                    list_of_dict_values = list(obj.values())
                    for value in list_of_dict_values:
                        if str(value).find("m3u8") > -1 and str(value) not in res:
                            if int(requests.get(value, allow_redirects=True).status_code) == 200:
                                pind2(f"Found a stream - {str(value)}", colours.OKGREEN, otype.REGULAR)
                            res.append(value)
            except KeyboardInterrupt:
                sys.exit()
                pass
            except Exception as e:
                p("Something went wrong pulling a m3u8 link", colours.FAIL, otype.ERROR, e)
                continue
    except KeyboardInterrupt:
        sys.exit()
        pass
    except Exception as e:
        print(e.with_traceback())
        p("Something went wrong with Selenium", colours.FAIL, otype.ERROR, e)
    return list(dict.fromkeys(res))


def html_find(link: str) -> list:
    """
    Looks for possible m3u8 links in html traffic from a streaming site.
    """
    pind(f"Trying to find m3u8 in page content - {link}", colours.OKCYAN, otype.DEBUG)
    res = []
    try:
        content = requests.get(link).text
        for match in regex.findall(r"([\'][^\'\"]+(\.m3u8)[^\'\"]*[\'])|([\"][^\'\"]+(\.m3u8)[^\'\"]*[\"])", content):
            for i in match:
                if (i.count("\'") == 2 and i.count("\"") == 0) or (i.count("\"") == 2 and i.count("\'") == 0) and ".m3u8" in i and i[1:-1] not in res:
                    if int(requests.get(i[1:-1], allow_redirects=True).status_code) == 200:
                        res.append(i[1:-1])
                        pind2(f"Found a stream - {str(i[1:-1])}", colours.OKGREEN, otype.REGULAR)
    except Exception as e:
        pass
    return res


def find_urls(ll: list) -> list:
    """
    Helper function used to scrape html and network traffic from a provided link.
    """
    res = []
    if len(ll) == 0:
        return res
    try:
        for link in ll:
            if os.environ.get('selenium') == "0":
                res.extend(x for x in selenium_find(link) if x not in res)
            res.extend(x for x in html_find(link) if x not in res)
    except KeyboardInterrupt:
        sys.exit()
        pass
    except Exception as e:
        return list(dict.fromkeys(res))
    if len(res) == 0:
        p(f"Did not find streams", colours.FAIL, otype.DEBUG)
    return list(dict.fromkeys(res))


def bypass_bitly(ll: list) -> list:
    """
    Ability to bypass bitly pages to get streaming site url.
    """
    res = []
    for link in ll:
        # Only process Bitly links
        if "bit.ly" in link:
            try:
                parsed_html = BeautifulSoup(requests.request("GET", link).text, features="lxml")
                url = parsed_html.body.find('a', attrs={'id': 'skip-btn'}).get('href')
                if url:
                    res.append(url)
            except Exception as e:
                p(f"Error occurred bypassing bitly - {link}", colours.FAIL, otype.ERROR)
        else:
            # Not a Bitly link, just append as-is
            res.append(link)
    return list(dict.fromkeys(res))


def pull_bitly_link(link) -> list:
    """
    Pull stream links from the event page table.
    """
    res = []
    parsed_html = BeautifulSoup(requests.get(link).text, "html.parser")
    # Find all <tr> rows
    for tr in parsed_html.find_all('tr'):
        # Find all <a> tags inside the row
        for a_tag in tr.find_all('a', href=True):
            href = a_tag['href']
            # Optionally, filter for links containing 'watch' or 'view'
            if "watch" in href or "view" in href or "totview" in href:
                if "https://hdplayerr.xyz/totview.php?src=" in href:
                    href = href.replace("https://hdplayerr.xyz/totview.php?src=", "")
                res.append(href)
                p(f"STREAM LINKS FOR EVENT: {href}", colours.HEADER, otype.REGULAR)
    return res


def make_match(api_res, hosts, lg) -> list:
    events = []
    for g in api_res:
        ht = g['homeTeam']
        at = g['awayTeam']
        if lg == EF:
            host_id = str(g['eventLink'].split('/')[-1]).split("?")[0]
        else:
            host_id = str(g['eventLink']).split('/')[-1]
        match = {
            "home_team": {
                "name": ht['name'],
                "icon_url": ht['logo']
            },
            "away_team": {
                "name": at['name'],
                "icon_url": at['logo']
            },
            "match": {
                "name": g.get('name', ''),
                "img_location": "",
                "url": f"{hosts[0]}{host_id}{hosts[1]}",
                "start": "",
                "stop": ""
            }
        }
        try:
            t = ''.join(g['startTime'].split(':'))
            if len(t) > 4:
                t = t[:(4-len(t))]
            t_end = str(int(t) + 300)
            if len(t_end) < 4:
                t_end = "0" + t_end
            try:
                match['match']['start'] = ''.join(g['formatedStartDate'].split('-')) + t + " GMT"
                match['match']['stop'] = ''.join(g['formatedStartDate'].split('-')) + t_end + " GMT"
            except:
                match['match']['start'] = ''.join(g['startDate'].split('-')) + t + " GMT"
                match['match']['stop'] = ''.join(g['startDate'].split('-')) + t_end + " GMT"
        except:
            pass
        if match['match']['name'] == '':
            match['match']['name'] = f"{match['away_team']['name']} vs {match['home_team']['name']}"
        match['match']['img_location'] = event_info.generate_img(match, lg)
        p(f"Found - {match['match']['name']}", colours.OKGREEN, otype.REGULAR)
        pind2(f"URL - {match['match']['url']}", colours.OKCYAN, otype.DEBUG)
        pind2(f"ICON - {match['match']['img_location']}", colours.OKCYAN, otype.DEBUG)
        events.append(event)
    return event


def find_streams(lg: str) -> list:
    """
    Finds current events that are active for a given league.
    """
    STREAM_LINK = os.environ.get('stream_link')
    p(f"COLLECTING {lg.upper()} STREAMING LINKS", colours.HEADER, otype.REGULAR)
    res = []
    path = None
    if lg == FOOTBALL:
        path = "football"
    elif lg == F1:
        path = "f1"
    elif lg == NFL:
        path = "nfl"
    elif lg == NBA:
        path = "nba"
    elif lg == NHL:
        path = "nhl"
    elif lg == UFC:
        path = "ufc"
    elif lg == BOXING:
        path = "boxing"
    elif lg == RUGBY:
        path = "rugby"

    if path:
        main_link = f"{STREAM_LINK}/{path}"
        p(f"USING LINK: " + main_link, colours.HEADER, otype.REGULAR)
        events = scrape_events(main_link)

    for event in events:
        event['stream_links'] = pull_bitly_link(event['url'])
        if event['stream_links'] and event not in res:
            res.append(event)
    if len(res) == 0:
        p(f"COULD NOT FIND ACTIVE {lg.upper()} STREAM LINKS", colours.FAIL, otype.ERROR)
    return res


def get_streams(s: list) -> list:
    return find_urls(bypass_bitly(s))


def scrape_events(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    events = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/events/"):
            event_info = {}

            event_info["name"] = href
            if "/events/" in event_info["name"]:
                event_info["name"] = href.replace("/events/", "")

            event_info["url"] = f"https://sportsurge.bz{href}"
            p(f"FOUND EVENT: " + event_info["name"] + "    " + event_info["url"], colours.HEADER, otype.REGULAR)
            # Get team names and images
            teams = a_tag.find_all("img", alt=True)
            if len(teams) == 2:
                event_info["home_team"] = teams[0]["alt"]
                event_info["home_team_img"] = teams[0]["src"]
                event_info["away_team"] = teams[1]["alt"]
                event_info["away_team_img"] = teams[1]["src"]
            events.append(event_info)
    return events