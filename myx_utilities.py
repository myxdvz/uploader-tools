from langcodes import *
import hashlib
import json, os, re
import mimetypes
import unicodedata

def getMAMCategories():
    categories = [
        "# Audiobooks - Action/Adventure",
        "# Audiobooks - Art",
        "# Audiobooks - Biographical",
        "# Audiobooks - Business",
        "# Audiobooks - Computer/Internet",
        "# Audiobooks - Crafts",
        "# Audiobooks - Crime/Thriller",
        "# Audiobooks - Fantasy",
        "# Audiobooks - Food",
        "# Audiobooks - General Fiction",
        "# Audiobooks - General Non-Fic",
        "# Audiobooks - Historical Fiction",
        "# Audiobooks - History",
        "# Audiobooks - Home/Garden",
        "# Audiobooks - Horror",
        "# Audiobooks - Humor",
        "# Audiobooks - Instructional",
        "# Audiobooks - Juvenile",
        "# Audiobooks - Language",
        "# Audiobooks - Literary Classics",
        "# Audiobooks - Math/Science/Tech",
        "# Audiobooks - Medical",
        "# Audiobooks - Mystery",
        "# Audiobooks - Nature",
        "# Audiobooks - Philosophy",
        "# Audiobooks - Pol/Soc/Relig",
        "# Audiobooks - Recreation",
        "# Audiobooks - Romance",
        "# Audiobooks - Science Fiction",
        "# Audiobooks - Self-Help",
        "# Audiobooks - Travel/Adventure",
        "# Audiobooks - True Crime",
        "# Audiobooks - Urban Fantasy",
        "# Audiobooks - Western",
        "# Audiobooks - Young Adult",
        "# E-books - Action/Adventure",
        "# E-books - Art",
        "# E-books - Biographical",
        "# E-books - Business",
        "# E-books - Comics/Graphic novels",
        "# E-books - Computer/Internet",
        "# E-books - Crafts",
        "# E-books - Crime/Thriller",
        "# E-books - Fantasy",
        "# E-books - Food",
        "# E-books - General Fiction",
        "# E-books - General Non-Fic",
        "# E-books - Historical Fiction",
        "# E-books - History",
        "# E-books - Home/Garden",
        "# E-books - Horror",
        "# E-books - Humor",
        "# E-books - Illusion/Magic",
        "# E-books - Instructional",
        "# E-books - Juvenile",
        "# E-books - Language",
        "# E-books - Literary Classics",
        "# E-books - Magazines/Newspapers",
        "# E-books - Math/Science/Tech",
        "# E-books - Medical",
        "# E-books - Mixed Collections",
        "# E-books - Mystery",
        "# E-books - Nature",
        "# E-books - Philosophy",
        "# E-books - Pol/Soc/Relig",
        "# E-books - Recreation",
        "# E-books - Romance",
        "# E-books - Science Fiction",
        "# E-books - Self-Help",
        "# E-books - Travel/Adventure",
        "# E-books - True Crime",
        "# E-books - Urban Fantasy",
        "# E-books - Western",
        "# E-books - Young Adult",
        "# Musicology - Guitar/Bass Tabs",
        "# Musicology - Individual Sheet",
        "# Musicology - Individual Sheet MP3",
        "# Musicology - Instructional Book with Video",
        "# Musicology - Instructional Media - Music",
        "# Musicology - Lick Library - LTP/Jam With",
        "# Musicology - Lick Library - Techniques/QL",
        "# Musicology - Music - Complete Editions",
        "# Musicology - Music Book",
        "# Musicology - Music Book MP3",
        "# Musicology - Sheet Collection",
        "# Musicology - Sheet Collection MP3",
        "# Radio - Comedy",
        "# Radio - Drama",
        "# Radio - Factual/Documentary",
        "# Radio - Reading"
    ]

    return categories

def getList(items, delimiter=",", encloser="", stripaccents=True):
    enclosedItems=[]
    for item in items:
        if type(item) == myx_classes.Contributor:
            enclosedItems.append(f"{encloser}{cleanseAuthor(item.name)}{encloser}")
        else:
            if type(item) == myx_classes.Series:
                enclosedItems.append(f"{encloser}{cleanseSeries(item.name)}{encloser}")
            else:
                enclosedItems.append(f"{encloser}{item.name}{encloser}")

    return delimiter.join(enclosedItems)

def getLanguage(code):
    lang = "English"
    try: 
        lang = Language.get(code).display_name()

    except:
        print ("Unable to get display name for Language: {code}, defaulting to English")
    
    return lang

def getHash(key):
    return hashlib.sha256(key.encode(encoding="utf-8")).hexdigest()

def getCachePath(cfg):
    #make sure log_path exists
    cache_path=cfg.get("Config/cache_path")

    if (cache_path is None) or (len(cache_path)==0):
        cache_path=os.path.join(os.getcwd(),"logs")        

    #build __cache__ folders if they don't exist
    os.makedirs(os.path.join(cache_path, "__cache__", "audible"), exist_ok=True)
    os.makedirs(os.path.join(cache_path, "__cache__", "google"), exist_ok=True)

    return cache_path

def isCached(cfg, key, category):
    #Config
    verbose = bool(cfg.get("Config/flags/verbose"))

    if verbose:
        print (f"Checking cache: {category}/{key}...")
    
    #Check if this book's hashkey exists in the cache, if so - it's been processed
    bookFile = os.path.join(getCachePath(cfg), "__cache__", category, key)
    found = os.path.exists(bookFile)  
    return found      
    
def cacheMe(cfg, key, category, content):
    #Config
    verbose = bool(cfg.get("Config/flags/verbose"))

    #create the cache file
    bookFile = os.path.join(getCachePath(cfg), "__cache__", category, key)
    with open(bookFile, mode="w", encoding='utf-8', errors='ignore') as file:
        file.write(json.dumps(content, indent=4))

    if verbose:
        print(f"Caching {key} in File: {bookFile}")
    return os.path.exists(bookFile)        

def loadFromCache(cfg, key, category):
    #return the content from the cache file
    bookFile = os.path.join(getCachePath(cfg), "__cache__", category, key)
    with open(bookFile, mode='r', encoding='utf-8') as file:
        f = file.read()
    
    return json.loads(f)

def getApiKey(cfg, source):
    apiKey=cfg.get(f"Config/sources/{source}ApiKey")

    if (apiKey is None):
        apiKey=""

    return apiKey

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                    if unicodedata.category(c) != 'Mn')

def cleanseAuthor(author):
    #remove some characters we don't want on the author name
    stdAuthor=strip_accents(author)

    #remove some characters we don't want on the author name
    for c in ["- editor", "- contributor", " - ", "'"]:
        stdAuthor=stdAuthor.replace(c,"")

    #replace . with space, and then make sure that there's only single space between words)
    stdAuthor=" ".join(stdAuthor.replace("."," ").split())
    return stdAuthor

def cleanseTitle(title="", stripaccents=True, stripUnabridged=False):
    #remove (Unabridged) and strip accents
    stdTitle=str(title)

    for w in [" (Unabridged)", "m4b", "mp3", ",", "- "]:
        stdTitle=stdTitle.replace(w," ")
    
    if stripaccents:
        stdTitle = strip_accents(stdTitle)

    #remove Book X
    stdTitle = re.sub (r"\bBook(\s)?(\d)+\b", "", stdTitle, flags=re.IGNORECASE)

    # remove any subtitle that goes after a :
    stdTitle = re.sub (r"(:(\s)?([a-zA-Z0-9_'\.\s]{2,})*)", "", stdTitle, flags=re.IGNORECASE)

    return stdTitle

def cleanseSeries(series):
    #remove colons
    cleanSeries = series
    for c in [":", "'"]:
        cleanSeries = cleanSeries.replace (c, "")

    return cleanSeries.strip()

def promptChoice (prompt, choices):
    while True:
        try:
            choice = int (input (f"{prompt}"))
            if choice in choices:
                return choice
            else:
                print ("Invalid choice, try again.")
        except ValueError as e:
            print (f"This is not a valid choice: {e}")
    