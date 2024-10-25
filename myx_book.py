from dataclasses import dataclass
from dataclasses import field
from pathvalidate import sanitize_filename
from myx_args import Config
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
    authors:list[str]= field(default_factory=list)
    narrators:list[str]= field(default_factory=list)
    series:list[Series]= field(default_factory=list)
    genres:list[str]= field(default_factory=list)
    tags:list[str]= field(default_factory=list)   
    delimiter:str="|" 
    source_path:str=""
    filename:str=""
    metadataJson:str=""
    includeSubtitle:bool=False
    extension:str=""
    #Added for MAMBook
    added:str=""
    bookmarked:str=""
    browseFlags=int=0
    cat:str=""
    categoryId:int=0
    catName:str=""
    vip:bool=False
    fl_vip:bool=False
    free:bool=False
    main_cat:int=0
    my_snatched:bool=False
    numfiles:int=0
    owner:int=0
    owner_name:str=""
    personal_fl:bool=False
    json:dict=None

    def __getMamIsbn__ (self):
        if len(self.asin):
            return f"ASIN: {self.asin}"
        else:
            return f"{self.isbn}"

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

    def __cleanseName__(self, name:str):
        #remove periods
        name=name.replace(".", "")
        honorifics=["Mr", "Mrs", "Ms", "Miss", "Dr", "PhD", "Professor", "Prof"]

        #remove honorifics
        for prefix in honorifics:
            name = name.removeprefix(prefix)
        
        return name.strip()

    def __cleanseSeries__(self, series:str):
        #remove The and Series
        prefixes=["The","A"]
        suffixes=["Series", "Novel", "Novels", "Trilogy", "Saga"]

        for prefix in prefixes:
           series = series.removeprefix(prefix)

        for suffix in suffixes:
            series = series.removesuffix(suffix)

        return series.strip()

    def getJSONFastFillOut (self, jff_path=None, jff_template=None):
        dry_run = self.config.get ("Config/flags/dry_run")
        verbose = self.config.get ("Config/flags/verbose")
            
        #generating JsonFastFilleout file defaults
        if jff_path is None:
            jff_path = self.config.get("Config/output_path")

        if jff_template is None:
            jff_template = self.config.get("Config/uploader-tools/json_fastfillout")

        #generate filename from template
        jff_filename = sanitize_filename(jff_template.format (**self.__dict__))

        json_file = os.path.join (jff_path, jff_filename + ".json")
        if verbose: print (f"Generating JsonFastFill file {json_file}")

        # --- Generate .json Metadata file ---
        #generate the mam json file for easy upload
        jff = {
            "isbn": self.__getMamIsbn__(),
            "title": self.title,
            "description": self.description.replace("<p>", "<p><br/>"),
            "authors": [],
            "series": [],
            "narrators": [],
            "tags": self.__getMamTags__(self.delimiter),
            "thumbnail": self.cover,
            "language": self.language,
            "category": self.category
        } 

        #subtitle
        if (self.includeSubtitle) and len(self.subtitle):
            jff["subtitle"]=self.subtitle

        #authors
        for author in self.authors:
            jff["authors"].append(self.__cleanseName__(author))

        #narrators
        for narrator in self.narrators:
            jff["narrators"].append(self.__cleanseName__(narrator))

        #series
        for series in self.series:
            jff["series"].append({"name": self.__cleanseSeries__(series.name), "number": series.number})

        try:
            with open(json_file, mode='w', encoding='utf-8') as jfile:
                json.dump(jff, jfile, indent=4)  

        except Exception as e:
            print (f"Error getting JSON Fast Fillout {json_file}: {e}")


    def export(self, filename):
        return False