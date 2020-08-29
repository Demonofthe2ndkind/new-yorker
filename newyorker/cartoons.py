"""
Created on Jun 10, 2018
Updated on Aud 26, 2020

@author: Demon of the Second Kind
"""
import ast
import bs4
import errno
import itertools
import json
import os
import requests
import sys
import uuid
        
from optparse import OptionParser
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.parse import urljoin
from urllib.parse import urlparse


class NYCartoonRetriever:
    "Script/API to retrieve the New Yorker magazine cartoons by keyword(s) and save them in the specified directory."
    
    __all__ = []
    __version__ = 1.1
    __date__ = "2018-06-10"
    __updated__ = "2020-08-28"
    
    
    def __init__(self, outdir = None, verbose = False, headers = None):

        self.__chunk_size = 100000
        self.__image_page_base_url = "https://condenaststore.com" 
        self.__search_page_base_url = self.__image_page_base_url + "/collections/new+yorker+cartoons/"
        self.__base_dir_name = outdir if outdir \
            else os.path.join(os.path.curdir, "cartoons")   
        self.__verbose = verbose 
        self.__headers = headers if headers \
            else {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36"}   


    def main(self):
        """When run as a script, process the command line arguments, then download the cartoons.""" 
        
        # Handle command line arguments and options
                
        program_name = os.path.basename(sys.argv[0])
        program_version = "v{0:.2f}".format(NYCartoonRetriever.__version__)
        program_build_date = "{0}".format(NYCartoonRetriever.__updated__)
    
        program_version_string = "%prog {0} ({1})".format(program_version, program_build_date)
        program_usage = """Usage: %prog search-keyword(s) [options]"""
        program_desc = """Search for and download cartoons from The New Yorker magazine cartoon gallery."""
        # Do not format the next statement
        program_footer = """Examples:
  newyorker email --verbose
  newyorker design desk -v -o ~/example/cartoons
  newyorker santa -v --headers \\
    '{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36"}'\n
Copyright 2018-2020, Demon of the Second Kind. Apache License 2.0\n"""
    
        argv = sys.argv[1:]
            
        try:
            # Setup option parser
            OptionParser.format_epilog = lambda self, formatter: self.epilog
            parser = OptionParser(program_usage, version = program_version_string, epilog = program_footer, description = program_desc)
            parser.add_option("-o", "--outdir", dest = "outdir", help = "set the base download directory [default: %default]", metavar = "DIR")
            parser.add_option("-v", "--verbose", dest = "verbose", action = "store_true", help = "show progress trace [default: %default]")
            parser.add_option("--headers", dest = "headers", help = "set HTTP request headers \n [default: %default]")
    
            # Set defaults
            parser.set_defaults(outdir = self.__base_dir_name, verbose = self.__verbose, headers = self.__headers)
    
            # Process args and options
            (opts, args) = parser.parse_args(argv)
            
            if (len(args) == 0):
                parser.print_help()
                return 1

            self.__base_dir_name = opts.outdir           
            self.__verbose = opts.verbose
            self.__headers = ast.literal_eval(opts.headers) if type(opts.headers) is str else opts.headers
    
            if (self.__verbose):
                print("Keywords = {0}".format(", ".join(args)))
                print("Base directory = {0}".format(self.__base_dir_name))
                print("Verbose = {0}".format(self.__verbose))
                print("HTTP headers = {0}".format(self.__headers))
                
            keywords = list(args)
            keywords.sort()
            
            # Search for and download the cartoon files
            images_downloaded = self.retrieve(keywords)
        
            # Print some stats
            if (self.__verbose):
                print("Images downloaded: {0}".format(images_downloaded))
            
            return 0
    
        except Exception as e:
            indent = len(program_name) * " "
            print(f"{program_name}: {e!r}", file=sys.stderr)
            print(f"{indent}  for help use --help", file=sys.stderr)

            return 2
        

    def retrieve(self, keywords):
        """Retrieve the cartoons and save them as files."""       

        if not keywords:
            raise ValueError("At least one search keyword has to be specified")

        # Make sure directory exists; if not, create one        
        dir_name = os.path.join(self.__base_dir_name, "-".join(keywords))
        self._ensure_dir_exists(dir_name)
        
        # Search for and download the cartoon files
        image_count = 0            
        for page_no in itertools.count(1):
            search_page_url = self._get_search_page_url(keywords, page_no)
            (image_page_urls, next_page_exists) = self._get_search_results(search_page_url)

            # Extract the image URLs from the search results and download the images
            for image_page_url in image_page_urls:
                image_url =  self._get_image_url(image_page_url)
                image_filename = self._download_image(dir_name, image_url)
                image_count += 1

                if (self.__verbose):
                    print("Saving image", image_url) 
                    print("     as", image_filename)
                
            if (not next_page_exists):
                break
    
        return image_count

        
    def _ensure_dir_exists(self, dir_name):
        """Check if the directory exists. If not, create one"""
        
        if (not os.path.isdir(dir_name)):
            try:
                os.makedirs(dir_name)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise            
        
    def _get_search_page_url(self, keywords, page_no):
        """Construct the URL of the search page based on the keywords and the page number"""
        
        fragment = quote(" ".join(keywords))
        url = urljoin(self.__search_page_base_url, fragment)
        
        if (page_no > 1):
            next_page_query = "?" + urlencode({"page" : str(page_no)})
            url += next_page_query
        
        return url
        
        
    def _get_search_results(self, search_url):
        """Get the search result page and extract the image URLs and Next Page indicator from it"""
        
        response = requests.get(search_url, headers = self.__headers)
        response.raise_for_status()
        
        search_page_parser = bs4.BeautifulSoup(response.text, "html.parser")
        image_tags = search_page_parser.find_all("img", attrs={"class" : "flowImage lazy"})
        
        # Yeah, I should have raised an exception if <img> tag's parent is not <a href="..."> 
        # but it is fun to use map/filter/lambda, so I am just filtering out <img> tags I cannot handle :-)  
        image_page_urls = map(lambda image_tag : urljoin(self.__image_page_base_url, image_tag.parent["href"]), 
                            filter(lambda image_tag : image_tag.parent["href"] is not None, image_tags))
        
        next_page_exists = (search_page_parser.find("a", attrs={"class" : "buttonbottomnext"}) is not None)                 

        return (image_page_urls, next_page_exists)
    
            
    def _get_image_url(self, image_page_url):
        """Get the image page and extract the image URL from it"""
        
        response = requests.get(image_page_url, headers = self.__headers)
        response.raise_for_status()
                        
        image_page_parser = bs4.BeautifulSoup(response.text, "html.parser")
        image_tag = image_page_parser.find("img", attrs={"id" : "mainimage"})
        if (image_tag is None):
            raise ValueError("Unexpected image page: missing link to the image")

        return image_tag["src"]
    
    
    def _download_image(self, dir_name, image_url):
        """Download the specified image and save it on disk"""
        
        response = requests.get(image_url, headers = self.__headers)
        response.raise_for_status()

        image_name = urlparse(image_url).path.split("/")[-1]
        if not image_name:
            raise ValueError("Unexpected image URL: no file name provided")
        
        full_filename = self._get_safe_filename(dir_name, image_name)        
        with open(full_filename, "wb") as image_file:
            for chunk in response.iter_content(self.__chunk_size):
                image_file.write(chunk)
                
        return full_filename
        
        
    def _get_safe_filename(self, dir_name, proposed_name):
        """Check if the file already exists; if so, add a unique suffix to it"""
        
        full_filename = os.path.join(dir_name, proposed_name)
        if (os.path.isfile(full_filename)):
            filename, extension = os.path.splitext(full_filename)
            if (not extension):
                extension = ".jpg"
            full_filename = filename + "_" + uuid.uuid4().hex + extension
            
        return full_filename


def main():
    """An entry point for console script"""
    retriever = NYCartoonRetriever()
    sys.exit(retriever.main())

        
if __name__ == "__main__":
    main()
