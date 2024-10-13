#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import time
from urllib.parse import urlparse, urlencode
import requests

def verbose_print(*args, **kwargs):
    if verbose_print.is_verbose:
        print(*args, file=sys.stderr, **kwargs)

verbose_print.is_verbose = False

def rate_limited_requester(url, params=None):
    if hasattr(rate_limited_requester, 'last_call'):
        elapsed = time.time() - rate_limited_requester.last_call
        if elapsed < 1 / args.rate_limit:
            time.sleep(1 / args.rate_limit - elapsed)
    
    verbose_print(f"Sending request to {url} with params {params}")
    try:
        response = requests.get(url, params=params, timeout=args.timeout, allow_redirects=not args.disable_redirects)
        rate_limited_requester.last_call = time.time()
        verbose_print(f"Received response with status code {response.status_code}")
        return response
    except requests.exceptions.RequestException as e:
        verbose_print(f"Error occurred while requesting {url}: {str(e)}")
        return None

def compare_responses(response1, response2):
    if response1 is None or response2 is None:
        return False
    return response1.text != response2.text or response1.status_code != response2.status_code

def test_parameters(url, params):
    base_response = rate_limited_requester(url)
    param_response = rate_limited_requester(url, params)
    return compare_responses(base_response, param_response)

def chunk_wordlist(wordlist, chunk_size):
    for i in range(0, len(wordlist), chunk_size):
        yield wordlist[i:i + chunk_size]

def discover_parameters(url, wordlist):
    discovered_params = []
    chunk_size = min(args.chunk_size, len(wordlist))
    
    for chunk in chunk_wordlist(wordlist, chunk_size):
        test_params = {param: 'test_value' for param in chunk}
        if test_parameters(url, test_params):
            # If the chunk produces a different response, test each parameter individually
            for param in chunk:
                if test_parameters(url, {param: 'test_value'}):
                    discovered_params.append(param)
                    verbose_print(f"Discovered parameter: {param}")
    
    return discovered_params

def construct_url_with_params(url, params):
    parsed_url = urlparse(url)
    query = urlencode({param: 'value' for param in params})
    
    if parsed_url.query:
        new_query = f"{parsed_url.query}&{query}"
    else:
        new_query = query

    return parsed_url._replace(query=new_query).geturl()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', help='Wordlist file path (required)', dest='wordlist', required=True)
    parser.add_argument('-r', help='Rate limit (requests per second)', type=float, dest='rate_limit', default=10)
    parser.add_argument('-t', help='Timeout for requests (seconds)', type=float, dest='timeout', default=10)
    parser.add_argument('-c', help='Chunk size for large wordlists', type=int, dest='chunk_size', default=20)
    parser.add_argument('--disable-redirects', help='Disable following redirects', action='store_true')
    parser.add_argument('-v', '--verbose', help='Enable verbose output', action='store_true')
    global args
    args = parser.parse_args()

    verbose_print.is_verbose = args.verbose

    verbose_print("Starting parameter hunter")
    verbose_print(f"Configuration: {vars(args)}")

    try:
        with open(args.wordlist, 'r') as f:
            wordlist = [line.strip() for line in f if line.strip()]
        verbose_print(f"Loaded wordlist with {len(wordlist)} entries")
    except FileNotFoundError:
        print(f"Error: Wordlist file '{args.wordlist}' not found.", file=sys.stderr)
        sys.exit(1)
    except IOError:
        print(f"Error: Unable to read wordlist file '{args.wordlist}'.", file=sys.stderr)
        sys.exit(1)

    if not wordlist:
        print("Error: Wordlist is empty.", file=sys.stderr)
        sys.exit(1)

    for url in sys.stdin:
        url = url.strip()
        verbose_print(f"\nProcessing URL: {url}")
        try:
            discovered_params = discover_parameters(url, wordlist)
            if discovered_params:
                full_url = construct_url_with_params(url, discovered_params)
                print(full_url)
            else:
                verbose_print(f"No parameters found for: {url}")
        except Exception as e:
            verbose_print(f"Error processing URL {url}: {str(e)}")

    verbose_print("Parameter hunting completed")

if __name__ == '__main__':
    main()
