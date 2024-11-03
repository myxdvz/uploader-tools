import ebooklib
from ebooklib import epub
from myx_book import Book
import myx_utilities
import httpx
import json

class EpubBook(Book):
    def __init__ (self, cfg=None):
        super().__init__(cfg)
        self.metadata="epub"
        self.extension="epub"
        
    def getByID (self, id=""):
        #flags
        dry_run=bool(self.config.get("Config/flags/dry_run"))
        verbose=bool(self.config.get("Config/flags/verbose"))

        #ID is path to epub
        print (f"Retrieving metadata: {id}")

        #read metadata from 
        self.id = id
        book=epub.read_epub(id, {"ignore_ncx": True})

        title = book.get_metadata("DC", "title")
        if len(title):
            self.title = title[0][0]

        subtitle = book.get_metadata("DC", "subtitle")
        if len(subtitle):
            self.subtitle = subtitle[0][0]

        description = book.get_metadata("DC", "description")
        if len(description):
            self.description = description[0][0]

        publisher = book.get_metadata("DC", "publisher")
        if len(publisher):
            self.publisher = publisher[0][0]

        date = book.get_metadata("DC", "date")
        if len(date):
            self.releaseDate = date[0][0]

        language = book.get_metadata("DC", "language")
        if len(language):
            self.language = myx_utilities.getLanguage(language[0][0])

        identifiers = book.get_metadata("DC", "identifier")
        if len(identifiers):
            #identifier could have multiple things
            self.identifiers=[]
            for id in identifiers:
                #this is a tuple, the first item is the ID, the second is a dictionary, and we're looking for '{http://www.idpf.org/2007/opf}scheme'
                if "{http://www.idpf.org/2007/opf}scheme" in id[1]:
                    self.identifiers.append ({"id": id[0], "type": id[1]["{http://www.idpf.org/2007/opf}scheme"]})
                    match id[1]["{http://www.idpf.org/2007/opf}scheme"]:
                        case "AMAZON": self.asin = id[0]
                        case "ISBN": self.isbn = id[0]     
                else:
                    self.isbn = id[0]                   

        authors = book.get_metadata("DC", "creator")
        if len(authors):
            for author in authors:
                self.authors.append (author[0])

        #genres
        subject = book.get_metadata("DC", "subject")
        if len(subject):
            for genre in subject:
                self.genres.append(genre[0])

        tags = book.get_metadata("DC", "tags")
        if len(subtitle):
            for tag in tags:
                self.tags.append(tag[0])

        #series
        #series += f"\t<ns0:meta name='calibre:series' content='{s.name}' />\n"
        #series += f"\t<ns0:meta name='calibre:series_index' content='{s.part}' />\n"        
        series = book.get_metadata("OPF", "calibre:series")
        parts = book.get_metadata("OPF", "calibre:series_index")
        if len(series):
            for i in range(len(series)):
                self.series.append (Series(series[i][0], parts[i][0]))

        #ID is ISBN or ASIN
        if len(self.isbn): self.id = self.isbn
        elif len(self.asin): self.id = self.asin

        #print them all out
        #if verbose:
            # print ("Series:", book.get_metadata("OPF", "calibre:series"))
            # print ("Colleciton:", book.get_metadata("OPF", "collection"))
            # print (book.get_metadata("OPF", "belongs-to-collection"))
            # print (book.get_metadata("OPF", "file-as"))
            # print (book.get_metadata("OPF", "dcterms:identifier"))
            # print (book.get_metadata("OPF", "group-position"))

            # print (f"title: {title}")
            # print (f"subtitle: {subtitle}"
            # print (f"description: {description}")
            # print (f"publisher: {publisher}")
            # print (f"date: {date}")
            # print (f"language: {language}")
            # print (f"identifier: {identifiers}")
            # print (f"authors: {authors}")
            # print (f"subject: {subject}")
            # print (f"tags: {tags}")
            # print (f"series: {series}")
            # print (self)
            # print (book.metadata["http://www.idpf.org/2007/opf"])
            # print (book.metadata["http://purl.org/dc/elements/1.1/"])

    def __getMamTags__ (self, delimiter="|"):
        return f"Publisher: {self.publisher} | Publication Date : {self.releaseDate[:10]} | {','.join(set(self.genres))}"
