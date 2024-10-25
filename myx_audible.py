from pathvalidate import sanitize_filename
from myx_book import Book
import myx_utilities
import httpx
import json
import os

class AudibleBook(Book):
    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="audible"
        #category is from Config        
        self.category=self.config.get("Config/uploader-tools/category")
        
    def getByID (self, id=""):
        print (f"Searching Audible for\n\tasin:{id}")

        books={}
        cacheKey = myx_utilities.getHash(f"{id}")
        if myx_utilities.isCached(self.config, cacheKey, "audible"):
            print (f"Retrieving {cacheKey} from audible")

            #this search has been done before, retrieve the results
            books = myx_utilities.loadFromCache(self.config, cacheKey, "audible")
        else:
            try:
                p=f"https://api.audible.com/1.0/catalog/products/{id}"

                r = httpx.get (
                    p,
                    params={
                        "asin": id,
                        "products_sort_by": "Relevance",
                        "response_groups": (
                            "media, series, product_attrs, relationships, contributors, product_desc, product_extended_attrs, category_ladders"
                        )
                    }
                )

                r.raise_for_status()
                books = r.json()

                #cache this results
                myx_utilities.cacheMe(self.config, cacheKey, "audible", books)

            except Exception as e:
                print(f"Error searching audible: {e}")
            
        #check for ["product"]
        if "product" in books:
            self.json=books
            self.__dic2Book__(books["product"])
            self.id=self.asin
        
        return self

    def __dic2Book__(self, book):
        #book is an Audible product dictionary
        if book is not None:
            if 'asin' in book: self.asin=str(book["asin"])
            if 'title' in book: self.title=str(book["title"])
            if 'subtitle' in book: self.subtitle=str(book["subtitle"])
            if 'publisher_summary' in book: self.description=str(book["publisher_summary"])
            if 'runtime_length_min' in book: self.length=book["runtime_length_min"]
            if 'authors' in book: 
                for author in book["authors"]:
                    self.authors.append(str(author["name"]))
            if 'narrators' in book: 
                for narrator in book["narrators"]:
                    self.narrators.append(str(narrator["name"]))
            if 'publisher_name' in book: self.publisher=str(book["publisher_name"])
            if 'issue_date' in book: self.releaseDate=str(book["issue_date"])
            if 'series' in book: 
                for s in book["series"]:
                    self.series.append(self.Series(str(s["title"]), str(s["sequence"])))
            if 'language' in book: self.language=str(book ["language"]).capitalize()
            if 'product_images' in book: self.cover=str(book ["product_images"]["500"])
            if 'category_ladders' in book:
                for cl in book["category_ladders"]:
                    for i, item in enumerate(cl["ladder"]):
                        #the first one is genre, the rest are tags
                        if (i==0):
                            self.genres.append(item["name"])
                        else:
                            self.tags.append(item["name"])    
            return self
        else:
            return None       

    def __getMamTags__ (self, delimiter="|"):
        return f"Duration: {self.__convert_to_hours_minutes__(self.length)} | Chapterized | Libation True Decrypt | Audible Release: {self.releaseDate} | Publisher: {self.publisher} | {','.join(set(self.genres))}"

    def export(self, filename):
        #Config
        verbose = bool(self.config.get("Config/flags/verbose"))

        if os.path.exists(filename):
            print (f"Target file {filename} exists... skipping export")
        else:
            #create the cache file
            with open(filename, mode="w", encoding='utf-8', errors='ignore') as file:
                file.write(json.dumps(self.json["product"], indent=4))

        return os.path.exists(filename)        
       