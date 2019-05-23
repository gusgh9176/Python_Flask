#-*- coding: utf-8 -*-
# file name : index.py
# pwd : /project_name/app/main/index.py

import os
from flask import Blueprint, request, render_template, flash, redirect, url_for
from flask import current_app as app
from werkzeug.utils import secure_filename

# 추가할 모듈이 있다면 추가
 
main = Blueprint('main', __name__, url_prefix='/')
ALLOWED_EXTENSIONS = set(['jpg'])

def allowed_file(filename):
      return '.' in filename and \
             filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/main', methods=['GET']) 
def index():
      # /main/index.html은 사실 /project_name/app/templates/main/index.html을 가리킵니다.
      return render_template('/main/index.html')

@main.route('/processing',methods=['GET','POST'])
def process():
      if request.method == 'POST':
            img = request.files['file']
            if img and allowed_file(img.filename):
                  # 이 아래에 모듈링크 img 변수 넣어서 넣으면 됨
                  
                  #f.save('c:/test/'+secure_filename(f.filename))
                  return render_template('/main/result.html', result_img = f)
      

      
