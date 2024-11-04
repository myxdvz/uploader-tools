from dataclasses import dataclass
from dataclasses import field
from pathvalidate import sanitize_filename
from myx_args import Config
from myx_book import Book
from myx_audible import AudibleBook
from myx_libation import LibationBook
from myx_epub import EpubBook
from myx_mam import MAMBook
from myx_tor import TBook
from glob import iglob, glob
from datetime import datetime
import myx_utilities
import httpx
import json
import pprint
import os, subprocess
import csv
import shutil
import time

@dataclass
class Library():
    config:Config
    library:str
    source_path:str=""
    output_path=str=""
    library_file=str=""
    metadata:str=""
    category:str=""
    lastscan:float=0
    files:list[str]=field(default_factory=list)
    upload_files:list[str]=field(default_factory=list)
    libraryCatalog:list[str]=field(default_factory=list)
    libraryBooks={}
    dryRun:bool=False
    verbose:bool=False

    def __post_init__ (self):
        super().__init__()
        if self.config is not None:
            #get information from the Config File
            self.dryRun = bool(self.config.get("Config/flags/dry_run"))
            self.verbose = bool(self.config.get("Config/flags/verbose"))
        

            #important settings for the specified library
            self.files = self.config.get(f"Config/{self.library}/files")
            self.source_path = self.config.get(f"Config/{self.library}/source_path")
            self.output_path = self.config.get(f"Config/{self.library}/output_path")
            self.library_file = self.config.get(f"Config/{self.library}/library_file")
            self.upload_files = self.config.get(f"Config/{self.library}/upload_files")
            self.metadata = self.config.get(f"Config/{self.library}/metadata")
            self.category = self.config.get(f"Config/{self.library}/category")
            self.lastscan = self.config.get(f"Config/{self.library}/last_libraryscan", None)


            #Check if source path exists
            if not os.path.exists(self.source_path):
                raise Exception (f"Libary not found. Please recheck {self.source_path}")

            #if library_file exists, use it as lastscan and backitup
            archive_path = os.path.join (self.output_path, "archive")
            os.makedirs(archive_path, exist_ok=True)
            if os.path.exists(self.library_file):
                archive_name = f"{os.path.splitext(os.path.basename(self.library))[0]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
                shutil.copy2(self.library_file, os.path.join(archive_path, archive_name))
                #last scan is config or if none, last scan date of library file
                if (self.lastscan is None):
                    self.lastscan = os.path.getmtime (self.library_file)

    def scan(self):
        print (f"Scanning {self.files} from {self.library} since {time.localtime(self.lastscan)}...")

        #find all files that fit the pattern
        for f in self.files:
            pattern = f.translate({ord('['):'[[]', ord(']'):'[]]'})
            print (f"Looking for {f} from {self.source_path}")
            #grab all files and put it in libraryBooks
            self.libraryCatalog.extend(iglob(f, root_dir=self.source_path, recursive=True))

        #for each book, grab the metadata, search MAM
        newMetadata=[]
        for entry in self.libraryCatalog:
            #check the last modtime of this file
            entry = os.path.join(self.source_path, entry)
            if os.path.getmtime(entry) > self.lastscan:
                hashkey = myx_utilities.getHash(str(entry))
                if self.verbose: print (f"File: {entry} >> Hash: {hashkey}")

                #check if this book is already in the library
                if hashkey in self.libraryBooks:
                    if self.verbose: print (f"This book is already in the library: {entry}")
                else:
                    if self.verbose: print (f"Adding {entry} into the Catalog using key: {hashkey}")
                    #grab metadata
                    match self.library:
                        case "libation":
                            book = LibationBook(self.config)

                        case "epub":
                            book = EpubBook(self.config)

                        case _:
                            raise Exception (f"{self.library} is an unsupported library")    

                    #load book metadata                
                    if book.getByID (entry):
                        self.libraryBooks[hashkey]={}
                        self.libraryBooks[hashkey]["entry"]=entry    
                        self.libraryBooks[hashkey]["book"]=book

        print (f"Scanned {len(self.libraryCatalog)}, added {len(self.libraryBooks.keys())} in your library")

        if not self.dryRun:
            #Check Library against MAM
            self.__checkMAM__()

        #Export the library
        self.__saveToFile__()

        return self.libraryBooks

    def prep4MAM (self):
        #load all the files from the last Library Scan (set in the config) into the library Catalog
        self.__loadFromFile__()

        #create a torrent for each file in the library catalog
        for file in self.libraryCatalog:
            book = None
            match self.library:
                case "libation": book = LibationBook(self.config)
                case "calibre": book = EpubBook(self.config)
                case _:
                    raise Exception(f"{self.library} library is not yet supported")

            #get book information
            if self.verbose: print (f"Loading book {file} from {self.library}")
            book.getByID (file)

            tbook = TBook(self.config, book, self.library)
            tbook.go() 

        #at this point, all the files have been prep, add then to client
        tbook.add2Client()       


    def __loadFromFile__(self):
        #Load My Audible Library from self.library
        lib_csv = self.library_file
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


    def __saveToFile__ (self):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))

        lib_csv = self.library_file
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

    def __checkMAM__(self):
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
        book["id"]=str(libraryBook["book"].id)
        book["isbn"]=str(libraryBook["book"].isbn)
        book["asin"]=str(libraryBook["book"].asin)
        book["title"]=libraryBook["book"].title
        book["subtitle"]=libraryBook["book"].subtitle
        book["series"]=libraryBook["book"].__getSeries__()
        book["authors"]=libraryBook["book"].__getAuthors__()
        book["narrators"]=libraryBook["book"].__getNarrators__()
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
