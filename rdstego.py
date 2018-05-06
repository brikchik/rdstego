#!/usr/bin/python
# -*- coding: UTF-8 -*-
# rdstego - video steganography tool (any video supported by FFMpeg -> mp4 [H264/MP3])
# author: Gleb Rudometov
# email: javist.gr@mail.ru
# have to be configured on both sides to hide and extract successfully (and make analysis harder):
OVERALL_CTR_VALUE='1111111111111111'    # cipher iv
INNER_CTR_VALUE='0000000000000000'      # cipher iv
KEY_LENGTH=12 # AES key size (up to 128 bits). Decrease it if video is way too short.
ADD_BLINKING=False # should we change the frames?
SEPARATOR='@#@#' # required for successful extraction.
SIGNATURE='&F%H' # signature of stegged frame in audio file. You can make it dynamic to make analysis harder yourself.
# extra settings
SHOW_VIDEO=False #show video while processing it?
SHOW_EXTRACTED_MESSAGE=False # show extracted data?
import random
import cv2
import os
import numpy
import argparse
import subprocess
import getpass
import zlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from PIL import Image, ImageDraw
LENGTH=8 # header(7 bytes for SIGNATURE and data size(3 byte number) + at least 1 free byte for data)
bmpeg1=((32, 32, 32), (40, 48, 64), (48, 56, 96),
        (56, 64, 128), (64, 80, 160), (80, 96, 192),
        (96, 112, 224), (112, 128, 256), (128, 160, 288),
        (160, 192, 320), (192, 224, 352), (224, 256, 384),
        (256, 320, 416), (320, 384, 448))
samplingRate = (44100, 48000, 32000)
samplingPerFrame = (1152, 1152, 384)
def ReadFile(filename): #returns string
    music_file=open(filename, 'rb')
    content=music_file.read()
    return(content)
def WriteFile(outfilename, content):#gets list
    out_file=open(outfilename, 'wb')
    out_file.write(''.join(content))
def FindFrame(content, headerPos=0, header=''):
    FIND_NEXT = headerPos!=0
    if FIND_NEXT: pos=headerPos+FrameSize(header)
    else: pos=0
    while pos<len(content)-3: # while is faster than for
        headerArray=content[pos:pos+4]
        if FIND_NEXT:
            if ord(headerArray[0])==0xFF and (ord(headerArray[1]) & 0xE0)==0xE0 and (ord(headerArray[2]) & 0xF0)!=0xF0:
                return pos, headerArray
        elif headerArray[0]==chr(0xFF) and (headerArray[1]==chr(0xFB) or ord(headerArray[1])==0xFA):
            return pos, headerArray                                
        pos+=1
    return -1, ''
def FrameSize(headerArray): # parsing frame header
    LayerIdx=(ord(headerArray[1]) >> 1) & 0x3 - 1
    BitrateIdx=(ord(headerArray[2]) >> 4) & 0xF - 1
    SamplingRateIdx=(ord(headerArray[2]) >> 2) & 0x3;
    Padding=(ord(headerArray[2]) >> 1) & 0x1;
    size=(samplingPerFrame[LayerIdx] / 8 * bmpeg1[BitrateIdx][LayerIdx] * 1000 / (samplingRate[SamplingRateIdx])+ Padding)
    return size
def Frames(content):
    pos, header=FindFrame(content)
    pos_list=[]
    count=0
    try:
        while True:
            pos, header=FindFrame(content, pos, header)
            pos_list.append(pos)
            count+=1
    except Exception: # is reached as ( pos > file size )
        return count, pos_list
def isAvailableToSteg(content, pos):
    k=0
    for i in range(0, LENGTH-2):
        if content[pos+36+i]==content[pos+36+i+1]: pass
        else: return False
    return True
def FramesAvailableToSteg(content): # returns number of frames and their posotions
    count=0
    available_frames=[]
    their_headers=[]
    pos=-1
    pos, header=FindFrame(content)
    while pos<len(content):
        try:
            pos, header=FindFrame(content, pos, header)
        except Exception:
            return count, available_frames, their_headers
        if isAvailableToSteg(content, pos):
            count+=1
            available_frames.append(pos)
            their_headers.append(header)
def MaxStegSize(content):
    num,positions,headers = FramesAvailableToSteg(content)
    if num==0:
        return False
    availableList=[]
    for frame in range(num):
        k=0
        while content[positions[frame]+43]==content[positions[frame]+43+k]:
            k+=1
        availableList.append(k)
    return sum(availableList), availableList
def AvailableInMp3(inputFile):
    content=ReadFile(inputFile)
    n, alist = MaxStegSize(content)
    return n
def HideFile(inputFile, fileToHide, resultFile):
    content=list(ReadFile(inputFile))
    secret=ReadFile(fileToHide)
    num,positions,headers = FramesAvailableToSteg(content)
    if num==0:
        return False
    bytesAvailable, availableList = MaxStegSize(content)
    if bytesAvailable<len(secret):
        print 'Lacks',len(secret)-bytesAvailable,'bytes'
        return False
    frame=0
    while frame<len(positions):
        mp3pos=positions[frame]
        available=availableList[frame]
        if available>len(secret):
            available=len(secret)
        if available<10: break
        content[mp3pos+36:mp3pos+40]=SIGNATURE
        content[mp3pos+40:mp3pos+43]=str(available).rjust(3,' ')
        content[mp3pos+43:mp3pos+43+available]=secret[:available]
        secret=secret[available:]
        frame+=1
    WriteFile(resultFile, content)
    return True
def RevealFile(inputFile, outputFile):
    content=ReadFile(inputFile)
    secret=[]
    num, positions= Frames(content)
    if num==0:
        return False
    size=None
    for frame in range(num):
        if content[positions[frame]+36:positions[frame]+40]==SIGNATURE:
            size=int(content[positions[frame]+40:positions[frame]+43])
            secret.append(content[positions[frame]+43:positions[frame]+43+size])
    WriteFile(outputFile, secret)
    return True
def DelDir(dirname, create=False): # remove or create directory with content
        try:
                for root, dirs, files in os.walk(dirname, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(dirname)
        except (Exception): pass
        if create: os.mkdir(dirname)
def delfile(filename): # remove file if possible
        try:
                os.remove(filename)
        except (Exception): pass
def clean(): # remove temporary files
        DelDir('temp')
        DelDir('temp2')
        DelDir('temp_out')
        DelDir('extracted_temp')
        delfile('sound.mp3')
        delfile('extracted_sound.mp3')
        delfile('decarr.txt')
        delfile('extracted_sound.mp3.txt')
        delfile('stegsound.mp3')
        delfile('rdstego.log')
def openimage(foldername, number): # get image from file
        try:
                frame = cv2.imread(u'{}/{:05d}.jpg'.format(foldername, number))
                return frame, True
        except ():
                print (u'Unable to open {}/{:05d}.jpg'.format(foldername, number))
                return [], False
def seek(foldername, brightness_list, frame_count=KEY_LENGTH): # gets key from frames
        hidden_message=[] # bits of key
        for c in range(1,frame_count+1):
                frame, success=openimage(foldername, c)
                if not success:
                        clean()
                        exit(1)
                frame_brightness = int(numpy.sum(frame)/frame.shape[0]/frame.shape[1])
                if (frame_brightness > brightness_list[c-1]):
                        hidden_message.append(u'1')
                else: hidden_message.append(u'0')
        return hidden_message
def check(out_video,Brightness_list, argument): # checks if information can be extracted after video compression
        print (u'Checking...')
        with open('rdstego.log', 'a') as f:
                code=subprocess.call(['ffmpeg','-i',out_video,'-r',str(25),'temp_out/%05d.jpg','-y','-hide_banner'],stdout=f, stderr=f)
        result=''.join(x for x in seek('temp_out', Brightness_list,len(os.listdir('temp'))))
        print (argument[0:KEY_LENGTH]+u' - hidden key')
        arr3=[]
        correct=0
        print (result[0:KEY_LENGTH]+ u' - extracted key')
        length=min(len(argument),len(result))
        for x in range(KEY_LENGTH):
                if argument[x]==result[x]:
                        correct+=1
                        arr3.append(u'1')
                else:
                        arr3.append(u'0')
        print (u'CORRECT: '+str(correct)+u' of '+str(KEY_LENGTH))
        if correct<KEY_LENGTH:
                return False
        else:
                return True
def insert(pix, val, STEP, width, height): # modifies frame. returns data for getting bit out of the frame
        pix[numpy.where(pix < STEP*2)] = STEP*2
        pix-=STEP
        maspoint=int(pix.sum()/width/height) # this number is transmitted separately
        if val=='1':
                pix+=STEP
        else:
                pix-=STEP
        return pix, maspoint
def no_insert(pix, val, STEP, width, height): # doesn't modify frame. returns data for getting bit out of the frame
        if val=='1':
                maspoint=int(pix.sum()/width/height)-STEP
        else:
                maspoint=int(pix.sum()/width/height)+STEP
        return pix, maspoint
def hide_key(foldername, argument, outfoldername, STEP, RESIZE_CONSTANT=1):  # hides key into frames. argument is information to hide
        frame_count=len(os.listdir('temp'))
        while len(argument)<=frame_count:argument+=random.choice(['0','1']) # to avoid simple analysis
        brightness_list=[] # data for extracting key bits out of frames
        for c in range(1, frame_count+1):
                frame, success = openimage(foldername, c)
                if not success:
                        clean()
                        exit(1)
                frame = cv2.resize(frame, dsize=None, fx=RESIZE_CONSTANT, fy=RESIZE_CONSTANT) # video resolution can be decreased
                if ADD_BLINKING: # whether to modify frames or not
                        out, mas = insert(frame, argument[c-1], STEP, frame.shape[1], frame.shape[0])
                else:
                        out, mas = no_insert(frame, argument[c-1], STEP, frame.shape[1], frame.shape[0])
                brightness_list.append(mas)
                try:
                        cv2.imwrite('{}/{:05d}.jpg'.format(outfoldername, c), frame)
                except():
                        print (u'Unable to write '+'{}/{:05d}.jpg'.format(outfoldername, c))
                        clean()
                        exit(1)
                ##### Show video #####
                if SHOW_VIDEO:
                        try:
                                out = cv2.resize(out, dsize=None, fx=1.0/RESIZE_CONSTANT, fy=1.0/RESIZE_CONSTANT)
                                cv2.imshow(u'Resulting video in real size', out)
                                k=cv2.waitKey(1)
                        except Exception as error:
                                print (u'Unable to show '+ error)
                ##### show block finished #####
        cv2.destroyAllWindows()
        return brightness_list # returns data for extracting key
def try_hide(message,key, STEP, RESIZE_RATE, out_video, password='', bytes_available=0): # tries to hide key until succeeded
        while len(password)<32: password+='1' # AES password for the whole file
        content='' # file content
        Brightness_list=[]
        DelDir('temp2', create=True)
        DelDir('temp_out',create=True)
        Brightness_list = hide_key('temp', key, 'temp2', STEP, RESIZE_RATE)
        with open('rdstego.log', 'a') as f:
                bytes_available=subprocess.call(['mp3stegz_console.exe','available','sound.mp3'],stdout=f, stderr=f)
        print(u'Bytes available (in audio): '+str(bytes_available))
        if len(os.listdir('temp'))<KEY_LENGTH:
                print (u'Video is too short.')
                clean()
                exit(1)
        if Brightness_list:
                print (u'Key is hidden. '+u'Step = '+str(STEP))
        try:
                for item in range(0,KEY_LENGTH):
                        content+="%d\n" % Brightness_list[item]
                print (u'Size of key recovery data = '+str(len(content)))
        except Exception as error:
                print (u'Unable to create file. Extraction is impossible. '+ error)
                clean()
                exit(1)
        print (u'Writing data to sound')
        content += SEPARATOR
        content += message
        content = zlib.compress(content)
        print (u'File size after compression: %d' % len(content))
        encryptor = Cipher(algorithms.AES(password), modes.CTR(OVERALL_CTR_VALUE), backend=default_backend()).encryptor()
        content = encryptor.update(content) + encryptor.finalize() # encrypting
        if len(content)>bytes_available:
                print (u'Message is too big')
                exit(0)
        with open('decarr.txt','wb') as f:
                f.write(content)
        print (u'Hiding data into audio...')
        HideFile('sound.mp3','decarr.txt','stegsound.mp3')
        print (u'Writing output video')
        with open('rdstego.log', 'a') as f:
                code=subprocess.call(['ffmpeg','-i','stegsound.mp3','-r',str(25),'-i','temp2/%05d.jpg','-c:v','libx264','-crf',str(25),'-acodec',
                                      'copy',out_video,'-y','-hide_banner'],stdout=f, stderr=f)
        return Brightness_list
def Hide(in_video, out_video, message, STEP, RESIZE_RATE, password=''):
        key=''.join(chr(random.randrange(0,255)) for i in range(KEY_LENGTH//8)) # encryption key
        while len(key)<32: key+='0'
        encryptor = Cipher(algorithms.AES(key), modes.CTR(INNER_CTR_VALUE), backend=default_backend()).encryptor()
        message = encryptor.update(message) + encryptor.finalize() # encrypting
        argument=''.join(format(ord(x), 'b').rjust(8,'0') for x in key) # key as a binary
        DelDir('temp', create=True)
        with open('rdstego.log', 'a') as f: # separate frames and audio
                code=subprocess.call(['ffmpeg','-i',in_video,'-f','mp3','sound.mp3','-r',str(25),'temp/%05d.jpg','-y','-hide_banner'],stdout=f, stderr=f)
        print (u'Opened video file')
        Brightness_list=try_hide(message,argument, STEP,RESIZE_RATE, out_video, password)
        while not check(out_video, Brightness_list, argument): # in case compression did change the key
                print (u'Trying again.')
                STEP+=1
                Brightness_list=try_hide(message,argument,STEP, RESIZE_RATE, out_video, password)
        print (u'Step ='+str(STEP))
        print (u'Do not forget to check quality')
        clean()
def Extract(in_video, out_file, password=''):
        while len(password)<32: password+='1' # password has to be 128bit
        message=''
        print (u'Extracting data from '+ in_video+ u' into ' +out_file)
        DelDir ('extracted_temp', create = True)
        with open('rdstego.log', 'a') as f:
                code=subprocess.call(['ffmpeg','-i',in_video,'-acodec','copy','extracted_sound.mp3','-r',str(25),'extracted_temp/%05d.jpg','-y','-hide_banner'],stdout=f, stderr=f)
        if code!=0: # separate frames and audio
                clean()
                return False
        brightness_list=[]
        success=RevealFile('extracted_sound.mp3','decarr.txt')
        if not success:
                print ('Audio is broken =(')
                clean()
                return False
        try:
                with open('decarr.txt', "rb") as f:
                        content=f.read()
                        decryptor = Cipher(algorithms.AES(password), modes.CTR(OVERALL_CTR_VALUE), backend=default_backend()).decryptor()
                        content = decryptor.update(content) + decryptor.finalize()
                        content = zlib.decompress(content)
                        data=content.split(SEPARATOR)
                        brightness_list=data[0].split('\n')
                        message=data[1]
        except Exception:
                clean()
                return False
        key= ''.join(seek('extracted_temp', [int(s) for s in brightness_list[0:KEY_LENGTH]]))
        with open(out_file, "wb") as f:
                bytelist=[]
                for i in range(0,KEY_LENGTH):
                        if key[i*8:i*8+8]:
                                bytelist.append(int(key[i*8:i*8+8],2)) # already has chars
                        else:
                                break
                key=''.join(chr(x) for x in bytelist)
                while len(key)<32: key+='0'
                decryptor = Cipher(algorithms.AES(key), modes.CTR(INNER_CTR_VALUE), backend=default_backend()).decryptor()
                message = decryptor.update(message) + decryptor.finalize()
                f.write(message)
        clean()
        return True
def Available (in_video, message_file): # check available space
        DelDir('temp', create=True)
        try:
                with open('rdstego.log', 'a') as f: # separate frames and audio
                        subprocess.call(['ffmpeg','-i',in_video,'-f','mp3','sound.mp3','-r',str(25),'temp/%05d.jpg','-y','-hide_banner'],stdout=f, stderr=f)
                print (u'Opened video')
                bytes_available=AvailableInMp3('sound.mp3')
                print(u'Bytes available (audio): '+str(bytes_available))
                frame_count=len(os.listdir('temp'))
                print(u'Max key length = '+str(frame_count)+u' bits (not more than 128bit)')
                key=''.join(chr(random.randrange(0,255)) for i in range(KEY_LENGTH//8)) # test encryption key
                file=key
                file+=SEPARATOR
                with open(message_file, 'r') as f:
                        mas=f.read()
                        print (u'File size = '+str(len(mas))+u' bytes')
                        file+=mas
                compressed_file=zlib.compress(file)
                return bytes_available-len(compressed_file), (bytes_available-len(compressed_file)>0)
        except:
                return -1, False
def main():
        parser = argparse.ArgumentParser(
                prog='rdstego',
        description=u'Rdstego is an application to hide or extract a message/file inside a video. Input video: any. Output video: *.MP4')
        subparsers = parser.add_subparsers(help=u'commands', dest='command')
        # check available space
        parser_available = subparsers.add_parser('available', help=u'Check available space')
        parser_available.add_argument('-i','--input', dest='input_video_file', help=u'Video', required=True)
        parser_available.add_argument("-f",  "--file", dest="message_file", help=u"File to hide.")
        # hide
        parser_hide = subparsers.add_parser('hide', help=u'Video file and data to embed')
        parser_hide.add_argument("-i", "--input", dest="input_video_file", required=True, help="Input video file.")
        group_secret = parser_hide.add_mutually_exclusive_group(required=True)
        group_secret.add_argument("-m",  "--message", dest="message", help=u"Secret text") # text to hide
        group_secret.add_argument("-f",  "--file", dest="message_file", help=u"Secret file") # file to hide
        parser_hide.add_argument("-o", "--output", dest="output_video_file", required=True, help=u"Video")
        parser_hide.add_argument("-s", "--initial_step", dest="initial_step", required=False, help=u"DEFAULT=1. Increase it if process requires many attempts (for speed)")
        parser_hide.add_argument("-r", "--resize_rate", dest="resize_rate", required=False, help=u"Decrease resolution by X")
        # extract
        parser_extract = subparsers.add_parser('extract', help=u'Extract data from video')
        parser_extract.add_argument("-i", "--input", dest="input_video_file", required=True, help=u"Video with embedded data")
        parser_extract.add_argument("-o", "--output", dest="extracted_file", help=u"File to write extracted data")
        args = parser.parse_args()
        # Hiding
        if args.command == 'hide':
                message = ''
                if args.message:
                        message = args.message
                        print (message)
                elif args.message_file:
                        try:
                                with open(args.message_file, "rb") as f:
                                        message = f.read()
                        except Exception as error:
                                print(u'Unable to get file')
                                print(error)
                                return
                if message == '':
                        print(u'Nothing to hide.')
                        return
                password = ''
                print (u'Type password')
                password = getpass.getpass(prompt='')
                password_confirmation = ''
                print (u'Type password again')
                password_confirmation = getpass.getpass(prompt='')
                if password_confirmation != password:
                        print(u"Passwords don't match.")
                        exit(0)
                initial_step=1
                if args.initial_step: initial_step=int(args.initial_step)
                resize_rate=1 # resolution decrease rate (1 = keep it, 2 = 0.5x initial size, etc.)
                if args.resize_rate: resize_rate=int(args.resize_rate)
                output_video_file = args.output_video_file
                if (not output_video_file): output_video_file = 'hidden.mp4'
                else:
                        if output_video_file[-4:].lower() != '.mp4':# add extension if required
                                output_video_file += '.mp4'
                # hide
                try:
                        Hide(args.input_video_file, output_video_file, message, initial_step, resize_rate, password)
                except Exception as error:
                        print(error)
                        clean()
                        exit(1)
                print (u'SUCCESS. You can use '+output_video_file)
        # Extraction
        elif args.command == 'extract':
                password = getpass.getpass('Type password: ')
                with open(args.extracted_file,'w'): pass
                try:
                        secret=Extract(args.input_video_file, args.extracted_file,password)
                except:
                        print (u'No hidden data found')
                        clean()
                        exit(0)
                print (u'Check file '+args.extracted_file)
                print (u'It may contain your data if password was correct')
                if SHOW_EXTRACTED_MESSAGE:
                        message=''
                        with open(args.extracted_file, 'r') as f:
                                message = f.read()
                        print (u'Data:')
                        print (''.join([chr(ord(x)) for x in message]))
        elif args.command == 'available':
                print (u'Checking free space')
                result, success = Available(args.input_video_file,args.message_file)
                if success:
                        print (u'Enough space. '+str(result)+u' bytes available after hide')
                elif result==-1:
                        print (u'Error.')
                else:
                        print (u'Not enough space: need '+str(abs(result))+u' bytes more')
                        if abs(result)<30:
                                print (u'You may try anyway')
                clean()
if __name__ == '__main__':
        main()
