import sys
import time
import xml.etree.cElementTree as ET
from .util.pretty_print import *
from .util import scraping
from dotenv import load_dotenv

load_dotenv()

FOOTBALL = "football"
F1 = "f1"
NFL = "nfl"
NBA = "nba"
NHL = "nhl"
UFC = "ufc"
BOXING = "boxing"
RUGBY = "rugby"

leagues = []
OUTPUT = os.path.join(os.getcwd(), "output")
os.environ['output'] = OUTPUT


def header():
    print()
    print()
    print(f"{colours.OKCYAN + colours.BOLD} ________  ________  ________  ________  _________    ___    ___ ________ ___  ________    ")
    print(f"{colours.OKCYAN + colours.BOLD}|\   ____\|\   __  \|\   __  \|\   __  \|\___   ___\ |\  \  /  /|\  _____\\  \|\   ___  \    ")
    print(f"{colours.OKCYAN + colours.BOLD}\ \  \___|\ \  \|\  \ \  \|\  \ \  \|\  \|___ \  \_| \ \  \/  / | \  \__/\ \  \ \  \\ \  \   ")
    print(f"{colours.OKCYAN + colours.BOLD} \ \_____  \ \   ____\ \  \\\  \ \   _  _\   \ \  \   \ \    / / \ \   __\\ \  \ \  \\ \  \  ")
    print(f"{colours.OKCYAN + colours.BOLD}  \|____|\  \ \  \___|\ \  \\\  \ \  \\  \|   \ \  \   \/  /  /   \ \  \_| \ \  \ \  \\ \  \ ")
    print(f"{colours.OKCYAN + colours.BOLD}    ____\_\  \ \__\    \ \_______\ \__\\ _\    \ \__\__/  / /      \ \__\   \ \__\ \__\\ \__\ ")
    print(f"{colours.OKCYAN + colours.BOLD}   |\_________\|__|     \|_______|\|__|\|__|    \|__|\___/ /        \|__|    \|__|\|__| \|__|")
    print(f"{colours.OKCYAN + colours.BOLD}   \|_________|                                     \|___|/                                  ")
    print()
    print(f"{colours.OKGREEN}    Summary: Stream sports events straight from your Jellyfin server. Sportyfin allows users to scrape for ")
    print(f"{colours.OKGREEN}             live streamed events and watch straight from Jellyfin. Sportyfin also generates meta-data that ")
    print(f"{colours.OKGREEN}             is used in Jellyfin to provide a great viewing experience.")
    print()
    print(f"{colours.OKGREEN}    Author: Simon")
    print(f"{colours.OKGREEN}    Version: 1.0.8")
    print(f"{colours.OKGREEN}    Github: https://github.com/simon3948/sportyfin")
    print()
    print()



# Main class
class StreamCollector:
    def __init__(self):
        self.streaming_sites = {
            FOOTBALL: scraping.find_website_links(FOOTBALL) if FOOTBALL in leagues else [],
            F1: scraping.find_website_links(F1) if F1 in leagues else [],
            NFL: scraping.find_website_links(NFL) if NFL in leagues else [],
            NBA: scraping.find_website_links(NBA) if NBA in leagues else [],
            NHL: scraping.find_website_links(NHL) if NHL in leagues else [],
            UFC: scraping.find_website_links(UFC) if UFC in leagues else [],
            BOXING: scraping.find_website_links(BOXING) if BOXING in leagues else [],
            RUGBY: scraping.find_website_links(RUGBY) if RUGBY in leagues else [],
        }
        self.leagues: list = leagues

    def collect(self) -> None:

        for lg in self.leagues:
            p(f"COLLECTING {lg.upper()} .M3U8 LINKS", colours.HEADER, otype.REGULAR)
            res = 0
            for event in self.streaming_sites[lg]:
                # Use direct keys from event dictionary
                p(f"Looking for {event.get('name', event.get('url'))} streams:", colours.WARNING, otype.REGULAR)
                print(f"stream_links: ", event['stream_links'])
                event['m3u8_urls'] = scraping.find_urls(scraping.bypass_bitly((event['stream_links'])))
                print(f"m3u8_urls: ", event['m3u8_urls'])
                res += len(event['m3u8_urls'])
                p(f"EVENT: {event.get('name', event.get('url'))} FOUND M3U8_URLS: {', '.join(event['m3u8_urls'])}", colours.HEADER, otype.REGULAR)
            if res == 0:
                p(f"COULD NOT FIND {lg.upper()} M3U8 LINKS", colours.FAIL, otype.REGULAR)

    def generate_xmltv(self, lg: str):
        root = ET.Element("tv")
        for event in self.streaming_sites[lg]:
            for url in event['m3u8_urls']:
                doc = ET.SubElement(root, "channel", id=str(url))
                ET.SubElement(doc, "display-name").text = event.get('name', event.get('url', 'Unknown'))
                ET.SubElement(doc, "icon").text = f"{OUTPUT}/{lg}/{event.get('img_location', '').split('/')[-1]}"

                doc_p = ET.SubElement(root, "programme", start=event.get('start', ''), stop=event.get('stop', ''), channel=str(url))
                ET.SubElement(doc_p, "title", lang="en").text = event.get('name', event.get('url', 'Unknown'))
                ET.SubElement(doc_p, "category", lang="en").text = "sports"
                audio = ET.Element("audio")
                doc_p.append(audio)
                ET.SubElement(audio, "stereo").text = "stereo"
                ET.SubElement(doc_p, "icon", src=f"{OUTPUT}/{lg}/{event.get('img_location', '').split('/')[-1]}")
        tree = ET.ElementTree(root)
        outp = os.path.join(OUTPUT, f"docs")
        if not os.path.isdir(f"{OUTPUT}"):
            os.makedirs(f"{OUTPUT}")
            os.makedirs(f"{outp}")
        elif not os.path.isdir(f"{outp}"):
            os.makedirs(f"{outp}")
        output_path = os.path.join(outp, f"{lg}.xml")
        tree.write(output_path)

    def generate_m3u(self, lg: str):
        with open(os.path.join(*[OUTPUT, "docs", f"{lg}.m3u"]), 'w') as file:
            file.write("#EXTM3U\n")
            for event in self.streaming_sites[lg]:
                for url in event['m3u8_urls']:
                    file.write(f"""#EXTINF:-1 tvg-id="{url}" tvg-country="USA" tvg-language="English" tvg-logo="{os.path.join(*[OUTPUT, lg, event.get('img_location', '').split('/')[-1]])}" group-title="{lg}",{event.get('name', event.get('url', 'Unknown'))}\n""")
                    file.write(f"""{url}\n""")

    def generate_docs(self):
        for lg in self.leagues:
            p(f"Generating XML channel data for {lg.upper()}", colours.HEADER, otype.REGULAR)
            self.generate_xmltv(lg)
            p(f"Generating m3u playlist data for {lg.upper()}", colours.HEADER, otype.REGULAR)
            self.generate_m3u(lg)

#todo make link configurable
def run(argv: list):
    global OUTPUT
    minutes = 30
    try:
        os.environ['stream_link'] = "https://sportsurge.bz"
        if "-v" in argv:
            os.environ["verbosity"] = "0"
        else:
            os.environ["verbosity"] = "1"
        if "-vv" in argv:
            os.environ["no_verbosity"] = "0"
        else:
            os.environ["no_verbosity"] = "1"
        if "-s" in argv:
            os.environ["selenium"] = "0"
        else:
            os.environ["selenium"] = "1"
        if "-football" in argv:
            leagues.append(FOOTBALL)
        if "-f1" in argv:
            leagues.append(F1)
        if "-nfl" in argv:
            leagues.append(NFL)
        if "-nba" in argv:
            leagues.append(NBA)
        if "-nhl" in argv:
            leagues.append(NHL)
        if "-ufc" in argv:
            leagues.append(UFC)
        if "-boxing" in argv:
            leagues.append(BOXING)
        if "-rugby" in argv:
            leagues.append(RUGBY)
        if "-a" in argv and len(leagues) == 0:
            leagues.append(FOOTBALL)
            leagues.append(F1)
            leagues.append(NFL)
            leagues.append(NBA)
            leagues.append(NHL)
            leagues.append(UFC)
            leagues.append(BOXING)
            leagues.append(RUGBY)
        elif "-a" in argv and len(leagues) != 0:
            p("Cannot pass -a with -football/-f1/-nfl/-nba/-nhl/-ufc/-boxing/-rugby", colours.FAIL, otype.ERROR)
            sys.exit()
        if "-t" in argv:
            try:
                if argv.index("-t") + 1 >= len(argv):
                    raise Exception("Missing time input (in minutes)")
                minutes = argv[argv.index("-t") + 1]
                if minutes.startswith("-"):
                    raise Exception("Missing time input (in minutes)")
            except Exception as e:
                p(e, colours.FAIL, otype.ERROR)
        if "-o" in argv:
            try:
                if argv.index("-o") + 1 >= len(argv):
                    raise Exception("Missing output location")
                dp = str(argv[argv.index("-o") + 1])
                OUTPUT = os.path.join(*[dp, "output"])
                if dp.startswith('~') and os.name == 'nt':
                    OUTPUT = os.path.join(os.path.expandvars("%userprofile%"), dp[2:])
                elif not dp.startswith('/') and not dp.startswith('~'):
                    if dp.startswith('.'):
                        OUTPUT = os.path.join(*[os.getcwd(), dp[2:], "output"])
                    else:
                        OUTPUT = os.path.join(*[os.getcwd(), dp, "output"])
                if OUTPUT.startswith("-"):
                    raise Exception("Missing output location")
                os.environ['output'] = OUTPUT
            except Exception as e:
                p(e, colours.FAIL, otype.ERROR)
                sys.exit()
        if len(leagues) == 0:
            sys.exit()
        header()
        if "-d" in argv:
            collector = StreamCollector()
            collector.collect()
            collector.generate_docs()
        else:
            while True:
                collector = StreamCollector()
                collector.collect()
                collector.generate_docs()
                p(f"Waiting {minutes} minutes until next update", colours.WARNING, otype.REGULAR)
                del collector
                time.sleep(int(int(minutes) * 60))
    except Exception as e:
        p(e, colours.FAIL, otype.ERROR, e)
