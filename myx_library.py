from dataclasses import dataclass
from dataclasses import field
from pathvalidate import sanitize_filename
from myx_args import Config
from myx_book import Book
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
    libraryBooks:list[str]= field(default_factory=list)

    def load(self):
        dryRun = bool(self.config.get("Config/flags/dry_run"))
        verbose = bool(self.config.get("Config/flags/verbose"))

        #Load My Audible Library from self.library
        if os.path.exists(self.library):        
            with open(self.library, newline="", errors='ignore', encoding='utf-8',) as csv_file:
                try:
                    i = 1
                    fields=self.__getLogHeaders__()    
                    reader = csv.DictReader(csv_file, fieldnames=fields)
                    for row in reader:
                        ##Create a new Book
                        #print (f"Reading row {i}")
                        if (i > 1):
                            f = str(row["file"])

                            self.libraryBooks.append(f)                    
                        i += 1

                except csv.Error as e:
                    print(f"Error loading library {self.library}: {e}") 
        else:
            print (f"Library doesn't exist: {self.library}")


    def __getLogHeaders__(self):
        headers=['book', 'file', 'paths', 'isMatched', 'isHardLinked', 'mamCount', 'audibleMatchCount', 'metadatasource', 'id3-matchRate', 'id3-asin', 'id3-title', 'id3-subtitle', 'id3-publisher', 'id3-length', 'id3-duration', 'id3-series', 'id3-authors', 'id3-narrators', 'id3-seriesparts', 'id3-language', 'mam-matchRate', 'mam-asin', 'mam-title', 'mam-subtitle', 'mam-publisher', 'mam-length', 'mam-duration', 'mam-series', 'mam-authors', 'mam-narrators', 'mam-seriesparts', 'mam-language', 'adb-matchRate', 'adb-asin', 'adb-title', 'adb-subtitle', 'adb-publisher', 'adb-length', 'adb-duration', 'adb-series', 'adb-authors', 'adb-narrators', 'adb-seriesparts', 'adb-language', 'sourcePath', 'mediaPath']
                        
        return dict.fromkeys(headers)
