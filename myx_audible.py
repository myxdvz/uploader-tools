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
        self.extension="m4b"
        
    def getByID (self, id=""):
        print (f"Searching Audible for\n\tasin:{id}")

        #id is ASIN
        self.id=id

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

            return True
        else:
            return False

    def search (self, params):
        verbose=bool(self.config.get("Config/flags/verbose"))
        print (f"Searching Audible for\n\t{params}")

        #get parameters, replace all spaces with +
        title=""
        author=""
        narrator=""
        keywords=""
        language="en"
        if "title" in params:
            title = params["title"]
        if "author" in params:
            author = params["author"]
        if "narrator" in params:
            narrator = params["narrator"]
        if "keywords" in params:
            keywords = params["keywords"]
        if "language" in params:
            language = params["language"]
        

        books={}
        cacheKey = myx_utilities.getHash(f"{params}")
        if myx_utilities.isCached(self.config, cacheKey, "audible"):
            print (f"Retrieving {cacheKey} from audible")

            #this search has been done before, retrieve the results
            books = myx_utilities.loadFromCache(self.config, cacheKey, "audible")
        else:
            try:
                p=f"https://api.audible.com/1.0/catalog/products"

                r = httpx.get (
                    p,
                    params={
                        "title": title,
                        "author": author,
                        "narrator": narrator,
                        "keywords": keywords,
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
        found=False
        if "products" in books:
            self.json=books
            count = len (books["products"])
            print (f"{count} books returned for {params}")
            if (count == 1):
                self.__dic2Book__(books["products"][0])
                found=True
            elif (count > 1):
                booksFound=[]
                choices=[]
                for book in books["products"]:
                    abook = AudibleBook(self.config)
                    abook.__dic2Book__(book)
                    if abook.language == myx_utilities.getLanguage(language):
                        booksFound.append(abook)

                        #display
                        print(f"[{len(booksFound)}] {abook.title}({abook.releaseDate}) by {abook.__getAuthors__()}, ASIN: {abook.asin}, Language: {abook.language}")
                        choices.append (len(booksFound))

                #add none
                print(f"[0] None of the above")                            
                choices.append (0)

                choice = myx_utilities.promptChoice (f"Pick a match [0-{len(booksFound)}]:  ", choices)
                if choice > 0:
                    if verbose: print(f"You've selected [{choice}] {booksFound[choice-1].title}({booksFound[choice-1].releaseDate}) by {booksFound[choice-1].__getAuthors__()}, ASIN: {booksFound[choice-1].asin}, Language: {booksFound[choice-1].language}")
                    self.__dic2Book__(books["products"][choice-1])
                    found=True

        return found

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
            if 'content_type' in book:
                self.contentType = str(book["content_type"])

            return self
        else:
            return None       

    def __getMamTags__ (self, delimiter="|"):
        return f"Duration: {self.__convert_to_hours_minutes__(self.length)} | Chapterized | Libation True Decrypt | Audible Release: {self.releaseDate} | Publisher: {self.publisher} | {','.join(set(self.genres))}"

    def getMAMCategory (self):  
        genre = ""
        
        if len(self.genres): genre = self.genres[0]
        match genre:
            case "Arts & Entertainment":
                self.category = "Audiobooks - Art"

            case "Biographies & Memoirs":
                if "True Crime" in self.tags: self.category = "Audiobooks - True Crime"
                else: self.category = "Audiobooks - Biographical"
                
            case "Business & Careers":
                self.category = "Audiobooks - Business"
                
            case "Children's Audiobooks":
                self.category = "Audiobooks - Juvenile"
                
            case "Comedy & Humor":
                self.category = "Audiobooks - Humor"
                
            case "Computers & Technology":
                self.category = "Audiobooks - Computer/Internet"
                
            case "Education & Learning":
                if "Language Learning" in self.tags: self.category = "Audiobooks - Language"
                elif "Words, Language & Grammar" in self.tags: self.category = "Audiobooks - Language"
                else: self.category = "Audiobooks - Instructional"
                
            case "Erotica":
                self.category = "Audiobooks - Romance"
                
            case "Health & Wellness":
                self.category = "Audiobooks - Medical"
                
            case "History":
                self.category = "Audiobooks - History"
                
            case "Home & Garden":
                if "Crafts & Hobbies" in self.tags: self.category = "Audiobooks - Craft"
                elif "Food & Wine" in self.tags: self.category = "Audiobooks - Food"
                else: self.category = "Audiobooks - Home/Garden"
                
            case "LGBTQ+":                
                if "Biographies & Memoirs" in self.tags: self.category = "Audiobooks - Biographical"
                elif "History" in self.tags: self.category = "Audiobooks - History"
                elif "Mystery, Thriller & Suspense" in self.tags: self.category = "Audiobooks - Mystery"
                elif "Science Fiction & Fantasy" in self.tags: self.category = "Audiobooks - Science Fiction"
                elif "Parenting & Families" in self.tags: self.category = "Audiobooks - General Non-Fic"
                elif "Literature & Fiction" in self.tags: self.category = "Audiobooks - General Fiction"
                else: self.category = "Audiobooks - Romance"
                
            case "Literature & Fiction":
                if "Action & Adventure" in self.tags: self.category = "Audiobooks - Action/Adventure"
                elif "Classics" in self.tags: self.category = "Audiobooks - Literary Classics"
                elif "Historical Fiction" in self.tags: self.category = "Audiobooks - Historical Fiction"
                elif "Horror" in self.tags: self.category = "Audiobooks - Horror"
                elif "Humor & Satire" in self.tags: self.category = "Audiobooks - Humor"
                elif "Memoirs, Diaries & Correspondence" in self.tags: self.category = "Audiobooks - Biographical"
                else: self.category = "Audiobooks - General Fiction"
                
            case "Money & Finance":
                self.category = "Audiobooks - Business"
                
            case "Mystery, Thriller & Suspense":
                if "Crime Fiction" in self.tags: self.category = "Audiobooks - Crime/Thriller"
                elif "True Crime" in self.tags: self.category = "Audiobooks - True Crime"
                else: self.category = "Audiobooks - Mystery"
                
            case "Politics & Social Sciences":
                if "Philosophy" in self.tags: self.category = "Audiobooks - Philosophy"
                else: self.category = "Audiobooks - Pol/Soc/Relig"
                
            case "Relationships, Parenting & Personal Development":
                self.category = "Audiobooks - Self-Help"
                
            case "Religion & Spirituality":
                self.category = "Audiobooks - Pol/Soc/Relig"

            case "Romance":
                #MAM has a few romance breakdowns
                if "Urban" in self.tags: self.category = "Audiobooks - Urban Fantasy"
                elif "Paranormal" in self.tags: self.category = "Audiobooks - Urban Fantasy"
                elif "Westerns" in self.tags: self.category = "Audiobooks - Western"
                else: self.category = "Audiobooks - Romance"

            case "Science & Engineering":
                self.category = "Audiobooks - Math/Science/Tech"
                
            case "Science Fiction & Fantasy":
                if "Fantasy" in self.tags: self.category = "Audiobooks - Fantasy"
                else: self.category = "Audiobooks - Science Fiction"
                
            case "Sports & Outdoors":
                if "Outdoors & Nature" in self.tags: self.category = "Audiobooks - Nature"
                else: self.category = "Audiobooks - Recreation"
                
            case "Teen & Young Adult":
                self.category = "Audiobooks - Young Adult"
                
            case "Travel & Tourism":
                self.category = "Audiobooks - Travel/Adventure"
                
            case _:
                self.category = "Audiobooks - General Fiction"

        return self.category

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
       