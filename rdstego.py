#!/usr/bin/python
# -*- coding: UTF-8 -*-
# rdstego - video steganography tool
# author: Gleb Rudometov
# email: javist.gr@mail.ru
# переменные, требующие настройки при создании стегосистемы:
OVERALL_CTR_VALUE='1111111111111111'    # нужны для корректного сокрытия и извлечения информации
INNER_CTR_VALUE='0000000000000000'      # должны совпадать при сокрытии и при извлечении на разных устройствах
KEY_LENGTH=128 #размер ключа шифрования в битах. максимум 128 бит (16 символов)
SHOW_VIDEO=False #показывать ли обрабатываемые фреймы
ADD_BLINKING=False #менять ли видеоряд?
SHOW_EXTRACTED_MESSAGE=False #показ извлечённой информации
# переменные, требующие настройки при создании стегосистемы.
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
def deldir(dirname, create=False): # функция удаления каталога с содержимым с возможностью создания каталога
        try:
                for root, dirs, files in os.walk(dirname, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(dirname)
        except (Exception): pass
        if create: os.mkdir(dirname)
def delfile(filename): # функция для удаления файла для случаев, когда удаление возможно
        try:
                os.remove(filename)
        except (Exception): pass
def clean():
        deldir('temp')
        deldir('temp2')
        deldir('temp_out')
        deldir('extracted_temp')
        delfile('sound.mp3')
        delfile('extracted_sound.mp3')
        delfile('decarr.txt')
        delfile('extracted_sound.mp3.txt')
        delfile('stegsound.mp3')
        delfile('rdmtstego.log')
def openimage(foldername, number):
        try:
                frame = cv2.imread(u'{}/{:05d}.jpg'.format(foldername, number))
                return frame, True
        except ():
                print (u'Не удалось открыть {}/{:05d}.jpg'.format(foldername, c))
                return [], False
def seek(foldername, brightness_list, frame_count=KEY_LENGTH): # извлекает ключ из видеоряда
        hidden_message=[] # извлекаемые биты
        for c in range(1,frame_count+1):
                frame, success=openimage(foldername, c)
                if not success:
                        exit(1)
                frame_brightness = int(numpy.sum(frame)/frame.shape[0]/frame.shape[1])
                if (frame_brightness > brightness_list[c-1]):
                        hidden_message.append(u'1')
                else: hidden_message.append(u'0')
        return hidden_message
def check(out_video,Brightness_list, argument):
        print (u'Проверка успеха операции')
        with open('rdmtstego.log', 'a') as f:
                code=subprocess.call(['ffmpeg','-i',out_video,'-r',str(25),'temp_out/%05d.jpg','-y','-hide_banner'],stdout=f, stderr=f)
        result=''.join(x for x in seek('temp_out', Brightness_list,len(os.listdir('temp'))))
        print (argument[0:KEY_LENGTH]+u' - закодированный ключ')
        arr3=[]
        correct=0
        print (result[0:KEY_LENGTH]+ u' - полученный ключ')
        length=min(len(argument),len(result))
        for x in range(KEY_LENGTH):
                if argument[x]==result[x]:
                        correct+=1
                        arr3.append(u'1')
                else:
                        arr3.append(u'0')
        print (u'СОВПАДАЕТ: '+str(correct)+u' of '+str(KEY_LENGTH))
        if correct<KEY_LENGTH:
                return False
        else:
                return True
def insert(pix, val, STEP, width, height): # 1 фрейм - упаковка ключа
        pix[numpy.where(pix < STEP*2)] = STEP*2
        pix-=STEP
        maspoint=int(pix.sum()/width/height) # точка отсчёта. будет передаваться отдельно от видеоряда
        if val=='1':
                pix+=STEP
        else:
                pix-=STEP
        return pix, maspoint
def no_insert(pix, val, STEP, width, height):
        if val=='1':
                maspoint=int(pix.sum()/width/height)-STEP
        else:
                maspoint=int(pix.sum()/width/height)+STEP
        return pix, maspoint
def hide(foldername, argument, outfoldername, STEP, RESIZE_CONSTANT=1):  # argument is information to hide
        #print (u'Ключ для кодирования в яркости видео: '+argument)
        frame_count=len(os.listdir('temp'))
        while len(argument)<=frame_count:argument+=random.choice(['0','1']) #чтобы все видео было случайным
        brightness_list=[] # нужен для последующего извлечения информации из видеоряда
        for c in range(1, frame_count+1):
                frame, success = openimage(foldername, c)
                if not success:
                        exit(1)
                frame = cv2.resize(frame, dsize=None, fx=RESIZE_CONSTANT, fy=RESIZE_CONSTANT)
                # меньше разрешение видео - быстрее упаковка ключа. портится качество
                if ADD_BLINKING:
                        out, mas = insert(frame, argument[c-1], STEP, frame.shape[1], frame.shape[0])
                else:
                        out, mas = no_insert(frame, argument[c-1], STEP, frame.shape[1], frame.shape[0])
                brightness_list.append(mas)
                try:
                        cv2.imwrite('{}/{:05d}.jpg'.format(outfoldername, c), frame)
                except():
                        print (u'Не удалось записать '+'{}/{:05d}.jpg'.format(outfoldername, c))
                        exit(1)
                ##### Вывод изображения #####
                if SHOW_VIDEO:
                        try:
                                out = cv2.resize(out, dsize=None, fx=1.0/RESIZE_CONSTANT, fy=1.0/RESIZE_CONSTANT)
                                cv2.imshow(u'Resulting video in real size', out)
                                k=cv2.waitKey(1)
                        except Exception as error:
                                print (u'Не найден дисплей', error)
                ##### конец вывода #####
        cv2.destroyAllWindows()
        return brightness_list
def try_hide(message,key, STEP, RESIZE_RATE, out_video, password='', bytes_available=0):
        while len(password)<32: password+='1' # пароль для шифрования всего содержимого аудиофайла. тебуется для расшифровки
        content='' # содержимое скрываемого в аудиоряде файла
        Brightness_list=[]
        deldir('temp2', create=True)
        deldir('temp_out',create=True)
        Brightness_list = hide('temp', key, 'temp2', STEP, RESIZE_RATE)
        with open('rdmtstego.log', 'a') as f:
                bytes_available=subprocess.call(['mp3stegz_console.exe','available','sound.mp3'],stdout=f, stderr=f)
        print(u'Всего байтов доступно (в аудио): '+str(bytes_available))
        if len(os.listdir('temp'))<KEY_LENGTH:
                print (u'Видео слишком короткое.')
                exit(1)
        if Brightness_list:
                print (u'Информация сохранена. '+u'Шаг яркости = '+str(STEP))
        try:
                for item in range(0,KEY_LENGTH):
                        content+="%d\n" % Brightness_list[item]
                print (u'Размер данных для извлечения ключа = '+str(len(content)))
        except Exception as error:
                print (u'Не удалось составить массив. Извлечь информацию из видео не получится.'+ error)
                exit(1)
        print (u'Запись сообщения в звук')
        content += '@#@#'
        content += message
        content = zlib.compress(content)
        print (u'Размер файла после сжатия: %d' % len(content))
        encryptor = Cipher(algorithms.AES(password), modes.CTR(OVERALL_CTR_VALUE), backend=default_backend()).encryptor()
        content = encryptor.update(content) + encryptor.finalize() # шифрование сообщения паролем
        if len(content)>bytes_available:
                print (u'Сообщение слишком большое для сокрытия в видеофайле')
                exit(0)
        with open('decarr.txt','wb') as f:
                f.write(content)
        print (u'Прячем файл в аудио...')
        try:
                with open('rdmtstego.log', 'a') as f:
                        code = subprocess.call(
                                ['mp3stegz_console.exe', 'hide','decarr.txt', 'sound.mp3','stegsound.mp3'], stdout=f, stderr=f)
                print (u'Список спрятан в аудио')
        except Exception as error:
                print (u'Список НЕ спрятан в аудио. Вероятно, он слишком большой.')
                print (error)
        print (u'ЗАПИСЬ ВИДЕО')
        with open('rdmtstego.log', 'a') as f:
                code=subprocess.call(['ffmpeg','-i','stegsound.mp3','-r',str(25),'-i','temp2/%05d.jpg','-c:v','libx264','-crf',str(25),'-acodec',
                                      'copy',out_video,'-y','-hide_banner'],stdout=f, stderr=f)
        return Brightness_list
def proceed(in_video, out_video, message, STEP, RESIZE_RATE, password=''):
        key=''.join(chr(random.randrange(0,255)) for i in range(KEY_LENGTH//8)) #ключ шифрования самого сообщения для AES, 16байт (128бит)
        while len(key)<32: key+='0'
        encryptor = Cipher(algorithms.AES(key), modes.CTR(INNER_CTR_VALUE), backend=default_backend()).encryptor()
        message = encryptor.update(message) + encryptor.finalize() # шифрование сообщения ключом
        argument=''.join(format(ord(x), 'b').rjust(8,'0') for x in key) #ключ в бинарном виде
        deldir('temp', create=True)
        with open('rdmtstego.log', 'a') as f: # отделяется аудио и фреймы
                code=subprocess.call(['ffmpeg','-i',in_video,'-f','mp3','sound.mp3','-r',str(25),'temp/%05d.jpg','-y','-hide_banner'],stdout=f, stderr=f)
        print (u'Видео открыто')
        Brightness_list=try_hide(message,argument, STEP,RESIZE_RATE, out_video, password)
        while not check(out_video, Brightness_list, argument): # если после сжатия видео ключ был потерян
                print (u'Пробуем ещё раз. Шаг яркости увеличен.')
                STEP+=1
                Brightness_list=try_hide(message,argument,STEP, RESIZE_RATE, out_video, password)
        print (u'Шаг яркости ='+str(STEP)+u'\nНе забудьте проверить качество видео перед использованием')
        clean()
def extract(in_video, out_file, password=''):
        while len(password)<32: password+='1' # пароль для шифрования всего содержимого аудиофайла. тебуется для расшифровки
        message=''
        print (u'Извлечение данных из '+ in_video+ u' в ' +out_file)
        deldir ('extracted_temp', create = True) # готовим папку для фреймов
        with open('rdmtstego.log', 'a') as f:
                code=subprocess.call(['ffmpeg','-i',in_video,'-acodec','copy','extracted_sound.mp3','-r',str(25),'extracted_temp/%05d.jpg','-y','-hide_banner'],stdout=f, stderr=f)
        if code!=0: # отделяется аудио и отделяются фреймы
                clean()
                raise Exception
        brightness_list=[]
        with open('rdmtstego.log', 'a') as f:
                code = subprocess.call(
                        ['mp3stegz_console.exe', 'reveal', 'extracted_sound.mp3'], stdout=f, stderr=f)
        if code!=0:
                print ('Аудио испорчено. К сожалению, информацию нельзя извлечь.')
                clean()
                return False
        try:
                with open('extracted_sound.mp3.txt', "rb") as f:
                        content=f.read()
                        decryptor = Cipher(algorithms.AES(password), modes.CTR(OVERALL_CTR_VALUE), backend=default_backend()).decryptor()
                        content = decryptor.update(content) + decryptor.finalize()
                        content = zlib.decompress(content)
                        data=content.split('@#@#')
                        brightness_list=data[0].split('\n')
                        message=data[1]
                print (u'Массив для извлечения информации открыт')
        except Exception as error:
                print (u'Не удалось получить массив. Извлечь информацию из видео не получится. '+ error)
        #print (brightness_list)
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
def available (in_video, message_file): #проверка до начала работы сокрытия. вызывается пользователем
        deldir('temp', create=True)
        try:
                with open('rdmtstego.log', 'a') as f: # отделяется аудио и фреймы
                        subprocess.call(['ffmpeg','-i',in_video,'-f','mp3','sound.mp3','-r',str(25),'temp/%05d.jpg','-y','-hide_banner'],stdout=f, stderr=f)
                print (u'Видео открыто')
                with open('rdmtstego.log', 'a') as f:
                        bytes_available=subprocess.call(['mp3stegz_console.exe','available','sound.mp3'],stdout=f, stderr=f)
                print(u'Всего байтов доступно (в аудио): '+str(bytes_available))
                frame_count=len(os.listdir('temp'))
                print(u'Максимальная длина ключа = '+str(frame_count)+u' бит (ключи длиннее 128бит не предусмотрены шифром)')
                key=''.join(chr(random.randrange(0,255)) for i in range(KEY_LENGTH//8)) #ключ шифрования самого сообщения для AES, 16байт (128бит)
                file=key
                file+='@#@#'
                with open(message_file, 'r') as f:
                        mas=f.read()
                        print (u'Размер файла '+str(len(mas))+u' байт')
                        file+=mas
                compressed_file=zlib.compress(file)
                return bytes_available-len(compressed_file), (bytes_available-len(compressed_file)>0)
        except:
                return -1, False
def main():
        parser = argparse.ArgumentParser(
                prog='rdstego',
        description=u'Программа rdstego предназначена для скрытия информации в видео и её извлечения. На выходе всегда получается *.mp4 файл')
                #Rdstego is an application to save or retrieve an encrypted message or encrypted file concealed inside a video.)
        subparsers = parser.add_subparsers(help=u'команды', dest='command')
        # Пункт "Доступное место"
        parser_available = subparsers.add_parser('available', help=u'Проверка пригодности видео. Показывает допустимый размер сообщения')
        parser_available.add_argument('-i','--input', dest='input_video_file', help=u'Видео файл для проверки', required=True)
        parser_available.add_argument("-f",  "--file", dest="message_file", help=u"Файл с секретными данными.")
        # Пункт "Спрятать"
        parser_hide = subparsers.add_parser('hide', help=u'Спрятать в видео')
        # Видеоконтейнер
        parser_hide.add_argument("-i", "--input", dest="input_video_file",
                                                         required=True, help="Input_video_file.")
        group_secret = parser_hide.add_mutually_exclusive_group(required=True)
        # Текстовое сообщение для упаковки
        group_secret.add_argument("-m",  "--message", dest="message",
                                                          help=u"Секретный текст")
        # Файл для упаковки
        group_secret.add_argument("-f",  "--file", dest="message_file",
                                                          help=u"Файл с секретными данными.")
        # Видео с файлом
        parser_hide.add_argument("-o", "--output", dest="output_video_file",
                                                         required=True, help=u"Видео с данными.")
        # Шаг мерцания (для кодирования в яркости)
        parser_hide.add_argument("-s", "--initial_step", dest="initial_step",
                                                         required=False, help=u"Минимальная сила мерцания видео.")
        # Коэффициент уменьшения (можно уменьшить разрешение контейнера)
        parser_hide.add_argument("-r", "--resize_rate", dest="resize_rate",
                                                         required=False, help=u"Коэффициент уменьшения разрешения видео. по умолчанию = 1")
        # Пункт "Извлечь"
        parser_extract = subparsers.add_parser('extract', help=u'Достать из видео')
        parser_extract.add_argument("-i", "--input", dest="input_video_file",
                                                           required=True, help=u"Видео с данными.")
        parser_extract.add_argument("-o", "--output", dest="extracted_file",
                                                           help=u"В какой файл записать информацию")
        args = parser.parse_args()
        # Спрятать
        if args.command == 'hide':
                message = ''
                if args.message:
                        message = args.message
                        print (message)
                elif args.message_file:
                        try:
                                with open(args.message_file, 'r', encoding='utf-8') as f:
                                        message = f.read()
                                        print (message)
                                        # Текстовый файл
                                        # Вывод содержимого для проверки
                        except Exception as error:
                                try:
                                        # Если файл не текстовый, то просто открываем
                                        with open(args.message_file, "rb") as f:
                                                message = f.read()# Бинарный файл
                                except Exception as error:
                                        # Совсем нет файла или сообщения
                                        print(u'Не удалось открыть секретный файл')
                                        print(error)
                                        return
                if message == '':
                        print(u'Пустое сообщение. Нечего прятать.')
                        return
                # Пароль для шифрования. Он должен быть и у получателя
                password = ''
                print (u'Задайте пароль')
                password = getpass.getpass(prompt='')
                password_confirmation = ''
                print (u'Введите пароль ещё раз')
                password_confirmation = getpass.getpass(prompt='')
                if password_confirmation != password:
                        print(u'Пароли не совпадают.')
                        exit(0)
                initial_step=1
                if args.initial_step: initial_step=int(args.initial_step) #сила мерцания
                resize_rate=1 # коэффициент уменьшения видео (1 = нормально, 2 = разрешение уменьшено вдвое, значения меньше 1 не поддерживаются)
                if args.resize_rate: resize_rate=int(args.resize_rate) #сила мерцания
                #лучше качество видео - меньше требуемый шаг. на большом STEP мерцание заметнее
                output_video_file = args.output_video_file
                if (not output_video_file): output_video_file = 'hidden.mp4'
                else:
                        if output_video_file[-4:].lower() != '.mp4':# Если нет расширения, нужно добавить
                                output_video_file += '.mp4'
                # Прячем
                try: proceed(args.input_video_file, output_video_file, message, initial_step, resize_rate, password)
                except Exception as error:
                        print(u'Непредвиденная ошибка')
                        print(error)
                        exit(1)
                print (u'УСПЕШНО. Можно использовать видео '+output_video_file)
        # Извлечение
        elif args.command == 'extract':
                password = ''
                print (u'Введите пароль') # Запросить пароль
                password = getpass.getpass('')
                try:
                        secret=extract(args.input_video_file, args.extracted_file,password)
                except:
                        print (u'Скрытых данных не обнаружено')
                        exit(0)
                print (u'Данные извлечены в файл '+args.extracted_file)
                if SHOW_EXTRACTED_MESSAGE:
                        message=''
                        with open(args.extracted_file, 'r') as f:
                                message = f.read()
                        print (u'Данные:')
                        print (''.join([chr(ord(x)) for x in message]))
        elif args.command == 'available':
                print (u'Проверка доступного места')
                result, success = available(args.input_video_file,args.message_file)
                if success:
                        print (u'Сообщение может поместиться. Ещё влезет около '+str(result)+u' байт')
                elif result==-1:
                        print (u'Ошибка.')
                else:
                        print (u'Не хватает места для '+str(abs(result))+u' байт')
                        print (u'Если сообщение не поместилось, но расхождение небольшое (меньше 20 байт), можно попытаться выполнить сокрытие.')
                        print (u'Успех зависит от генератора случайных чисел.')
                clean()
if __name__ == '__main__':
        clean() # на случай сбоя при предыдущем запуске
        main()
