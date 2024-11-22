#from pypdf import PdfReader
from myx_book import Book
from pprint import pprint
import myx_utilities
import datetime
import json
import os

class PdfBook(Book):
    subject:str=""
    creator:str=""
    producer:str=""
    creation_date:datetime=None
    modification_date:datetime=None

    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="pdf"
        self.extension="pdf"

    def getByID (self, id=""):
        #flags
        dry_run=bool(self.config.get("Config/flags/dry_run"))
        verbose=bool(self.config.get("Config/flags/verbose"))

        #ID is path to epub
        print (f"Retrieving metadata: {id}")

        #id is path to epub
        self.id = id

        #parse path and filename
        self.source_path = os.path.dirname(id)
        self.filename = os.path.splitext(os.path.basename(id))[0]

        #read metadata from 
        # book = PdfReader(id)
        # metadata = book.metadata
        # pprint (metadata)

        # self.title = metadata.title

        # if (metadata.author is not None) and len(metadata.author) > 0:
        #     self.authors.append (metadata.author)

        # if (metadata.subject is not None) and len(metadata.subject) > 0:
        #     self.genres.append (metadata.subject)

        # self.publisher = metadata.producer
        # self.releaseDate = str(metadata.creation_date)

        # if (metadata.creator is not None) and len(metadata.creator) > 0:
        #     self.tags.append (metadata.creator)
