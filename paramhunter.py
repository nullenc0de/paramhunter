#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import re
import time
from urllib.parse import urlparse, urlencode
import requests

import arjun.core.config as mem
from arjun.core.utils import populate, confirm
from arjun.core.anomaly import define, compare
from arjun.plugins.heuristic import heuristic

def verbose_print(*args, **kwargs):
    if mem.var['verbose']:
        print(*args, file=sys.stderr, **kwargs)

def safe_slicer(dic, n):
    if not dic or n <= 0:
        return [dic]
    k, m = divmod(len(dic), n)
    return [dict(list(dic.items())[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]) for i in range(n)]

def rate_limited_requester(url, payload={}):
    if hasattr(rate_limited_requester, 'last_call'):
        elapsed = time.time() - rate_limited_requester.last_call
        if elapsed < 1 / mem.var['rate_limit']:
            time.sleep(1 / mem.var['rate_limit'] - elapsed)
    
    verbose_print(f"Sending request to {url} with payload {payload}")
    try:
        response = requests.get(url, params=payload, timeout=mem.var['timeout'], allow_redirects=not mem.var['disable_redirects'])
        rate_limited_requester.last_call = time.time()
        verbose_print(f"Received response with status code {response.status_code}")
        return response
    except requests.exceptions.Timeout:
        verbose_print(f"Request to {url} timed out")
        return None
    except requests.exceptions.RequestException as e:
        verbose_print(f"Error occurred while requesting {url}: {str(e)}")
        return None

def bruter(url, factors, params):
    verbose_print(f"Bruteforcing with params: {params}")
    response = rate_limited_requester(url, params)
    if response is None:
        return []
    conclusion = compare(response, factors, params)
    verbose_print(f"Bruter conclusion: {conclusion}")
    return conclusion[1] if conclusion[0] != '' else []

def narrower(url, factors, param_groups):
    anomalous_params = []
    for i, params in enumerate(param_groups):
        verbose_print(f"Narrowing down group {i+1}/{len(param_groups)}")
        result = bruter(url, factors, params)
        if result:
            anomalous_params.extend(safe_slicer(dict(result), 2))
        if mem.var['kill']:
            return anomalous_params
    return anomalous_params

def initialize(url, wordlist):
    verbose_print(f"Initializing for URL: {url}")
    if not url.startswith('http'):
        verbose_print("URL doesn't start with http, skipping")
        return 'skipped'
    
    fuzz = "z" + ''.join([chr(i) for i in range(97, 103)])  # "zabcdef"
    verbose_print("Sending initial fuzz requests")
    response_1 = rate_limited_requester(url, {fuzz[:-1]: fuzz[::-1][:-1]})
    response_2 = rate_limited_requester(url, {fuzz[:-1]: fuzz[::-1][:-1]})
    
    if response_1 is None or response_2 is None:
        verbose_print("Invalid responses received, skipping")
        return 'skipped'

    verbose_print("Running heuristic analysis")
    found, _ = heuristic(response_1, wordlist)
    verbose_print(f"Heuristic found parameters: {found}")
    
    verbose_print("Defining factors")
    factors = define(response_1, response_2, fuzz, fuzz[::-1], wordlist)
    
    verbose_print("Populating parameter groups")
    populated = populate(wordlist)
    param_groups = safe_slicer(populated, mem.var['chunks'])
    
    last_params = []
    while param_groups:
        verbose_print(f"Narrowing down {len(param_groups)} parameter groups")
        param_groups = narrower(url, factors, param_groups)
        param_groups = confirm(param_groups, last_params)
        if not param_groups:
            break

    confirmed_params = []
    for param in last_params:
        if validate_parameter(url, param):
            name = list(param.keys())[0]
            confirmed_params.append(name)
    
    verbose_print(f"Confirmed parameters: {confirmed_params}")
    return confirmed_params

def validate_parameter(url, param):
    verbose_print(f"Validating parameter: {param}")
    return (
        validate_by_response_diff(url, param) or
        validate_by_error_message(url, param) or
        validate_by_reflection(url, param) or
        validate_by_content_length(url, param)
    )

def validate_by_response_diff(url, param):
    verbose_print("Validating by response difference")
    response1 = rate_limited_requester(url, {})
    response2 = rate_limited_requester(url, param)
    if response1 is None or response2 is None:
        return False
    return compare(response1, response2, param)[0] != ''

def validate_by_error_message(url, param):
    verbose_print("Validating by error message")
    response = rate_limited_requester(url, param)
    if response is None:
        return False
    error_patterns = [
        r"(?i)error",
        r"(?i)invalid",
        r"(?i)required",
        r"(?i)missing"
    ]
    return any(re.search(pattern, response.text) for pattern in error_patterns)

def validate_by_reflection(url, param):
    verbose_print("Validating by reflection")
    param_name = list(param.keys())[0]
    param_value = "UNIQUE_REFLECT_STRING"
    response = rate_limited_requester(url, {param_name: param_value})
    if response is None:
        return False
    return param_value in response.text

def validate_by_content_length(url, param):
    verbose_print("Validating by content length")
    response1 = rate_limited_requester(url, {})
    response2 = rate_limited_requester(url, param)
    if response1 is None or response2 is None:
        return False
    return abs(len(response1.content) - len(response2.content)) > 100  # arbitrary threshold

def construct_request(url, params):
    verbose_print(f"Constructing request for URL: {url} with params: {params}")
    parsed_url = urlparse(url)
    query = urlencode({param: 'value' for param in params})
    
    if parsed_url.query:
        new_query = f"{parsed_url.query}&{query}"
    else:
        new_query = query

    new_url = parsed_url._replace(query=new_query).geturl()
    
    request_lines = [f"GET {new_url} HTTP/1.1",
                     f"Host: {parsed_url.netloc}",
                     "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                     "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                     "Accept-Language: en-US,en;q=0.5",
                     "Accept-Encoding: gzip, deflate",
                     "Connection: close",
                     "Upgrade-Insecure-Requests: 1",
                     "",
                     ""]

    return '\n'.join(request_lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', help='Wordlist file path (required)', dest='wordlist', required=True)
    parser.add_argument('-c', help='Chunk size', type=int, dest='chunks', default=250)
    parser.add_argument('-r', help='Rate limit (requests per second)', type=float, dest='rate_limit', default=10)
    parser.add_argument('-t', help='Timeout for requests (seconds)', type=float, dest='timeout', default=10)
    parser.add_argument('--disable-redirects', help='Disable following redirects', action='store_true')
    parser.add_argument('-v', '--verbose', help='Enable verbose output', action='store_true')
    args = parser.parse_args()

    mem.var = vars(args)
    mem.var['kill'] = False  # Initialize kill switch
    
    # Ensure chunks is at least 1
    mem.var['chunks'] = max(1, mem.var['chunks'])

    verbose_print("Starting parameter hunter")
    verbose_print(f"Configuration: {mem.var}")

    try:
        with open(args.wordlist, 'r') as f:
            wordlist = set(f.read().splitlines())
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
            these_params = initialize(url, list(wordlist))
            
            if these_params and these_params != 'skipped':
                full_request = construct_request(url, these_params)
                print(full_request)
            else:
                verbose_print(f"No parameters found or URL skipped for: {url}")
        except Exception as e:
            verbose_print(f"Error processing URL {url}: {str(e)}")

    verbose_print("Parameter hunting completed")

if __name__ == '__main__':
    main()
