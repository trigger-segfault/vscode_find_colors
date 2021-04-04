#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""Read VS Code theme colors and output them in a terminal
"""

__version__ = '1.0.0'
__date__    = '2021-04-03'
__author__  = 'Robert Jordan'
__credits__ = '''JSON cleanup by Dan McDougall <daniel.mcdougall@liftoffsoftware.com>
source: <https://gist.github.com/liftoff/ee7b81659673eca23cd9fc0d8b8e68b7>'''

# VSCODE DEFAULT THEMES
# <https://github.com/microsoft/vscode/tree/main/extensions/theme-defaults/themes>

#######################################################################################

import json, os, re
from collections import namedtuple, OrderedDict
from types import SimpleNamespace
from typing import Dict, Iterable, Iterator, List, Tuple


## COLOR TUPLES ##

RGB = namedtuple('RGB', ('r', 'g', 'b'))
HSV = namedtuple('HSV', ('hue', 'sat', 'val'))


## TERMINAL COLOR HELPERS ##

# normal color namespaces
# this expects Windows Terminal or equivalent terminal color code support
Fore = SimpleNamespace(BLACK='\x1b[30m', BLUE='\x1b[34m', CYAN='\x1b[36m', GREEN='\x1b[32m', MAGENTA='\x1b[35m', RED='\x1b[31m', RESET='\x1b[39m', WHITE='\x1b[37m', YELLOW='\x1b[33m', LIGHTBLACK_EX='\x1b[90m', LIGHTBLUE_EX='\x1b[94m', LIGHTCYAN_EX='\x1b[96m', LIGHTGREEN_EX='\x1b[92m', LIGHTMAGENTA_EX='\x1b[95m', LIGHTRED_EX='\x1b[91m', LIGHTWHITE_EX='\x1b[97m', LIGHTYELLOW_EX='\x1b[93m')
Back = SimpleNamespace(BLACK='\x1b[40m', BLUE='\x1b[44m', CYAN='\x1b[46m', GREEN='\x1b[42m', MAGENTA='\x1b[45m', RED='\x1b[41m', RESET='\x1b[49m', WHITE='\x1b[47m', YELLOW='\x1b[43m', LIGHTBLACK_EX='\x1b[100m', LIGHTBLUE_EX='\x1b[104m', LIGHTCYAN_EX='\x1b[106m', LIGHTGREEN_EX='\x1b[102m', LIGHTMAGENTA_EX='\x1b[105m', LIGHTRED_EX='\x1b[101m', LIGHTWHITE_EX='\x1b[107m', LIGHTYELLOW_EX='\x1b[103m')
Style = SimpleNamespace(BRIGHT='\x1b[1m', DIM='\x1b[2m', NORMAL='\x1b[22m', RESET_ALL='\x1b[0m')

# dictionary for easier **foreground** color formatting
# >>> '{DIM}{GREEN}{!s}{RESET_ALL}'.format('hello world', **Colors)
Colors = dict(**Fore.__dict__, **Style.__dict__)

def terminal_rgb_text(hexrgb:str, text:str):
    rgb = hex2rgb(hexrgb)
    bg = ''
    if get_luminance(*rgb) < 0.1:
        bg = '\x1b[47;1m'
    fg = '\x1b[38;2;{};{};{}m'.format(*rgb)
    return '{bg}{fg}{}\x1b[0m'.format(text, bg=bg, fg=fg)

def terminal_hexrgb(hexrgb:str, bgcolor:bool=True):
    rgb = hex2rgb(hexrgb)
    BG_OR_FG = {False:'3', True:'4'}
    bg = '\x1b[{bg_or_fg}8;2;{};{};{}m'.format(*rgb, bg_or_fg=BG_OR_FG[bgcolor])
    if contrast_color(*rgb):
        fg = '\x1b[{fg_or_bg}7;1m'.format(fg_or_bg=BG_OR_FG[not bgcolor]) # white
    else:
        fg = '\x1b[{fg_or_bg}0m'.format(fg_or_bg=BG_OR_FG[not bgcolor])   # black
    return '{bg}{fg}{}\x1b[0m'.format(hexrgb, bg=bg, fg=fg)


## BASIC COLOR HELPERS ##

# def hex_to_rgb(hexrgb:str) -> Tuple[int,int,int]:
def hex2rgb(hexrgb:str) -> RGB:
    """hex2rgb('#RRGGBB') -> RGB(R, G, B)
    hex2rgb('#RGB') -> RGB(RR, GG, BB)
    """
    if not isinstance(hexrgb, str):
        raise TypeError('hex2rgb argument must be str, not {0.__class__.__name__} ({0!r})'.format(hexrgb))
    if re.match(r"^#[0-9A-Fa-f]{3}[Ff]?$", hexrgb):
        return RGB(int(hexrgb[1]*2, 16), int(hexrgb[2]*2, 16), int(hexrgb[3]*2, 16))
    elif re.match(r"^#[0-9A-Fa-f]{6}(?:[Ff]{2})?$", hexrgb):
        return RGB(int(hexrgb[1:3], 16), int(hexrgb[3:5], 16), int(hexrgb[5:7], 16))
    else:
        raise ValueError('Unexpected color format {!r}'.format(hexrgb))

# def rgb_to_hsv(r:int, g:int, b:int) -> Tuple[float,float,float]:
def rgb2hsv(r:int, g:int, b:int) -> HSV:
    """rgb2hsv(r,g,b) -> HSV(0~360, 0~100, 0~100)

    source: <https://www.w3resource.com/python-exercises/math/python-math-exercise-77.php>
    """
    r, g, b = r/255.0, g/255.0, b/255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx-mn
    if  mx == mn: h = 0
    elif mx == r: h = (60 * ((g-b)/df) + 360) % 360
    elif mx == g: h = (60 * ((b-r)/df) + 120) % 360
    elif mx == b: h = (60 * ((r-g)/df) + 240) % 360
    if mx == 0: s = 0
    else:       s = (df/mx)*100
    v = mx*100
    return HSV(h, s, v)

def hex2hsv(hexstr:str) -> HSV:
    """hex2hsv('#RRGGBB') -> rgb2hsv(R, G, B) -> HSV(0~360, 0~100, 0~100)
    hex2hsv('#RGB') -> rgb2hsv(RR, GG, BB) -> HSV(0~360, 0~100, 0~100)
    """
    return rgb2hsv(*hex2rgb(hexstr))

def normalize_hexrgb(hexrgb:str) -> str:
    """normalize_hexrgb('#Ffe34D') -> '#ffe34D'
    normalize_hexrgb('#c1A') -> '#cc11aa'
    """
    rgb = hex2rgb(hexrgb)
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def sort_by_hsv(hexrgb:str) -> float:
    if hexrgb is None:
        # higher than max hue, sat, val
        return (360 * 100 * 100) + (100 * 100) + 1

    hue, sat, val = hex2hsv(hexrgb)
    SAT_THRESH = 5.0
    # rules:
    # color before grayscale
    # hue: 0-360
    # sat: (100-SAT_THRESH) * val: (100-0)
    #
    # then:
    # val: 100-0
    # sat: (SAT_THRESH-0) * val: (100-0)

    satval = (100-sat) * (100-val)
    if sat > SAT_THRESH: # not grayscale
        return (hue * 100 * 100) + satval
    else:
        # higher than max hue
        return (360 * 100 * 100) + satval

def get_luminance(r:int, g:int, b:int) -> float:
    """get_luminance(r, g, b) -> float

    source: <https://stackoverflow.com/a/1855903/7517185>
    """
    # Counting the perceptive luminance - human eye favors green color... 
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255

def contrast_color(r:int, g:int, b:int, *, black=False, white=True, threshold:float=0.5) -> bool:
    """contrast_color(r, g, b) -> black:False -or- white:True
    contrast_color(r, g, b, black=_, white=_) -> black -or- white

    source: <https://stackoverflow.com/a/1855903/7517185>
    """
    if get_luminance(r, g, b) > threshold:
        return black  # bright colors - black font
    else:
        return white  # dark colors - white font

def contrast_rgb(r:int, g:int, b:int, *, threshold:float=0.5) -> RGB:
    """contrast_rgb(r, g, b) -> RGB(0, 0, 0) -or- RGB(255, 255, 255)

    source: <https://stackoverflow.com/a/1855903/7517185>
    """
    if get_luminance(r, g, b) > threshold:
        return RGB(0, 0, 0)  # bright colors - black font
    else:
        return RGB(255, 255, 255)  # dark colors - white font


## JSON HELPERS ##

# VS Code json files are loose on the rules, so we need this

# <https://gist.github.com/liftoff/ee7b81659673eca23cd9fc0d8b8e68b7>
# __version__ = '1.0.0'
# __version_info__ = (1, 0, 0)
# __license__ = "Unlicense"
# __author__ = 'Dan McDougall <daniel.mcdougall@liftoffsoftware.com>'

def remove_comments(json_like):
    """
    Removes C-style comments from *json_like* and returns the result.  Example::
        >>> test_json = '''\
        {
            "foo": "bar", // This is a single-line comment
            "baz": "blah" /* Multi-line
            Comment */
        }'''
        >>> remove_comments('{"foo":"bar","baz":"blah",}')
        '{\n    "foo":"bar",\n    "baz":"blah"\n}'
    """
    comments_re = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    def replacer(match):
        s = match.group(0)
        if s[0] == '/': return ""
        return s
    return comments_re.sub(replacer, json_like)

def remove_trailing_commas(json_like):
    """
    Removes trailing commas from *json_like* and returns the result.  Example::
        >>> remove_trailing_commas('{"foo":"bar","baz":["blah",],}')
        '{"foo":"bar","baz":["blah"]}'
    """
    trailing_object_commas_re = re.compile(
        r'(,)\s*}(?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    trailing_array_commas_re = re.compile(
        r'(,)\s*\](?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    # Fix objects {} first
    objects_fixed = trailing_object_commas_re.sub("}", json_like)
    # Now fix arrays/lists [] and return the result
    return trailing_array_commas_re.sub("]", objects_fixed)


## THEME PARSER ##

class VSCodeThemeParser(object):
    def __init__(self):
        # scope-mapped data, populated by include()
        self._token_lookup:dict  = {}  # {scope: dict}  global lookup to overwritten entries
        self.color_scopes:dict  = {}  # {scope: color}
        self.style_scopes:dict  = {}  # {scope: (color, style)}
        self.normal_scopes:dict = {}  # {scope: None}

        # ordered color-mapped data, populated by build_color_map()
        self.colors:OrderedDict = OrderedDict()  # {color: [scopes]}
        self.styles:OrderedDict = OrderedDict()  # {style: {color: [scopes]}}
        self.normal:list = []  # [scopes]

    def clear(self):
        self._token_lookup.clear()
        self.color_scopes.clear()
        self.style_scopes.clear()
        self.normal_scopes.clear()

        self.colors.clear()
        self.styles.clear()
        self.normal.clear()

    def _load_json(self, filename:str) -> dict:
        with open(filename, 'rt', encoding='utf-8') as f:
            json_text:str = f.read()
            # filter JSON text because VSCode is lenient
            json_text = remove_comments(json_text)
            json_text = remove_trailing_commas(json_text)
            data:dict = json.loads(json_text)
            return data

    def include(self, filename:str, *, follow_includes:bool=True, silent:bool=False, _includepath:str=None):
        data:dict = self._load_json(filename)
        if not silent:
            if not _includepath:
                print('loading:    {}'.format('./{}'.format(os.path.basename(filename))))
            else:
                print('including:  {}'.format(_includepath))

        # read includes first, in order to overwrite existing scopes
        if follow_includes:
            basedir:str = os.path.split(filename)[0]
            include = data.get('include', None)
            if include is None:
                pass  # nothing to include
            elif isinstance(include, str):
                self.include(os.path.join(basedir, include), _includepath=include, follow_includes=follow_includes, silent=silent)
            elif isinstance(include, list):
                for inc in include:
                    self.include(os.path.join(basedir, inc), _includepath=inc, follow_includes=follow_includes, silent=silent)
            else:
                raise TypeError('Unknown include type {.__class__.__name__}'.format(include))

        # read the main file
        tokenColors:list = data.get('tokenColors', [])
        for tokenColor in tokenColors:
            self._add_token_color(tokenColor)

    def _add_token_color(self, tokenColor:dict):
        scope    = tokenColor['scope']
        settings = tokenColor['settings']
        fg    = settings.get('foreground', None)
        style = settings.get('fontStyle',  None)
        if fg is not None: fg = normalize_hexrgb(fg)

        value = (fg, style)
        if style is not None:
            lookup = self.style_scopes
            value = (fg, style)
        elif fg is not None:
            lookup = self.color_scopes
            value = fg
        else:
            lookup = self.normal_scopes
            value = None
        
        if isinstance(scope, str):
            self._add_token_color_scope(lookup, scope, value)
        elif isinstance(scope, list):
            for s in scope:
                self._add_token_color_scope(lookup, s, value)
        else:
            raise TypeError('Unknown scope type {.__class__.__name__}'.format(scope))

    def _add_token_color_scope(self, lookup:dict, scope:str, value:object):
        existing_lookup:dict = self._token_lookup.get(scope, None)
        if existing_lookup and existing_lookup is not lookup:
            del existing_lookup[scope]
        lookup[scope] = value


    def build_color_maps(self):
        # always clear and rebuild
        self.colors.clear()
        self.styles.clear()
        self.normal.clear()

        color_map, style_map, normal_list = self._map_colors_to_scopes()

        # insert sorted order into OrderedDicts
        for fg,scopes in sorted(color_map.items(), key=lambda pair: sort_by_hsv(pair[0])):
            self.colors[fg] = scopes

        for style,styled_color_map in sorted(style_map.items(), key=lambda pair: pair[0]):
            sorted_styled_colors = self.styles.setdefault(style, OrderedDict())
            for fg,scopes in sorted(styled_color_map.items(), key=lambda pair: sort_by_hsv(pair[0])):
                sorted_styled_colors[fg] = scopes
        
        self.normal = normal_list

    def _map_colors_to_scopes(self) -> Tuple[dict, dict, list]:
        """_map_colors_to_scopes() -> (color_map:dict, style_map:dict, normal_list:list)
        """
        # always clear and rebuild
        color_map:dict = {}
        style_map:dict = {}
        normal_list:list = []

        # populate maps by color (and style, and nothing)
        for scope,fg in self.color_scopes.items():
            color_list:list = color_map.setdefault(fg, [])
            color_list.append(scope)
        
        for scope,(fg,style) in self.style_scopes.items():
            styled_color_map:dict = style_map.setdefault(style, {})
            styled_color_list = styled_color_map.setdefault(fg, [])
            styled_color_list.append(scope)

        normal_list.extend(self.normal_scopes.keys())
        
        # sort scope namespaces
        for color_list in color_map.values():
            color_list.sort()
        for styled_color_map in style_map.values():
            for styled_color_list in styled_color_map.values():
                styled_color_list.sort()
        normal_list.sort()

        return (color_map, style_map, normal_list)


## MAIN FUNCTION ##

def main(argv:list=None):
    import argparse
    parser = argparse.ArgumentParser(
        description='Read VS Code theme colors and output them to the terminal.',
        add_help=True)
    
    parser.add_argument('file', metavar='JSONFILE', action='store', help='json file to parse')
    # parser.add_argument('-o', '--output', metavar='OUTFILE', action='store', default=None, required=False, help='output file for markdown')
    parser.add_argument('-c', '--compare', metavar='JSONFILE', action='store', default=None, required=False, help='compare colors with input file')
    parser.add_argument('-s', '--scopes', metavar='COLOR|NUM', nargs='+', action='store', required=False, help='list the scopes using a specified color')
    parser.add_argument('-S', '--all-scopes', action='store_true', default=False, required=False, dest='all_scopes', help='list all scopes for every color')
    parser.add_argument('-l', '--list', action='store_true', default=False, required=False, help='list all colors (default behavior)')
    parser.add_argument('-q', '--quiet', action='store_true', default=False, required=False, help='reduce console output to only requested info')
    parser.add_argument('-I', '--no-includes', action='store_false', default=True, required=False, dest='follow_includes', help='don\'t follow include directives')
    #TODO: --search option for scope names

    args = parser.parse_args(argv)

    num_commands = sum(map(bool, [args.list, args.compare, args.scopes or args.all_scopes])) #, args.output]))
    multiple = num_commands > 2
    quiet = args.quiet
    headers = multiple or not quiet
    follow_includes = args.follow_includes

    theme = VSCodeThemeParser()
    theme.include(args.file, silent=quiet, follow_includes=follow_includes)
    theme.build_color_maps()

    if args.compare is not None:
        theme2 = VSCodeThemeParser()
        theme2.include(args.compare, silent=quiet, follow_includes=follow_includes)
        theme2.build_color_maps()

    if args.compare is not None:
        if headers: print('{BRIGHT}{WHITE}---- COMPARE ----{RESET_ALL}'.format(**Colors))
        if not quiet: print()
        EMPTY = '             '
        colors1 = list(theme.colors.items())
        colors2 = list(theme2.colors.items())
        for i in range(max(len(colors1), len(colors2))):
            item1 = colors1[i] if i < len(colors1) else EMPTY
            if item1 is not EMPTY:
                color,scopes = colors1[i]
                item1 = '[{1:>2}]  {0}'.format(terminal_hexrgb(color), len(scopes))
            item2 = colors2[i] if i < len(colors2) else EMPTY
            if item2 is not EMPTY:
                color,scopes = colors2[i]
                item2 = '{0}  [{1:>2}]'.format(terminal_hexrgb(color), len(scopes))
            print('{:>2}) {}  :  {}'.format(i+1, item1, item2))
            # print('{}:  [{:>2}]'.format(terminal_hexrgb(color), len(scopes)))
        print()
            
    elif not quiet or args.list or num_commands == 0:
        if headers: print('{BRIGHT}{WHITE}---- COLORS ----{RESET_ALL}'.format(**Colors))
        if not quiet: print()
        for i,(color,scopes) in enumerate(theme.colors.items()):
            print('{:>2}) {}:  [{:>2}]'.format(i+1, terminal_hexrgb(color), len(scopes)))
        print()

    color_list = list(theme.colors.keys())
    scopes = None
    if args.all_scopes:
        scopes = list(theme.colors.keys())
    elif args.scopes:
        scopes = [normalize_hexrgb(s) if s[0]=='#' else color_list[int(s)-1] for s in args.scopes]

    if scopes is not None:
        if headers: print('{BRIGHT}{WHITE}---- SCOPES ----{RESET_ALL}'.format(**Colors))
        if not quiet: print()
        for color in scopes:
            color_scopes = theme.colors[color]
            print('[{:>2}) {}]'.format(color_list.index(color)+1, terminal_hexrgb(color)))
            for scope in color_scopes:
                print(terminal_rgb_text(color, scope))
            print()


## MAIN CONDITION ##

if __name__ == '__main__':
    exit(main())
