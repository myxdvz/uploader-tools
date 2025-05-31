from pathvalidate import sanitize_filename
from myx_audible import AudibleBook
import myx_utilities
import httpx
import json
import os, re

class LibbyBook(AudibleBook):
    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="libby"
    
    def getByID (self, id=""):
        #flags
        dry_run=bool(self.config.get("Config/flags/dry_run"))
        verbose=bool(self.config.get("Config/flags/verbose"))

        #id is the path of the m4b file in the libation download folder
        if verbose: print (f"Getting metadata for \n\tLibby Book:{id}")

        #id is the path to the libby folder
        self.id = id 
        
        #parse path and filename
        self.source_path = id

        #libby filename is empty, instead it has a list of files
        self.filename = ""
        for f in sorted(os.listdir(id)):
            if f.endswith (".mp3"):
                self.files.append(f)

        #metadata path - max 255
        self.metadataJson = self.getMetadataJsonFilename()

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

            return True

        else:
            #metadata was not found, query audible instead
            asin = self.getAsin(self.filename)
            audibleBook = AudibleBook(self.config)
            audibleBook.getByID (asin)
            if not dry_run:
                audibleBook.export (self.metadataJson)
            
            self = audibleBook
            return True
    
    def getAsin(self, filename):
        #derive asin from the filename, formatted *[asin].m4b
        match = re.search(r"\[(?P<asin>[a-zA-Z0-9]+)\]",filename, re.IGNORECASE)
        if match:
            return match.groupdict()["asin"]
        else:
            return None

    def getMetadataJsonFilename(self):
        #filename = self.source_path, sanitize_filename(self.filename) + ".metadata.json"
        filename = os.path.join(self.source_path, "metadata", "metadata.json")
        print (f"Metadata: {filename}")

        return filename

    def __dic2Book__(self, book):
        #book is an Overdrive/Libby product dictionary
        if book is not None:
            #if 'asin' in book: self.asin=str(book["asin"])
            if 'title' in book: self.title=str(book["title"])
            if 'description' in book: self.description=str(book["description"]["full"])
            if 'coverUrl' in book: self.cover=str(book["coverUrl"])
            if 'creator' in book:
                for author in book["creator"]:
                    if author["role"] == "author":
                        self.authors.append(str(author["name"]))
                    elif author["role"] == "narrator":
                        self.narrators.append(str(author["name"]))
            if 'spine' in book:
                duration=0
                for chapters in book["spine"]:
                    duration += float(chapters["duration"])

                self.length=int(duration/60)

            return self
        else:
            return None       

    def __getMamTags__ (self, delimiter="|"):
        return f"Duration: {self.__convert_to_hours_minutes__(self.length)} | Chapterized | Libby | Release Date: {self.releaseDate} | Publisher: {self.publisher} | {','.join(set(self.genres))}"

        