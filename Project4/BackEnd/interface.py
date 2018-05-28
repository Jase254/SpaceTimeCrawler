import searchEngine
from flask import Flask, jsonify
from flask_cors import cross_origin

app = Flask(__name__)

engine = searchEngine.InvertedDictionary()

@app.route('/')
@cross_origin()
def initialize():
    global engine
    return 'Home!'


@app.route('/search/tfidf/<string:search_term>', methods=['POST', 'GET'])
@cross_origin()
def search_tfidf(search_term):
    obtained_urls = engine.search(search_term, 'tfidf')
    return jsonify(obtained_urls)


@app.route('/search/time', methods=['POST', 'GET'])
@cross_origin()
def get_search_time():
    time = engine.get_time()
    time = float("{0:.3f}".format(time))
    return jsonify(time)


@app.route('/search/cosine/<string:search_term>', methods=['POST', 'GET'])
@cross_origin()
def search_cosine(search_term):
    obtained_urls = engine.search(search_term, 'cosine')
    return jsonify(obtained_urls)


if __name__ == '__main__':
    app.run()