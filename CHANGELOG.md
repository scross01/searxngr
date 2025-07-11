Change Log
==========

- added configuration options for authenticating to searxng sites using basic auth
- improved error handling for config file issues

## v0.4.3

- fixed `--url-handler` option

## v0.4.2

- fixed issue when `categories` not set in the configuration file
- fixed handling of empty `categories` and `engines` entries in configuration file

## v0.4.1

- fixed issue when searching using multiple categories
- fixed issue with the `--social` category selection option

## v0.4.0

- fixed category shortcut command line option issues and added `--files` and `--music`  options
- fixed issue where default cateogry selection was peventing engine selection
- output now shows all engines that provided the result, not just the primary response
- added `--timeout` command line and configuraiton option
- added `s` prompt option to show the current settings
- added `d` prompt to toggle debug mode
- added `j index` prompt to output the full json of a specfic result
- added `t time-range` prompt to change the search time range (e.g. `t week`)
- added `site:` prompt to change the site filter
- improved prompt handling and error handling

## v0.3.0

- added `n`, `p`, `f` prompt options to fetch the next, prev or first set of search results based on the result count size
- added `x` prompt option to toggle url expansion
- interactive console now maintains a history of commands and queries
- added `c index` prompt option to copy url to clipboard
- added `--nocolor` command line option to disable rich color formatted output to terminal
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
