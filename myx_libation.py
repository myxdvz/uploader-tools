from myx_audible import AudibleBook
import myx_utilities
import httpx
import json
import os

class LibationBook(AudibleBook):
    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="libation"
    
    def getByID (self, id=""):
        #id is the path of the m4b file in the libation download folder
        print (f"Getting metadata for \n\tLibation Book:{id}")

        #parse path and filename
        self.source_path = os.path.dirname(id)
        self.filename = os.path.splitext(os.path.basename(id))[0]

        #metadata path
        self.metadataJson = os.path.join (self.source_path, self.filename + ".metadata.json")

        if os.path.exists(self.metadataJson):
            print (f"Loading metadata from \n\tMetadata Json:{self.metadataJson}")
            product={}
            try:
                #load book info from metadata.json file
                with open(self.metadataJson, mode='r', encoding='utf-8') as file:
                    f = file.read()
            
                product=json.loads(f)

            except Exception as e:
                print(f"Error loading metadata.json: {e}")

            #check for ["product"]
            self.__dic2Book__(product)
            self.id=self.asin

        else:
            print(f"Metadata file {self.metadata}, not found")

        return self
