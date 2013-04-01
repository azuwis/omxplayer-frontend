# http://doom10.org/index.php?topic=916.0
# Converts SSA and ASS subtitles to SRT format.  Only supports UTF-8.
# Output may differ from Aegisub's exporter.
#
# Requires Python 2.7+.  Python 3.0 updates by RiCON.
#
# Copyright 2010, 2012 by Poor Coding Standards.  All Rights Reserved

import codecs
import os.path
import sys

from copy import copy
from datetime import datetime

class SSADialogueEvent(object):
    '''Container for a single line of an SSA script.'''
    def __init__(self, line):
        '''Reads timecodes and text from line.'''
        try:
            parts = line.split(': ', 1)
            eventType = parts[0]
            eventBody = parts[1]
            if not eventType == 'Dialogue':
                raise ValueError('Not a dialogue event: %s' % line)
            fields = eventBody.split(',', 9)
            start = fields[1]
            end = fields[2]
            text = fields[-1]
        except IndexError:
            raise ValueError('Parsing error: %s' % line)

        self.start = datetime.strptime(start, '%H:%M:%S.%f')
        self.end = datetime.strptime(end, '%H:%M:%S.%f')
        self.text = text
        
    def convert_tags(self):
        '''Returns SRT-styled text.  Does not inherit from styles.'''
        equivs = {'i1':'<i>', 'i0':'</i>', 'b1':'<b>', 'b0':'</b>', \
                  'u1':'<u>', 'u0':'</u>', 's1':'<s>', 's0':'</s>'}
        # Parse the text one character at a time, looking for {}.
        parsed = []
        currentTag = []
        tagIsOpen = False
        for i in self.text:
            if not tagIsOpen:
                if i != '{':
                    parsed.append(i)
                else:
                    tagIsOpen = True
            else:
                if i != '}':
                    currentTag.append(i)
                else:
                    tagIsOpen = False
                    tags = ''.join(currentTag).split('\\')
                    for j in tags:
                        if j in equivs:
                            parsed.append(equivs[j])
                    currentTag = []
        line = ''.join(parsed)
        # Replace SSA literals with the corresponding ASCII characters.
        line = line.replace('\\N', '\n').replace('\\n', '\n').replace('\\h', ' ')
        return line
    
    def out_srt(self, index):
        '''Converts event to an SRT subtitle.'''
        # datetime stores microseconds, but SRT/SSA use milliseconds.
        srtStart = self.start.strftime('%H:%M:%S.%f')[0:-3].replace('.', ',')
        srtEnd = self.end.strftime('%H:%M:%S.%f')[0:-3].replace('.', ',')
        srtEvent = str(index) + '\r\n' \
                   + srtStart + ' --> ' + srtEnd + '\r\n' \
                   + self.convert_tags() + '\r\n'
        return srtEvent

    def __repr__(self):
        return self.out_srt(1)


def resolve_stack(stack, out, tcNext):
    '''Resolves cases of overlapping events, as SRT does not allow them.'''
    stack.sort(key=cmp_to_key(end_cmp))
    stackB = [stack.pop(0)]
    # Combines lines with identical timing.
    while stack:
        prevEvent = stackB[-1]
        currEvent = stack.pop(0)
        if prevEvent.end == currEvent.end:
            prevEvent.text += '\\N' + currEvent.text
        else:
            stackB.append(currEvent)
    while stackB:
        top = stackB[0]
        combinedText = '\\N'.join([i.text for i in stackB])
        if top.end <= tcNext:
            stackB[0].text = combinedText
            out.append(stackB.pop(0))
            for i in stackB:
                i.start = top.end
        else:
            final = copy(top)
            final.text = combinedText
            final.end = tcNext
            out.append(final)
            # Copy back to stack, which is from a different namespace.
            for i in stackB:
                i.start = tcNext
            break
    return stackB

def cmp_to_key(mycmp):
    '''Convert a cmp= function into a key= function.'''
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

# Comparison functions for sorting.
start_cmp = lambda a, b: (a.start > b.start) - (a.start < b.start)
end_cmp = lambda a, b: (a.end > b.end) - (a.end < b.end)

def main(infile, outfile):
    '''Convert the SSA/ASS file infile into the SRT file outfile.'''
    stream = codecs.open(infile, 'r', 'utf8')
    sink = codecs.open(outfile, 'w', 'utf8')

    # HACK: Handle UTF-8 files with Byte-Order Markers.
    if stream.read(1) == str(codecs.BOM_UTF8, 'utf8'):
        stream.seek(3)
    else:
        stream.seek(0)

    # Parse the stream one line at a time.
    events = []
    for i in stream:
        text = i.strip()
        try:
            events.append(SSADialogueEvent(text))
        except ValueError:
            continue

    events.sort(key=cmp_to_key(start_cmp))

    stack = []
    merged = []
    while events:
        currEvent = events.pop(0)
        if not stack:
            stack.append(currEvent)
            continue
        if currEvent.start != stack[-1].start:
            stack = resolve_stack(stack, merged, currEvent.start)
        stack.append(currEvent)
    else:
        if stack:
            stack = resolve_stack(stack, merged, stack[-1].end)

    # Write the file. SRT requires each event to be numbered.
    index = 1
    sink.write(str(codecs.BOM_UTF8, 'utf8'))
    for i in merged:
        # The overlap resolution can create zero-length lines.
        if i.start != i.end:
            sink.write(i.out_srt(index) + '\r\n')
            index += 1

    stream.close()
    sink.close()

# Read command line arguments.
if __name__ == "__main__":
    try:
        infile = sys.argv[1]
        try:
            outfile = sys.argv[2]
        except IndexError:
            outfile = os.path.splitext(infile)[0] + '.srt'
    except:
        script_name = os.path.basename(sys.argv[0])
        sys.stderr.write('Usage: {0} infile [outfile]\n'.format(script_name))
        sys.exit(2)
    main(infile, outfile)
