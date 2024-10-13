# ParamHunter

ParamHunter is a powerful and flexible tool for discovering hidden parameters in web applications. Built upon the foundation of the Arjun project, ParamHunter offers enhanced functionality and improved performance for parameter discovery.

## Features

- Efficient parameter discovery using various techniques
- Rate limiting to prevent overwhelming target servers
- Verbose output option for detailed process information
- Customizable wordlists for parameter guessing
- Handles GET requests with discovered parameters

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/paramhunter.git
   cd paramhunter
   ```

2. Install the required dependencies:
   ```
   pip install requests ratelimit urllib3
   ```

3. Ensure you have Python 3.6 or higher installed.

## Usage

Basic usage:

```
cat urls.txt | python3 paramhunter.py -w wordlist.txt
```

This will process the URLs from `urls.txt`, using `wordlist.txt` as the source of potential parameter names.

### Options

- `-w FILE`: Specify the wordlist file (required)
- `-c INT`: Set the chunk size for processing (default: 250)
- `-r FLOAT`: Set the rate limit in requests per second (default: 10)
- `-t FLOAT`: Set the timeout for requests in seconds (default: 5)
- `--disable-redirects`: Disable following redirects
- `-v, --verbose`: Enable verbose output

### Example with Verbose Output

```
cat urls.txt | python3 paramhunter.py -w wordlist.txt -v -r 5 -t 10
```

This will run ParamHunter with verbose output, a rate limit of 5 requests per second, and a timeout of 10 seconds per request.

## Output

ParamHunter outputs the full HTTP GET requests for each URL, including any discovered parameters. In verbose mode, it also provides detailed information about the discovery process.

## Contributing

Contributions to ParamHunter are welcome! Please feel free to submit pull requests, create issues or spread the word.

## License

[MIT License](LICENSE)

## Acknowledgements

ParamHunter is based on the [Arjun](https://github.com/s0md3v/Arjun) project by s0md3v. We express our gratitude for their excellent work in the field of web parameter discovery.

## Disclaimer

ParamHunter is intended for use in authorized security testing only. Users are responsible for complying with applicable laws and regulations. The developers assume no liability for misuse or damage caused by this program.
