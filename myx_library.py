from dataclasses import dataclass
from dataclasses import field
from pathvalidate import sanitize_filename
from myx_args import Config
from myx_book import Book
from myx_audible import AudibleBook
from myx_libation import LibationBook
from myx_mam import MAMBook
from glob import iglob, glob
from datetime import datetime
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
    libraryBooks={}

    def loadFromFile(self, lib_csv):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))

        #Load My Audible Library from self.library
        if os.path.exists(lib_csv):        
            with open(lib_csv, newline="", errors='ignore', encoding='utf-8',) as csv_file:
                try:
                    i = 1
                    fields=self.__getHeaders__()    
                    reader = csv.DictReader(csv_file, fieldnames=fields)
                    for row in reader:
                        ##Create a new Book
                        #print (f"Reading row {i}")
                        if (i > 1):
                            f = str(row["entry"])

                            self.libraryCatalog.append(f)                    
                        i += 1

                except csv.Error as e:
                    print(f"Error loading library {lib_csv}: {e}") 
        else:
            print (f"Library doesn't exist: {lib_csv}")


    def saveToFile (self, lib_csv=""):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))
        output_path = self.config.get("Config/output_path")

        if (len(lib_csv) == 0):
            lib_csv = os.path.join (output_path,f"mylibrary_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv")

        if len(self.libraryBooks.keys()):
            write_headers = not os.path.exists(lib_csv)
            with open(lib_csv, mode="a", newline="", errors='ignore') as csv_file:
                try:
                    fields=self.__getHeaders__()
                    #pprint (fields)
                    for book in self.libraryBooks.values():
                        row = self.__getItemDictionary__(book)
                        #pprint(row)
                        #create a writer
                        writer = csv.DictWriter(csv_file, fieldnames=fields)
                        if write_headers:
                            writer.writeheader()
                            write_headers=False
                        writer.writerow(row)

                except csv.Error as e:
                    print(f"file {logFilePath}: {e}")

            print (f"Saved your library to: {lib_csv}")

        else:
            print (f"Library doesn't exist: {lib_csv}")

    def scan(self, library, lastscan=0, filePattern=["**/*.m4b"]):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))

        print (f"Scanning {filePattern} from {library} since {lastscan}...")
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
        newMetadata=[]
        for entry in self.libraryCatalog:
            #check the last modtime of this file
            entry = os.path.join(library, entry)
            if os.path.getmtime(entry) > lastscan:
                hashkey = myx_utilities.getHash(str(entry))
                if verbose: print (f"File: {entry} >> Hash: {hashkey}")

                #check if this book is already in the library
                if hashkey in self.libraryBooks:
                    if verbose: print (f"This book is already in the library: {entry}")
                else:
                    if verbose: print (f"Adding {entry} into the Catalog using key: {hashkey}")
                    #grab metadata
                    book = LibationBook(self.config)
                    #get ASIN from the file name
                    asin = book.getAsin(entry)
                    #load book metadata                
                    if book.getByID (entry):
                        #add this book in the library, if NOT a podcast
                        if (book.contentType != "Podcast"):
                            self.libraryBooks[hashkey]={}
                            self.libraryBooks[hashkey]["entry"]=entry    
                            self.libraryBooks[str(hashkey)]["book"]=book
                        else:
                            print (f"{entry} is a podcast... skipping")
                    else:
                        #no metadata information found, create one
                        newMetadata.append(entry)
                        audibleBook = AudibleBook(self.config)
                        audibleBook.getByID (asin)
                        prefix=""
                        if not dryRun:
                            audibleBook.export (book.metadataJson)
                        else:
                            prefix = "[Dry Run] - "
                        print (f"{prefix}Creating new metadata.json for {entry}")
                        if (audibleBook.contentType != "Podcast"):
                            self.libraryBooks[hashkey]={}
                            self.libraryBooks[hashkey]["entry"]=entry    
                            self.libraryBooks[str(hashkey)]["book"]=audibleBook
                        else:
                            print (f"{entry} is a podcast... skipping")

        print (f"Scanned {len(self.libraryCatalog)}, added {len(self.libraryBooks.keys())} in your library, created {len(newMetadata)} new metadata.json files")

        if not dryRun:
            #Check Library against MAM
            self.checkMAM()

        #Export the library
        self.saveToFile()

        return self.libraryBooks

    def checkMAM(self):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))

        #for each audible/libation book in the libraryBooks
        for lb in self.libraryBooks.values():
            mamBook = MAMBook(self.config)
            #do a MAM search based on author, title, extension
            title=lb["book"].__cleanseTitle__()
            ext=lb["book"].extension

            authors=lb["book"].__getAuthors__(delimiter='|', encloser='"')
            if len(lb["book"].authors) > 1:
                authors = f"({authors})"

            series=lb["book"].__getSeries__(delimiter='|', encloser='"')
            if len(lb["book"].series) > 1:
                series = f"({series})"

            #Matching my book with MAM
            search = f"{authors} {title}"
            lb["cleansed-authors"]=authors
            lb["cleansed-title"]=title
            lb["cleansed-series"]=series

            if not lb["book"].__isForbiddenAuthor__():
                try:
                    if verbose: print (f"MAM search: {search}...")
                    mamBook.search (search)
                    #save MAM search
                    lb["mam"] = mamBook
                except Exception as e:
                    if verbose: print (f"Encountered error searching {search}: {e}")

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


    def __getHeaders__(self):
        headers=['entry', 'content_type', 'id', 'isbn',  'asin',  'title',  'subtitle', 'series', 'authors',  'narrators',  'cleansed-title',  'cleansed-authors',  'cleansed-series',  'mam-count', 'mam-links']
        for format in ["m4b", "mp3", "epub"]:
            headers.append(f"mam-count-{format}")
            headers.append(f"mam-vip-{format}")
        return dict.fromkeys(headers)

    def __getItemDictionary__ (self, libraryBook):
        #library book information
        book={}
        book["entry"]=libraryBook["entry"]
        book["content_type"]=libraryBook["book"].contentType
        book["id"]=libraryBook["book"].id
        book["isbn"]=libraryBook["book"].isbn
        book["asin"]=libraryBook["book"].asin
        book["title"]=libraryBook["book"].title
        book["subtitle"]=libraryBook["book"].subtitle
        book["series"]=libraryBook["book"].series
        book["authors"]=libraryBook["book"].authors
        book["narrators"]=libraryBook["book"].narrators
        #calclated fields
        book["cleansed-title"]=libraryBook["cleansed-title"]
        book["cleansed-authors"]=libraryBook["cleansed-authors"]
        book["cleansed-series"]=libraryBook["cleansed-series"]
        #mam book information
        if "mam" in libraryBook: 
            book["mam-count"]=libraryBook["mam"].found
            for format in ["m4b", "mp3", "epub"]:
                book[f"mam-count-{format}"], book[f"mam-vip-{format}"]=libraryBook["mam"].countByFileType(format)
            book["mam-links"]=libraryBook["mam"].getLinks()
        else: 
            book["mam-count"]=-1
            for format in ["m4b", "mp3", "epub"]:
                book[f"mam-count-{format}"]=-1
                book[f"mam-vip-{format}"]=False
            book["mam-links"]="None"

        return book  
