from myx_book import Book
import myx_utilities
import httpx
import json

class GoogleBook(Book):
    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="google"

    def getByID (self, id=""):
        apiKey=myx_utilities.getApiKey(self.config, self.metadata)
        print (f"Searching Google Books for\n\tisbn:{id}")
        #9780698146402, 0698146409

        books={}
        cacheKey = myx_utilities.getHash(f"{id}")
        if myx_utilities.isCached(self.config, cacheKey, "google"):
            print (f"Retrieving {cacheKey} from google")

            #this search has been done before, retrieve the results
            books = myx_utilities.loadFromCache(self.config, cacheKey, "google")
        else:
            try:
                #&key={YOUR_API_KEY}
                p=f"https://www.googleapis.com/books/v1/volumes"

                r = httpx.get (
                    p,
                    params={
                        "q": f"isbn:{id}",
                        "key": apiKey,
                        "orderBy": "relevance",
                        "printType": "all",
                        "projection": "full"
                    }
                )

                r.raise_for_status()
                books = r.json()

                #cache this results
                myx_utilities.cacheMe(self.config, cacheKey, "google", books)

            except Exception as e:
                print(f"Error searching googlebooks: {e}")
                
        #check for ["items"][0]["volumeInfo"]
        if "totalItems" in books:
            self.json=books
            count = int(books["totalItems"])
            print (f"{count} books returned for {id}.")
            if (count == 1):
                self.__dic2Book__(books["items"][0]["volumeInfo"])
                self.id=self.isbn
        return self

    def __dic2Book__(self, book):
        #book is an google books volumeInfo dictionary
        if book is not None:
            if 'id' in book: self.id=str(book["id"])
            if 'industryIdentifiers' in book: self.isbn=str(book["industryIdentifiers"][0]["identifier"])
            if 'title' in book: self.title=str(book["title"])
            if 'subtitle' in book: self.subtitle=str(book["subtitle"])
            if 'description' in book: self.description=str(book["description"])
            if 'authors' in book: 
                for author in book["authors"]:
                    self.authors.append(str(author))
            if 'narrators' in book: 
                for narrator in book["narrators"]:
                    self.narrators.append(str(narrator))
            if 'publisher' in book: self.publisher=str(book["publisher"])
            if 'publishedDate' in book: self.releaseDate=str(book["publishedDate"])
            if 'series' in book: 
                for s in book["series"]:
                    self.series.append(self.Series(str(s["title"]), str(s["sequence"])))
            if 'language' in book: self.language=myx_utilities.getLanguage(str(book ["language"]))
            if 'imageLinks' in book: self.cover=str(book["imageLinks"]["thumbnail"])
            if 'mainCategory' in book: self.genres.append(str(book["mainCategory"]))
            if 'categories' in book:
                for cl in book["categories"]:
                    self.tags.append(cl)            

            return self
        else:
            if verbose: print (f"Empty record - {book}")
            return None        

    def __getMamTags__ (self, delimiter="|"):
        return f"Publish Date: {self.releaseDate} | Publisher: {self.publisher} | {','.join(set(self.tags))}"


