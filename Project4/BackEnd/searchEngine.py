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
        self.start_time = 0
        self.end_time = 0

    # tokenize query; maps token to number of occurrences in contents
    def tokenize(self, contents):
        word = ''
        tokens = {}
        contents += " "
        for c, i in enumerate(contents):
            if i.isalnum():
                # concatenate alpha-numeric to end of word
                word += i
            elif word != '':
                word = word.lower()
                if (word in tokens) and (word not in self.stopWords):
                    # get occurrences and add one
                    occurrences = tokens[word]
                    occurrences += 1
                    # map word to update occurrences
                    tokens[word] = occurrences
                elif word not in self.stopWords:
                    # new token, map to 1 occurrence
                    tokens[str(word)] = 1

                word = ''  # reset word to build again
        return tokens

    # tokenize documents for index; maps token to tuple of occurrences in doc and where each occurrence is
    def tokenize_and_count(self, contents):
        word = ''
        tokens = {}
        index = 0
        for c, i in enumerate(contents):
            if word == '':
                # for new word, keep track of starting index
                index = c
            if i.isalnum():
                # concatenate alpha-numeric to end of word
                word += i
            elif word != '':
                word = word.lower()
                if word in tokens:
                    # get occurrences and add one
                    occurrences = tokens[word][0]
                    occurrences += 1
                    # get list of indices and append new index word
                    indices = tokens[word][1]
                    indices.append(index)
                    # create posting tuple and map word to new tuple
                    posting = tuple([occurrences, indices])
                    tokens[word] = posting

                else:
                    # new token, map to tuple of 1 occurrence and index where it occurred
                    tokens[str(word)] = tuple([1, [index]])

                # reset word to build again
                word = ''
        return tokens

    # # not called i think
    # def sort_tokens(self, token_dict):
    #     return sorted(token_dict.items(), key=lambda x: (-x[1], x[0]))

    # def print_tokens(self):
    #     for i in self.invDict:
    #         print ('%s - %i' % (i[0], i[1]))

    # calculate log term frequency given number of occurrences of a token
    def calc_tf(self, term_frequency):
        tf = 1 + math.log(term_frequency, 10)
        tf = float("{0:.2f}".format(tf))
        return tf

    # read html file given file path returning relevant text
    def read_file(self, id):
        name = "WEBPAGES_RAW/" + id
        final_contents = ''

        # open file and check for errors
        try:
            f = io.open(name, "r", encoding='utf-8')
        except Exception as e:
            print ("Error! {}".format(e))
            return

        # make the soup
        contents = f.read()
        soup = BeautifulSoup(contents)
        # go through soup and find relevant tags
        for tags in soup.findAll(['p', 'h1', 'h2', 'h3', 'title']):
            # remove irrelevant tags if found in above tags
            for a in tags(['a', 'img', 'script', 'style']):
                a.decompose()
            # remove comments
            for element in tags(text=lambda text: isinstance(text, Comment)):
                element.extract()
            # concatenate alpha-numeric characters from relevant tags to final contents
                final_contents += re.sub('[^0-9a-zA-Z]+', ' ', tags.getText(' ')) + '\n'

        f.close()
        return final_contents

    # calculate tf-idf for inverted index
    def calc_tfidf(self):
        for keys in self.invDict:
            # retrieve doc frequency from dict and calculate inverted doc frequency
            df = len(self.invDict[keys])
            idf = math.log((self.docCount/df), 10)

            # loop through posting list for token "key"
            for i, docs in enumerate(self.invDict[keys]):
                # calculate tf-idf from idf and stored term frequency
                tf_idf = idf * docs[1][0]
                tf_idf = float("{0:.3f}".format(tf_idf))
                # remake posting to include tf-idf instead of term frequency and add to dict
                posting = tuple([docs[0], tuple([tf_idf, docs[1][1]])])
                self.invDict[keys][i] = posting

    # create inverted index
    def create(self):
        # counter for progress purposes
        i = 0
        self.read_json()
        # loop through html files
        for docs in self.urls:
            try:
                i += 1
                # read file and tokenize contents
                page_contents = self.read_file(docs)
                tokens = self.tokenize_and_count(page_contents)
                for keys in tokens:
                    # construct posting for token
                    tf = self.calc_tf(tokens[keys][0])
                    posting = tuple([tf, tokens[keys][1]])
                    tokens[keys] = posting
                    if keys in self.invDict:
                        # append new document, term frequency, and index list to token's posting list
                        self.invDict[keys].append(tuple([str(docs), tokens[keys]]))
                    else:
                        # create mapping of token to document id, term frequency, and index list
                        self.invDict[keys] = [tuple([str(docs), tokens[keys]])]
                if i % 1000 == 0:
                    # print out status report every 1000 pages processed
                    print("# docs {}".format(i))

            except Exception as e:
                print('ERROR: {}'.format(e))
                continue

        # set token count and calculate tf-idf for whole inverted index
        self.tokCount = len(self.invDict)
        self.calc_tfidf()

        # insert inverted index into database
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
                self.db.Corpus.insert(entry)
                if i % 1000 == 0:
                    # print out status report every 1000 items added to corpus
                    print('{} Items added to Corpus'.format(i))
        except Exception as e:
            print('MONGODB ERROR')
            print('{}'.format(e))

    # read json file to dictionary and database
    def read_json(self):
        # set class dictionary urls to map document ids to urls
        with open('WEBPAGES_RAW/bookkeeping.json') as f:
            self.urls = json.load(f)

        # create urls database that maps document ids to urls
        for key in self.urls:
            entry = {'docId': key,
                     'url': self.urls[key]}
            self.db2.Urls.insert(entry)

        # set document count variable
        self.docCount = len(self.urls)
        # self.db2.Urls.insert(self.urls)  ############# DO WE NEED THIS ###################################

    # helper function that returns number of documents in inverted index
    def get_docCount (self):
        self.docCount = self.db2.Urls.count()
        return self.docCount

    # helper function to get analytics of inverted index: token and document count
    def analytics(self):
        self.tokCount = self.db.Corpus.count()
        print("Unique Token Count: {}".format(self.tokCount))

        self.docCount = self.db2.Urls.count()
        print("Document Count: {}".format(self.docCount))

    # calculate tf-idf for user query
    def calc_query_tfidf(self, query_dict):
        query_tfidf = {}
        for term in query_dict:
            # retrieve term frequency from query dictionary
            tf = query_dict[term]
            # retrieve from database the query token
            result = self.db.Corpus.find({"token": term}, {"posting.docId": 1, "_id": 0})
            # calculate token idf from the length of retrieved posting list
            query_df = len(result.next()['posting'])
            query_idf = math.log((self.get_docCount() / query_df), 10)
            # calculate tf-idf using query idf and query tf
            tf_idf = query_idf * (1 + math.log(tf, 10))
            tf_idf = float("{0:.3f}".format(tf_idf))
            # map term to cacluated tf-idf
            query_tfidf[term] = tf_idf
        return query_tfidf

    # union posting lists of query terms
    def union_postings(self, query_dict):
        union_tfidf = {}
        union_index = {}
        for token in query_dict:
            # retrieve from database the query token, docId, and metrics
            result = self.db.Corpus.find({"token": token}, {"posting.docId": 1, "posting.metrics.": 1, "_id": 0})
            posting = result.next()['posting']
            # loop through token's posting list
            for doc in posting:
                # grab document tf-idf and indices from metrics
                doc_tfidf = doc['metrics']['tf-idf']
                doc_indices = doc['metrics']['indices']
                # sort indices to grab earliest usage of term in document
                doc_indices.sort()
                first_index = doc_indices[0]
                docId = doc['docId']
                if docId in union_tfidf:
                    # retrieve old first index from map
                    index = union_index[docId]
                    if first_index < index:
                        # new first index occurs earlier than old index, set to new one
                        index = first_index
                    # map docId to earliest index
                    union_index[docId] = index
                    # map docId to sum of old tf-idf and new tf-idf
                    # this rewards documents that contains multiple query words
                    union_tfidf[docId] = union_tfidf[docId] + doc_tfidf
                else:
                    # document is new, map docId to retrieved tf-idf and first index
                    union_tfidf[docId] = doc_tfidf
                    union_index[docId] = first_index
        return union_tfidf, union_index

    # helper function for cosine scoring
    def calc_scoresAndLengths(self, query_tfidf):
        scores = {}
        doc_lengths = {}
        indices = {}
        for token in query_tfidf:
            # retrieve from database the query token, docId, and metrics
            result = self.db.Corpus.find({"token": token}, {"posting.docId": 1, "posting.metrics": 1, "_id": 0})
            posting = result.next()['posting']
            # loop through token's posting list
            for doc in posting:
                # grab document tf-idf and indices from metrics
                doc_tfidf = doc['metrics']['tf-idf']
                doc_indices = doc['metrics']['indices']
                # sort indices to grab earliest usage of term in document
                doc_indices.sort()
                first_index = doc_indices[0]
                docId = doc['docId']
                # calculate score with query tf-idf and document tf-idf
                score = query_tfidf[token] * doc_tfidf
                if docId in scores:
                    # retrieve old first index from map
                    index = indices[docId]
                    if first_index < index:
                        # new first index occurs earlier than old index, set to new one
                        index = first_index
                    # map docId to earliest index
                    indices[docId] = index
                    # map docId to query score
                    scores[docId] += float("{0:.3f}".format(score))
                else:
                    # document is new, map docId to score and first index
                    scores[docId] = float("{0:.3f}".format(score))
                    indices[docId] = first_index
                if docId in doc_lengths:
                    # map docId to current value plus new vector length, unfinished
                    doc_lengths[docId] += doc_tfidf**2
                else:
                    # map docId to vector length, unfinished
                    doc_lengths[docId] = doc_tfidf ** 2

        return scores, indices, doc_lengths

    # helper function to finish document vector length calculation
    def finish_lengths(self, doc_lengths):
        for doc in doc_lengths:
            doc_lengths[doc] = math.sqrt(doc_lengths[doc])
        return doc_lengths

    # helper function to finish score calculation by normalizing document length
    def finish_scores(self, scores, doc_lengths):
        for doc in scores:
            scores[doc] = scores[doc]/doc_lengths[doc]
        return scores

    # helper function to retrieve top 10 or less documents
    def strip_scores(self, scores):
        final_docs = []
        num_final = 10
        if len(scores) < 10:
            # if query resulted in less than 10 docs, set final length to that
            num_final = len(scores)
        for i in range(num_final):
            # create final document dictionary
            final_docs.append(scores[i])
        return final_docs

    # search using cosine heuristic
    def search_cosine(self, query):
        # tokenize query and calculate scores
        query_dict = self.tokenize(query)
        query_tfidf = self.calc_query_tfidf(query_dict)
        scores, indices, doc_lengths = self.calc_scoresAndLengths(query_tfidf)
        # finish above calculations
        doc_lengths = self.finish_lengths(doc_lengths)
        scores = self.finish_scores(scores, doc_lengths)
        # sort scores dictionary and get top 10 or less documents and corresponding indices
        sorted_scores = sorted(scores.items(), key=operator.itemgetter(1), reverse=True)
        final_docs = self.strip_scores(sorted_scores)
        final_docs = self.listToDict(final_docs)
        final_indices = self.get_top_indices(final_docs, indices)
        return final_docs, final_indices, query

    # helper function to convert list to dictionary
    def listToDict (self, list):
        new_dict = {}
        for i in range(len(list)):
            new_dict[list[i][0]] = list[i][1]
        return new_dict

    # helper function to retrieve index of first query word in top documents
    def get_top_indices(self, top_docs, indices):
        top_indices = {}
        for docId in indices:
            if docId in top_docs:
                # document is in top documents, map docId to first index
                top_indices[docId] = indices[docId]
        return top_indices

    # search using tf-idf sum heuristic
    def search_tfidf(self, query):
        # tokenize query and calculate scores
        query_dict = self.tokenize(query)
        union_scores, union_indices = self.union_postings(query_dict)
        # sort scores dictionary and get top 10 or less documents and corresponding indices
        sorted_scores = sorted(union_scores.items(), key=operator.itemgetter(1), reverse=True)
        final_docs = self.strip_scores(sorted_scores) # gets docIds of top 10 scoring
        final_docs = self.listToDict(final_docs)
        final_indices = self.get_top_indices(final_docs, union_indices)
        return final_docs, final_indices, query_dict

    # retrieve urls from database using document ids
    def get_urls(self, docIds):
        top_urls = {}
        for doc in docIds:
            result = self.db2.Urls.find({"docId": doc}, {"url": 1, "_id": 0})
            url = result.next()
            top_urls[doc] = url
        return top_urls

    # helper function to get text for snippet
    def get_titleandContents(self, docId):
        final_contents = ''
        # open file and check for errors
        try:
            file_name = "../../Project3/WEBPAGES_RAW/" + docId
            f = io.open(file_name, "r", encoding='utf-8')
        except Exception as e:
            print ("Error: {}".format(e))
            return

        # make the soup
        contents = f.read()
        soup = BeautifulSoup(contents)
        # go through soup and find relevant tags
        for tags in soup.findAll(['p', 'h1', 'h2', 'h3', 'title']):
            # remove irrelevant tags if found in above tags
            for a in tags(['a', 'img', 'script', 'style']):
                a.decompose()
            # remove contents
            for element in tags(text=lambda text: isinstance(text, Comment)):
                element.extract()
            # concatenate alpha-numeric characters from relevant tags to final contents
                final_contents += re.sub('[^0-9a-zA-Z]+', ' ', tags.getText(' ')) + '\n'

        # retrieve title of html page
        if soup.title is None:
            title = "Not Available"
        else:
            title = soup.title.string

        f.close()
        return title, final_contents

    # retrieve snippet of text surrounding first occurence of query word
    def get_snippet(self, contents, first_index):
        if first_index - 60 < 0:
            # first index is close to beginning, set start of window to beginning of contents
            beg = 0
        else:
            # set start of window to between 60 and 50 characters before beginning of word looking for space
            beg = contents.find(' ', first_index-60, first_index-50) + 1
        if first_index + 60 >= len(contents):
            # first index is near end, set end of window to end of contents
            end = len(contents)
        else:
            # set end of window to between 50 and 60 characters after beginning of word looking for space
            end = contents.find(' ', first_index+50, first_index+60)

        # get snippet from calculated window
        snippet = contents[beg:end]
        # check that snippet is not too long
        if len(snippet) > 130:
            snippet = snippet[:130]
        return snippet

    # perform a search given a query and mode: tfidf or cosine
    def search(self, query, mode):
        # set start time to see how long the query takes
        self.start_time = time()
        # perform inputted search
        if mode == 'tfidf':
            top_docs, top_indices, query_dict = self.search_tfidf(query)
        else:
            top_docs, top_indices, query_dict = self.search_cosine(query)
        # retrieve top urls associated with top documents
        top_urls = self.get_urls(top_docs)
        final_dict = {}
        for doc in top_docs:
            # get title and snippet of text for top document
            title, contents = self.get_titleandContents(doc)
            snippet = self.get_snippet(contents, top_indices[doc])
            # retrieve url for top document
            url = top_urls[doc]['url']
            # create dicationary entry in json format for return
            final_dict[str(url)] = {'title': str(title), 'snippet': str(snippet)}

        # stop keeping time as search is done
        self.end_time = time() - self.start_time
        return final_dict

    # helper function to get how long search took
    def get_time(self):
        return self.end_time


'''
NOTE TO JASON:
Fixed the bug (I think) for less than 10 results.
Added a get time function.
Added a LOT of comments
check out line 215 i'm pretty sure we don't need it as we insert insert into urls right above that
'''

# start_time = time()
# test = InvertedDictionary()
# test.search("computer science", 'cosine')
# end_time = time() - start_time
# print("elapse time: {}s".format(end_time))