#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import requests
import time
from urllib.parse import urlparse, parse_qs, urlencode
from bs4 import BeautifulSoup
import random
import string

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
        response = requests.get(url, params=params, timeout=args.timeout, allow_redirects=True)
        rate_limited_requester.last_call = time.time()
        verbose_print(f"Received response with status code {response.status_code}")
        return response
    except requests.exceptions.RequestException as e:
        verbose_print(f"Error occurred while requesting {url}: {str(e)}")
        return None

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def compare_responses(response1, response2, param, test_value):
    if response1 is None or response2 is None:
        return False
    
    if response1.status_code != response2.status_code:
        return True
    
    if abs(len(response1.content) - len(response2.content)) > 100:
        return True
    
    soup1 = BeautifulSoup(response1.text, 'html.parser')
    soup2 = BeautifulSoup(response2.text, 'html.parser')
    
    # Check if the parameter value appears in the response
    if test_value in soup2.get_text() and test_value not in soup1.get_text():
        return True
    
    # Check for significant changes in the page structure
    if len(soup1.find_all()) != len(soup2.find_all()):
        return True
    
    return False

def test_parameter(url, param):
    base_response = rate_limited_requester(url)
    if base_response is None:
        return False

    test_value = generate_random_string()
    param_response = rate_limited_requester(url, {param: test_value})

    if param_response is None:
        return False

    return compare_responses(base_response, param_response, param, test_value)

def discover_parameters(url, wordlist):
    existing_params = parse_qs(urlparse(url).query)
    discovered_params = []
    
    for param in wordlist:
        if param not in existing_params and test_parameter(url, param):
            discovered_params.append(param)
            verbose_print(f"Discovered parameter: {param}")
    
    return discovered_params

def construct_url_with_params(url, params):
    parsed_url = urlparse(url)
    existing_params = parse_qs(parsed_url.query)
    
    for param in params:
        if param not in existing_params:
            existing_params[param] = ['value']
    
    new_query = urlencode(existing_params, doseq=True)
    return parsed_url._replace(query=new_query).geturl()

def main():
    parser = argparse.ArgumentParser(description="Parameter Hunter - Discover hidden parameters in URLs")
    parser.add_argument('-w', '--wordlist', help='Wordlist file path (required)', required=True)
    parser.add_argument('-r', '--rate-limit', help='Rate limit (requests per second)', type=float, default=10)
    parser.add_argument('-t', '--timeout', help='Timeout for requests (seconds)', type=float, default=10)
    parser.add_argument('-v', '--verbose', help='Enable verbose output', action='store_true')
    global args
    args = parser.parse_args()

    verbose_print.is_verbose = args.verbose

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
                verbose_print(f"No new parameters found for: {url}")
        except Exception as e:
            verbose_print(f"Error processing URL {url}: {str(e)}")

if __name__ == "__main__":
    main()
