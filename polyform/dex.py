#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:

"""
Copyright 2019 Brandon Gillespie; All rights reserved.

This module is for dex bits to be run outside of a lambda.

V1 Data Expectation Syntax. Dirty hack right now while I fiddle with things,
but ultimately I need make this more standard w/BNF rules and a lexical parser.

Rules:

* Expressions: each line is an expression that must return a "truthy" value.
* Expression Line Break: Break lines by ending with a single backslash `\\`
* Assignments: Assining to a variable on the left (`var = expr`) puts the result
  of the expression into the context for the polyform.  Synonymous:

    name = expression
    expression |> assign(context, 'name')
    assign(expression, context, 'name')

* Follow: `->` is syntactic sugar for following a relationship from a node in the
  universe.  Synonyms:

        node->key
        follow(node, key)

* Comment: `# comment` -- anything following a hashtag, doesn't care if it's quoted
* Pipeline: `|>`              -- pipe for "chaining" function calls.  Synonym:

    # pipelined as:
    this(arg1) |> that(arg2) |> there(arg3, arg4)
    # calls as:
    there(that(this(arg1), arg2), arg3, arg4)

* function arguments support comma delimited followed by keyword=value
* dictionary selector of dict[name], dict['name'] supported, as well as dict.name
    - FUTURE: for dict.name support dict.*.val -- expand into array
* Interpolation of known keywords:
    $this -- polyform base
    $self -- the polyform name (outer polyform.meta.name)
    $form -- the sub-form name
    -- all others are pulled as keywords from context, ala:
    $invoker -- context['invoker']

* Accepted functions:
    - assign(name, context, value) - for setting something in context
    - pull('id')          - retrieve data at 'id' in universe
    - push(data, 'id')    - update data in universe at 'id'
    - follow(node, key)   - follow a key relationship off of node.  sugar: `->`
    - to(data, 'label')   - convert data to the type specified by 'label'
    - is(data, 'label')   - throw error if it is not data type, otherwise return data
    - are(data, 'label')  - sugar synonym with is(), for readability
    - in_range(data, start, end) - data is a number in the range of start to end
    - tempfd()            - create a temporary read/write binary fd
    - load(binary, as_type) - load binary data with the as_type load method
                              (currently: xgb), return a filedescriptor (fd)
    - b64enc/b64dec       - encode/decode base64 to/from binary
    - inspect(data)       - output raw data to console, and return data # useful
                            for debugging
    - <<other function>>  - any other function reference is looked up in context
                            of executing service and its imported namespace
    - context             - data dictionary of input values and attributes (for expect phase)
    - result              - data dictionary containing any results (for finish phase)
    - autoclean(data)     - datacleaner.autoclean() synonym
    - convert(data, tyepdef) - convert data to be matching typedef, which can be:
                                  ("csv>>dataframe")
                                  ("dict>>dataframe", "X") (where x is the row index)
"""

import json
import re

def _next_line_cleaned(block):
    if not block:
        raise EOFError("unexpected end of data")
    line = block[0]
    match = COMMENT_DQ_RX.search(line)
    if match is not None:
        line = line[:match.start(0)]
    #line.strip()
    return (line.strip(), block[1:])

# as this is a quick hack, it is easier to do two rx's
#COMMENTQ1_RX = re.compile(r'''(?:"[^"]*"|[^"#])*(#)''')
#COMMENTQ2_RX = re.compile(r"""(?:'[^']*'|[^'#])*(#)""")
#COMMENT_DQ_RX = re.compile(r'''(?:"(?:[^"\\]|\\.)*"|[^"#])*(#|$)''')
#COMMENT_DQ_RX = re.compile(r'''(?:"[^"]*"|[^"#])*(#).*$''')
#COMMENT_DQ_RX = re.compile(r'''([\#\@].*?)(?=([\r\n ]|$))''')
#COMMENT_DQ_RX = re.compile(r'''
#    (?:"[^"]*"|[^"#])*(#).*$
#''', flags=re.VERBOSE)
#COMMENT_DQ_RX = re.compile(r'''
#(?:"[^"]*"|[^"#])*(#)
#''')
#'''
#("[^"]*(?<!\\)"|[^"#]).*?(#)
#'''
#re.compile(r'''(?m),(?=[^"]*"(?:[^"\r\n]*"[^"]*")*[^"\r\n]*$)''')
COMMENT_DQ_RX = re.compile(r'''#.*$''')

def dex_trim(block): # where block is a list of strings
    """
    In order:
      1. remove comments
      2. remove blank lines
      2. join multi-lines escaped with \\
      3. remove excess whitespace on beginning/end of lines

    >>> dex_trim('''
    ... 0:begin basic line end # comment
    ...   1:begin "#" moar "#\\""; end # comment "test"
    ... 2:begin "#'"; end # comment
    ... ''')
    ['0:begin basic line end', '1:begin "', '2:begin "']
    >>> dex_trim('line that \\\\\\nwraps    \\\\\\n many times')
    ['line that wraps    many times']
    """
    # multiline in regex is a PITA, skip it for now
    # >>> strip_comments('''
    # ... 0:begin basic line end # comment
    # ... 0:.................^---^cut here
    # ... 1:begin "a#b\\""; end # "te#st" # moar
    # ... 1:..............^---^cut here
    # ... 2:begin "#" moar "#\\""; end # comment "test"
    # ... 2:.....................^---^cut here
    # ... 3:begin "#'"; end # comment.
    # ... 3:............^---^cut here
    # ... begin '\\'#\\''; end # comment.
    # ... begin '"\\'#\\'"'; end # comment.
    # ... begin "'# "; end # comment.
    # ... # full line
    # ... ''')
    out = list()
    if isinstance(block, str):
        block = re.split('\r?\n', block)
    while block:
        line, block = _next_line_cleaned(block)
        if not line:
            continue
        while line[-1] == '\\':
            line = line[0:-1]
            nline, block = _next_line_cleaned(block)
            line += nline
        out.append(line)
    return out

    # >>> dex_transpile('''
    # ...      # given/full/aliases/etc
    # ...      $invoker->name.* why:"displaying in app"
    # ...      # this why is the default, so is left out of the remaining
    # ...      $invoker->behavior.phone.log why:$this.analyzePhoneLog
    # ...      $invoker->behavior.geoloc.log why:$this
    # ...      $invoker->behavior.geoloc.now why:$this as:socket
    # ...      $invoker->behavior.voice.log why:$this
    # ...      $invoker->behavior.scs.log why:$this
    # ...      $invoker->thing.do why:$this as:call("api")
    # ...      $invoker->behavior.*.log why:$this
    # ...      $invoker->person.name why:$this format:synthetic
    # ...      $invoker->person.health.bloodpressure why:$this format:synthetic
    # ...      $invoker->my.photos.* why:$this as:real \\\\
    # ...        doc:"only photos I tag for this app, such as whiteboard snapshots"
    # ... ''')
    # ohmy
ASSIGNMENT_RX = re.compile(r'''^([a-zA-Z0-9_"'\[\].]+)\s*=(?!=)+\s*(.*)''')
#ASSIGN_DIG_RX = re.compile(r'^([a-zA-Z0-9_.]+)\s*=(?!=)+\s*(.*)')
FUNCTION_RX = re.compile(r'^([a-zA-Z0-9_]+)(\((.*)\))?$') # [^)]+)\))?$')
INTERPOLATE_RX = re.compile(r'\$([a-zA-Z0-9_]+)')
FOLLOW_RX = re.compile(r'([$a-zA-Z0-9_.]+)->([a-zA-Z0-9_.*]+)')
# pylint: disable=too-many-branches
def dex_transpile(indata, default_assign=None):
    # pylint: disable=line-too-long
    """
    Receive DES definition, transpile to Pythonic form

    >>> dex_transpile('''
    ...    model = pull("BACFAF-1FA14D-89FA") # hardcode the model data node
    ... ''')
    ['assign(pull("BACFAF-1FA14D-89FA"), context, \\'model\\')']

    >>> dex_transpile('''
    ...    f1("red") |> f2("green") |> f3("blue")
    ... ''')
    ['f3(f2(f1("red"), "green"), "blue")']
    >>> dex_transpile('''
    ...    key = f1("red") |> f2("green") |> f3("blue")
    ... ''')
    ['assign(f3(f2(f1("red"), "green"), "blue"), context, \\'key\\')']
    >>> dex_transpile('''
    ...      owner = $owner.id # this is implicit, but putting here to be explicit
    ... ''')
    ["assign(context['owner'].id, context, 'owner')"]
    >>> dex_transpile('''
    ...    requestor |> is(entity($owner))
    ...    dataFrame = accept->csv |> is("pandas:data_frame")
    ... ''')
    ["is(requestor, entity(context['owner']))", 'assign(is(follow(accept,\\'csv\\'), "pandas:data_frame"), context, \\'dataFrame\\')']
    >>> dex_transpile('''
    ...    model_input = model.csv |> StringIO() |> pandas.read_csv
    ...    result.modelbin |> push(context.model.id)
    ... ''')
    ["assign(pandas.read_csv(StringIO(model.csv)), context, 'model_input')", 'push(result.modelbin, context.model.id)']
    """
    #if not context:

    out = list()
#    $invoker == context['invoker']
    first = True
    for line in dex_trim(indata):
        #### unfold syntax sugar first
#        match = ASSIGN_DIG_RX.match(line)
#        if match and '.' in match.group(1):
##            print("MATCH DIG_RX={}".format(match.groups())) # match)
#            assign = dotkey2index(None, match.group(1).split("."))
#            line = assign + " = " + match.group(2)
        match = ASSIGNMENT_RX.match(line)
        if match:
            key = match.group(1)
            rest = match.group(2)
            if '.' in key:
                key = key.split(".")
            else:
                key = "'" + key + "'"
            line = "{} |> assign(context, {})".format(rest, key)

#            print("MATCH ASSIGN_RX={}".format(match.groups())) # match)
#            line = match.group(2) + " |> assign(context, '" + match.group(1) + "')"
        elif first and default_assign and "assign(" not in line:
            line = line + "|> assign(context, '" + default_assign + "')"
            first = False

#        match = INTERPOLATE_RX.match(line)
        # dict.keys (( maybe just skip this sugar: leaving it allows for adhoc object.method references ))
        # match $name->digval -- ${name}->{dig.val.deeper}
        line = re.sub(FOLLOW_RX, lambda x: 'follow(' + x.group(1) + ",'" + x.group(2)+ "')", line)
        # interpolate
        #line = re.sub(DICT_DIG_RX, lambda x: 'context[' + x + ']', line)
        line = re.sub(INTERPOLATE_RX, lambda x: "context['" + x.group(1) + "']", line)

        #print("     `{}`".format(line))
        #### split functions
        stack = list()
        place = 0
        for part in re.split(r'\s*\|>\s*', line):
            match = FUNCTION_RX.search(part)
            if match:
                stack.append([match.group(1), match.group(3)])
                #if match.group(2):
#                print("MATCH <{}> <{}> <{}>".format(*match.groups()))
#                print("=> {}".format([match.group(1), match.group(3)]))
#                stack.append(['', part])
            else:
                if place == 0: # if first in stack it's an argument, otherwise it's a function
                    stack.append([None, part])
                else:
                    stack.append([part, None])
            place += 1

#        import json
#        print(json.dumps(stack, indent=1))
        #### reformat into python
        expr = ''
        for func, arg in stack:
            if not expr: # first arg can come from context
                if not arg and func:
#                    if func[0] in "'\"":
                    expr = func
#                    else:
#                        print("Kick "  + func)
#                        expr = "context['{}']".format(func)
                elif not func:
                    expr = arg # "{}({}, {})".format(func, expr, arg)
                else:
                    expr = "{}({})".format(func, arg)
            elif not arg:
                expr = "{}({})".format(func, expr)
            else:
                expr = "{}({}, {})".format(func, expr, arg)

        out.append(expr)
    return out

def dotkey2index(index, keys):
    """convert this.name to this['name']"""
    if not keys:
        return index
    if index:
        buf = '[' + json.dumps(keys[0]) + ']'
        return dotkey2index(index + buf, keys[1:])
    return dotkey2index(keys[0], keys[1:])
