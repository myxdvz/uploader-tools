from dataclasses import dataclass
from dataclasses import field
from pathvalidate import sanitize_filename
from myx_args import Config
import unicodedata
import myx_utilities
import pprint
import json
import os, re

@dataclass
class Book:
    #Series Class
    @dataclass
    class Series:
        name:str=""
        number:str=""
        separator:str=""
        
        def getSeriesPart(self):
            if (len(self.part.strip()) > 0):
                return f"{self.name} {self.separator}{str(self.part)}"
            else:
                return self.name

    config:Config
    id:str=""
    asin:str=""
    isbn:str=""
    title:str=""
    subtitle:str=""
    publisher:str=""
    length:int=0
    duration:float=0
    language:str="English"
    description:str=""
    releaseDate:str=""    
    cover:str=""
    metadata:str=""
    category:str=""
    authors:list[str]=field(default_factory=list)
    narrators:list[str]=field(default_factory=list)
    series:list[Series]=field(default_factory=list)
    genres:list[str]=field(default_factory=list)
    tags:list[str]=field(default_factory=list)   
    identifiers:list[str]=field(default_factory=list)   
    delimiter:str="|" 
    source_path:str=""
    filename:str=""
    files:list[str]=field(default_factory=list)
    metadataJson:str=""
    includeSubtitle:bool=False
    extension:str=""
    contentType:str=""
    formatType:str=""
    booksFound:list=None
    json:dict=None

    def __getMamIsbn__ (self):
        if len(self.isbn):
            return f"{self.isbn}"
        elif len(self.asin):
            return f"ASIN: {self.asin}"
        else:
            return ""

    def __getMamTags__ (self, delimiter="|"):
        return self.tags

    def __convert_to_hours_minutes__ (self, minutes):
        hours = minutes // 60
        minutes = minutes % 60

        duration = ""
        if hours > 0:
            duration = f"{hours} hours "

        if minutes > 0:
            duration += f"{minutes} minutes"

        return duration

    def __cleanseTitle__ (self, stripaccents=True, stripUnabridged=False):
        #remove (Unabridged) and strip accents
        stdTitle=str(self.title)

        for w in ["(Dramatized Adaptation)", "[Dramatized Adaptation]", "(Unabridged)", "m4b", "mp3", ",", "-", "?", "!"]:
            stdTitle=stdTitle.replace(w," ")
        
        if stripaccents:
            stdTitle = myx_utilities.strip_accents(stdTitle)

        # remove any subtitle that goes after a :
        stdTitle = re.sub (r"(:(\s)?([a-zA-Z0-9_'\.\s]{2,})*)$", "", stdTitle, flags=re.IGNORECASE)

        return stdTitle        

    def __cleanseName__(self, name:str):
        honorifics=["Mr.", "Mrs.", "Ms.", "Miss", "Dr.", "Professor", "Prof.", "Sgt.", "Staff Sgt", "Father", "Saint"]
        suffixes=["PhD", "RMT", "MFT", "MD", "EdM", "LMFT", "M.S.Ed", "- editor", "- foreword", "- Translated by", "MBA",
            "MSBA", "CRE", "LCSW", "- contributor", "- adaptation", "- adaption", "- read to", "- translator", "- Edited by",
            "- author/editor", "- preface"]

        #remove honorifics
        for prefix in honorifics:
            name = name.removeprefix(prefix + " ")
        
        for suffix in suffixes:
            #name = name.replace(suffix, " ")
            name = name.replace(" " + suffix.lower(), " ")

        #remove periods, extra spaces, then reassemble
        name=name.replace(".", " ")
        names = name.split()
       
        return  " ".join(names).strip()

    def __cleanseSeries__(self, series:str):
        #remove The and Series
        prefixes=["The","A"]
        suffixes=["Series", "Novel", "Novels", "Trilogy", "Saga", "Mystery", "Mysteries"]

        for prefix in prefixes:
           series = series.removeprefix(prefix + " ")

        for suffix in suffixes:
            series = series.removesuffix(" " + suffix)

        return series.strip()

    def __getAuthors__ (self, delimiter=",", encloser="", stripaccents=True):
        if len(self.authors):
            items=[]
            for author in self.authors:
                items.append(f"{encloser}{self.__cleanseName__(author)}{encloser}")
            return delimiter.join(items)         
        else:
             return ""

    def __getNarrators__ (self, delimiter=",", encloser="", stripaccents=True):
        if len(self.narrators):
            items=[]
            for narrator in self.narrators:
                items.append(f"{encloser}{self.__cleanseName__(narrator)}{encloser}")
            return delimiter.join(items)         
        else:
             return ""

    def __getSeries__ (self, delimiter=",", encloser="", stripaccents=True):
        if len(self.series):
            items=[]
            for s in self.series:
                items.append(f"{encloser}{self.__cleanseSeries__(s.name)}{encloser}")
            return delimiter.join(items)         
        else:
             return ""

    def __isForbiddenAuthor__ (self, forbidden_authors=""):
        verbose = bool(self.config.get ("Config/flags/verbose"))

        if len(forbidden_authors) == 0:
            forbidden_authors = self.config.get("Config/uploader-tools/forbidden_authors", [])

        found = False
        for a in self.authors:
            if self.__cleanseName__(a) in forbidden_authors:
                if verbose: print (f"{a}'s {self.title} is a forbidden author")
                found = True
                break

        return found

    def getJSONFastFillOut (self, jff_path=None, jff_template=None):
        dry_run = bool(self.config.get ("Config/flags/dry_run"))
        verbose = bool(self.config.get ("Config/flags/verbose"))
        #self.includeSubtitle=bool(self.config.get("Config/flags/includeSubtitle"))
            
        #generating JsonFastFilleout file defaults
        if jff_path is None:
            jff_path = self.config.get("Config/output_path")

        if jff_template is None:
            jff_template = self.config.get("Config/uploader-tools/json_fastfillout", "{metadata}-{title}-{id}" )

        #generate filename from template
        jff_filename = sanitize_filename(jff_template.format (**self.__dict__))

        json_file = os.path.join (jff_path, jff_filename + ".json")
        if verbose: print (f"Generating JsonFastFill file {json_file}")

        # --- Generate .json Metadata file ---
        #generate the mam json file for easy upload
        jff = {
            "isbn": self.__getMamIsbn__(),
            "title": myx_utilities.mlaTitleCase(self.title),
            "description": self.description.replace("<p>", "<p><br/>"),
            "tags": self.__getMamTags__(self.delimiter),
            "thumbnail": self.cover,
            "language": self.language,
            "category": self.getMAMCategory()
        } 

        #subtitle
        if (self.includeSubtitle) and len(self.subtitle):
            jff["subtitle"]=self.subtitle

        #authors
        if len(self.authors): jff["authors"] = []
        for author in self.authors:
            jff["authors"].append(self.__cleanseName__(author))

        #narrators
        if len(self.narrators): jff["narrators"] = []
        for narrator in self.narrators:
            jff["narrators"].append(self.__cleanseName__(narrator))

        #series
        if len(self.series): jff["series"] = []
        for series in self.series:
            jff["series"].append({"name": self.__cleanseSeries__(series.name), "number": series.number})

        try:
            with open(json_file, mode='w', encoding='utf-8') as jfile:
                json.dump(jff, jfile, indent=4)  

        except Exception as e:
            print (f"Error getting JSON Fast Fillout {json_file}: {e}")

    def export(self, filename):
        return False

    def getMAMCategory (self):  
        return self.category        

    def query(self, parameters):
        #if there's an ID, get by ID
        if "isbn" in parameters:
            return self.getByID (parameters["isbn"])

        elif "asin" in parameters:
            return self.getByID (parameters["asin"])

        else: 
            return self.search (parameters)
    
    def getByID (self, id):
        print ("If you're seeing this, then this feature has not been implemented for this Book")

    def search (self, params):
        print ("If you're seeing this, then this feature has not been implemented for this Book")

    def hardlinkFiles (self, destination, isHardlink=True):
        #flags
        dry_run=bool(self.config.get("Config/flags/dry_run"))
        verbose=bool(self.config.get("Config/flags/verbose"))

        if len(self.filename):
            print (f"Hardlinking {self.filename}")
            source = os.path.join (self.source_path, self.filename)
            dest = os.path.join (destination, sanitize_filename(self.filename))

            if verbose: print(f"Source: {source} >> Destination: {dest}")
            if (os.path.exists(source) and (not os.path.exists(dest))):
                try:
                    #Hardlink or Copy
                    if isHardlink:
                        if verbose: print (f"Hardlinking {source} to {dest}")
                        if not dry_run:
                            os.link(source, dest)
                    else:
                        #copy
                        if verbose: print (f"Copying {source} to {dest}")
                        if not dry_run:
                            shutil.copy2 (source, dest)                                
                except Exception as e:
                    print (f"\tFailed due to {e}")   

        #this book might have multiple files
        if len(self.files):
            print (f"Hardlinking {len(self.files)} files...")
            for f in self.files:
                fn = f
                if verbose: print (f"Filename: {fn}")
                source = os.path.join (self.source_path, fn)
                dest = os.path.join (destination, sanitize_filename(fn))

                if verbose: print(f"Source: {source} >> Destination: {dest}")
                if (os.path.exists(source) and (not os.path.exists(dest))):
                    try:
                        #Hardlink or Copy
                        if isHardlink:
                            if verbose: print (f"Hardlinking {source} to {dest}")
                            if not dry_run:
                                os.link(source, dest)
                        else:
                            #copy
                            if verbose: print (f"Copying {source} to {dest}")
                            if not dry_run:
                                shutil.copy2 (source, dest)                                
                    except Exception as e:
                        print (f"\tFailed due to {e}")  

        return 
        