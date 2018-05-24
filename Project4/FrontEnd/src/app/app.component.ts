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
  displayScore: number = 0;
  broke: boolean = false;
  cosine: boolean = false;

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
        this.displayScore = 3;
      }, rej => {
        console.log("endpoint broke")
        this.broke = true;
        this.dataLoading = false;
      });
    }
    else {
      this.httpService.search_tfidf(searchTerm).then(_ => {
        this.urls = [];
        this.urls = this.httpService.getData();
        console.log('fulfilled');
        this.dataLoading = false;
        this.displayScore = 3;
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
