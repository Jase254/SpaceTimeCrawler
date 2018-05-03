import logging
from datamodel.search.JekahnHunsingk_datamodel import JekahnHunsingkLink, OneJekahnHunsingkUnProcessedLink
from spacetime.client.IApplication import IApplication
from spacetime.client.declarations import Producer, GetterSetter, Getter
import BeautifulSoup as BS
from urlparse import urljoin
import sys
import datetime
import requests
import urllib3

from lxml import html,etree
import re, os
from time import time
from uuid import uuid4

from urlparse import urlparse, parse_qs
from uuid import uuid4

logger = logging.getLogger(__name__)
LOG_HEADER = "[CRAWLER]"



@Producer(JekahnHunsingkLink)
@GetterSetter(OneJekahnHunsingkUnProcessedLink)
class CrawlerFrame(IApplication):
    app_id = "JekahnHunsingk"

    def __init__(self, frame):
        self.app_id = "JekahnHunsingk"
        self.frame = frame
        self.starttime = time()
        self.link_dict = {}
        self.max_links = (0, 'url')
        self.elapse_time = 0
        self.total_links = 0
        self.total_pages_scraped = 0
        self.total_time = 0
        self.session_links = 0
        self.session_pages = 0

        self.read_history()

    def read_history(self):
        try:
            with open('History.txt', 'r') as history:
                self.total_links = int(history.readline())

                max_link = int(history.readline())
                url = history.readline()
                self.max_links = (max_link, url)

                self.total_pages_scraped = int(history.readline())
                self.total_time = float(history.readline())

                history.close()
        except IOError as e:
            pass

    def initialize(self):
        logs = open('Analytics.txt', 'a')
        logs.write('---------------------------------------\n')
        logs.write('Session Date {}\n'.format(datetime.datetime.now()))
        logs.write('---------------------------------------\n')
        logs.close()

        links = self.frame.get_new(OneJekahnHunsingkUnProcessedLink)
        if len(links) > 0:
            print ("Resuming from the previous state.")
            self.download_links(links)
        else:
            l = JekahnHunsingkLink("http://www.ics.uci.edu/")
            print (l.full_url)
            self.frame.add(l)

    def update(self):
        unprocessed_links = self.frame.get_new(OneJekahnHunsingkUnProcessedLink)
        if unprocessed_links:
            self.download_links(unprocessed_links)

    def download_links(self, unprocessed_links):
        try:
            for link in unprocessed_links:
                print ("\nGOT A LINK TO DOWNLOAD {}".format(link.full_url))
                downloaded = link.download()
                links = extract_next_links(downloaded)

                valid_link_count = 0
                for l in links:
                    if is_valid(l):
                        valid_link_count += 1
                        self.frame.add(JekahnHunsingkLink(l))

                print ("{} has {} valid links".format(link.full_url, valid_link_count))
                self.total_links += valid_link_count

                if valid_link_count > self.max_links[0]:
                    self.max_links = (valid_link_count, downloaded.url)  # should we check for final_url?

                self.link_dict[downloaded] = valid_link_count    # should this be keying downloaded.url?
                self.session_links += valid_link_count
                self.session_pages += 1                          # should we just add 1 each time?
                if self.session_pages%10 == 0:
                    self.write_analytics()
                if self.session_pages == 3000:
                    self.elapse_time = time() - self.starttime
                    self.shutdown()
        except KeyboardInterrupt:
            try:
                self.shutdown()
            except SystemExit:
                os._exit(0)



    def shutdown(self):
        self.total_pages_scraped += self.session_pages
        self.elapse_time = time() - self.starttime
        self.total_time += self.elapse_time

        self.write_analytics()
        print ("SHUTTING DOWN . . .")
        print ("Time time spent this session: {} seconds.".format(self.elapse_time))
        sys.exit(0)

    def write_analytics(self):
        history = open('History.txt', 'w')
        history.writelines("{}\n".format(self.total_links))
        history.writelines("{}\n".format(self.max_links[0]))
        history.writelines("{}\n".format(self.max_links[1].strip()))
        history.writelines("{}\n".format(self.total_pages_scraped))
        history.writelines("{}".format(self.total_time))
        history.close()

        logs = open('Analytics.txt', 'a')
        logs.write('---------------------------------------\n')
        logs.write('\nCurrent Session:\n')
        logs.write('\tSession Elapse Time {}\n'.format(self.elapse_time))
        logs.write('\tMax Link Page: {}\n'.format(self.max_links[1].strip()))
        logs.write('\tMax Links: {}\n'.format(self.max_links[0]))
        logs.write("\tPages Scraped: {}\n".format(self.session_pages))
        logs.write("\tLinks Scraped: {}\n\n".format(self.session_links))

        logs.write('\nScrape History:\n')
        logs.write('\tTotal Elapse Time {}\n'.format(self.total_time))
        logs.write('\tMax Link Page: {}\n'.format(self.max_links[1].strip()))
        logs.write('\tMax Links: {}\n'.format(self.max_links[0]))
        logs.write("\tTotal Pages Scraped: {}\n".format(self.total_pages_scraped))
        logs.write("\tTotal Links Scraped: {}\n\n".format(self.total_links))
        logs.write('---------------------------------------\n')

        logs.close()


def extract_next_links(rawDataObj):
    output_links = []

    if rawDataObj.is_redirected:
        rawDataObj.url = rawDataObj.final_url

    if rawDataObj.http_code == 200:
        soup = BS.BeautifulSoup(rawDataObj.content)

        for links in soup.findAll('a'):
            output_links.append(urljoin(rawDataObj.url, links.get('href')).encode('ascii'))
    else:
        print("ERROR! Page returned a {} code".format(rawDataObj.http_code))
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
    return output_links


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
    if parsed.fragment != '':   # if link has fragment id
        return False
    if "calendar" in url:       # if link is calender
        return False
    if len(url) > 100:       # if link is really long
        return False
    if "?" in url or "%" in url or "&" in url or "+" in url or "=" in url:
        return False

    try:
        r = requests.get(url)
        if r.status_code >= 400:   # double checking returns error code
            return False
        if r.encoding.lower() != 'utf-8' and r.encoding.lower() != 'iso-8859-1':
            return False
    except Exception as e:
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
