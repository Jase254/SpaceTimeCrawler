import datetime
import logging
import os
import re
import sys
from time import time
from urlparse import urljoin
from urlparse import urlparse

import BeautifulSoup as BS
import requests
from datamodel.search.JekahnHunsingk_datamodel import JekahnHunsingkLink, OneJekahnHunsingkUnProcessedLink
from spacetime.client.IApplication import IApplication
from spacetime.client.declarations import Producer, GetterSetter

logger = logging.getLogger(__name__)
LOG_HEADER = "[CRAWLER]"

# Global dictionary to hold valid link counts
domain_dict = {}

@Producer(JekahnHunsingkLink)
@GetterSetter(OneJekahnHunsingkUnProcessedLink)
class CrawlerFrame(IApplication):
    app_id = "JekahnHunsingk"

    def __init__(self, frame):
        # Create variables for metrics
        self.app_id = "JekahnHunsingk"
        self.frame = frame
        self.starttime = time()
        self.max_links = (0, 'url')
        self.elapse_time = 0
        self.total_links = 0
        self.total_pages_scraped = 0
        self.total_time = 0
        self.session_links = 0
        self.session_pages = 0

        self.read_history()

    # Read history to keep running totals
    def read_history(self):
        global domain_dict

        # Reading history and populate totals
        try:
            with open('History.txt', 'r') as history:
                self.total_links = int(history.readline())

                max_link = int(history.readline())
                url = history.readline()
                self.max_links = (max_link, url)

                self.total_pages_scraped = int(history.readline())
                self.total_time = float(history.readline())

                line = history.readline()

                while line:
                    key_value = line.split()
                    domain_dict[key_value[0]] = int(key_value[1])
                    line = history.readline()

                history.close()

        except IOError as e:
            pass

    def initialize(self):
        # Write date/time header when crawler starts
        logs = open('Analytics.txt', 'a')
        logs.write('---------------------------------------\n')
        logs.write('Session Date {}\n'.format(datetime.datetime.now()))
        logs.write('---------------------------------------\n\n')
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

                # Count valids per each url
                valid_link_count = 0
                for l in links:
                    if is_valid(l):
                        valid_link_count += 1
                        self.frame.add(JekahnHunsingkLink(l))

                # Sum total valid links
                self.total_links += valid_link_count

                # Check for max links and url
                if valid_link_count > self.max_links[0]:
                    self.max_links = (valid_link_count, downloaded.url)

                # Calculate metrics
                self.session_links += valid_link_count
                self.session_pages += 1

                # Write analytics every 10 pages scraped
                if self.session_pages % 10 == 0:
                    self.elapse_time = time() - self.starttime
                    self.total_time += self.elapse_time
                    self.write_analytics()

                # Stop crawler after scraping 3000 pages
                if self.session_pages == 3000 or self.total_pages_scraped == 3000:
                    self.elapse_time = time() - self.starttime
                    self.shutdown()

        # Shutdown on keyboard interrupt
        except KeyboardInterrupt:
            try:
                self.shutdown()
            except SystemExit:
                os._exit(0)
        except IOError:
            try:
                self.shutdown()
            except SystemExit:
                os._exit(0)

    # Shutdown crawler and write analytics
    def shutdown(self):

        self.write_analytics()

        print ("SHUTTING DOWN . . .")
        print ("Time time spent this session: {} seconds.".format(self.elapse_time))
        sys.exit(0)

    # Write analytics file and history logs
    def write_analytics(self):
        global domain_dict

        # Add metrics of current session to total
        self.total_pages_scraped += self.session_pages
        self.elapse_time = time() - self.starttime
        self.total_time += self.elapse_time

        # Rewrite history file with updated metrics
        history = open('History.txt', 'w')
        history.writelines("{}\n".format(self.total_links))
        history.writelines("{}\n".format(self.max_links[0]))
        history.writelines("{}\n".format(self.max_links[1].strip()))
        history.writelines("{}\n".format(self.total_pages_scraped))
        history.writelines("{}\n".format(self.total_time))
        for keys in domain_dict:
            history.write("{}\t{}\n".format(keys, domain_dict[keys]))
        history.close()

        # Append new metrics to analytics file
        # Current sessions and total crawl
        logs = open('Analytics.txt', 'a')
        logs.write('Current Session:\n')
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

        # Output domain link counts
        logs.write('\nSub-Domain Link Counts:\n')
        for keys in domain_dict:
            logs.write('\t{}: {}\n'.format(keys, domain_dict[keys]))
        logs.write('\n---------------------------------------\n\n')
        logs.close()


def extract_next_links(rawDataObj):
    output_links = []

    # check for redirected link and reset url
    if rawDataObj.is_redirected:
        rawDataObj.url = rawDataObj.final_url

    # Check if page is "OK" before trying to scrape links
    # Create Beautiful Soup object for HTML parsing
    if rawDataObj.http_code == 200:
        soup = BS.BeautifulSoup(rawDataObj.content)

        # Find all ahref tags
        # Make sure links are ASCII encoded
        # Add valid link to list
        for links in soup.findAll('a'):
            output_links.append(urljoin(rawDataObj.url, links.get('href')).encode('ascii'))
    else:
        # Return empty list if url is not "OK"
        print("ERROR! Page returned a {} code".format(rawDataObj.http_code))
        print(rawDataObj.error_message)
        return []

    return output_links


def is_valid(url):
    # Parsed link using urllib3 library
    parsed = urlparse(url)

    # Reference to global for url domain list
    global domain_dict

    # Check for HTTP or HTTPS scheme
    if parsed.scheme not in {"http", "https"}:
        return False

    # Dynamic link checks and traps
    # Remove links with fragments
    if parsed.fragment != '':
        return False

    # Remove links with queries
    if parsed.query != '':
        return False

    # Remove links that have dynamic calendars
    if "calendar" in url:
        return False

    # Remove links that are over length
    if len(url) > 100:
        return False

    # Double check scraped link for valid codes
    # Check links for correct encoding
    try:
        r = requests.get(url)
        if r.status_code >= 400:
            return False
        if r.encoding.lower() != 'utf-8' and r.encoding.lower() != 'iso-8859-1':
            return False
    except Exception as e:
        return False

    # Check file extensions and host name
    try:
        valid = ".ics.uci.edu" in parsed.hostname \
                and not re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4" \
                                 + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
                                 + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
                                 + "|thmx|mso|arff|rtf|jar|csv" \
                                 + "|rm|smil|wmv|swf|wma|zip|rar|gz|pdf)$", parsed.path.lower())

        # Creating dictionary of subdomain links
        # Increment count or create key
        key = parsed.netloc
        if valid:
            if key in domain_dict:
                domain_dict[key] += 1
            else:
                domain_dict[key] = 1

        return valid
    except TypeError as e:
        print ("TypeError for ", parsed)
        return False
