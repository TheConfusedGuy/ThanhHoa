# -*- coding: utf-8 -*-
import os
from unidecode import unidecode

folder = 'Am_Thanh_Data/ĐỐI NHÂN XỬ THẾ'
files = os.listdir(folder)
for filename in files:
    if filename.lower().endswith('.mp3'):
        ascii_name = unidecode(filename)
        ascii_name = ascii_name.replace(' ', '_')
        src = os.path.join(folder, filename)
        dst = os.path.join(folder, ascii_name)
        if src != dst:
            print(f'Renaming: {src} -> {dst}')
            os.rename(src, dst)
print('Done.')
