import logging
from datamodel.search.JekahnHunsingk_datamodel import JekahnHunsingkLink, OneJekahnHunsingkUnProcessedLink
from spacetime.client.IApplication import IApplication
from spacetime.client.declarations import Producer, GetterSetter, Getter
import BeautifulSoup as BS
from urlparse import urljoin
import sys
import datetime
import requests

from lxml import html,etree
import re, os
from time import time
from uuid import uuid4

from urlparse import urlparse, parse_qs
from uuid import uuid4

logger = logging.getLogger(__name__)
LOG_HEADER = "[CRAWLER]"

pages_crawled = 0
links_crawled = 0
max_links = (0, 'url')

@Producer(JekahnHunsingkLink)
@GetterSetter(OneJekahnHunsingkUnProcessedLink)
class CrawlerFrame(IApplication):
    app_id = "JekahnHunsingk"

    def __init__(self, frame):
        self.app_id = "JekahnHunsingk"
        self.frame = frame
        self.starttime = time()

    def initialize(self):
        self.count = 0

        logs = open('Analytics', 'a')
        logs.write('\nSession Date {}\n'.format(datetime.datetime.now()))
        logs.close()

        links = self.frame.get_new(OneJekahnHunsingkUnProcessedLink)
        if len(links) > 0:
            print "Resuming from the previous state."
            self.download_links(links)
        else:
            l = JekahnHunsingkLink("http://www.ics.uci.edu/")
            print l.full_url
            self.frame.add(l)

    def update(self):
        unprocessed_links = self.frame.get_new(OneJekahnHunsingkUnProcessedLink)
        if unprocessed_links:
            self.download_links(unprocessed_links)

    def download_links(self, unprocessed_links):
        for link in unprocessed_links:
            print "Got a link to download:", link.full_url
            downloaded = link.download()
            links = extract_next_links(downloaded)
            for l in links:
                if is_valid(l):
                    self.frame.add(JekahnHunsingkLink(l))
            if pages_crawled == 5:
                self.shutdown()

    def shutdown(self):
        global pages_crawled
        global max_links
        global links_crawled

        elapse_time = time() - self.starttime

        print ("Time time spent this session: {} seconds.".format(elapse_time))

        logs = open('Analytics', 'a')
        logs.write('\n\nSession Elapse Time {}\n'.format(elapse_time))
        logs.write('Max Link Page: {}\n'.format(max_links[1]))
        logs.write('Max LinksLinks: {}\n'.format(max_links[0]))
        logs.close()
        sys.exit(0)

def extract_next_links(rawDataObj):
    outputLinks = []

    global pages_crawled
    global max_links
    global links_crawled

    current_links = 0

    print("Code: {}".format(rawDataObj.http_code))

    if rawDataObj.is_redirected:
        print("redirected!")
        rawDataObj.url = rawDataObj.final_url

    if rawDataObj.http_code == 200:
        pages_crawled += 1
        soup = BS.BeautifulSoup(rawDataObj.content)

        for links in soup.findAll('a'):
            outputLinks.append(urljoin(rawDataObj.url, links.get('href')).encode('ascii'))

        current_links = len(outputLinks)
        links_crawled += current_links

        if current_links > max_links[0]:
            max_links = (current_links, rawDataObj.url)

        logs = open('Analytics', 'a')
        logs.write('\tPage: {}\n'.format(rawDataObj.url))
        logs.write('\tLinks Scraped: {}\n'.format(current_links))
        logs.close()

        print(outputLinks)

    else:
        print("error! Page returned a {} code".format(rawDataObj.http_code))
        print(rawDataObj.error_message)

    '''
    rawDataObj is an object of type UrlResponse declared at L20-30
    datamodel/search/server_datamodel.py
    the return of this function should be a list of urls in their absolute form
    Validation of link via is_valid function is done later (see line 42).
    It is not required to remove duplicates that have already been downloaded. 
    The frontier takes care of that.
    
    Suggested library: lxml
    '''
    return outputLinks

def is_valid(url):
    '''
    Function returns True or False based on whether the url has to be
    downloaded or not.
    Robot rules and duplication rules are checked separately.
    This is a great place to filter out crawler traps.
    '''
    parsed = urlparse(url)
    if parsed.scheme not in set(["http", "https"]):
        return False

    if url.find('calendar'):
        return False

    if parsed.query != '':
        return False

    if requests.get(url).status_code >= 400:
        return False

    try:
        return ".ics.uci.edu" in parsed.hostname \
               and not re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4" \
                                + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
                                + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
                                + "|thmx|mso|arff|rtf|jar|csv" \
                                + "|rm|smil|wmv|swf|wma|zip|rar|gz|pdf)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        return False



