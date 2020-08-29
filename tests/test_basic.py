import unittest
from unittest import mock

from newyorker.cartoons import NYCartoonRetriever

import os
from requests.exceptions import HTTPError
import tempfile
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.parse import urljoin
from urllib.parse import urlparse
import uuid
import yaml


class TestPrivateMethods(unittest.TestCase):

    def setUp(self):
        self.base_dir_name = os.path.join(os.path.curdir, "cartoons")
        self.retriever = NYCartoonRetriever(outdir = self.base_dir_name)

        # Load the test data to use in the tests
        data_file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/test_data.yaml") 
        with open(data_file_name) as data_file:      
            self.test_data = yaml.load(data_file, yaml.SafeLoader)


    def _build_mock_response(self, status = 200, text = "", iter_content = [], raise_for_status = None):
        """Build a mock requests.Response object"""
        mock_resp = mock.Mock()

        mock_resp.status_code = status
        mock_resp.text = text

        mock_resp.iter_content = mock.Mock()
        mock_resp.iter_content.side_effect = iter([iter_content])

        mock_resp.raise_for_status = mock.Mock()
        if raise_for_status:
            mock_resp.raise_for_status.side_effect = raise_for_status

        return mock_resp


    def test_get_safe_filename(self):
        """Test getting a safe file name for an image file"""
        
        with tempfile.TemporaryDirectory() as dir_name:  
            fileext = ".jpg"

            # File name should stay the same for unique name
            proposed_safe_filename = uuid.uuid4().hex + fileext
            actual_name = self.retriever._get_safe_filename(dir_name, proposed_safe_filename)
            self.assertEqual(os.path.join(dir_name, proposed_safe_filename), actual_name, \
                msg="The proposed file name should stay the same for a unique name.")

            # File should change for an existing file
            with tempfile.NamedTemporaryFile("a", dir = dir_name, suffix = fileext) as file:
                proposed_safe_filename = file.name
                actual_name = self.retriever._get_safe_filename(dir_name, proposed_safe_filename)
                self.assertNotEqual(os.path.join(dir_name, proposed_safe_filename), actual_name, \
                    msg="The proposed file name should have changed if is not a unique name.")


    @mock.patch("newyorker.cartoons.requests.get")
    def test_download_image(self, mock_get):
        """Test downloading an image by URL"""

        # Test the good url first
        image_url = self.test_data["good_image_url"]["url"]
        image_data = self.test_data["good_image_url"]["image_data"]

        mock_get.return_value = self._build_mock_response(iter_content = [bytes.fromhex(image_data)])

        with tempfile.TemporaryDirectory() as dir_name:          
            full_filename = self.retriever._download_image(dir_name, image_url)
            with open(full_filename, "rb") as read_back_file:
                chunk = read_back_file.read(100)

            self.assertEqual(bytes.fromhex(image_data), \
                chunk, msg = "For the 'good' image URL, the image data written must match the test data")

        # Test the url that missing file name
        image_url = self.test_data["bad_image_url"]["url"]
        image_data = self.test_data["bad_image_url"]["image_data"]

        mock_get.return_value = self._build_mock_response(iter_content = [bytes.fromhex(image_data)])

        with tempfile.TemporaryDirectory() as dir_name:
            with self.assertRaises(ValueError, msg = "URLs without file name in them must raise an exception"):
                full_filename = self.retriever._download_image(dir_name, image_url)

        # Test the rection to a HTTP error
        image_url = self.test_data["good_image_url"]["url"]
        image_data = self.test_data["good_image_url"]["image_data"]

        mock_get.return_value = self._build_mock_response(status = 500, raise_for_status = HTTPError('Server-side error'))

        with tempfile.TemporaryDirectory() as dir_name:          
            with self.assertRaises(Exception, msg = "HTTP errors must raise an exception"):
                full_filename = self.retriever._download_image(dir_name, image_url)


    def test_ensure_dir_exists(self):
        """There is really nothing to test there"""
        pass


    @mock.patch("newyorker.cartoons.requests.get")
    def test_get_image_url(self, mock_get):
        """ Test extracting image tag(s) from the page retrived by the image page URL"""

        image_page_url = self.test_data["image_page_url"]
        image_page_response = self.test_data["image_page_response"]
        image_tag_src = self.test_data["image_tag_src"]
        
        mock_get.return_value = self._build_mock_response(text = image_page_response)

        self.assertEqual(self.retriever._get_image_url(image_page_url), \
            image_tag_src, msg = "Unable to extract image tag from the image page")


    def test_get_search_page_url(self):
        """Test building the search page URL"""

        keywords = ["design", "desk"]
        search_page_base_url = self.test_data["search_page_base_url"]

        fragment = quote(" ".join(keywords))
        url = urljoin(search_page_base_url, fragment)

        self.assertEqual(self.retriever._get_search_page_url(keywords, 1),  url, \
            msg = "The search page URL is malformed" )

        next_page_query = "?" + urlencode({"page" : str(2)})
        url += next_page_query

        self.assertEqual(self.retriever._get_search_page_url(keywords, 2),  url, \
            msg = "The search page URL is malformed" )


    @mock.patch("newyorker.cartoons.requests.get")
    def test_get_search_results(self, mock_get):
        """Test of running a search and parsing the results page"""

        search_url = self.test_data["search_url"]
        search_response = self.test_data["search_response"]
        image_page_urls = self.test_data["image_page_urls"]
        next_page_exists = self.test_data["next_page_exists"]
        
        mock_get.return_value = self._build_mock_response(text = search_response)

        (actual_image_page_urls, actual_next_page_exists) = self.retriever._get_search_results(search_url)

        self.assertEqual(list(actual_image_page_urls), \
            image_page_urls, msg = "Unable to extract image tags from the search page")

        self.assertEqual(actual_next_page_exists, \
            next_page_exists, msg = "Incorrect next-page-exists indicator detected")

    
    @mock.patch("newyorker.cartoons.NYCartoonRetriever._get_search_results")
    @mock.patch("newyorker.cartoons.NYCartoonRetriever._get_image_url")
    @mock.patch("newyorker.cartoons.NYCartoonRetriever._download_image")
    def test_retrieve(self, mock_download_image, mock_get_image_url, mock_get_search_results):
        """Test full functionality of cartoon retrieval"""
        # Note the mock function paramters must be in reverse order of @patch decorations

        # Test the empty / None keywords first
        with self.assertRaises(Exception, msg = "Missing keywords must throw an exception"):
            self.retriever.retrieve(None)

        with self.assertRaises(Exception, msg = "Missing keywords must throw an exception"):
            self.retriever.retrieve([])

        # Test a proper keyword list
        keywords = ["email"]
        image_page_url = self.test_data["image_page_url"]
        image_tag_src = self.test_data["image_tag_src"]

        mock_get_search_results.return_value = ([image_page_url], None)
        mock_get_image_url.return_value = image_tag_src
        mock_download_image.return_value = self.retriever._get_safe_filename(self.base_dir_name, \
            urlparse(image_tag_src).path.split("/")[-1])

        self.assertEqual(self.retriever.retrieve(keywords), \
            1, msg = "Something wrong with the retrival logic")
