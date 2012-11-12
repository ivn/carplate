# -*- coding: utf-8 -*-
import cv2

import numpy as np

from Queue import Queue

from SWT_Support import *

from Bresenham import Selector


makestep = lambda point, step: (point[0] + step[0], point[1] + step[1])
checkbound = lambda point, image: (
            (point[0] < image.shape[0]) and (point[1] < image.shape[1]) and
            (point [0] >= 0) and (point [1] >= 0))

checkbound_sq = lambda point, image: (
            (point[0] + 1 < image.shape[0]) and (point[1] + 1 < image.shape[1]) and
            (point [0] - 1 > 0) and (point [1] - 1 > 0))

#barrier const for CC
CC_B = float('inf')

def Variance(vec, image):
    avg = float(sum((image[p[0], p[1]] for p in vec))) / len(vec)
    res = 1.0 / len(vec) * sum(( (image[p[0], p[1]] - avg)**2 for p in vec))
    return res

def VarianceFromRect(p1, p2, image):
    tmp = []
    for i in xrange(p1[0], p2[0]):
        for j in xrange(p1[1], p2[1]):
            tmp.append((i, j))
    if not tmp: return 0
    return Variance(tmp, image)

def CutRect(image, p1, p2, border=0):
    return image[p1[0]-border:p2[0]+border, p1[1]-border:p2[1]+border]

#Должен давать нам 1 штрих
def Stroke(image, angles_img, point):
    stroke = []
    if not checkbound_sq(point, image): return 
    oldangle = angles_img[point[0], point[1]]#Получаем угол
    angle = oldangle
    if (oldangle == None) or (np.isnan(oldangle)): return 

    #Получаем шаг. Тут надо вставить брезенхейма. Ну мне так кажется
    #selector = Selector(point[0], point[1], (np.pi + angles_img[point[0], point[1]]) % (2*np.pi))
    step = dirselect(angles_img[point[0], point[1]])#stepmap[point[0]][point[1]]
    step = (step[1], step[0])
    if not step:return 
        
    diff = anglediff(oldangle, angle) 
    #point = selector.GetPoint()
    point = makestep(point, step)
    if not checkbound_sq(point, image):# or mask[point[0], point[1]] == 255:
        return 

    #Пока не уткнемся в градиент различающийся с нашим более чем в 30* ползем в направлении step
    #Из-за кривого шага на больших расстояниях дает нехороший результат
    while image[point[0], point[1]] == 0:
        #if (image[point[0], point[1]] != 0):
        stroke.append(point)        
        point = makestep(point, step)
        #point = selector.GetPoint()
        #Если уткнулись в край картинки - считаем луч ошибочным
        if not checkbound_sq(point, image):# or mask[point[0], point[1]] == 255:
            return 
        #if (image[point[0], point[1]] != 0):
    angle = angles_img[point[0], point[1]]
    diff = anglediff(oldangle, angle)
    if abs(diff) > (np.pi / 3):
        return stroke
    else:
        return 
    #print 'step:', step, 'point', point, 'angle', oldangle
    #return stroke

#Поиск компонент. Наверно :)
def SearchComponent(image, center, mask, cntrimg, original):
    component = [center]
    q = Queue()
    q.put(center)
    mask[center[0], center[1]] = 255
    while not q.empty():
        point = q.get()
        #print point        
        for i in xrange(-1, 2):
            for j in xrange(-1, 2):
                if i == 0 and j == 0: continue
                #print 'i', i, 'j', j
                tmp = makestep(point, (i, j))
                if checkbound(tmp, image) and (
                    mask[tmp[0], tmp[1]] == 0) and (
                        image[tmp[0], tmp[1]] < CC_B) and (
                   cntrimg[tmp[0], tmp[1]] == 0) and(
                   #abs(image[point[0], point[1]] - image[tmp[0], tmp[1]]) < CC_D) :
                   1/4. < image[point[0], point[1]] / image[tmp[0], tmp[1]] < 4):

                    q.put(tmp)
                    component.append(tmp)
                    mask[tmp[0], tmp[1]] = 255
    #if len(component) < 2:
    #    return {}
    variance = Variance(component, image)
    #beauty but weak
    minY = min((p[1] for p in component))
    maxY = max((p[1] for p in component))
    minX = min((p[0] for p in component))
    maxX = max((p[0] for p in component))
    bboxvariance = VarianceFromRect((minX, minY), (maxX, maxY), original)
    if bboxvariance:
        bboxvariance /= ((maxX-minX)*(maxY-minY))
    return {
            'points' : component, 
            'variance' : variance, 
            'height' : maxY  - minY, 
            'width' : maxX - minX, 
            'X' : minX, 'Y' : minY, 'X2' : maxX, 'Y2' : maxY,
            'bboxvariance' : bboxvariance,
        }
                    

#cv2.imshow('orig', img)


def FindLetters(gray):
    print 'Finding counters...'
    orig = gray.copy()
    gray = cv2.Canny(gray, 10, 230)
    edges = []
    print 'Calc gradient\'s angle...'
    #Название списка не совсем корректно. Тут мы получаем градиент (точнее угол) всех (ну почти) точек
    angles_img = np.zeros(gray.shape)
    angles_img[:] = float('nan')
    for j in xrange(1, gray.shape[1]-1):
        for i in xrange(1, gray.shape[0]-1):    
            if gray[i, j] == 255:
                edges.append((i, j))
                angles_img[i, j] = gradient(orig, (i, j))
            #angles_img[i, j] = gradient(gray, (i, j))

    #stepmap = [ [dirselect(x) for x in vect] for vect in angles_img]

    #Хранит "слепок" всех лучей, требуется по сути только для отладки
    mask = np.zeros(gray.shape)

    print 'Tracing rays...'
    rays = []
    #for i in xrange(1, gray.shape[1] - 1):#Бежим по всем точкам
    #    for j in xrange(1, gray.shape[0] - 1):
    for e in edges:
        if True:#=)
            i = e[1]
            j = e[0]
            #Проверяем прошли ли мы эту точку
            if mask[j, i] != 255:
                res = Stroke(gray, angles_img, (j, i))            
                if res :#len(res) > 0:
                    #print res
                    rays.append(res)
                    #tmp = gray.copy()
                    #for p in res:#Показываем луч
                    #    tmp[p[0], p[1]] = 255
                    #    mask[p[0], p[1]] = 255
                    #cv2.imshow('77', tmp)
                    #Для удобства просмотра
                    #cv2.waitKey(5)
            #exit()

    print 'Calc Stroke Width...'
    swimage = np.zeros(gray.shape)
    swimage[:] = float('inf')
    for ray in rays:
        for p in ray:
            if swimage[p[0], p[1]] > len(ray):
                #print len(ray)
                swimage[p[0], p[1]] = len(ray)

    #swimage %= 255#Криво, ну да ладно

    mask = np.zeros(gray.shape)
    components = []
    print 'Search Components'
    for j in xrange(gray.shape[1]):
        for i in xrange(gray.shape[0]):
            if (mask[i, j] == 0) and (swimage[i, j] < CC_B):#CC_B = inf - "барьер"
                res = SearchComponent(swimage, (i, j), mask, gray, orig)
                if (
                    len(res['points']) > 10
                    and (res['height'] > 10 and res['width'] > 3)
                    and (res['bboxvariance'] > 2.5)
                    #and ((res['width'] * res['height']) * 0.15 < (len(res['points'])))
                    and (0.1 < (float(len(res['points']))/(res['width']*res['height'])) < 1)
                    #and ((res['height'] > 9) and (res['width'] > 3)) 
                    and (1/2.5 < res['width'] / res['height'] < 2.5)
                    #and (0.25 < min(float(res['width'])/res['height'], float(res['height'])/res['width']) < 1)
                    ):
                    if res['variance'] < 50:
                        components.append(res)
                        #print  (len(res['points'])/(res['width']*res['height']))
                        #tmp = gray.copy()
                        #for p in res['points']:#Показываем компонент
                        #    tmp[p[0], p[1]] = 255                    
                        #cv2.imshow('11111', tmp)
                        #cv2.waitKey(1000)
    print 'filtering letter candidats...'
    lettercandidats = []
    for c in components:
        for c2 in components:#
            if (
                (c != c2) #and (c['width'] != 0 and c['height'] != 0
                and (2/3. < c2['width']/c['width'] < 1.5)
                and (2/3. < c2['height']/c['height'] < 1.5)
                ):
                lettercandidats.append(c)
                break
    return lettercandidats

def GetLetters(img):
    lettercandidats = FindLetters(img)
    return [CutRect(img, (c['X'], c['Y']), (c['X2'], c['Y2'])) for c in lettercandidats]


if __name__ == '__main__':
    print 'loading image....'
    img = cv2.imread('img/cars/2.jpg')
    #img = cv2.imread('img/cars/3.jpg')
    #img = cv2.imread('img/pure/3.jpg')
    #img = cv2.imread('img/numbers/1.jpg')
    gr = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    orig = gr.copy()
    lettercandidats = FindLetters(gr)

    tmp = orig.copy()
    print 'writting letters'
    for i, c in enumerate(lettercandidats):
        cv2.imwrite('result/' + str(i) + ".tif", CutRect(orig, (c['X'], c['Y']), (c['X2'], c['Y2']), 3))
        #cv2.imshow('result/' + str(i) + ".jpg", CutRect(orig, (c['X'], c['Y']), (c['X2'], c['Y2'])))
        #print c['bboxvariance']
        #cv2.waitKey(10000)
        for p in c['points']:#Показываем компонент
            tmp[p[0], p[1]] = 255                    
        #cv2.imshow('11111', tmp)
    cv2.imwrite('test.jpg', tmp)
    cv2.imshow('res', tmp)
    print 'Sum len of letters:', len(lettercandidats)
    cv2.waitKey(10000)
    
