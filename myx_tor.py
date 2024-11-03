from dataclasses import dataclass
from dataclasses import field
from pathvalidate import sanitize_filename
import qbittorrentapi
from qbittorrentapi import Client
from myx_args import Config
from myx_book import Book
import myx_args
import myx_utilities
import httpx
import json
import pprint
import os, subprocess

@dataclass
class TBook():
    config:Config=None
    book:Book=None
    upload_folder:str=""
    upload_fn:str=""
    torrentfiles:list=None

    def go(self):
        #Assumption:  getByID has been called:
        #self.source_path: should be the parent folder of the file
        #self.filename: should be the name of the m4b or epub file
        if self.book is None:
            print ("Please load a book first")
        else:
            steps = self.config.get("Config/uploader-tools/steps")

            #"steps": ["prepUpload", "createTorrent", "createJson"],
            for step in steps:
                try:
                    getattr(self, step)()
                except Exception as e:
                    print (f"Error running step {step}: {e}")

    def __getUploadBookFolder__ (self):
        #Config
        verbose=bool(self.config.get("Config/flags/vebose"))
        upload_path=self.config.get("Config/uploader-tools/upload_path")
        in_series=self.config.get("Config/uploader-tools/in_series")
        no_series=self.config.get("Config/uploader-tools/no_series")

        #Get primary author
        if ((self.book.authors is not None) and (len(self.book.authors) == 0)):
            author=""
        else:
            author=self.book.authors[0]

        #standardize author name (replace . with space, and then make sure that there's only single space)
        if len(author):
            author=myx_utilities.cleanseAuthor(author)

        #Does this book belong in a series - only take the first series?
        series=""
        part=""
        if (len(self.book.series) > 0):
            series = f"{myx_utilities.cleanseSeries(self.book.series[0].name)}"
            part = str(self.book.series[0].number)

        title = f"{myx_utilities.cleanseTitle(self.book.title)}"

        tokens = {}
        tokens["author"] = sanitize_filename(author)
        tokens["series"] = sanitize_filename(series)
        tokens["part"] = sanitize_filename(part)
        tokens["title"] = sanitize_filename(self.book.title)
        tokens["cleanTitle"] = sanitize_filename(title)

        sPath = ""
        if len(self.book.series):
            x = in_series.format (**tokens)
            sPath = x
        else:
            y = no_series.format (**tokens)
            sPath = y

        if verbose: print (f"Upload Path: {upload_path} >> sPath: {sPath}")
        return os.path.join(upload_path, sPath)  

    def __isForbiddenAuthor__ (self, forbidden_authors):
        found = False
        for a in self.book.authors:
            if a in forbidden_authors:
                if verbose: print (f"{a}'s {self.book.title} is a forbidden author")
                found = True
                break

        return found
        
    def __prepUpload__ (self):
        #Assumption:  getByID has been called:
        #self.source_path: should be the parent folder of the file
        #self.filename: should be the name of the m4b or epub file        
        #metadata would have already been loaded

        #flags
        dry_run=bool(self.config.get("Config/flags/dry_run"))
        verbose=bool(self.config.get("Config/flags/verbose"))

        #where to prep the files to upload
        upload_path=self.config.get("Config/uploader-tools/upload_path")
        upload_files=self.config.get("Config/uploader-tools/upload_files")

        #list of forbidden authors
        forbidden_authors=self.config.get("Config/uploader-tools/forbidden_authors")

        #1. Check if the source files exist
        if verbose: print (f"Checking if source_path {self.book.source_path} exists...")
        if os.path.exists(self.book.source_path):
            #Check if this books is from a forbidden author, if yes -- don't proceed
            if verbose: print (f"Checking if {self.book.authors} are forbidden...")
            if not self.__isForbiddenAuthor__ (forbidden_authors):
                #Create the folder in the upload_path
                if verbose: print (f"Generating Upload Book folder...")
                self.upload_folder = self.__getUploadBookFolder__()
                if verbose: print (f"getUploadBookFolder: {self.upload_folder}")

                #makedir in upload_path
                if verbose: print (f"Creating directory {self.upload_folder}...")
                if not dry_run:
                    os.makedirs (self.upload_folder, exist_ok=True)

                #Hardlink the files
                if verbose: print(f"File: {self.book.filename} >> Source: {self.book.source_path}")
                if verbose: print (f"Hardlinking {self.book.filename}")
                #for each upload_files, hardlink the files
                for ft in upload_files:
                    #check if the file already exists in the target directory
                    filename = self.book.filename + ft
                    if verbose: print (f"Filename: {filename}")
                    source = os.path.join (self.book.source_path, filename)
                    dest = os.path.join (self.upload_folder, sanitize_filename(filename))
                    if verbose: print(f"Source: {source} >> Destination: {dest}")
                    if (os.path.exists(source) and (not os.path.exists(dest))):
                        try:
                            if verbose: print (f"Hardlinking {source} to {dest}")
                            if not dry_run:
                                os.link(source, dest)
                        except Exception as e:
                            print (f"\tFailed due to {e}")   

                return self.upload_folder 
            else:
                print (f"{self.book.authors} are forbidden ... skipping")

        else:
            print (f"Source File {self.book.source_path} doesn't exist")

    def prepUpload(self):
        #Assumption:  getByID has been called:
        #self.source_path: should be the parent folder of the file
        #self.filename: should be the name of the m4b or epub file        

        #the step is to create a folder in the Upload_path and hardlink the cue, m4b and jpg files    
        print ("Preparing Upload Files...")
        self.__prepUpload__()
    
    def createTorrent (self, folder=None):

        #if no parameter, use self.upload_folder
        if folder is None:
            folder = self.upload_folder

        if len(folder):
            print (f"Creating a torrent for {self.upload_folder}")
            file = self.__createTorrent__(folder)

            #add the torrent file to the list
            if os.path.exists(file):
                if (self.torrentfiles is None): self.torrentfiles=[]
                self.torrentfiles.append(file)

        else:
            print ("Please provide folder to create torrent from...")


    def createJson (self):
        print ("Creating Json fast fillout...")
        self.book.getJSONFastFillOut(jff_path=self.upload_folder)

    def __createTorrent__ (self, folder):
        dry_run = self.config.get("Config/flags/dry_run")
        verbose = self.config.get("Config/flags/verbose")
        announceURL = self.config.get("Config/uploader-tools/announce")
        torrent_path = self.config.get("Config/uploader-tools/torrent_path")
        
        torrent_file = os.path.splitext(os.path.basename(folder))[0]
        self.upload_fn = os.path.join (torrent_path, torrent_file + ".torrent")
        if verbose: print (f"Creating a torrent file {self.upload_fn}")

        if os.path.exists(self.upload_fn):
            print (f"File {self.upload_fn} exists. Skipping torrent creation")
        else:
            if os.path.exists(folder):
                piece_size = self.__getPieceSize__(folder)
                #py3createtorrent -t udp://tracker.opentrackr.org:1337/announce file_or_folder
                cmnd = ['py3createtorrent','--private', '--force', '--piece-length', str(piece_size), '--tracker', announceURL, folder, '--output', self.upload_fn]
                cmnd = self.__addExclusions__(cmnd)
                if verbose: print (f"Running command: {cmnd}")
                if not dry_run:
                    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out, err =  p.communicate()
        
        return self.upload_fn

    def __addExclusions__ (self, commandlist):
        paths = self.config.get("Config/uploader-tools/exclude_paths",[])
        for path in paths:
            commandlist.append("--exclude")
            commandlist.append(path)

        patterns = self.config.get("Config/uploader-tools/exclude_patterns",[])
        for pattern in patterns:
            commandlist.append("--exclude-pattern-ci")
            commandlist.append(pattern)

        return commandlist


    def __getDirSize__(self, path='.'):
        #returns total size of all files in the directory
        total = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self.__getDirSize__ (entry.path)
        return total

    def __getPieceSize__ (self, path):
        filesize = self.__getDirSize__(path) / (1024 * 1024)
        piecesize = 0

        if (0 <= filesize <= 69): piecesize = 32
        elif (69 <= filesize <= 137): piecesize = 64
        elif (137 <= filesize <= 275): piecesize = 128
        elif (275 <= filesize <= 550): piecesize = 256
        elif (550 <= filesize <= 1100): piecesize = 512
        elif (1100 <= filesize <= 2200): piecesize = 1024
        elif (2200 <= filesize <= 4403): piecesize = 2048
        elif (4402 <= filesize <= 8796): piecesize = 4096
        else: piecesize=0

        print (f"folder: {path} >> size: {filesize} MiB >> piece length: {piecesize} KiB")

        return piecesize

    def add2Client(self):
        #connect to your client
        conn_info = dict(
            host=self.config.get ("Config/client/host"),
            port=self.config.get ("Config/client/port"),
            username=self.config.get ("Config/client/username"),
            password=self.config.get ("Config/client/password")
        )
        qbt_client = qbittorrentapi.Client(**conn_info)       

        #login
        # try:
        #     qbt_client.auth_log_in()
        # except qbittorrentapi.LoginFailed as e:
            # print(f"Error logging in {e}") 
        
        # Add all files that were generated
        category=self.config.get ("Config/client/category", "uploads")
        print (f"Adding {len(self.torrentfiles)} torrents to client with category {category}")
        try:
            msg =  qbt_client.torrents_add(torrent_files=self.torrentfiles, category=category, is_paused=True, use_auto_torrent_management=True)

            print (msg)
            if  msg != "Ok.":
                raise Exception("Failed to add torrent.")
            
            # now get all the added torrents, and force recheck
            torrents = qbt_client.torrents_info(status_filter="stopped", category=category)
            print (torrents)

            #force recheck
            print(f"Force rechecking ...")
            for torrent in torrents:
                torrent.recheck()

        except Exception as e:
            print (e)   

        return

