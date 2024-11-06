from dataclasses import dataclass
from dataclasses import field
from myx_book import Book
import myx_utilities
import requests
import os
import pickle
import httpx
import json

class MAMBook(Book):
    total:int=0
    found:int=0

    #Added Attributes for MAMBook
    added:str=""
    bookmarked:str=""
    browseFlags=int=0
    cat:str=""
    categoryId:int=0
    catName:str=""
    vip:bool=False
    fl_vip:bool=False
    free:bool=False
    main_cat:int=0
    my_snatched:bool=False
    numfiles:int=0
    owner:int=0
    owner_name:str=""
    personal_fl:bool=False
    filetype:str=""

    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="mam"     
        self.booksFound=[]
        
    def getByID (self, id=""):
        #ID is assumed to be search string
        self.search(id)
        #if there is only one result, set self to the only result      
        return (len(self.booksFound) > 0)

    def search (self, params, interactive=False):
        #Config
        session = self.config.get("Config/sources/session")
        log_path = self.config.get("Config/log_path")

        #get parameters, replace all spaces with +
        text=""
        ebook=True
        audiobook=True
        if "text" in params:
            text = params["text"]
        if "ebook" in params:
            ebook = bool(params["ebook"])
        if "audiobook" in params:
            audiobook = bool(params["audiobook"])

        #search string
        if len(text):
            text = f'{text} @dummy mamDummy'

        #cache results for this search string
        books={}
        cacheKey=myx_utilities.getHash(str(params))
        
        if myx_utilities.isCached(self.config, cacheKey, "mam"):
            #this search has been done before, load results from cache
            books = myx_utilities.loadFromCache(self.config, cacheKey, "mam")
        
        else:
            #save cookie for future use
            cookies_filepath = os.path.join(log_path, 'cookies.pkl')
            sess = requests.Session()

            #a cookie file exists, use that
            if os.path.exists(cookies_filepath):
                cookies = pickle.load(open(cookies_filepath, 'rb'))
                sess.cookies = cookies
            else:
                #assume a session ID is passed as a parameter
                sess.headers.update({"cookie": f"mam_id={session}"})

            #test session and cookie
            r = sess.get('https://www.myanonamouse.net/jsonLoad.php', timeout=5)  # test cookie
            if r.status_code != 200:
                raise Exception(f'Error communicating with API. status code {r.status_code} {r.text}')
            else:
                # save cookies for later
                with open(cookies_filepath, 'wb') as f:
                    pickle.dump(sess.cookies, f)

                mam_categories = []
                if audiobook:
                    mam_categories.append(13) #audiobooks
                    mam_categories.append(16) #radio

                if ebook:
                    mam_categories.append(14)
                
                params = {
                    "tor": {
                        "text": text,  # The search string.
                        "srchIn": {
                            "title": "true",
                            "author": "true",
                            "fileTypes": "true",
                            "series": "true"
                        },
                        "browseFlagsHideVsShow": "0",
                        "main_cat": mam_categories
                    },
                    "searchType": "all",
		            "searchIn": "torrents",
                    "thumbnail": "", 
                    "description": "",
                    "posterLink": "",
                    "perpage":50
                }

                try:
                    r = sess.post('https://www.myanonamouse.net/tor/js/loadSearchJSONbasic.php', json=params)
                    if r.text == '{"error":"Nothing returned, out of 0"}':
                        return self

                    books = r.json()

                    #cache this result before returning it
                    myx_utilities.cacheMe(self.config, cacheKey, "mam", books)
            
                except Exception as e:
                    print(f'error searching MAM {e}')

        #check for ["data"]
        found=False
        if "data" in books:
            self.json=books
            self.total = int(books["total"])
            self.found = int(books["found"])

            if interactive:
                count = self.found
                print (f"{count} books returned for {params}")
                if (count == 1):
                    self.__dic2Book__(book["data"][0])
                    found=True
                elif (count > 1):
                    booksFound=[]
                    choices=[]
                    for book in books["data"]:
                        abook = MAMBook(self.config)
                        abook.__dic2Book__(book)
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
            else:
                for book in books["data"]:
                    self.booksFound.append(self.__dic2Book__(book))   

        return self


    def __dic2Book__(self, b):
        #book is a MAM torrent record
        book = Book (self.config)
        book.metadata="mam"
        if b is not None:
            if 'id' in b: 
                book.id=str(b["id"])
            if 'asin' in b: 
                book.asin=str(b["asin"])
            if 'title' in b: 
                book.title=str(b["title"])
            if 'description' in b: 
                book.description=str(b["description"])
            if 'author_info'in b:
                #format {id:author, id:author}
                if len(b["author_info"]):
                    authors = json.loads(b["author_info"])
                    for author in authors.values():
                        book.authors.append(str(author))
            if 'narrator_info'in b:
                #format {id:narrator, id:narrator}
                if len(b["narrator_info"]):
                    narrators = json.loads(b["narrator_info"])
                    for narrator in narrators.values():
                        book.narrators.append(str(narrator))
            if 'series_info'in b:
                #format {"35598": ["Kat Dubois", "5"]}
                if len(b["series_info"]):
                    series_info = json.loads(b["series_info"])
                    for series in series_info.values():
                        s=list(series)
                        book.series.append(self.Series(str(s[0]), s[1]))    
            if 'thumbnail' in b: 
                book.cover=str(b["thumbnail"])
            if 'lang_code' in b: 
                book.language=myx_utilities.getLanguage((b["lang_code"]))
            if 'my_snatched' in b:
                book.my_snatched=bool((b["my_snatched"])) 


            book.tags.append(str(b["tags"]))
            book.added=str(b["added"])
            book.bookmarked=str(b["bookmarked"])
            book.browseFlags=int(b["browseflags"])
            book.cat=str(b["cat"])
            book.categoryId=int(b["category"])
            book.category=str(b["catname"])
            book.vip=bool((b["vip"])) 
            book.fl_vip=bool((b["fl_vip"])) 
            book.free=bool((b["free"])) 
            book.main_cat=int(b["main_cat"])
            book.numfiles=int(b["numfiles"])
            book.owner=int(b["owner"])
            book.owner_name=str(b["owner_name"])
            book.personal_fl=str(b["personal_freeleech"])
            book.filetype=str(b["filetype"])

            return book
        else:
            return None       

    def getJSONFastFillOut (self, jff_path=None, jff_template=None):
        #overrides book.jsonFastFillOut by generating one for all books in search
        for book in self.booksFound:
            #print (book.description)
            book.getJSONFastFillOut(jff_path, jff_template)

    def getLinks(self):
        links=[]
        for book in self.booksFound:
            links.append (f"{book.id}")

        return links

    def countByFileType(self, format):
        count=0
        vip=False

        for book in self.booksFound:
            if format in book.filetype.split(" "):
                count += 1
                vip = book.vip
        
        return count, vip