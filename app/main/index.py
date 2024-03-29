#-*- coding: utf-8 -*-
# file name : index.py
# pwd : /project_name/app/main/index.py
import os
from flask import Blueprint, request, render_template, flash, redirect, url_for
from flask import current_app as app
from werkzeug.utils import secure_filename
import math
import cv2
import numpy as np
import imutils
from keras.models import model_from_json
from PIL import Image     #pip install pillow
from pytesseract import * #pip install pytesseract
import configparser
from googletrans import Translator
from keras import backend as K

translator=Translator()
# 추가할 모듈이 있다면 추가

#사각형
class rectang:
    x1=0
    y1=0
    x2=0
    y2=0
    live = 1
    def __init__(self, x1, y1, x2, y2):
        self.x1=x1
        self.y1=y1
        self.x2=x2
        self.y2=y2

#허프 변환
def removeVerticalLines(img, limit):
    lines = None
    threshold = 100
    minLength = 60
    lineGap = 10
    rho = 1
    lines = cv2.HoughLinesP(img, rho, np.pi/180, threshold, minLength, lineGap)
    if(lines is not None):   # lines  이 비지 않았을때만 실행한다.
        for i in range(len(lines)):
            for x1, y1, x2, y2 in lines[i]:
                gapY = abs(y2-y1)
                gapX = abs(x2-x1)
                if(gapY>limit or gapX>limit and limit>0):
                    cv2.line(img, (x1,y1), (x2,y2), (0, 0, 0), 3)

def change1(img):
    temp_img = img.copy()
    temp_img = cv2.bilateralFilter(temp_img,9,75,75)
    #노이즈 제거 위한 커널(erode)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    erode = cv2.erode(temp_img, kernel, iterations=1)
    #이미지 grayscale
    gray = cv2.cvtColor(temp_img, cv2.COLOR_BGR2GRAY)
    #global 이진화
    ret1, th = cv2.threshold(gray,127,255,cv2.THRESH_BINARY)
    canny = cv2.Canny(th,180,250, apertureSize = 5)
    #직선 제거
    removeVerticalLines(canny, 70)
    return canny


def change2(img):
    temp_img = img.copy()

    # 노이즈 제거 위한 커널(erode)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 1))
    # 이미지 grayscale
    #     gray = cv2.cvtColor(temp_img, cv2.COLOR_BGR2GRAY)
    erode = cv2.erode(temp_img, kernel, iterations=2)

    # 이진화
    #     ret1, th = cv2.threshold(dilation,127,255,cv2.THRESH_BINARY)
    ret1, th = cv2.threshold(erode, 127, 255, cv2.THRESH_BINARY)
    canny = cv2.Canny(th, 180, 250, apertureSize=5)
    return canny


# 작은 사각형 합쳐서 큰 사각형 합치는 함수
def combineRectang(rect_List):
    avr_height = 0
    #   사각형 내부 사각형 live = 0 만듬
    for r1 in range(len(rect_List)):
        for r2 in range(len(rect_List)):
            if ((rect_List[r1].x1 < rect_List[r2].x1) and (rect_List[r1].x2 >= rect_List[r2].x2)):
                if ((rect_List[r1].y1 < rect_List[r2].y1) and (rect_List[r1].y2 >= rect_List[r2].y2)):
                    rect_List[r2].live = 0
    # live = 0 인 인덱스 제거
    temp_List = []
    for x in rect_List:
        if (x.live == 1):
            temp_List.append(x);
    rect_List = temp_List

    # 버블 정렬로 사각형들 왼쪽에서 오른쪽순으로 정렬함(가장 왼쪽 사각형이 0)
    for i in range(len(rect_List)):
        for j in range(0, len(rect_List) - (i + 1)):
            if (rect_List[j].x1 > rect_List[j + 1].x1):
                temp_rect = rect_List[j]
                rect_List[j] = rect_List[j + 1]
                rect_List[j + 1] = temp_rect
    # 높이 평균 1번
    for x in rect_List:
        avr_height = avr_height + abs(x.y2 - x.y1)
    avr_height = avr_height / len(rect_List)

    #     오른쪽으로 인접한 사각형 구할때 필요한 count 값 만들기
    for i in range(len(rect_List) - 1):
        for j in range((i + 1), len(rect_List)):
            plate_width = 0
            dif_x = abs(rect_List[i].x2 - rect_List[j].x1)  # 문자 하나의 끝과 다음 사각형 문자 시작 사이의 x거리차이
            dif_y = abs(rect_List[i].y1 - rect_List[j].y1)
            # 첫번째 합쳐지는 j 찾음 = k
            if (rect_List[j].live == 1 and dif_x < avr_height * 1.5 and dif_y < avr_height * 0.5):
                rect_List[j].live = 0
                plate_width = abs(rect_List[i].x2 - rect_List[j].x2)  # i 끝과 j 끝의 x좌표 차이
            rect_List[i].x2 = rect_List[i].x2 + plate_width

    # 리스트에서 live ==0 인 인덱스 제거
    rect_List2 = []
    for x in rect_List:
        if (x.live == 1):
            rect_List2.append(x)
    # 가로 사각형 합치기 끝

    # 버블 정렬로 사각형들 위에서 아래순으로 정렬함(가장 위 사각형이 0)
    for i in range(len(rect_List2)):
        for j in range(0, len(rect_List2) - (i + 1)):
            if (rect_List2[j].y1 > rect_List2[j + 1].y1):
                temp_rect = rect_List2[j]
                rect_List2[j] = rect_List2[j + 1]
                rect_List2[j + 1] = temp_rect

    # 높이 평균 2번
    avr_height = 0
    for x in rect_List2:
        avr_height = avr_height + abs(x.y2 - x.y1)
    avr_height = avr_height / len(rect_List2)
    # 세로 사각형 합치기
    for i in range(len(rect_List2) - 1):

        for j in range((i + 1), len(rect_List2)):
            plate_height = 0
            switch = False
            dif_x = abs(rect_List2[i].x1 - rect_List2[j].x1)  # 가로 합치는 부분과 다름, i와 j의 사각형 시작 x좌표 차이
            dif_x2 = abs(rect_List2[i].x2 - rect_List2[j].x2)
            dif_y = abs(rect_List2[i].y2 - rect_List2[j].y1)  # 가로 합치는 부분과 다름, i의 끝과 j의 시작 사이의 y좌표 차이

            if (rect_List2[i].x1 >= rect_List2[j].x1 and rect_List2[i].x2 <= rect_List2[j].x2):
                switch = True
            elif (rect_List2[i].x1 <= rect_List2[j].x1 and rect_List2[i].x2 >= rect_List2[j].x2):
                switch = True
            # 첫번째 합쳐지는 j 찾음 = k
            elif (dif_x < avr_height * 2 and dif_x2 < avr_height * 2):
                switch = True
            if (switch and dif_y < avr_height and rect_List2[j].live):
                rect_List2[j].live = 0
                plate_height = rect_List2[j].y2 - rect_List2[i].y2  # i 끝과 j 끝의 y좌표 차이
                if (rect_List2[i].x1 > rect_List2[j].x1):
                    rect_List2[i].x1 = rect_List2[j].x1
                if (rect_List2[i].x2 < rect_List2[j].x2):
                    rect_List2[i].x2 = rect_List2[j].x2
            rect_List2[i].y2 = rect_List2[i].y2 + plate_height
    # 세로 사각형 합치기 끝

    # 리스트에서 live ==0 인 인덱스 제거 제거
    rect_List3 = []
    for x in rect_List2:
        if (x.live == 1):
            rect_List3.append(x);
    '''
    for r1 in range(len(rect_List3)):
        for r2 in range(len(rect_List3)):
            if (r1 == r2):
                continue
            if ((rect_List3[r1].x1 <= rect_List3[r2].x1) and (rect_List3[r1].x2 >= rect_List3[r2].x2)):
                if ((rect_List3[r1].y2 - rect_List3[r1].y1) > (rect_List3[r2].y2 - rect_List3[r2].y1)):
                    rect_List3[r2].live = 0
            if ((rect_List3[r1].y1 <= rect_List3[r2].y1) and (rect_List3[r1].y2 >= rect_List3[r2].y2)):
                if ((rect_List3[r1].x2 - rect_List3[r1].x1) > (rect_List3[r2].x2 - rect_List3[r2].x1)):
                    rect_List3[r2].live = 0
    rect_List4 = []
    for x in rect_List3:
        if (x.live == 1):
            rect_List4.append(x);
    '''
    return rect_List3

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
                  K.clear_session()
                  # 이미지 변수에 저장
                  img.save('./temp_src/' + secure_filename(img.filename))
                  src=cv2.imread('./temp_src/'+secure_filename(img.filename), cv2.IMREAD_UNCHANGED)
                  os.remove('./temp_src/'+secure_filename(img.filename))
                  # 텐서플로우에 전달할 이미지를 저장할 배열
                  image_List = []
                  # rectangle 배열
                  rect_List = []

                  # drawContours 가 원본이미지를 변경하기에 이미지 복사
                  img1 = src.copy()  # 처음 Contours 그려짐
                  img2 = src.copy()  # Rectangle Contours 그려짐

                  # CannyEdge
                  canny = change1(src)

                  # Contours 찾음
                  contours, hierachy = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                  # 그림에 Contours 그림
                  img1 = cv2.drawContours(img1, contours, -1, (0, 255, 0), 1)

                  # Contours를 사각형으로 만듬
                  for cnt in contours:

                        # 크기 작은 사격형 Contours 그리지 않음
                        x, y, w, h = cv2.boundingRect(cnt)
                        aspect_ratio = float(w) / h
                        if (w < 70) or (h < 50):
                              continue
                        # rectangle 좌표들 배열에 저장
                        rect_List.append(rectang(x, y, x + w, y + h))

                  # 사각형 내부의 사각형 제거. 가로,세로 좌표가 다른 사각형 내부에 포함되면 그려지지않게함
                  for r1 in rect_List:
                        switch = True
                        for r2 in rect_List:
                              continue
                        # 해당 될시 그리는부분 스킵
                        if (switch):
                              # 배열에 텐서플로우에 전달할 이미지 저장
                              dst = src.copy()
                              dst = src[r1.y1:r1.y2, r1.x1:r1.x2]
                              dst_gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
                              dst_ret, dst_gray = cv2.threshold(dst_gray, 127, 255, cv2.THRESH_BINARY)
                              dst_laplacian = cv2.Laplacian(dst_gray, cv2.CV_8U)
                              dst_laplacian = cv2.resize(dst_laplacian, dsize=(100, 100), interpolation=cv2.INTER_AREA)
                              image_List.append(dst_gray)

                  for r1 in rect_List:
                        img2 = cv2.rectangle(img2, (r1.x1, r1.y1), (r1.x2, r1.y2), (0, 0, 0), 1)
                  # cv2.imshow("check1", img3)
                  # cv2.waitKey(0)
                  json_file = open("model.json", "r")
                  loaded_model_json = json_file.read()
                  json_file.close()
                  loaded_model = model_from_json(loaded_model_json)
                  loaded_model.load_weights("model.h5")
                  loaded_model.compile(loss="binary_crossentropy", optimizer="adam", metrics=['accuracy'])

                  # 모델에 맞게 inputdata를 reform
                  for i in range(len(image_List)):
                        image_List[i] = cv2.resize(image_List[i], (200, 200))
                        image_List[i] = image_List[i] / 255

                  image_List = np.asarray(image_List)
                  image_List = image_List.reshape(len(image_List), 200, 200, 1)

                  # In[91]:

                  # 모델에 image를 적용하여 predict class 출력
                  y = loaded_model.predict_classes(image_List)

                  # 모델을 거쳐 말풍선인 이미지만 저장할 배열 생성
                  text_rect_List = []
                  text_image_List = []

                  # In[92]:

                  # predict내부의 값을 가지고 말풍선이 담긴 이미지 저장
                  for i in range(len(y)):
                        if y[i] == 0:
                              dst = src.copy()
                              dst = src[rect_List[i].y1:rect_List[i].y2, rect_List[i].x1:rect_List[i].x2]
                              text_rect_List.append(
                                    rectang(rect_List[i].x1, rect_List[i].y1, rect_List[i].x2, rect_List[i].y2))
                              text_image_List.append(dst)

                  for r1 in text_rect_List:
                      img2 = cv2.rectangle(img2, (r1.x1, r1.y1), (r1.x2, r1.y2), (255, 0, 0), 3)
                  # cv2.imshow("말풍선 판별", img2)
                  # cv2.waitKey(0)
                  print("step1 : 말풍선 위치 추출 완료")

                  text_rect_List2 = []
                  text_image_List2 = []
                  i = 0
                  for r1 in text_rect_List:
                      if (r1.live == 1):
                          dst = src[r1.y1:r1.y2, r1.x1:r1.x2]
                          # cv2.imshow("temp", dst)
                          # cv2.waitKey(0)
                          j = 0
                          for r2 in text_rect_List:
                              if ((r2.live == 1) and (r1.live == 1) and (i != j)):
                                  if (((r1.y1 < r2.y2) and (r1.y2 > r2.y1)) and ((r1.x1 < r2.x2) and (r1.x2 > r2.x1))):
                                      if (((min(r1.y2, r2.y2) - max(r1.y1, r2.y1)) > (r1.y2 - r1.y1) * 0.7) and (
                                              (min(r1.x2, r2.x2) - max(r1.x1, r2.x1)) > (r1.y2 - r1.y1) * 0.7)):
                                          r1.live = 0
                                          r2.x1 = min(r1.x1, r2.x1)
                                          r2.x2 = max(r1.x2, r2.x2)
                                          r2.y1 = min(r1.y1, r2.y1)
                                          r2.y2 = max(r1.y2, r2.y2)
                              j = j + 1
                      i = i + 1

                  for r1 in text_rect_List:
                      if (r1.live == 1):
                          text_rect_List2.append(r1)
                          img2 = cv2.rectangle(img2, (r1.x1, r1.y1), (r1.x2, r1.y2), (0, 255, 0), 3)

                  text_rect_List2.reverse()
                  for r1 in text_rect_List2:
                      dst = src[r1.y1:r1.y2, r1.x1:r1.x2]
                      text_image_List2.append(dst)

                  img2 = cv2.pyrDown(img2)
                  img2 = cv2.pyrDown(img2)
                  #cv2.imshow("blue=Abandoned  green=save", img2)
                  #cv2.waitKey(0)

                  print("step2 : 중복 제거 완료")


                  count = 0
                  # 이미지 변수에 저장
                  for image in text_image_List2:
                        # 텐서플로우에 전달할 이미지를 저장할 배열
                        # rectangle 배열
                        combine_image_List = []
                        combine_rect_List = []
                        combine_src = image
                        # drawContours 가 원본이미지를 변경하기에 이미지 복사
                        combine_img1 = combine_src.copy()  # 처음 Contours 그려짐
                        combine_img2 = combine_src.copy()  # Rectangle Contours 그려짐
                        # CannyEdge
                        combine_canny = change2(combine_src)

                        # Contours 찾음
                        combine_contours, combine_hierachy = cv2.findContours(combine_canny, cv2.RETR_TREE,
                                                                              cv2.CHAIN_APPROX_SIMPLE)

                        # 그림에 Contours 그림
                        combine_img1 = cv2.drawContours(combine_img1, combine_contours, -1, (0, 255, 0), 1)

                        # Contours를 사각형으로 만듬
                        for cnt in combine_contours:

                              # 정해진 크기가 아닌 사격형 Contours 그리지 않음
                              x, y, w, h = cv2.boundingRect(cnt)
                              aspect_ratio = float(w) / h
                              if (h < 15) or (h > 50) or (w > 40):
                                    continue
                              if (aspect_ratio > 1.5) and (aspect_ratio <= 0.2):
                                    continue
                              # rectangle 좌표들 배열에 저장
                              combine_rect_List.append(rectang(x, y, x + w, y + h))

                              #######중심함수
                        if (len(combine_rect_List) != 0):
                              combine_rect_List = combineRectang(combine_rect_List)

                        for o3 in range(len(combine_rect_List)):
                              combine_img2 = cv2.rectangle(combine_img2,
                                                           (combine_rect_List[o3].x1, combine_rect_List[o3].y1),
                                                           (combine_rect_List[o3].x2, combine_rect_List[o3].y2),
                                                           (0, 255, 0), 1)

                              # 배열에 텐서플로우에 전달할 이미지 저장
                              combine_dst = combine_src.copy()
                              combine_dst = combine_src[combine_rect_List[o3].y1:combine_rect_List[o3].y2,
                                            combine_rect_List[o3].x1:combine_rect_List[o3].x2]
                              comb_gray = cv2.cvtColor(combine_dst, cv2.COLOR_BGR2GRAY)
                              dst_ret, comb_gray = cv2.threshold(comb_gray, 127, 255, cv2.THRESH_BINARY)
                              # print('세로',combine_rect_List[o3].y2-combine_rect_List[o3].y1, '가로', combine_rect_List[o3].x2-combine_rect_List[o3].x1)
                              combine_image_List.append(comb_gray)

                        # for i in range(len(combine_image_List)):
                        #    cv2.imshow("img"+str(i),image_List[i])
                        # cv2.imshow("combine_img2", combine_img2)
                        # cv2.waitKey(0)

                        '''
                        print("go ? :")
                        go=input()
                        if(go==0):
                            continue
                        '''

                        # ln[93]:
                        json_file = open("model2.json", "r")
                        loaded_model_json = json_file.read()
                        json_file.close()
                        loaded_model = model_from_json(loaded_model_json)
                        loaded_model.load_weights("model2.h5")
                        loaded_model.compile(loss="binary_crossentropy", optimizer="adam", metrics=['accuracy'])

                        for i in range(len(combine_image_List)):
                              combine_image_List[i] = cv2.resize(combine_image_List[i], (200, 200))
                              combine_image_List[i] = combine_image_List[i] / 255

                        combine_image_List = np.asarray(combine_image_List)
                        combine_image_List = combine_image_List.reshape(len(combine_image_List), 200, 200, 1)

                        # ln[94]:

                        # 모델에 image를 적용하여 predict class 출력
                        try:
                              y = loaded_model.predict_classes(combine_image_List)
                        except:
                              continue
                        # print(y)

                        # 모델을 거쳐 문단인 이미지만 저장할 배열 생성
                        p_rect_List = []
                        p_image_List = []

                        # ln[95]:

                        # predict내부의 값을 가지고 문단이 담긴 이미지 저장
                        for i in range(len(y)):
                              if y[i] == 0:
                                    dst = combine_src.copy()
                                    dst = combine_src[combine_rect_List[i].y1 - 5:combine_rect_List[i].y2,
                                          combine_rect_List[i].x1:combine_rect_List[i].x2]
                                    cv2.imwrite('./temp_image/' + str(count) + '.jpg', dst)

                                    count = count + 1
                                    p_rect_List.append(rectang(combine_rect_List[i].x1, combine_rect_List[i].y1,
                                                               combine_rect_List[i].x2, combine_rect_List[i].y2))
                                    p_image_List.append(dst)

                        for r1 in p_rect_List:
                              img = cv2.rectangle(combine_img2, (r1.x1, r1.y1), (r1.x2, r1.y2), (0, 255, 255), 1)

                        # cv2.imshow("check2", combine_img2)
                        # cv2.waitKey(0)
                  print("step3 : 문단 위치 추출 완료")
                  try:
                      path_dir = './temp_image/'
                      temp_image = os.listdir(path_dir)
                      temp_image.sort(key=len)

                      final_text = []
                      final_temp=''

                      for t_image in temp_image:
                            final_temp=''
                            path = './temp_image/'
                            img = Image.open(path + t_image)

                            fileName = str(i)
                            outText = image_to_string(img, lang='eng')
                            outText = outText.lower()
                            if(outText==''):
                                continue
                            final_temp = final_temp + "(" + t_image + ") >>\n" + outText + "\n"

                            outText = outText.replace('\n', ' ')
                            en_var = translator.translate(outText, dest='ko')

                            final_temp = final_temp + "-->\n" + en_var.text

                            final_text.append(final_temp)
                  except:
                      print(".")

                  for i in range(0, count):
                      # 처리 이후 임시 파일 삭제
                      os.remove(path + str(i)+'.jpg')
                  print("step4 : 글자 추출, 번역 완료")
                  return render_template('/main/result.html', textList = final_text, len=len(final_text))
      

      
