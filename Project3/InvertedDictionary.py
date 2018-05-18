import sys
import operator
import string
import re
import io
from BeautifulSoup import BeautifulSoup, Comment
from collections import OrderedDict
from pymongo import MongoClient
from time import time
import math

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
        self.db2 = client.Urls
        # self.intialize_mongo()

    def tokenize_and_count(self, contents):
        word = ''  # set up word for building
        tokens = {}
        index = 0

        for c, i in enumerate(contents):
            if word == '':
                index = c
            if i.isalnum():  # if letter is alpha-numeric, concatenate to end of word
                word += i
            elif word != '':
                word = word.lower()
                if word in tokens:  # if word is in dict, add one to value for occurences
                    occurences = tokens[word][0]
                    occurences += 1

                    indices = tokens[word][1]
                    indices.append(index)

                    posting = tuple([occurences, indices])

                    tokens[word] = posting

                else:  # else it put in dict and set value i.e. occurence to 1
                    tokens[str(word)] = tuple([1, [index]])

                word = ''  # reset word to build again
        return tokens

    def sort_tokens(self, dict):
        return sorted(dict.items(), key=lambda x: (-x[1], x[0]))

    def print_tokens(self):
        for i in self.invDict:
            print ('%s - %i' % (i[0], i[1]))

    def calc_tf(self, term_frequency):
        tf = 1 + math.log(term_frequency, 10)
        tf = float("{0:.2f}".format(tf))
        return tf


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

    def calc_tfidf(self):

        for keys in self.invDict:
            df = len(self.invDict[keys])
            idf = math.log((self.docCount/df), 10)

            for i, docs in enumerate(self.invDict[keys]):
                tf_idf = idf * docs[1][0]
                tf_idf = float("{0:.3f}".format(tf_idf))
                posting = tuple([docs[0], tuple([tf_idf, docs[1][1]])])
                self.invDict[keys][i] = posting

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
                    tf = self.calc_tf(tokens[keys][0])
                    posting = tuple([tf, tokens[keys][1]])

                    tokens[keys] = posting

                    if keys in self.invDict:
                        self.invDict[keys].append(tuple([str(docs), tokens[keys]]))
                    else:
                        self.invDict[keys] = [tuple([str(docs), tokens[keys]])]
                if i % 1000 == 0:
                    print("# docs {}".format(i))

            except Exception as e:
                print('you fucked up! {}'.format(e))
                continue

        self.tokCount = len(self.invDict)
        self.calc_tfidf()

        try:
            for items, posting in self.invDict.iteritems():

                entry = {'token': items,
                         'posting:': []}

                for docs in posting:
                    posting_list = {'docId': docs[0],
                                    'metrics':
                                        {'ft-idf': docs[1][0],
                                         'indices': docs[1][1]}}

                    entry['posting:'].append(posting_list)
                print entry
                self.db.Corpus.insert(entry)
                if i % 1000 == 0:
                    print('{} Items added to Corpus'.format(i))
        except Exception as e:
            print('mongo fucked up!')
            print('{}'.format(e))

    # read_file gets the contents of the file
    def read_json(self):

        with open('WEBPAGES_RAW/bookkeeping.json') as f:
            self.urls = json.load(f)

        self.docCount = len(self.urls)
        self.db2.Urls.insert(self.urls)

    # def analytics(self):

    def search(self, query):
        result = (self.db.Corpus.find( {'token': query}, {"posting.docId": 1}))
        print(result.next())



start_time = time()
test = InvertedDictionary()

test.search('woods')
end_time = time() - start_time

print("elapse time: {}s".format(end_time))
