import string
import re
import io
from BeautifulSoup import BeautifulSoup, Comment
from collections import OrderedDict
from pymongo import MongoClient
import nltk
from nltk.corpus import stopwords
from time import time
import math
import operator
import numpy as np

import json

class InvertedDictionary:

    def __init__(self):
        self.invDict = {}
        self.tokCount = 0
        self.urls = {}
        self.sorted_dict = OrderedDict()
        client = MongoClient('localhost:27017')
        self.db = client.Corpus
        self.db2 = client.Urls
        self.docCount = 0
        self.stopWords = set(stopwords.words('english'))

    def tokenize(self, contents):
        word = ''  # set up word for building
        tokens = {}
        contents += " "

        for c, i in enumerate(contents):
            if i.isalnum():  # if letter is alpha-numeric, concatenate to end of word
                word += i
            elif word != '':
                word = word.lower()
                if (word in tokens) and (word not in self.stopWords):  # if word is in dict, add one to value for occurences
                    occurences = tokens[word]
                    occurences += 1
                    tokens[word] = occurences

                elif word not in self.stopWords:  # else it put in dict and set value i.e. occurence to 1
                    tokens[str(word)] = 1

                word = ''  # reset word to build again

        return tokens

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
                         'posting': []}

                for docs in posting:
                    posting_list = {'docId': docs[0],
                                    'metrics':
                                        {'tf-idf': docs[1][0],
                                         'indices': docs[1][1]}}

                    entry['posting'].append(posting_list)
                print entry
                self.db.Corpus.insert(entry)
                if i % 1000 == 0:
                    print('{} Items added to Corpus'.format(i))
        except Exception as e:
            print('mongo fucked up!')
            print('{}'.format(e))


    def read_json(self):

        with open('WEBPAGES_RAW/bookkeeping.json') as f:
            self.urls = json.load(f)

        for key in self.urls:
            entry = {'docId': key,
                     'url': self.urls[key]}
            self.db2.Urls.insert(entry)

        self.docCount = len(self.urls)
        self.db2.Urls.insert(self.urls)

    def get_docCount (self):
        self.docCount = self.db2.Urls.count()
        return self.docCount

    def analytics(self):
        self.tokCount = self.db.Corpus.count()
        print("Unique Token Count: {}".format(self.tokCount))

        self.docCount = self.db2.Urls.count()
        print("Document Count: {}".format(self.docCount))

    # def search(self, query):
    #     query = string.lower(query)
    #     urls = []
    #     i = 0
    #     result = self.db.Corpus.find({"token": query}, {"posting.docId": 1, "_id": 0}).limit(10)
    #     posting = result.next()
    #
    #     for docs in posting[unicode('posting')]:
    #         doc_ids = (str(docs[unicode('docId')]))
    #         entry = self.db2.Urls.find_one({'docId': doc_ids}, {'docId': 0, '_id': 0})
    #         urls.append(str(entry[unicode('url')]))
    #         i += 1
    #         if i == 10:
    #             break
    #
    #     for links in urls:
    #         print(links)

    def merge_postings(self, query_dict):
        merged = set()
        print (len(merged))
        lengths = []
        postings = {}
        for token in query_dict:
            result = self.db.Corpus.find({"token": token}, {"posting.docId": 1, "_id": 0})
            posting = set()
            for docId in result.next()['posting']:
                posting.add(str(docId['docId']))
            postings[token] = posting
            lengths.append(len(posting))
            if len(merged) == 0:
                merged = posting
            else:
                print ("in intersect, length of merge = {}".format(len(merged)))
                merged = merged.intersection(posting)
                print ("in intersect after merge, length of merge = {}".format(len(merged)))

    def calc_query_tfidf(self, query_dict):
        query_tfidf = {}
        for term in query_dict:
            tf = query_dict[term]
            result = self.db.Corpus.find({"token": term}, {"posting.docId": 1, "_id": 0})
            query_df = len(result.next()['posting'])
            query_idf = math.log((self.get_docCount() / query_df), 10)
            tf_idf = query_idf * (1 + math.log(tf, 10))
            tf_idf = float("{0:.3f}".format(tf_idf))
            query_tfidf[term] = tf_idf
        return query_tfidf

    def union_postings(self, query_dict):
        union = {}
        for token in query_dict:
            result = self.db.Corpus.find({"token": token}, {"posting.docId": 1, "posting.metrics.tf-idf": 1, "_id": 0})
            posting = result.next()['posting']
            for doc in posting:
                doc_tfidf = doc['metrics']['tf-idf']
                docId = doc['docId']
                if (docId in union):
                    union[docId] += doc_tfidf
                else:
                    union[docId] = doc_tfidf
        return union

    def calc_scoresAndLengths(self, query_tfidf):
        scores = {}
        doc_lengths = {}
        for token in query_tfidf:
            result = self.db.Corpus.find({"token": token}, {"posting.docId": 1, "posting.metrics.tf-idf": 1, "_id": 0})
            posting = result.next()['posting']
            for doc in posting:
                doc_tfidf = doc['metrics']['tf-idf']
                docId = doc['docId']
                score = query_tfidf[token] * doc_tfidf
                if docId in scores:
                    scores[docId] += float("{0:.3f}".format(score))
                else:
                    scores[docId] = float("{0:.3f}".format(score))
                if docId in doc_lengths:
                    doc_lengths[docId] += doc_tfidf**2
                else:
                    doc_lengths[docId] = doc_tfidf ** 2

        return scores, doc_lengths

    def finish_lengths(self, doc_lengths):
        for doc in doc_lengths:
            doc_lengths[doc] = math.sqrt(doc_lengths[doc])
        return doc_lengths

    def finish_scores(self, scores, doc_lengths):
        for doc in scores:
            scores[doc] = scores[doc]/doc_lengths[doc]
        return scores

    def strip_scores(self, scores):
        final_docs = []
        for i in range(10):
            final_docs.append(str(scores[i][0]))
        return final_docs

    def search_cosine(self, query):
        query_dict = self.tokenize(query)
        query_tfidf = self.calc_query_tfidf(query_dict)
        scores, doc_lengths = self.calc_scoresAndLengths(query_tfidf)
        doc_lengths = self.finish_lengths(doc_lengths)
        scores = self.finish_scores(scores, doc_lengths)

        sorted_scores = sorted(scores.items(), key=operator.itemgetter(1), reverse=True)
        final_docs = self.strip_scores(sorted_scores)
        return final_docs

    def search_tfidf(self, query):
        query_dict = self.tokenize(query)
        union_scores = self.union_postings(query_dict)

        sorted_scores = sorted(union_scores.items(), key=operator.itemgetter(1), reverse=True)
        final_docs = self.strip_scores(sorted_scores)
        return final_docs, query_dict

    def get_urls(self, docIds):
        top_urls = {}
        for doc in docIds:
            result = self.db2.Urls.find({"docId": doc}, {"url": 1, "_id": 0})
            url = result.next()
            top_urls[doc] = url
        return top_urls

    def get_titleandContents(self, docId):
        try:
            file_name = "../../Project3/WEBPAGES_RAW/" + docId
            f = io.open(file_name, "r", encoding='utf-8')
        except Exception as e:
            print ("Error! {}".format(e))
            return
        contents = f.read()
        soup = BeautifulSoup(contents)
        clear = ''

        for tags in soup.findAll(['p', 'h1', 'h2', 'h3', 'title']):

            for a in tags(['a', 'img', 'script', 'style']):
                a.decompose()

            for element in tags(text=lambda text: isinstance(text, Comment)):
                element.extract()

            clear += re.sub('[^0-9a-zA-Z]+', ' ', tags.getText(' ')) + '\n'

        title = soup.title.string
        f.close()
        return title, clear

    def get_indices(self, top_docs, query_dict):
        doc_indices = {}
        for token in query_dict:
            result = self.db.Corpus.find({"token": token}, {"posting.docId": 1, "posting.metrics.indices": 1, "_id": 0})
            posting = result.next()['posting']
            for doc in posting:
                indices = doc['metrics']['indices']
                docId = doc['docId']
                if docId in top_docs and docId not in doc_indices:
                    doc_indices[docId] = indices
                elif docId in top_docs and docId in doc_indices:
                    old_list = doc_indices[docId]
                    doc_indices[docId] = old_list + indices
        return doc_indices

    def get_snippet(self, contents, indices):
        # window of just first occurence in doc, window of 20 before and 30 after
        indices.sort()
        first_index = indices[0]
        if first_index - 20 < 0:
            beg = 0
        else:
            beg = contents.find(' ', first_index-20, first_index-10) + 1
        if first_index + 30 >= len(contents):
            end = len(contents)
        else:
            end = contents.find(' ', first_index+20, first_index+30)
        snippet = contents[beg:end]
        return snippet


    def search(self, query):
        top_docs, query_dict = self.search_tfidf(query)
        doc_indices = self.get_indices(top_docs, query_dict)
        top_urls = self.get_urls(top_docs)
        final_dict = {}
        for doc in top_docs:
            title, contents = self.get_titleandContents(doc)
            snippet = self.get_snippet(contents, doc_indices[doc])
            url = top_urls[doc]['url']
            final_dict[str(url)] = {'title': str(title), 'snippet': str(snippet)}

        # for printing if you want to test
        # for entry in final_dict:
        #     print ("{} - {}".format(entry, final_dict[entry]))
        return final_dict

'''
NOTE TO JASON:
Hey, finished this last night, just was in the zone lol.
Here is the search all finished. From the frontend just call invDictObj.search("query").
That will return a url mapped to a dictionary of title and snippet.
If you want to try, uncomment the code below this and the small print section I commented in search at the end.
It works pretty well, it takes about 2.5 seconds to run.
Only issue I found was sometimes a snippet was long for some reason (even though i specified length).
'''

# start_time = time()
# test = InvertedDictionary()
# test.search("computer science")
# end_time = time() - start_time
# print("elapse time: {}s".format(end_time))