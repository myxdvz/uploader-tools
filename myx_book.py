from dataclasses import dataclass
from dataclasses import field
from myx_args import Config
import myx_utilities
import pprint
import json
import os

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
    source:str=""
    category:str=""
    series:list[Series]= field(default_factory=list)
    authors:list[str]= field(default_factory=list)
    narrators:list[str]= field(default_factory=list)
    genres:list[str]= field(default_factory=list)
    tags:list[str]= field(default_factory=list)    
    delimiter:str="|"
    config:Config=None
    source_path:str=""

    def __getMamIsbn__ (self):
        if len(self.asin):
            return f"ASIN: {self.asin}"
        else:
            return f"{self.isbn}"

    def __getMamTags__ (self, delimiter="|"):
        return self.tags

    def getJSONFastFillOut (self, path, filename):
        #write the file out
        json_file = os.path.join(path, filename + ".json")

        # --- Generate .json Metadata file ---
        #generate the mam json file for easy upload
        jff = {
            "isbn": self.__getMamIsbn__(),
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "authors": [],
            "series": [],
            "narrators": [],
            "tags": self.__getMamTags__(self.delimiter),
            "thumbnail": self.cover,
            "language": self.language,
            "category": self.category
        } 

        #authors
        for author in self.authors:
            jff["authors"].append(author)

        #narrators
        for narrator in self.narrators:
            jff["narrators"].append(narrator)

        #series
        for series in self.series:
            jff["series"].append({"name": series.name, "number": series.number})

        try:
            with open(json_file, mode='w', encoding='utf-8') as jfile:
                json.dump(jff, jfile, indent=4)  

        except Exception as e:
            print (f"Error getting JSON Fast Fillout {json_file}: {e}")

