from myx_book import Book
import myx_utilities
import httpx
import json

class GoogleBook(Book):
    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="google"
        self.extension="epub"


    def getByID (self, id=""):
        apiKey=myx_utilities.getApiKey(self.config, self.metadata)
        print (f"Searching Google Books for\n\tisbn:{id}")
        
        #id is ISBN
        self.id=id

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
                return True
        else:
            return False

    def search (self, params):
        verbose=bool(self.config.get("Config/flags/verbose"))
        apiKey=myx_utilities.getApiKey(self.config, self.metadata)

        #get parameters, replace all spaces with +
        title=""
        author=""
        if "title" in params:
            title = params["title"].replace(" ","+")
        if "author" in params:
            author = params["author"].replace(" ","+")
        print (f"Searching Google Books for\n\ttitle:{title}\n\tauthor:{author}")

        books={}
        cacheKey = myx_utilities.getHash(f"{params}")
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
                        "q": f"q=intitle:{title}+inauthor:{author}",
                        "key": apiKey,
                        "orderBy": "relevance",
                        "printType": "all",
                        "projection": "full",
                        "langRestrict": "en"
                    }
                )

                r.raise_for_status()
                books = r.json()

                #cache this results
                myx_utilities.cacheMe(self.config, cacheKey, "google", books)

            except Exception as e:
                print(f"Error searching googlebooks: {e}")
                
        #check for ["items"][0]["volumeInfo"]
        found=False
        if "totalItems" in books:
            self.json=books
            count = int(books["totalItems"])
            print (f"{count} books returned for {title}-{author}")
            if (count == 1):
                self.__dic2Book__(books["items"][0]["volumeInfo"])
                if verbose: print(f"{self.title}({self.releaseDate}) by {self.__getAuthors__()}, ISBN: {self.isbn}, Language: {self.language}")
                found=True

            elif (count > 1):
                booksFound = []
                choices=[]
                for item in books["items"]:
                    #display all options
                    gbook=GoogleBook(self.config)
                    gbook.__dic2Book__(item["volumeInfo"])
                    booksFound.append(gbook)

                    #display
                    print(f"[{len(booksFound)}] {gbook.title}({gbook.releaseDate}) by {gbook.__getAuthors__()}, ISBN: {gbook.isbn}, Language: {gbook.language}")
                    choices.append (len(booksFound))

                #add none
                print(f"[0] None of the above")                            
                choices.append (0)

                choice = myx_utilities.promptChoice (f"Pick a match [0-{len(booksFound)}]:  ", choices)

                if choice > 0:
                    if verbose: print(f"You've selected [{choice}] {booksFound[choice-1].title}({booksFound[choice-1].releaseDate}) by {booksFound[choice-1].__getAuthors__()}, ISBN: {booksFound[choice-1].isbn}, Language: {booksFound[choice-1].language}")
                    self.__dic2Book__(books["items"][choice-1]["volumeInfo"])
                    found=True

        return found

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

    def getMAMCategory (self):  
        bisgMapping = {
            "Antiques & Collectibles": "E-books - Crafts",
            "Architecture": "E-books - Art",
            "Art": "E-books - Art",
            "Bibles": "E-books - Pol/Soc/Relig",
            "Biography & Autobiography": "E-books - Biographical",
            "Body, Mind & Spirit": "E-books - Self-Help",
            "Business & Economics": "E-books - Business",
            "Comics & Graphic Novels": "E-books - Comics/Graphic novels",
            "Computers": "E-books - Computer/Internet",
            "Cooking": "E-books - Food",
            "Crafts & Hobbies": "E-books - Crafts",
            "Design": "E-books - Art",
            "Drama": "E-books - General Fiction",
            "Education": "E-books - Instructional",
            "Family & Relationships": "E-books - General Fiction",
            "Fiction": "E-books - General Fiction",
            "Foreign Language Study": "E-books - Language",
            "Games & Activities": "E-books - Recreation",
            "Gardening": "E-books - Home/Garden",
            "Health & Fitness": "E-books - Self-Help",
            "History": "E-books - History",
            "House & Home": "E-books - Home/Garden",
            "Humor": "E-books - Humor",
            "Juvenile Fiction": "E-books - Juvenile",
            "Juvenile NonFiction": "E-books - Juvenile",
            "Language Arts & Disciplines": "E-books - Language",
            "Law": "E-books - General Fiction",
            "Literary Collections": "E-books - Mixed Collections",
            "Literary Criticism": "E-books - Literary Classics",
            "Mathematics": "E-books - Math/Science/Tech",
            "Medical": "E-books - Medical",
            "Music": "E-books - Art",
            "Nature": "E-books - Nature",
            "Performing Arts": "E-books - Art",
            "Pets": "E-books - General Non-Fic",
            "Philosophy": "E-books - Philosophy",
            "Photography": "E-books - Art",
            "Poetry": "E-books - Art",
            "Political Science": "E-books - Pol/Soc/Relig",
            "Psychology": "E-books - Math/Science/Tech",
            "Reference": "E-books - General Non-Fic",
            "Religion": "E-books - Pol/Soc/Relig",
            "Science": "E-books - Math/Science/Tech",
            "Self-Help": "E-books - Self-Help",
            "Social Science": "E-books - Pol/Soc/Relig",
            "Sports & Recreation": "E-books - Recreation",
            "Study Aids": "E-books - Instructional",
            "Technology & Engineering": "E-books - Math/Science/Tech",
            "Transportation": "E-books - Travel/Adventure",
            "Travel": "E-books - Travel/Adventure",
            "True Crime": "E-books - Crime/Thriller",
            "Young Adult Fiction": "E-books - Young Adult",
            "Young Adult NonFiction": "E-books - Young Adult"
        }
        
        genre=""
        if len(self.genres): genre = self.genres[0]
        elif len(self.genres) == 0 and len(self.tags): genre = self.tags[0]
        
        if len(genre) and genre in bisgMapping:
             self.category =  bisgMapping[genre]
        else:
             self.category =  "E-books - General Non-Fic"

        return self.category

