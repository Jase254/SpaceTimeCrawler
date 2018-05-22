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


@app.route('/search/<string:search_term>', methods=['POST', 'GET'])
@cross_origin()
def search(search_term):
    return 'search term: {}'.format(search_term)


if __name__ == '__main__':
    app.run()