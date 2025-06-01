Change Log
==========

## v0.3.0-dev

- added `--json` command line option to output the query response json and exit
- added `--config` command line option to open configuraiton file in system default editor
- added support for `--categories` to get results from multiple sections
- added `-N`, `--news` command line option to only get results from news section
- added `-V`, `--videos` command line option to only get results from videos section
- added `-S`, `--social` command line option to only get results from social section

## v0.2.3

- updated packaging and build system resolve install issues
- show usage and exit if no search query provided
- improved ssl verification error handling
- strip non printable characters from url

## v0.2.2

- fixed issue `--engines` command line option

## v0.2.1

- fixed missing time option in help output

## v0.2.0

- fixed multi-page queries when `--num N` was greater that the initial result size
- added `--np` and `--noprompt` options to just search and exit
- added `-l` `--language` command line options and `language` configuration option to set search result language prefernece
- added `-j` `--first` command line option to open the first result and exit
- added `--lucky` command line option to open a random result and exit
- added `week` option to `--time-range` option and enabled `d`, `w`, `m`, `y` as short codes
- added `--unsafe` command line option as alternative for `--safe-search none`
- added `--version` command line option
- switch from using requests to httpx
- added default http headers set User Agent
- added `--http-method` command line and `http_method` configuration option to use GET of POST for querys
- added `--no-verify-ssl` command line and `no-verify-ssl` configuraiton option for sites with self signed ccertificates
- added `--noua` command line option to disable User Agent

## v0.1.0

- Initial release
