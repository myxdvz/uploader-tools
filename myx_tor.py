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
import shutil

@dataclass
class TBook():
    config:Config
    book:Book
    library:str=""
    upload_folder:str=""
    upload_fn:str=""
    torrentfiles:list=None
    #flags
    dryRun:bool=False
    verbose:bool=False
    hardlink:bool=False
    #settings
    category:str=""
    upload_path:str=""
    libtorrent_path:str=""
    upload_files:list[str]=field(default_factory=list)

    def __post_init__ (self):
        super().__init__()
        if self.config is not None:
            #get information from the Config File
            self.dryRun = bool(self.config.get("Config/flags/dry_run"))
            self.verbose = bool(self.config.get("Config/flags/verbose"))
            torrent_path = self.config.get(f"Config/uploader-tools/torrent_path")
            
            if len(self.library):
                #important settings for the specified library
                self.upload_path=self.config.get(f"Config/{self.library}/upload_path")
                self.upload_files=self.config.get(f"Config/{self.library}/upload_files")
                self.libtorrent_path=self.config.get(f"Config/{self.library}/torrent_path", torrent_path)
                self.category=self.config.get (f"Config/{self.library}/category", "uploads")
            else:
                self.upload_path=self.config.get(f"Config/uploader-tools/upload_path")
                self.upload_files=self.config.get(f"Config/uploader-tools/upload_files")
                self.libtorrent_path=torrent_path
                self.category=self.config.get (f"Config/uploader-tools/category", "uploads")

            self.hardlink=bool(self.config.get(f"Config/{self.library}/hardlink"))
        
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
        in_series=self.config.get("Config/uploader-tools/in_series")
        no_series=self.config.get("Config/uploader-tools/no_series")

        #Get primary author
        author=""
        if (self.book.authors is not None) and (len(self.book.authors) > 0):
            author=self.book.__cleanseName__(self.book.authors[0])

        #Does this book belong in a series - only take the first series?
        series=""
        part=""
        if (len(self.book.series) > 0):
            series = f"{self.book.__cleanseSeries__(self.book.series[0].name)}"
            part = str(self.book.series[0].number)

        title = f"{self.book.__cleanseTitle__()}"

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

        if self.verbose: print (f"Upload Path: {self.upload_path} >> sPath: {sPath}")
        return os.path.join(self.upload_path, sPath)  

    def __isForbiddenAuthor__ (self, forbidden_authors):
        found = False
        for a in self.book.authors:
            if a in forbidden_authors:
                if self.verbose: print (f"{a}'s {self.book.title} is a forbidden author")
                found = True
                break

        return found
        
    def __prepUpload__ (self):
        #Assumption:  getByID has been called:
        #self.source_path: should be the parent folder of the file
        #self.filename: should be the name of the m4b or epub file        
        #metadata would have already been loaded

        #list of forbidden authors
        forbidden_authors=self.config.get("Config/uploader-tools/forbidden_authors")

        #1. Check if the source files exist
        if self.verbose: print (f"Checking if source_path {self.book.source_path} exists...")
        if os.path.exists(self.book.source_path):
            #Check if this books is from a forbidden author, if yes -- don't proceed
            if self.verbose: print (f"Checking if {self.book.authors} are forbidden...")
            if not self.__isForbiddenAuthor__ (forbidden_authors):
                #Create the folder in the upload_path
                if self.verbose: print (f"Generating Upload Book folder...")
                self.upload_folder = self.__getUploadBookFolder__()
                if self.verbose: print (f"getUploadBookFolder: {self.upload_folder}")

                #makedir in upload_path
                if self.verbose: print (f"Creating directory {self.upload_folder}...")
                if not self.dryRun:
                    os.makedirs (self.upload_folder, exist_ok=True)

                #Hardlink the files
                if self.verbose: 
                    print(f"File: {self.book.filename} >> Source: {self.book.source_path}")
                
                #for each upload_files, hardlink the files
                for ft in self.upload_files:
                    #check if the file already exists in the target directory
                    filename = self.book.filename + ft
                    if self.verbose: print (f"Filename: {filename}")
                    source = os.path.join (self.book.source_path, filename)
                    dest = os.path.join (self.upload_folder, sanitize_filename(filename))
                    if self.verbose: print(f"Source: {source} >> Destination: {dest}")
                    if (os.path.exists(source) and (not os.path.exists(dest))):
                        try:
                            #Hardlink or Copy
                            if self.hardlink:
                                if self.verbose: print (f"Hardlinking {source} to {dest}")
                                if not self.dryRun:
                                    os.link(source, dest)
                            else:
                                #copy
                                if self.verbose: print (f"Copying {source} to {dest}")
                                if not self.dryRun:
                                    shutil.copy2 (source, dest)                                
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
    
    def createTorrent (self, folder):

        #if no parameter, use self.upload_folder
        if folder is None:
            folder = self.upload_folder

        if len(folder):
            print (f"Creating a torrent for {folder}")
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
        announceURL = self.config.get("Config/uploader-tools/announce")
        
        #the torrent file is the folder name
        torrent_file = os.path.basename(os.path.normpath(folder))
        self.upload_fn = os.path.join (self.libtorrent_path, torrent_file + ".torrent")
        if self.verbose: print (f"Creating a torrent file {self.upload_fn}")

        if os.path.exists(self.upload_fn):
            print (f"File {self.upload_fn} exists. Skipping torrent creation")
        else:
            if os.path.exists(folder):
                piece_size = self.__getPieceSize__(folder)
                #py3createtorrent -t udp://tracker.opentrackr.org:1337/announce file_or_folder
                cmnd = ['py3createtorrent','--private', '--force', '--piece-length', str(piece_size), '--tracker', announceURL, folder, '--output', self.upload_fn]
                cmnd = self.__addExclusions__(cmnd)
                if self.verbose: print (f"Running command: {cmnd}")
                if not self.dryRun:
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
        print (f"Adding {len(self.torrentfiles)} torrents to client with category {self.category}")
        try:
            msg =  qbt_client.torrents_add(torrent_files=self.torrentfiles, category=self.category, is_paused=True, use_auto_torrent_management=True)

            #print (msg)
            if  msg != "Ok.":
                raise Exception("Failed to add torrent.")
            
            # now get all the added torrents, and force recheck
            torrents = qbt_client.torrents_info(status_filter="stopped", category=self.category)
            #print (torrents)

            #force recheck
            print(f"Force rechecking ...")
            for torrent in torrents:
                torrent.recheck()

        except Exception as e:
            print (e)   

        return

