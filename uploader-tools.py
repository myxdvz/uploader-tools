from myx_audible import AudibleBook
from myx_google import GoogleBook
from myx_yaml import YamlBook
from myx_libation import LibationBook
from myx_tor import TBook
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

def main(cfg):
    action=myx_args.params.action
    books=myx_args.params.book
    dryRun=cfg.get("Config/flags/dry_run")
    verbose=cfg.get("Config/flags/verbose")

    #assume all parameters are from command line
    if verbose: print (f"Action: {action}, Books: {books}, Dry Run: {dryRun}, Verbose: {verbose}")

    match action:
        case "createJson":
            #uploader-tools createJson --book [IDs, files]
            createJsonFastFill(cfg, books)

        case "createTorrent":
            #uploader-tools createTorrent --book [IDs, files]
            createTorrent(cfg, books)

        case _:
            print ("Please select from the following actions: createJson, createTorrent")


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
