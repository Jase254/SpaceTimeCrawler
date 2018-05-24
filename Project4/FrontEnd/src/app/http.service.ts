import { Injectable } from '@angular/core';
import {Http} from "@angular/http";
import { SearchResult } from "./app.model";
import {log} from "util";

@Injectable()
export class HttpService {

  constructor(private http: Http) {
  }

  private backEndUrl = 'http://localhost:5000';
  data;
  results  = [];
  num_urls = 0;
  private rejected = false;

  search_tfidf(searchTerm: String) {
    let promise = new Promise((resolve, reject) => {
      this.http.get(this.backEndUrl + '/search/tfidf/' + searchTerm)
        .toPromise()
        .then(res => {
          this.data = res.json();
          this.results = []
          this.num_urls = 0
          for(let key in this.data){
            let title  = this.data[key]['title'];
            let snippet = this.data[key]['snippet'];
            this.results[this.num_urls] = new SearchResult(key, title, snippet);
            ++this.num_urls;
          }

          resolve();
        }, rej => {
          reject();
          this.rejected = true;
        });
    });
    return promise;
  };

  search_cosine(searchTerm: String) {
    let promise = new Promise((resolve, reject) => {
      this.http.get(this.backEndUrl + '/search/cosine/' + searchTerm)
        .toPromise()
        .then(res => {
          this.data = res.json();
          this.results = []
          this.num_urls = 0
          for(let key in this.data){
            let title  = this.data[key]['title'];
            let snippet = this.data[key]['snippet'];
            this.results[this.num_urls] = new SearchResult(key, title, snippet);
            ++this.num_urls;
          }

          resolve();
        }, rej => {
          reject();
          this.rejected = true;
        });
    });
    return promise;
  };

  getData(){
    return this.results;
  }
}
