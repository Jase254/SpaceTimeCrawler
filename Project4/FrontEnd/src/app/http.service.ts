import { Injectable } from '@angular/core';
import {Http} from "@angular/http";

@Injectable()
export class HttpService {

  constructor(private http: Http) {
  }

  private backEndUrl = 'https://20180204t094600-dot-allthefeels-1337.appspot.com/';
  data;
  private rejected = false;

  getTweets(searchTerm: String) {
    let promise = new Promise((resolve, reject) => {
      this.http.get(this.backEndUrl + 'moretweets/' + searchTerm)
        .toPromise()
        .then(res => {
          this.data = res.json();
          resolve();
        }, rej => {
          reject();
          this.rejected = true;
        });
    });
    return promise;
  };
}
