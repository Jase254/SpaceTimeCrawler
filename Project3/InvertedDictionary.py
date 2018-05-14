import sys
import operator
import string
import re
import io
from BeautifulSoup import BeautifulSoup, Comment
from collections import OrderedDict
from pymongo import MongoClient

import json

class InvertedDictionary:

    def __init__(self):
        self.invDict = {}
        self.docCount = 0
        self.tokCount = 0
        self.urls = {}
        self.sorted_dict = OrderedDict()
        client = MongoClient('localhost:27017')
        self.db = client.Corpus
        # self.intialize_mongo()

    def tokenize_and_count(self, contents):
        word = ''  # set up word for building
        tokens = {}

        for i in contents:
            if i.isalnum():  # if letter is alpha-numeric, concatenate to end of word
                word += i
            elif word != '':
                if word.lower() in tokens:  # if word is in dict, add one to value for occurences
                    tokens[word.lower()] += 1
                else:  # else it put in dict and set value i.e. occurence to 1
                    tokens[str(word.lower())] = 1
                word = ''  # reset word to build again
        return tokens

    def sort_tokens(self, dict):
        return sorted(dict.items(), key=lambda x: (-x[1], x[0]))

    def print_tokens(self):
        for i in self.invDict:
            print ('%s - %i' % (i[0], i[1]))

    def read_file(self, id):
        name = "WEBPAGES_RAW/" + id
        clear = ''

        try:
            f = io.open(name, "r", encoding='utf-8')
        except Exception as e:
            print ("Error! {}".format(e))
            return
        contents = f.read()
        soup = BeautifulSoup(contents)

        for tags in soup.findAll(['p', 'h1', 'h2', 'h3', 'title']):

            for a in tags(['a', 'img', 'script', 'style']):
                a.decompose()

            for element in tags(text=lambda text: isinstance(text, Comment)):
                element.extract()

            clear += re.sub('[^0-9a-zA-Z]+', ' ', tags.getText(' ')) + '\n'
            # clear += tags.getText(' ') + '\n'

        f.close()
        return clear

    def create(self):

        i = 0
        page_contents = ''

        self.read_json()

        for docs in self.urls:
            try:
                i += 1
                page_contents = self.read_file(docs)
                tokens = self.tokenize_and_count(page_contents)

                for keys in tokens:
                    if keys in self.invDict:
                        self.invDict[keys].append(tuple([str(docs), tokens[keys]]))
                        self.db.Corpus.update_one(
                            {'token': keys},
                            {
                                '$set': {
                                    'posting': self.invDict[keys]
                                }
                            }
                        )
                    else:
                        self.invDict[keys] = [tuple([str(docs), tokens[keys]])]
                        self.db.Corpus.insert_one(
                            {'token': keys,
                             'posting': self.invDict[keys]
                             }
                        )
                if i == 1000:
                    break
            except Exception as e:
                print('you fucked up! {}'.format(e))
                continue

        for key in sorted(self.invDict):
            print "%s: %s" % (key, self.invDict[key])


    # read_file gets the contents of the file
    def read_json(self):

        with open('WEBPAGES_RAW/bookkeeping.json') as f:
            self.urls = json.load(f)

        self.docCount = len(self.urls)



test = InvertedDictionary()
test.create()