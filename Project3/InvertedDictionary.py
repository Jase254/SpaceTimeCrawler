import sys
import operator
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
        return self.invDict

    def sort_tokens(self):
        return sorted(self.invDict.items(), key=lambda x: (-x[1],x[0]))

    def print_tokens(self):
        for i in self.invDict:
            print ('%s - %i' % (i[0], i[1]))


    def read_file(self, id):
        name = "WEBPAGES_RAW/" + id
        try:
            f = open(name, "r")
        except Exception as e:
            print ("Error! {}".format(e))
            return
        contents = f.read()
        #print (contents)
        soup = BS.BeautifulSoup(contents)
        for string in soup.stripped_strings:
            print(repr(string))
        soup.str
        #print (soup)
        #print (soup)
        text = soup.getText()
        #print (text)
        f.close()
        return text

    # read_file gets the contents of the file
    def read_json(self):
        with open('WEBPAGES_RAW/bookkeeping.json') as f:
            self.urls = json.load(f)
        i = 0
        for keys in self.urls:
            print(keys)
            i += 1
            if i == 5:
                self.read_file(keys)
                break


test = InvertedDictionary()
test.read_json()