from myx_book import Book
import myx_utilities
import httpx
import json
import yaml
import os

class YamlBook(Book):
    def __init__ (self):
        super().__init__()
        self.source="file"

    def getByID (self, id=""):
        add_hash = self.config.get("Config/flags/add_hash", False)

        #for a local book, we're expecting a yaml file as the id
        yaml_file = id
        if os.path.exists(yaml_file):
            try:
                with open(yaml_file, mode='r', encoding='utf-8') as yfile:
                    book = yaml.safe_load(yfile) 

                    #set the book object
                    self.__dic2Book__(book)
                    fn = os.path.splitext(os.path.basename(yaml_file))[0]
                    if add_hash:
                        self.id = f"{fn}-{myx_utilities.getHash(yaml_file)}"
                    else:
                        self.id = f"{fn}"

            except Exception as e:
                print (f"Error getting YAML {yaml_file}: {e}")
        else:
            print (f"Local book file doesn't exist: {id}")

        return self

    def __dic2Book__(self, book):
        #book is an Yaml dictionary
        if book is not None:
            if 'asin' in book: self.asin=str(book["asin"])
            if 'isbn' in book: self.isbn=str(book["isbn"])
            if 'title' in book: self.title=str(book["title"])
            if 'subtitle' in book: self.subtitle=str(book["subtitle"])
            if 'description' in book: self.description=str(book["description"])
            if 'language' in book: self.language=str(book ["language"])
            if 'thumbnail' in book: self.cover=str(book ["thumbnail"])
            if 'tags' in book: self.tags=str(book ["tags"])
            if 'category' in book: self.category=str(book ["category"])
            if 'authors' in book: 
                for author in book["authors"]:
                    self.authors.append(str(author))
            if 'narrators' in book: 
                for narrator in book["narrators"]:
                    self.narrators.append(str(narrator))
            if 'series' in book: 
                for s in book["series"]:
                    self.series.append(self.Series(str(s["name"]), str(s["number"])))

            return self
        else:
            return None        

