# uploader-tools
A few QoL tools for uploaders

## Install
* Python >= 3.10
* httpx==0.27.2
* langcodes==3.4.0
* pathvalidate==3.2.0
* PyYAML==6.0.2
* Requests==2.32.3

1. run pip install -r requirements.txt to install dependencies
2. copy templates/default_config.cfg into config/settings.json and modify your settings and defaults (cache_path, metadata, input_path, output_path)
3. the following config setting can be overriden by command line parameters: metadata, input_path, output_path, dry_run, verbose


## Usage Examples
Generate JSONFastFillout file from Audible metadata
~~~
python uploader-tools.py createJson --book [list of ASIN/ISBN] --metadata audible
~~~

Generate JSONFastFillout file from Google metadata
~~~
python uploader-tools.py createJson --book [list of ISBN] --metadata google
~~~

Generate JSONFastFillout file from a local file (must be a yaml file)
~~~
python uploader-tools.py createJson --book [list of file paths] --metadata file
~~~

Generate JSONFastFillout file from a libation exported metadata
~~~
python uploader-tools.py createJson --book [list of libation M4B paths] --metadata libation
~~~

Generate Torrent file from a Libation m4b filepath and corresponding JsonFastFillout file. Metadata is generated from the Libation metadata.json file
The following settings are in the config file: announceUrl, upload_path, torrent_path
~~~
python uploader-tools.py createTorrent --book [list of libation M4B paths] --metadata libation
~~~

## Disclaimers
* GoogleBooks API is notorious for returning 429 (rate limits)

