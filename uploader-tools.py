import myx_args
import myx_book
import myx_utilities
import pprint
import os, sys, subprocess, shlex, re

def createJsonFastFill(cfg):
    books=myx_args.params.book
    metadata=cfg.get("Config/metadata")
    output=cfg.get("Config/output_path")
    dryRun=cfg.get("Config/flags/dry_run")
    verbose=cfg.get("Config/flags/verbose")

    for bookid in books.split(","):
        match metadata:
            case "file":
                #yaml file
                book = myx_book.YamlBook()

            case "google":
                #googlebooks api
                book = myx_book.GoogleBook()

            case _:
                #default is audible
                book = myx_book.AudibleBook()

        #pass config file
        book.config = cfg
        #get book information
        if verbose: print (f"Loading book {bookid} from {metadata}")
        book.getByID(bookid)

        if len(book.id):
            #generating JsonFastFilleout file
            jsonFile = f"{metadata}-{book.id}"
            if verbose: print (f"Generating JsonFastFill file {os.path.join (output, jsonFile)}")
            book.getJSONFastFillOut(output, jsonFile)

def createTorrent(cfg):
    metadata=cfg.get("Config/metadata")
    output=cfg.get("Config/output_path")
    dryRun=cfg.get("Config/flags/dry_run")
    verbose=cfg.get("Config/flags/verbose")


    print (f"Creating Torrent File from {folder}")
    #check if source folder exists
    if os.path.exists(source):
        #myx_utilities.createTorrent())
        return

def main(cfg):
    action=myx_args.params.action
    metadata=cfg.get("Config/metadata")
    output=cfg.get("Config/output_path")
    dryRun=cfg.get("Config/flags/dry_run")
    verbose=cfg.get("Config/flags/verbose")

    #assume all parameters are from command line
    if verbose: print (f"Action: {action}, Dry Run: {dryRun}, Verbose: {verbose}")

    match action:
        case "createJson":
            #uploader-tools createJson --book [IDs, files] --source [audible, file]
            createJsonFastFill(cfg)

        case "createTorrent":
            #uploader-tools createTorrent --book [IDs, files] --source [audible, file] --input [path/to/files]
            #createTorrent(cfg)
            print (f"This feature is still in testing... coming soon!")

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
