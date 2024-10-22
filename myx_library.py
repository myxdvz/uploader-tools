from dataclasses import dataclass
from dataclasses import field
from pathvalidate import sanitize_filename
from myx_args import Config
from myx_book import Book
from myx_libation import LibationBook
from glob import iglob, glob
import myx_utilities
import httpx
import json
import pprint
import os, subprocess
import csv

@dataclass
class Library():
    config:Config=None
    library:str=""
    libraryCatalog:list[str]= field(default_factory=list)
    libaryBooks={}


    def loadFromFile(self, lib_csv):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))

        #Load My Audible Library from self.library
        if os.path.exists(lib_csv):        
            with open(lib_csv, newline="", errors='ignore', encoding='utf-8',) as csv_file:
                try:
                    i = 1
                    fields=self.__getLogHeaders__()    
                    reader = csv.DictReader(csv_file, fieldnames=fields)
                    for row in reader:
                        ##Create a new Book
                        #print (f"Reading row {i}")
                        if (i > 1):
                            f = str(row["file"])

                            self.libraryCatalog.append(f)                    
                        i += 1

                except csv.Error as e:
                    print(f"Error loading library {lib_csv}: {e}") 
        else:
            print (f"Library doesn't exist: {lib_csv}")


    def __getLogHeaders__(self):
        headers=['book', 'file', 'paths', 'isMatched', 'isHardLinked', 'mamCount', 'audibleMatchCount', 'metadatasource', 'id3-matchRate', 'id3-asin', 'id3-title', 'id3-subtitle', 'id3-publisher', 'id3-length', 'id3-duration', 'id3-series', 'id3-authors', 'id3-narrators', 'id3-seriesparts', 'id3-language', 'mam-matchRate', 'mam-asin', 'mam-title', 'mam-subtitle', 'mam-publisher', 'mam-length', 'mam-duration', 'mam-series', 'mam-authors', 'mam-narrators', 'mam-seriesparts', 'mam-language', 'adb-matchRate', 'adb-asin', 'adb-title', 'adb-subtitle', 'adb-publisher', 'adb-length', 'adb-duration', 'adb-series', 'adb-authors', 'adb-narrators', 'adb-seriesparts', 'adb-language', 'sourcePath', 'mediaPath']
                        
        return dict.fromkeys(headers)

    def scan(self, library, filePattern=["**/*.m4b"]):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))

        print (f"Scanning {filePattern} from {library}...")
        #if os.path.exists(library):
        #set library root path
        self.libary = library

        #find all files that fit the pattern
        for f in filePattern:
            pattern = f.translate({ord('['):'[[]', ord(']'):'[]]'})
            print (f"Looking for {f} from {library}")
            #grab all files and put it in libraryBooks
            self.libraryCatalog.extend(iglob(f, root_dir=library, recursive=True))

        #for each book, grab the metadata, search MAM
        for entry in self.libraryCatalog:
            print (f"Adding {entry} into the Catalog")
            if not dryRun:
                #grab metadata
                book = LibationBook(self.config)
                book.getByID (entry)

                #add in libraryBoks
                key = myx_utilities.getHash(book.source_path)
                self.libraryBooks[key]=book

        #generate a csv file

        return

    def sanitize(self, library):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))
        badFiles=[]

        if os.path.exists(library):
            #set library root path
            self.libary = library

            for dir, subdirs, files in os.walk(library):
                for f in files:
                    if (f != sanitize_filename(f)):
                        if verbose: print (f"Renaming {os.path.join(dir, f)} to {os.path.join(dir, sanitize_filename(f))}")
                        badFiles.append (f)
                        if not dryRun:
                            os.rename(os.path.join(dir, f), os.path.join(dir, sanitize_filename(f)))      

        return badFiles

    def exportLibrary(self, lib_path=""):
        outputPath = self.config.get("Config/output")

        write_headers = not os.path.exists(logFilePath)
        with open(logFilePath, mode="a", newline="", errors='ignore') as csv_file:
            try:
                for f in bookFiles:
                    #get book records to log
                    if (f.isMatched):
                        row=f.getLogRecord(f.audibleMatch, cfg)
                    else:
                        row=f.getLogRecord(f.ffprobeBook, cfg)
                    #get fieldnames
                    row["matches"]=len(f.audibleMatches)
                    fields=row.keys()

                    #create a writer
                    writer = csv.DictWriter(csv_file, fieldnames=fields)
                    if write_headers:
                        writer.writeheader()
                        write_headers=False
                    writer.writerow(row)

            except csv.Error as e:
                print(f"file {logFilePath}: {e}")