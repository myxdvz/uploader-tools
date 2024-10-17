from dataclasses import dataclass
from dataclasses import field
import myx_utilities
import myx_args
import pprint
import json
import httpx, os
import yaml

@dataclass
class Book:
    #Series Class
    @dataclass
    class Series:
        name:str=""
        number:str=""
        separator:str=""
        
        def getSeriesPart(self):
            if (len(self.part.strip()) > 0):
                return f"{self.name} {self.separator}{str(self.part)}"
            else:
                return self.name

    id:str=""
    asin:str=""
    isbn:str=""
    title:str=""
    subtitle:str=""
    publisher:str=""
    length:int=0
    duration:float=0
    language:str="English"
    description:str=""
    releaseDate:str=""    
    cover:str=""
    source:str=""
    category:str=""
    series:list[Series]= field(default_factory=list)
    authors:list[str]= field(default_factory=list)
    narrators:list[str]= field(default_factory=list)
    genres:list[str]= field(default_factory=list)
    tags:list[str]= field(default_factory=list)    
    delimiter:str="|"
    config:myx_args.Config=None

    def __getMamIsbn__ (self):
        if len(self.asin):
            return f"ASIN: {self.asin}"
        else:
            return f"{self.isbn}"

    def __getMamTags__ (self, delimiter="|"):
        return self.tags

    def getJSONFastFillOut (self, path, filename):
        #write the file out
        json_file = os.path.join(path, filename + ".json")

        # --- Generate .json Metadata file ---
        #generate the mam json file for easy upload
        jff = {
            "isbn": self.__getMamIsbn__(),
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "authors": [],
            "series": [],
            "narrators": [],
            "tags": self.__getMamTags__(self.delimiter),
            "thumbnail": self.cover,
            "language": self.language,
            "category": self.category
        } 

        #authors
        for author in self.authors:
            jff["authors"].append(author)

        #narrators
        for narrator in self.narrators:
            jff["narrators"].append(narrator)

        #series
        for series in self.series:
            jff["series"].append({"name": series.name, "number": series.number})

        try:
            with open(json_file, mode='w', encoding='utf-8') as jfile:
                json.dump(jff, jfile, indent=4)  

        except Exception as e:
            print (f"Error getting JSON Fast Fillout {json_file}: {e}")


@dataclass
class AudibleBook(Book):
    def __init__ (self):
        super().__init__()
        self.source="audible"

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
            if 'language' in book: self.language=str(book ["language"])
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
        return f"Duration: {self.length} min | Chapterized | Libation True Decrypt | Audible Release: {self.releaseDate} | Publisher: {self.publisher} | {','.join(set(self.genres))}"

@dataclass
class YamlBook(Book):
    def __init__ (self):
        super().__init__()
        self.source="file"

    def getByID (self, id=""):
        #for a local book, we're expecting a yaml file as the id
        yaml_file = id
        if os.path.exists(yaml_file):
            try:
                with open(yaml_file, mode='r', encoding='utf-8') as yfile:
                    book = yaml.safe_load(yfile) 

                    #set the book object
                    self.__dic2Book__(book)
                    #set the ID of the book, hash of file
                    self.id = myx_utilities.getHash(yaml_file)

            except Exception as e:
                print (f"Error getting YAML {yaml_file}: {e}")
        else:
            print (f"Local book file doesn't exist: {id}")

        return self

    def __dic2Book__(self, book):
        #book is an Yaml dictionary
        if book is not None:
            if 'asin' in book: self.asin=str(book["asin"])
            if 'isbn' in book: self.isbn=str(book["isbn"])
            if 'title' in book: self.title=str(book["title"])
            if 'subtitle' in book: self.subtitle=str(book["subtitle"])
            if 'description' in book: self.description=str(book["description"])
            if 'language' in book: self.language=str(book ["language"])
            if 'thumbnail' in book: self.cover=str(book ["thumbnail"])
            if 'tags' in book: self.tags=str(book ["tags"])
            if 'category' in book: self.category=str(book ["category"])
            if 'authors' in book: 
                for author in book["authors"]:
                    self.authors.append(str(author))
            if 'narrators' in book: 
                for narrator in book["narrators"]:
                    self.narrators.append(str(narrator))
            if 'series' in book: 
                for s in book["series"]:
                    self.series.append(self.Series(str(s["name"]), str(s["number"])))

            return self
        else:
            return None        

@dataclass
class GoogleBook(Book):
    def __init__ (self):
        super().__init__()
        self.source="google"

    def getByID (self, id=""):
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
                p=f"https://www.googleapis.com/books/v1/volumes"

                r = httpx.get (
                    p,
                    params={
                        "q": f"isbn:{id}",
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
            count = int(books["totalItems"])
            print (f"{count} books returned for {id}.")
            if (count == 1):
                self.__dic2Book__(books["items"][0]["volumeInfo"])
                self.id=self.isbn
        return self

    def __dic2Book__(self, book):
        #book is an google books volumeInfo dictionary
        print (book)
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


