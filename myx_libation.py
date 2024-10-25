from pathvalidate import sanitize_filename
from myx_audible import AudibleBook
import myx_utilities
import httpx
import json
import os, re

class LibationBook(AudibleBook):
    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="libation"
    
    def getByID (self, id=""):
        #flags
        dry_run=bool(self.config.get("Config/flags/dry_run"))
        verbose=bool(self.config.get("Config/flags/verbose"))

        #id is the path of the m4b file in the libation download folder
        if verbose: print (f"Getting metadata for \n\tLibation Book:{id}")

        #parse path and filename
        self.source_path = os.path.dirname(id)
        self.filename = os.path.splitext(os.path.basename(id))[0]

        #metadata path
        self.metadataJson = os.path.join (self.source_path, sanitize_filename(self.filename) + ".metadata.json")

        if os.path.exists(self.metadataJson):
            if verbose: print (f"Loading metadata from \n\tMetadata Json:{self.metadataJson}")
            product={}
            try:
                #load book info from metadata.json file
                with open(self.metadataJson, mode='r', encoding='utf-8') as file:
                    f = file.read()
            
                product=json.loads(f)

            except Exception as e:
                print(f"Error loading metadata.json: {e}")

            #check for ["product"]
            self.json=product
            self.__dic2Book__(product)
            self.id=self.asin

            return self

        else:
            print(f"Metadata file {self.metadata}, not found")
            return None

    def getAsin(self, filename):
        #derive asin from the filename, formatted *[asin].m4b
        match = re.search(r"\[(?P<asin>[a-zA-Z0-9]+)\]",filename, re.IGNORECASE)
        if match:
            return match.groupdict()["asin"]
        else:
            return None



        