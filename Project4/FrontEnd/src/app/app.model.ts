export class SearchResult{
  url: string;
  title: string;
  snippet: string;

  constructor(link: string, heading: string, caption: string){
    this.url = link;
    this.title = heading;
    this.snippet = caption;
  }
}
