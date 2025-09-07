import time
import regex
import datetime
import json
import sys
from . import event_info
from .pretty_print import *
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import traceback

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
    driver = None
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-dev-shm-usage')
        # Use system Chromium inside container; allow override via CHROME_BIN
        chrome_options.binary_location = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
        # Enable performance logging and network events
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        chrome_options.add_experimental_option('perfLoggingPrefs', {
            'enableNetwork': True,
            'enablePage': False
        })
        driver = webdriver.Chrome(options=chrome_options)
        # Explicitly enable Network domain to ensure events are captured
        try:
            driver.execute_cdp_cmd('Network.enable', {})
        except Exception:
            pass
    except Exception as e:
        traceback.print_exc()
        p("Could not start Selenium Chrome driver", colours.FAIL, otype.ERROR, e)
        return res  # Return early if driver creation fails

    try:
        driver.get(link)
        time.sleep(10)  # wait for network activity
        perf = driver.get_log('performance')
        for entry in perf:
            try:
                message = json.loads(entry.get('message', '{}')).get('message', {})
                method = message.get('method', '')
                params = message.get('params', {})
                url = None
                if method == 'Network.responseReceived':
                    url = params.get('response', {}).get('url')
                elif method == 'Network.requestWillBeSent':
                    url = params.get('request', {}).get('url')
                if url and '.m3u8' in url and url not in res:
                    try:
                        if int(requests.get(url, allow_redirects=True).status_code) == 200:
                            pind2(f"Found a stream - {url}", colours.OKGREEN, otype.REGULAR)
                        res.append(url)
                    except Exception:
                        # Even if GET fails, keep the candidate URL
                        res.append(url)
            except KeyboardInterrupt:
                sys.exit()
            except Exception as e:
                p("Something went wrong parsing performance logs", colours.FAIL, otype.ERROR, e)
                continue
    except KeyboardInterrupt:
        sys.exit()
        pass
    except Exception as e:
        traceback.print_exc()
        p("Something went wrong with Selenium", colours.FAIL, otype.ERROR, e)
    finally:
        if driver:
            driver.quit()
    return list(dict.fromkeys(res))


def html_find(link: str) -> list:
    """
    Looks for possible m3u8 links in html traffic from a streaming site.
    """
    pind(f"Trying to find m3u8 in page content - {link}", colours.OKCYAN, otype.DEBUG)
    res = []
    try:
        content = requests.get(link).text
        for match in regex.findall(r"([\'][^\'\"]+(\.m3u8)[^\'\"]*[\'])|(https?:\/\/[^\s'\"<>]+\.m3u8(?:[^\s'\"<>]*)?)|([\"][^\'\"]+(\.m3u8)[^\'\"]*[\"])", content):
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
    Scrapes .m3u8 links from a list of URLs using Selenium and HTML parsing.
    """
    res = []
    if not ll:
        return res
    try:
        for link in ll:
            # Use Selenium first unless explicitly disabled
            if os.environ.get('selenium', '1') != "0":
                p(f"SEARCHING NETWORK TRAFFIC FOR LINK" + link, colours.HEADER, otype.REGULAR)
                res.extend(x for x in selenium_find(link) if x not in res)
            # Fallback to simple HTML parsing
            p(f"SEARCHING HTML FOR LINK" + link, colours.HEADER, otype.REGULAR)
            res.extend(x for x in html_find(link) if x not in res)
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        p(f"Exception in find_urls: {e}", colours.FAIL, otype.ERROR)
        return list(dict.fromkeys(res))
    if not res:
        p(f"Did not find streams", colours.FAIL, otype.DEBUG)
    return list(dict.fromkeys(res))


def bypass_bitly(ll: list) -> list:
    """
    Ability to bypass bitly pages to get streaming site url.
    Only processes Bitly links; other links are returned unchanged.
    """
    res = []
    for link in ll:
        if "bit.ly" in link:
            try:
                response = requests.get(link)
                parsed_html = BeautifulSoup(response.text, features="lxml")
                skip_btn = parsed_html.body.find('a', attrs={'id': 'skip-btn'})
                url = skip_btn.get('href') if skip_btn else None
                if url:
                    res.append(url)
                else:
                    p(f"Could not find skip button on Bitly page - {link}", colours.FAIL, otype.ERROR)
            except Exception as e:
                p(f"Error occurred bypassing bitly - {link}", colours.FAIL, otype.ERROR)
        else:
            # Not a Bitly link, just append as-is
            res.append(link)
    # Remove duplicates
    return list(dict.fromkeys(res))


def pull_links(link) -> list:
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


def find_website_links(lg: str) -> list:
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
        event['stream_links'] = pull_links(event['url'])
        if event['stream_links'] and event not in res:
            res.append(event)
    if len(res) == 0:
        p(f"COULD NOT FIND ACTIVE {lg.upper()} STREAM LINKS", colours.FAIL, otype.ERROR)
        p(" ")
    return res


def get_streams(s: list) -> list:
    print(f"get_streams received: {s}")
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