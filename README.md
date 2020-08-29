# Project Description
Search for and download cartoons from The New Yorker magazine cartoon gallery.

# Install 
```
    python -m pip install --upgrade newyorker
```

# Running as Script
```
    Usage: 
        newyorker search-keyword-list [options]

    Options:
        --outdir, -o    Set the output directory for cartoons.
        --verbose, -v   Show progress trace.
        --headers       Set the HTTP headers for the requests.
        --help, -h      Print help. 
        --version       Print the script version.

    Examples:
        newyorker email --verbose
        newyorker design desk -v -o ~/example/cartoons
        newyorker santa -v --headers \
            '{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36"}'
```

# Using API
```
    from newyorker.cartoons import NYCartoonRetriever

    #  Windows-style output folder
    retriever = NYCartoonRetriever(outdir = r"c:\python\example", verbose = True, \
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36"})
    image_count = retriever.retrieve(["email"])
```

# Testing
```
    python -m unittest tests.test_basic
```

# Disclaimer
This project is not associated with The New Yorker magazine.


