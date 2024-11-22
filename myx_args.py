import argparse
import os
import json
from pprint import pprint

#Module Variables
params:any

def importArgs():
    appDescription = """Uploader toolkit - useful scripts to help an uploader automate some of their tasks"""
    parser = argparse.ArgumentParser(prog="uploader-tools", description=appDescription)
    #Primary Action to run
    parser.add_argument ("action", choices=["query", "createJson", "createTorrent", "prep4upload", "mylib2mam", "scanLibrary", "sanitizeLibrary"], help="A specific task or tool to run")
    parser.add_argument ("-m", "--metadata", choices=["audible", "google", "mam", "file", "libation", "epub"], help="Source of metadata")
    parser.add_argument ("-p", "--params", help="Parameters for the action", nargs="+")

    #Debug flags
    parser.add_argument("--dry-run", default=None, action="store_true", help="If provided, will override dryRun in config")
    parser.add_argument("--verbose", default=None, action="store_true", help="If provided, will print additional info")
    parser.add_argument("--add-hash", default=None, action="store_true", help="If provided, will add hash to output filenames")
    parser.add_argument("--quiet", default=None, action="store_true", help="If provided, it will skip any interactive elements")

    #get all arguments
    args = parser.parse_args()

    #set module variable to args
    return args

def merge_dictionaries_recursively (dict1, dict2):
    """ Update two config dictionaries recursively.
        Args:
            dict1 (dict): first dictionary to be updated
            dict2 (dict): second dictionary which entries should be preferred
    """
    if dict2 is None: return

    for k, v in dict2.items():
        if k not in dict1:
            dict1[k] = dict()
        if isinstance(v, dict):
            merge_dictionaries_recursively (dict1[k], v)
        else:
            dict1[k] = v    

class Config(object):  
    """ Simple dict wrapper that adds a thin API allowing for slash-based retrieval of
        nested elements, e.g. cfg.get_config("meta/dataset_name")
    """
    def __init__(self, configFile, params):
        try:
            with open(configFile) as cf_file:
                cfg = json.loads (cf_file.read())

                #override config with command line param
                if params.metadata is not None:
                    cfg["Config"]["metadata"] = params.metadata                 

                #override config/flags with command line param
                if params.dry_run is not None:
                    cfg["Config"]["flags"]["dry_run"] = bool(params.dry_run)            

                if params.verbose is not None:
                    cfg["Config"]["flags"]["verbose"] = bool(params.verbose)            

                if params.add_hash is not None:
                    cfg["Config"]["flags"]["add_hash"] = bool(params.verbose)            

                if params.quiet is not None:
                    cfg["Config"]["flags"]["quiet"] = bool(params.quiet)            

            self._data = cfg            
        except Exception as e:
            raise Exception(e)

    def get(self, path=None, default=None):
        # we need to deep-copy self._data to avoid over-writing its data
        sub_dict = dict(self._data)

        if path is None:
            return sub_dict

        path_items = path.split("/")[:-1]
        data_item = path.split("/")[-1]

        try:
            for path_item in path_items:
                sub_dict = sub_dict.get(path_item)

            value = sub_dict.get(data_item, default)

            return value
        except (TypeError, AttributeError):
            return default
