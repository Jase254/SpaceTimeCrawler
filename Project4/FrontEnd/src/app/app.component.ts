import { Component, Input } from '@angular/core';
import { HttpService } from './http.service';
import { SearchResult } from "./app.model";
import { DecimalPipe } from "@angular/common";

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  holder: string;

  constructor(private httpService: HttpService) {
    this.holder = 'Computer Science';
  }

  urls = [];
  dataLoading: boolean = false;
  broke: boolean = false;
  cosine: boolean = false;
  noResults  = false;
  searchTime = '3.2';

  searchUrls(searchTerm) {
    this.urls = [];
    this.dataLoading = true;
    console.log(this.cosine);


    console.log(searchTerm);
    if (this.cosine) {
      this.httpService.search_cosine(searchTerm).then(_ => {
        this.urls = [];
        this.urls = this.httpService.getData();
        console.log('fulfilled');
        this.dataLoading = false;
      }, rej => {
        console.log("endpoint broke");
        this.broke = true;
        this.dataLoading = false;
      });

      this.httpService.search_time().then(_ => {
        this.searchTime = this.httpService.getTime();
      }, rej => {
        this.searchTime = '0'
      });

    }
    else {
      this.httpService.search_tfidf(searchTerm).then(_ => {
        this.broke = false;
        this.noResults = false;
        this.urls = [];
        this.urls = this.httpService.getData();

        this.httpService.search_time().then(_ => {
          this.searchTime = this.httpService.getTime()
        }, rej => {
          this.searchTime = '0'
        });

        if(this.urls.length == 0) {
          this.noResults = true;
        }
        console.log('fulfilled');
        this.dataLoading = false;
      }, rej => {
        console.log("endpoint broke")
        this.broke = true;
        this.dataLoading = false;
      });
    }
  }
}

  @Component({
    selector: 'app-sentiment',
    template: `<h1>{{_name}}Test</h1>`,
    styleUrls: ['./app.component.css']
  })
  export class SentimentComponent {
  _name: string;
  @Input()
  set name(str: string) {
    this._name = str;
    console.log(str);
  }
}
