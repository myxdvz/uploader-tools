# uploader-tools
A few QoL tools for uploaders

## Install
* Python >= 3.10
* httpx==0.27.2
* langcodes==3.4.0
* PyYAML==6.0.2

1. run pip install -r requirements.txt to install dependencies
2. copy default_config.cfg into settings.json and modify with your settings and defaults (cache_path, metadata, input_path, output_path)
3. the following config setting can be overriden by command line parameters: metadata, input_path, output_path, dry_run, verbose


## Usage Examples
Generate JSONFastFillout file from Audible metadata
~~~
python uploader-tools.py createJson --book [comma delimited list of ASIN/ISBN] --metadata audible
~~~

Generate JSONFastFillout file from Google metadata
~~~
python uploader-tools.py createJson --book [comma delimited list of ASIN/ISBN] --metadata google
~~~

Generate JSONFastFillout file from a local file (must be a yaml file)
~~~
python uploader-tools.py createJson --book [comma delimited list of file paths] --metadata file
~~~

Generate Torrent file from a media folder and corresponding JsonFastFillout file. It will check if a metadata.json file exists to generate metadata file
The following settings are in the config file: announceUrl, upload_path, torrent_path
~~~
python uploader-tools.py createTorrent --input /path/to/media
~~~

Generate Torrent file from a media folder and corresponding JsonFastFillout file. It will check if a metadata.json file exists to generate metadata file
The following settings are in the config file: announceUrl, upload_path, torrent_path
~~~
python uploader-tools.py createTorrent --input /path/to/media --book [ids or file] --metadata file
~~~


