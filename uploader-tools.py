from myx_epub import EpubBook
from myx_audible import AudibleBook
from myx_google import GoogleBook
from myx_yaml import YamlBook
from myx_libation import LibationBook
from myx_mam import MAMBook
from myx_tor import TBook
from myx_library import Library
import myx_args
import myx_book
import myx_utilities
import pprint
import os, sys, subprocess, shlex, re

def loadBook(cfg, bookid):
    metadata=cfg.get("Config/metadata")
    output=cfg.get("Config/output_path")
    dryRun=cfg.get("Config/flags/dry_run")
    verbose=cfg.get("Config/flags/verbose")

    match metadata:
        case "file":
            #yaml file
            book = YamlBook(cfg)

        case "google":
            #googlebooks api
            book = GoogleBook(cfg)

        case "libation":
            #googlebooks api
            book = LibationBook(cfg)

        case "mam":
            #MAM api
            book = MAMBook(cfg)

        case "epub":
            #MAM api
            book = EpubBook(cfg)

        case _:
            #default is audible
            book = AudibleBook(cfg)

    #get book information
    if verbose: print (f"Loading book {bookid} from {metadata}")
    book.getByID(bookid)

    return book

def createJson(cfg, books):
    for bookid in books:    
        book = loadBook(cfg, bookid)
        book.getJSONFastFillOut()

    return

def createTorrent(cfg, books):
    for book in books:
        tbook = TBook(cfg, book)
        tbook.createTorrent(book)
        tbook.add2Client()

    return

def prep4upload(cfg, books):
    for bookid in books:
        book = loadBook(cfg, bookid)
        tbook = TBook(cfg, book)
        tbook.go()

    return

def mylib2mam(cfg, libraries):
    #books is a path to a library file with all the books that needs to be processed
    for library in libraries:
        #load books from my library
        myLib = Library(cfg, library)
        myLib.prep4MAM()

def scanLibrary(cfg, books):
    dryRun = bool(cfg.get("Config/flags/dry_run"))
    verbose = bool(cfg.get("Config/flags/verbose"))
    
    for book in books:
        #books is a path to the libation/library root
        myLib = Library(cfg, book)

        #scan books from my library
        myLib.scan()

def sanitizeLibrary(cfg, books):
    dryRun = bool(cfg.get("Config/flags/dry_run"))
    verbose = bool(cfg.get("Config/flags/verbose"))
    
    #books is a path to the libation/library root
    myLib = Library(cfg)

    for book in books:
        #scan books from my library
        badFiles = myLib.sanitize(book)
        print (f"Found {len(badFiles)} badly named files in your library at {book}")

def query (cfg, params):
    metadata=cfg.get("Config/metadata")
    output=cfg.get("Config/output")
    verbose=bool(cfg.get("Config/flags/verbose"))

    #query supports id, title and author parameters
    parameters={}

    for param in params:
        #parse the key value pair
        parameters[param.split("=")[0]]=param.split("=")[1]

    match metadata:
        case "file":
            #yaml file
            book = YamlBook(cfg)

        case "google":
            #googlebooks api
            book = GoogleBook(cfg)

        case "libation":
            #googlebooks api
            book = LibationBook(cfg)

        case "mam":
            #MAM api
            book = MAMBook(cfg)

        case "epub":
            #MAM api
            book = EpubBook(cfg)

        case _:
            #default is audible
            book = AudibleBook(cfg)

    #get book information
    if verbose: print (f"Querying {metadata} using {parameters}")   
    
    if book.query(parameters) and (output == "jff"):
        book.getJSONFastFillOut()
        
    return book
    

def main(cfg):
    action=myx_args.params.action
    params=myx_args.params.params
    dryRun=cfg.get("Config/flags/dry_run")
    verbose=cfg.get("Config/flags/verbose")

    #assume all parameters are from command line
    if verbose: print (f"Action: {action}, Params: {params}, Dry Run: {dryRun}, Verbose: {verbose}")

    match action:
        case "query":
            query (cfg, params)

        case "createJson":
            #creates a Json file for the passed books
            #--book is a list of ISBN, ASIN or Yaml Files
            createJson(cfg, params)

        case "createTorrent":
            #creates a Torrent file from a folder
            #--book is a list of paths to upload folder
            createTorrent(cfg, params)

        case "prep4upload":
            #performs all steps in the torrent creation process (steps in config) for a list of books
            #--book is a list of M4B files from source, e.g. libation folder
            prep4upload(cfg, params)

        case "mylib2mam":
            #performs all steps in the torrent creation process for all books in the passed library file
            #--book is path to a CSV file that has a list of M4B paths, sames a prep4upload with a file input
            mylib2mam(cfg, params)

        case "scanLibrary":
            #scans your library -- and then what?
            scanLibrary(cfg, params)

        case "sanitizeLibrary":
            #scans your library -- and sanitizes filenames (removes colons)
            #--book is a root path
            sanitizeLibrary(cfg, params)

        case _:
            print ("Invalid action...")


if __name__ == "__main__":
    if not sys.version_info > (3, 10):
        print ("uploader-tools require python 3.10 or higher. Please upgrade your version")
    else:
        #process commandline arguments
        myx_args.params = myx_args.importArgs()

        #check if config files are present
        settingsConfig = "config/settings.json"
        if (os.path.exists(settingsConfig)):
            try:
                #import config
                cfg = myx_args.Config(settingsConfig, myx_args.params)

            except Exception as e:
                raise Exception(f"\nThere was a problem reading your config file {settingsConfig}: {e}\n")
            
            #start the program
            main(cfg)

        else:
            print(f"\nYour config path is invalid. Please check and try again!\n\tConfig file path:{settingsConfig}\n")
