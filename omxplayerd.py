#!/usr/bin/python
# -*- coding: utf-8 -*-
import subprocess
import time
import re
import web
import os
import pipes
import string

urls = (
'^/$','Interface',
'^/shutdown$','Shutdown',
'^/play/(.*)$','Play',
'^/path/?(.*)$','Path',
'^/playlist/?(.*)$','Playlist',
'^/([^/]*)$','Other'
)

PLAYABLE_TYPES = ['.264','.avi','.bin','.divx','.f4v','.h264','.m4e','.m4v','.m4a','.mkv','.mov','.mp4','.mp4v','.mpe','.mpeg','.mpeg4','.mpg','.mpg2','.mpv','.mpv2','.mqv','.mvp','.ogm','.ogv','.qt','.qtm','.rm','.rts','.scm','.scn','.smk','.swf','.vob','.wmv','.xvid','.x264','.mp3','.flac','.ogg','.wav', '.flv', '.mkv']
MEDIA_RDIR = 'media/'
PAGE_FOLDER = 'omxfront/'
PAGE_NAME = 'interface.htm'
OMXIN_FILE='omxin'

play_list = []

command_send={
'speedup':'1',
'speeddown':'2',
'nextaudio':'k',
'prevaudio':'j',
'nextchapter':'o',
'prevchapter':'i',
'nextsubs':'m',
'prevsubs':'n',
'togglesubs':'s',
'stop':'q',
'pause':'p',
'volumedown':'-',
'volumeup':'+',
'languagedown':'j',
'languageup':'k',
'seek-30':'\x1b\x5b\x44',
'seek+30':'\x1b\x5b\x43',
'seek-600':'\x1b\x5b\x42',
'seek+600':'\x1b\x5b\x41'}

class Other:
    def GET(self,name):
        if not name == '':
            if name in command_send:
                omx_send(command_send[name])
                return '[{\"message\":\"OK\"}]'
            else:
                if os.path.exists(os.path.join(PAGE_FOLDER,name)):
                    page_file = open(os.path.join(PAGE_FOLDER,name),'r')
                    page = page_file.read()
                    page_file.close()
                    return page
                return '[{\"message\":\"FAIL\"}]'
        print('Incorrect capture!')
        return '[{\"message\":\"ERROR!!!\"}]'

class Play:
    def GET(self,file):
        omx_play(file)
        return '[{\"message\":\"OK\"}]'

class Shutdown:
    def GET(self):
        subprocess.call('/sbin/shutdown -h now',shell=True)
        return '[{\"message\":\"OK\"}]'

class Interface:
    def GET(self):
        page_file = open(os.path.join(PAGE_FOLDER,PAGE_NAME),'r')
        page = page_file.read()
        page_file.close()
        web.header('Content-Type', 'text/html')
        return page


class Path:
    def GET(self, path=''):
        itemlist = []
        if path.startswith('..'):
            path = ''
        for item in os.listdir(os.path.join(MEDIA_RDIR,path)):
            if os.path.isfile(os.path.join(MEDIA_RDIR,path,item)):
                fname = os.path.splitext(item)[0]
                fname = re.sub('\.', ' ',fname)
                fname = re.sub('\s+',' ',fname)
                fname = string.capwords(fname.strip())
                singletuple = (os.path.join(path,item),fname,'file')
            else:
                fname = re.sub('\.', ' ',item)
                fname = re.sub('\s+',' ',fname)
                fname = string.capwords(fname.strip())
                singletuple = (os.path.join(path,item),fname,'dir')
            itemlist.append(singletuple)
        itemlist = [f for f in itemlist if not os.path.split(f[0])[1].startswith('.')]
        itemlist = [f for f in itemlist if os.path.splitext(f[0])[1].lower() in PLAYABLE_TYPES or f[2]=='dir']
        list.sort(itemlist, key=lambda alpha: alpha[1])
        list.sort(itemlist, key=lambda dirs: dirs[2])
        outputlist=[]
        for line in itemlist:
            outputlist.append('{\"path\":\"'+line[0]+'\", \"name\":\"'+line[1]+'\", \"type\":\"'+line[2]+'\"}')
        return '[\n'+',\n'.join(outputlist)+']'

#This class is not complete yet and only populates the global playlist.
#TO-DO
class Playlist:
   def GET(self, item=''):
       if not item=='':
           play_list.append(item)
       output = '[/n'
       for i, part in enumerate(play_list):
           output = output + '{\"'+i+'\":'+string.capwords(os.path.splitext(part)[0])+'\"}\n'
       output = output + ']'
       return output

if __name__ == "__main__":
    subprocess.Popen('sudo su -c "clear >/dev/tty1; setterm -cursor off >/dev/tty1"',shell=True)
    app = web.application(urls,globals())
    app.run()

def omx_send(data):
    subprocess.Popen('echo -n '+data+' >'+re.escape(OMXIN_FILE),shell=True)
    return 1

def omx_play(file):
    #omx_send('q')
    #time.sleep(0.5) #Possibly unneeded - crashing fixed by other means.
    subprocess.Popen('killall omxplayer.bin',stdout=subprocess.PIPE,shell=True)
    subprocess.Popen('clear',stdout=subprocess.PIPE,shell=True)
    prepare_subtitle(file)
    subprocess.Popen('omxplayer --align center --font /usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf -o hdmi '+os.path.join(MEDIA_RDIR,re.escape(file))+' <'+re.escape(OMXIN_FILE),shell=True)
    omx_send('.')
    return 1

def prepare_subtitle(file):
    import glob
    fileprefix,_ = os.path.splitext(file)
    fileprefix = os.path.join(MEDIA_RDIR, fileprefix)
    used_srt = fileprefix + '.srt'
    srts = glob.glob(fileprefix + '*.srt')
    if len(srts) == 0:
        filepath_withmedia = os.path.join(MEDIA_RDIR,file)
        shooter_subs = fetch_shooter(filepath_withmedia)
        if shooter_subs:
            force_utf8_and_filter_duplicates(shooter_subs)
            save_to_disk(shooter_subs, filepath_withmedia)
        asses = glob.glob(fileprefix + '*.ass')
        if len(asses) > 0:
            import ass2srt
            for ass in asses:
                ass2srt.main(ass, os.path.splitext(ass)[0] + '.srt')
        srts = glob.glob(fileprefix + '*.srt')
    # omxplayer use exactly matched .srt subtitle, rename the first globed .srt to that
    for srt in srts:
        os.rename(srt, used_srt)
        break
    if os.path.exists(used_srt):
        with open(fileprefix + '.srt', 'r+b') as f:
            s = f.read()
            enc,_,s = guess_locale_and_convert(s)
            if not enc in ['utf_8','ascii']:
                f.seek(0)
                f.write(s)

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

def filter_in(stream, regex):
    # find matches and join them
    return b''.join(re.findall('{0}'.format(regex), stream))

def filter_out(stream, regex):
    # kick out matches and join the remains
    return b''.join(re.split('(?:{0})+'.format(regex), stream))

@singleton
class Charset(object):
    def detect_bom(self, stream):
        for sig,enc in self.bom:
            if stream.startswith(sig):
                return sig,enc
        return None,None
    
    def strip_ascii(self, stream):
        # filter out ASCII as much as possible by the heuristic that a
        # \x00-\x7F byte that following \x80-\xFF is not ASCII.
        pattern = '(?<![\x80-\xFE]){0}'.format(self.generate_regex('ascii'))
        return filter_out(stream, pattern)
        
    def interprete_stream(self, stream, enc):
        '''ASCII bytes (\x00-\x7F) can be standalone or be the low
        byte of the pattern. We count them separately.
      
        @pattern: the list of code points
        Return: (#ASCII, #ENC, #OTHER)
        '''
        interpretable = filter_in(stream, self.generate_regex(enc))
        standalone_ascii = filter_out(interpretable, self.generate_regex(enc,False))
    
        return len(standalone_ascii), len(interpretable)-len(standalone_ascii), len(stream)-len(interpretable)

    def generate_regex(self, enc, with_ascii=True):
        if with_ascii and not enc == 'ascii':
            return '|'.join(self.codec['ascii'] + self.codec[enc])
        else:
            return '|'.join(self.codec[enc])

    def __init__(self):
        from collections import defaultdict
        # http://unicode.org/faq/utf_bom.html#BOM
        self.bom = ((b'\x00\x00\xFE\xFF', 'utf_32_be'), (b'\xFF\xFE\x00\x00', 'utf_32_le'),
                    (b'\xFE\xFF',         'utf_16_be'), (b'\xFF\xFE',         'utf_16_le'),
                    (b'\xEF\xBB\xBF',     'utf_8'), )

        self.codec = defaultdict(list)
        codec = self.codec

        # http://en.wikipedia.org/wiki/Ascii
        codec['ascii'] = ('[\x09\x0A\x0D\x20-\x7E]',)

        # http://en.wikipedia.org/wiki/GBK
        codec['gbk'] = ('[\xA1-\xA9][\xA1-\xFE]',              # Level GBK/1
                        '[\xB0-\xF7][\xA1-\xFE]',              # Level GBK/2
                        '[\x81-\xA0][\x40-\x7E\x80-\xFE]',     # Level GBK/3
                        '[\xAA-\xFE][\x40-\x7E\x80-\xA0]',     # Level GBK/4
                        '[\xA8-\xA9][\x40-\x7E\x80-\xA0]',     # Level GBK/5
                        '[\xAA-\xAF][\xA1-\xFE]',              # user-defined
                        '[\xF8-\xFE][\xA1-\xFE]',              # user-defined
                        '[\xA1-\xA7][\x40-\x7E\x80-\xA0]',     # user-defined
                        )
        codec['gb2312'] = codec['gbk'][0:2]

        # http://www.cns11643.gov.tw/AIDB/encodings.do#encode4
        codec['big5'] = ('[\xA4-\xC5][\x40-\x7E\xA1-\xFE]|\xC6[\x40-\x7E]',          # 常用字
                         '\xC6[\xA1-\xFE]|[\xC7\xC8][\x40-\x7E\xA1-\xFE]',           # 常用字保留範圍/罕用符號區
                         '[\xC9-\xF8][\x40-\x7E\xA1-\xFE]|\xF9[\x40-\x7E\xA1-\xD5]', # 次常用字
                         '\xF9[\xD6-\xFE]',                                          # 次常用字保留範圍
                         '[\xA1-\xA2][\x40-\x7E\xA1-\xFE]|\xA3[\x40-\x7E\xA1-\xBF]', # 符號區標準字
                         '\xA3[\xC0-\xE0]',                                          # 符號區控制碼
                         '\xA3[\xE1-\xFE]',                                          # 符號區控制碼保留範圍
                         '[\xFA-\xFE][\x40-\x7E\xA1-\xFE]',                          # 使用者造字第一段
                         '[\x8E-\xA0][\x40-\x7E\xA1-\xFE]',                          # 使用者造字第二段
                         '[\x81-\x8D][\x40-\x7E\xA1-\xFE]',                          # 使用者造字第三段
                         )

        # http://www.w3.org/International/questions/qa-forms-utf-8
        codec['utf_8'] = ('[\xC2-\xDF][\x80-\xBF]',            # non-overlong 2-byte
                          '\xE0[\xA0-\xBF][\x80-\xBF]',        # excluding overlongs
                          '[\xE1-\xEC\xEE\xEF][\x80-\xBF]{2}', # straight 3-byte
                          '\xED[\x80-\x9F][\x80-\xBF]',        # excluding surrogates
                          '\xF0[\x90-\xBF][\x80-\xBF]{2}',     # planes 1-3
                          '[\xF1-\xF3][\x80-\xBF]{3}',         # planes 4-15
                          '\xF4[\x80-\x8F][\x80-\xBF]{2}',     # plane 16
                          )

def guess_locale(stream, naive=True):
    # prepare the sample
    sample = Charset().strip_ascii(stream)
    if len(sample)>2048:
        sample = sample[0:2048]

    # true when having less than 0.5% (~10) bytes cannot be interpreted
    threshold = int(len(sample) * .005)
    if Charset().interprete_stream(sample, 'utf_8')[2] < threshold:
        return 'utf_8','und'
    elif naive:
        # In the particular context of subtitles, traditional Chinese is more
        # likely encoded in BIG5 rather than GBK.
        #
        # The priority is GB2312>BIG5>GBK when the bytes can interpreted by at
        # least two of them. If this is not you want, please set naive=False.
        for enc,lang in [('gb2312','chs'), ('big5','cht'), ('gbk','cht')]:
            if Charset().interprete_stream(sample, enc)[2] < threshold:
               return enc,lang 
    else:
        # GBK and BIG5 share most code points and hence it's almost impossible
        # to take a right guess by only counting non-interpretable bytes.
        #
        # A clever statistic approach can be found at:
        # http://www.ibiblio.org/pub/packages/ccic/software/data/chrecog.gb.html
        l = len(re.findall('[\xA1-\xFE][\x40-\x7E]',sample))
        h = len(re.findall('[\xA1-\xFE][\xA1-\xFE]',sample))
        if l == 0:
            return 'gb2312','chs'
        elif float(l)/float(h) < 0.25:
            return 'gbk','chi'
        else:
            return 'big5','cht'
    return 'ascii','eng'

def guess_locale_and_convert(stream):
    sig,enc = Charset().detect_bom(stream)
    if sig:
        stream = stream[len(sig):]
        lang = 'und'
    else:
        enc,lang = guess_locale(stream)
        
    if not enc in ['utf_8', 'ascii']:
        stream = stream.decode(enc,'ignore').encode('utf_8')
    return enc,lang,stream

def parse_shooter_package(fileobj):
    '''Parse shooter returned package of subtitles.
    Return subtitles encoded in UTF-8.
    '''
    subtitles = []
    f = fileobj

    # read contents
    import struct, io
    c = f.read(1)
    package_count = struct.unpack(b'!b', c)[0]

    for i in range(package_count):
        # NOTE: '_' is the length of following byte-stream
        c = f.read(8)
        _,desc_length = struct.unpack(b'!II', c)
        description = f.read(desc_length).decode('utf_8')
        sub_delay = float(description.partition('=')[2]) / 1000.0 if description and 'delay' in description else 0
        if description:
            print('Subtitle description: {0}'.format(description))

        c = f.read(5)
        _,file_count = struct.unpack(b'!IB', c)
            
        for j in range(file_count):
            c = f.read(8)
            _,ext_len = struct.unpack(b'!II', c)
            ext = f.read(ext_len)

            c = f.read(4)
            file_len = struct.unpack(b'!I', c)[0]
            sub = f.read(file_len)
            if sub.startswith(b'\x1f\x8b'):
                import gzip
                sub = gzip.GzipFile(fileobj=io.BytesIO(sub)).read()

            subtitles.append({'extension': ext,
                              'delay': sub_delay,
                              'content': sub})

    print('{0} subtitle(s) fetched.'.format(len(subtitles)))
    return subtitles

def fetch_shooter(filepath):
    import hashlib
    filehash = ''
    sz = os.path.getsize(filepath)
    if sz>8192:
        with open(filepath,'rb') as f:
            filehash = ';'.join([(f.seek(s), hashlib.md5(f.read(4096)).hexdigest())[1] for s in (lambda l:[4096, l/3*2, l/3, l-8192])(sz)])
    import httplib
    schemas = ['http', 'https'] if hasattr(httplib, 'HTTPS') else ['http']
    servers = ['www', 'splayer', 'svplayer'] + ['splayer'+str(i) for i in range(1,13)]
    splayer_rev = 2437 # as of 2012-07-02
    tries = [2, 10, 30, 60, 120]

    # generate data for submission
    # shooter.cn uses UTF-8.
    head,tail = os.path.split(filepath)
    pathinfo = '\\'.join(['D:', os.path.basename(head), tail])
    v_fingerpint = b'SP,aerSP,aer {0} &e(\xd7\x02 {1} {2}'.format(splayer_rev, pathinfo.encode('utf_8'), filehash.encode('utf_8'))
    vhash = hashlib.md5(v_fingerpint).hexdigest()
    import random
    boundary = '-'*28 + '{0:x}'.format(random.getrandbits(48))

    header = [('User-Agent',   'SPlayer Build {0}'.format(splayer_rev)),
              ('Content-Type', 'multipart/form-data; boundary={0}'.format(boundary))
              ]
    items = [('filehash', filehash), ('pathinfo', pathinfo.encode('utf_8')), ('vhash', vhash)]
    data = ''.join(['--{0}\n'
                    'Content-Disposition: form-data; name="{1}"\n\n'
                    '{2}\n'.format(boundary, *d) for d in items]
                   + ['--' + boundary + '--'])

    # fetch
    import urllib2
    fetched_subtitles = ''
    for i, t in enumerate(tries):
        try:
            print('Wait for {0}s to reconnect (Try {1} of {2})...'.format(t,i+1,len(tries)+1))
            time.sleep(t)

            url = '{0}://{1}.shooter.cn/api/subapi.php'.format(random.choice(schemas), random.choice(servers))

            # shooter.cn uses UTF-8.
            req = urllib2.Request(url.encode('utf_8'))
            for h in header:
                req.add_header(h[0].encode('utf_8'), h[1].encode('utf_8'))
            req.add_data(data)

            print('Connecting server {0} with the submission:\n'
                          '\n{1}\n'
                          '{2}\n'.format(url,
                                         '\n'.join(['{0}:{1}'.format(*h) for h in header]),
                                         data))

            # todo: with context manager
            response = urllib2.urlopen(req, timeout=5)
            fetched_subtitles = parse_shooter_package(response)
            response.close()

            if fetched_subtitles:
                break
        except Exception, e:
            print(e)
    return fetched_subtitles

def force_utf8_and_filter_duplicates(subtitles):
    print('Trying to filter duplicated subtitles...')

    for s in subtitles:
        _,s['lang'],s['content'] = guess_locale_and_convert(s['content'])
            
    dup_tag = [False]*len(subtitles)
    for i in range(len(subtitles)):
        if dup_tag[i]:
            continue
        for j in range(i+1, len(subtitles)):
            sa = subtitles[i]
            sb = subtitles[j]
            if sa['extension'] != sb['extension'] or sa['lang'] != sb['lang']:
                continue
            import difflib
            similarity = difflib.SequenceMatcher(None, sa['content'], sb['content']).real_quick_ratio()
            print('Similarity is {0}.'.format(similarity))
            if similarity > 0.9:
                dup_tag[j] = True
    # TODO: reserve longer subtitles 
    subtitles = [subtitles[i] for i in range(len(subtitles)) if not dup_tag[i]]
    print('{0} subtitle(s) reserved after duplicates filtering.'.format(len(subtitles)))

def save_to_disk(subtitles, filepath, save_dir=None):
    prefix,_ = os.path.splitext(filepath)
    if save_dir:
        prefix = os.path.join(save_dir, os.path.basename(prefix))

    # save subtitles
    for s in subtitles:
        suffix = '.' + s['lang'] if not s['lang'] == 'und' else ''
                
        path = prefix + suffix + '.' + s['extension']
        if os.path.exists(path):
            path = prefix + suffix + '1.' + s['extension']
        with open(path,'wb') as f:
            f.write(s['content'])
            print('Saved the subtitle as {0}'.format(path.encode('utf_8')))
            s['path'] = path
