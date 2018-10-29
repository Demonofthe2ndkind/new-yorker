'''
Created on Jun 10, 2018

@author: Demon of the Second Kind
'''
import os
import sys
import errno
import itertools
import requests
import bs4

class CartoonRetriever: 
    
    __all__ = []
    __version__ = 1.0
    __date__ = '2018-06-10'
    __updated__ = '2018-06-10'
    
    
    def __init__(self):
        self.__chunk_size = 100000
        self.__search_page_base_url = "https://condenaststore.com/collections/new+yorker+cartoons/"    
        self.__user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36"
        self.__headers = {"User-Agent": self.__user_agent}
        
    
    def main(self):
        '''Retrieves New Yorker magazine cartoons by keyword(s) and saves them in the specified directory''' 
        
        # Handle command line arguments and options
        from optparse import OptionParser
        
        program_name = os.path.basename(sys.argv[0])
        program_version = "v%.2f" % CartoonRetriever.__version__
        program_build_date = "%s" % CartoonRetriever.__updated__
    
        program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
        program_usage = '''usage: %prog search-keyword(s) [-o output-directory-for-cartoons]''' 
        program_longdesc = '''Retrieves NY cartoons by keyword(s) and saves them in the specified directory'''
        program_license = "Copyright 2018 Demon of the Second Kind                                            \
                    Licensed under the Apache License 2.0\nhttp://www.apache.org/licenses/LICENSE-2.0"
    
        argv = sys.argv[1:]
            
        try:
            # setup option parser
            parser = OptionParser(program_usage, version=program_version_string, epilog=program_longdesc, description=program_license)
            parser.add_option("-o", "--out", dest="outdir", help="set base directory to save cartoons [default: %default]", metavar="DIR")
            parser.add_option("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %default]")
    
            # set defaults
            parser.set_defaults(outdir=os.path.join(os.path.curdir, "cartoons"), verbose=0)
    
            # process args and options
            (opts, args) = parser.parse_args(argv)
            
            if (len(args) == 0):
                parser.error("At least one search keyword needs to be specified")
    
            if (opts.verbose > 0):
                print("verbosity level = %d" % opts.verbose)
                print("keywords = %s" % " ".join(args))
                print("base directory = %s" % opts.outdir)
                
            keywords = list(args)
            dir_name = opts.outdir
                            
            # Make sure directory exists; if not, create one
            keywords.sort()
            dir_name = os.path.join(dir_name, "-".join(keywords))
            self._ensure_dir_exists(dir_name)
            
            # Search for and download the cartoon files
            images_downloaded = 0            
            for page_no in itertools.count(1):
                search_page_url = self._get_search_page_url(keywords, page_no)
                (image_page_urls, next_page_exists) = self._get_search_results(search_page_url)
                for image_page_url in image_page_urls:
                    image_url =  self._get_image_url(image_page_url)
                    image_filename = self._download_image(dir_name, image_url)
                    images_downloaded += 1
                    
                    if (opts.verbose > 0):
                        print("Saving image", image_url) 
                        print("     as", image_filename)
             
                if (not next_page_exists):
                    break
        
            # Print some stats
            if (opts.verbose > 0):
                print("Done. Images downloaded: %d" % images_downloaded)
            
            return 0
    
        except Exception as e:
            indent = len(program_name) * " "
            sys.stderr.write(program_name + ": " + repr(e) + "\n")
            sys.stderr.write(indent + "  for help use --help")
            
            return 2
        
        
    def _ensure_dir_exists(self, dir_name):
        '''Check if the directory exists. If not, create one'''
        
        if (not os.path.isdir(dir_name)):
            try:
                os.makedirs(dir_name)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise            
        
    def _get_search_page_url(self, keywords, page_no):
        '''Construct the URL of the search page based on the keywords and the page number'''
        
        from urllib.parse import urlencode
        from urllib.parse import urljoin
        from urllib.parse import quote
    
        fragment = quote(" ".join(keywords))
        url = urljoin(self.__search_page_base_url, fragment)
        
        if (page_no > 1):
            page_no_query = "?" + urlencode({"page" : str(page_no)})
            url += page_no_query
        
        return url
        
        
    def _get_search_results(self, search_url):
        '''Get the search result page and extract the image URLs and Next Page indicator from it'''
        
        from urllib.parse import urljoin 
        
        response = requests.get(search_url, headers = self.__headers)
        response.raise_for_status()
        
        search_page_parser = bs4.BeautifulSoup(response.text, "html.parser")
        image_tags = search_page_parser.find_all("img", attrs={"class" : "imageSearchEngineProduct imageall"})
        
        # Yeah, I should have raised an exception if <img> tag's parent is not <a href="..."> 
        # but I was eager to try map/filter/lambda, so I just filtering out <img> tags I cannot handle :-)  
        image_page_urls = map(lambda image_tag : urljoin(self.__search_page_base_url, image_tag.parent["href"]), 
                              filter(lambda image_tag : image_tag.parent["href"] is not None, image_tags))
        
        next_page_exists = (search_page_parser.find("a", attrs={"id" : "linknext"}) is not None)        
         
        return (image_page_urls, next_page_exists)
    
            
    def _get_image_url(self, image_page_url):
        '''Get the image page and extract the image URL from it'''
        
        response = requests.get(image_page_url, headers = self.__headers)
        response.raise_for_status()
        
        image_page_parser = bs4.BeautifulSoup(response.text, "html.parser")
        image_tag = image_page_parser.find("img", attrs={"id" : "mainimage"})
        if (image_tag is None):
            raise ValueError("Unexpected image page: missing link to the image")
        
        return image_tag["src"]
    
    
    def _download_image(self, dir_name, image_url):
        '''Download the specified image and save it on disk'''
        
        from urllib.parse import urlparse
        response = requests.get(image_url, headers = self.__headers)
        response.raise_for_status()

        try:        
            image_name = urlparse(image_url).path.split('/')[-1]
        except Exception:
            raise  ValueError("Unexpected image URL: no file name provided")
        
        full_filename = self._get_safe_filename(dir_name, image_name)        
        with open(full_filename, "wb") as image_file:
            for chunk in response.iter_content(self.__chunk_size):
                image_file.write(chunk)
                
        return full_filename
        
        
    def _get_safe_filename(self, dir_name, proposed_name):
        '''Check if the file already exists; if so, add a unique suffix to it'''
        
        import uuid
        
        full_filename = os.path.join(dir_name, proposed_name)
        if (os.path.isfile(full_filename)):
            filename, extension = os.path.splitext(full_filename)
            if (not extension):
                extension = ".jpg"
            full_filename = filename + "_" + uuid.uuid4().hex + extension
            
        return full_filename
        
        
if __name__ == "__main__":
    retriever = CartoonRetriever()
    sys.exit(retriever.main())
