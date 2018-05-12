import sys
import operator
import string
import BeautifulSoup as BS
import json

class InvertedDictionary:

    def __init__(self):
        self.invDict = {}
        self.docCount = 0
        self.tokCount = 0
        self.urls = {}

    def tokenize_and_count(self, contents):
        word = ''  # set up word for building
       # tokens = {}
        for i in contents:
            if i.isalnum():  # if letter is alpha-numeric, concatenate to end of word
                word += (i)
            elif word != '':
                if word.lower() in self.invDict:  # if word is in dict, add one to value for occurences
                    self.invDict[word.lower()] += 1
                else:  # else it put in dict and set value i.e. occurence to 1
                    self.invDict[word.lower()] = 1
                word = ''  # reset word to build again

    def sort_tokens(self):
        return sorted(self.invDict.items(), key=lambda x: (-x[1],x[0]))

    def print_tokens(self):
        for i in self.invDict:
            print ('%s - %i' % (i[0], i[1]))


    def read_file(self, id):
        name = "WEBPAGES_RAW/" + id
        clear = ''

        try:
            f = open(name, "r")
        except Exception as e:
            print ("Error! {}".format(e))
            return
        contents = f.read()
        soup = BS.BeautifulSoup(contents)

        for tags in soup.findAll(['p', 'h1', 'h2', 'h3', 'title']):
            for a in tags(['a', 'img', 'script', 'style']):
                a.decompose()
            clear += tags.getText() + '\n'

        f.close()
        return clear

    def create(self):
        i = 0
        page_contents = ''

        self.read_json()

        for keys in self.urls:
            print(keys)
            i += 1
            page_contents = self.read_file(keys)
            self.tokenize_and_count(page_contents)
            if i == 6:
                break


    # read_file gets the contents of the file
    def read_json(self):

        with open('WEBPAGES_RAW/bookkeeping.json') as f:
            self.urls = json.load(f)

        self.docCount = len(self.urls)



test = InvertedDictionary()
test.read_json()