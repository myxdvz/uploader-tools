from myx_audible import AudibleBook
from myx_google import GoogleBook
from myx_yaml import YamlBook
from myx_libation import LibationBook
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

        case _:
            #default is audible
            book = AudibleBook(cfg)

    #get book information
    if verbose: print (f"Loading book {bookid} from {metadata}")
    book.getByID(bookid)

    return book

def createJsonFastFill(cfg, books):
    for bookid in books:    
        book = loadBook(cfg, bookid)

        if len(book.id):
            book.getJSONFastFillOut()

    return

def createTorrent(cfg, books):
    for bookid in books:
        book = loadBook(cfg, bookid)
        tbook = TBook(cfg, book)
        tbook.go()

    return

def mylib2mam(cfg, books):
    #books is a path to a log with all the books that needs to be processed
    for book in books:
        #load books from my library
        myLib = Library(cfg, book)
        myLib.loadFromFile(book)

        #create a torrent for each file in the library
        for file in myLib.libraryCatalog:
            book = loadBook(cfg, file)
            tbook = TBook(cfg, book)
            tbook.go()        

def scanLibrary(cfg, books):
    dryRun = bool(cfg.get("Config/flags/dry_run"))
    verbose = bool(cfg.get("Config/flags/verbose"))
    
    #books is a path to the libation/library root
    myLib = Library(cfg)

    for book in books:
        #scan books from my library
        myLib.scan(book)
        print (f"Found {len(myLib.libraryCatalog)} in your library at {book}")

def sanitizeLibrary(cfg, books):
    dryRun = bool(cfg.get("Config/flags/dry_run"))
    verbose = bool(cfg.get("Config/flags/verbose"))
    
    #books is a path to the libation/library root
    myLib = Library(cfg)

    for book in books:
        #scan books from my library
        badFiles = myLib.sanitize(book)
        print (f"Found {len(badFiles)} badly named files in your library at {book}")


def main(cfg):
    action=myx_args.params.action
    books=myx_args.params.book
    dryRun=cfg.get("Config/flags/dry_run")
    verbose=cfg.get("Config/flags/verbose")

    #assume all parameters are from command line
    if verbose: print (f"Action: {action}, Books: {books}, Dry Run: {dryRun}, Verbose: {verbose}")

    match action:
        case "createJson":
            #creates a Json file for the passed books
            #uploader-tools createJson --book [IDs, files]
            createJsonFastFill(cfg, books)

        case "createTorrent":
            #performs all steps in the torrent creation process (steps in config) for a list of books
            #uploader-tools createTorrent --book [IDs, files]
            createTorrent(cfg, books)

        case "mylib2mam":
            #performs all steps in the torrent creation process for all books in the passed library file
            mylib2mam(cfg, books)

        case "scanLibrary":
            #scans your library -- and then what?
            scanLibrary(cfg, books)

        case "sanitizeLibrary":
            #scans your library -- and then what?
            sanitizeLibrary(cfg, books)

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
