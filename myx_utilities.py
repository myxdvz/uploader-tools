from langcodes import *
import hashlib
import json, os

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

def createTorrent (cfg, book, directory, filename):
    verbose = cfg.get("Config/flags/verbose")
    announceURL = cfg.get("Config/library/announce")
    torrent_path = cfg.get("Config/library/torrent_path")
    torrent_file = os.path.join(torrent_path, filename + ".torrent")

    #py3createtorrent -t udp://tracker.opentrackr.org:1337/announce file_or_folder
    cmnd = ['py3createtorrent','--private', '--force', '--tracker', announceURL, directory, '--output', torrent_file]
    if verbose: print (f"Running: {cmnd}")
    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err =  p.communicate()
    pprint(out)
    pprint(err)

    #generate the mam json file for easy upload
    mamBook = {
        "authors": [book.getAuthors()],
        "description": book.description,
        "narrators": [book.getNarrators()],
        "tags": f"Duration: {book.length} min | Chapterized | Libation True Decrypt | Audible Release: {book.releaseDate} | Publisher: {book.publisher} | {book.genres}",
        "thumbnail": "",
        "title": book.title,
        "language": book.language,
        "series": [],
        "category": "Audibooks - General Fiction"
    } 
    #Set series
    for s in book.series:
        mamBook["series"].append({name: s.name, number: s.part})

    json_file = os.path.join(torrent_path, filename + ".json")
    with open(json_file, mode='w', encoding='utf-8') as file:
        json.dump(mamBook, file)    

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
