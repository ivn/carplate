# -*- coding: utf-8 -*-
import cv2

import numpy as np

from Queue import Queue

from SWT_Support import *

from Bresenham import Selector

from time import time

import cProfile

import pickle

makestep = lambda point, step: (point[0] + step[0], point[1] + step[1])
checkbound = lambda point, image: (
            (point[0] < image.shape[0]) and (point[1] < image.shape[1]) and
            (point [0] >= 0) and (point [1] >= 0))

checkbound_sq = lambda point, image: (
            (point[0] + 1 < image.shape[0]) and (point[1] + 1 < image.shape[1]) and
            (point [0] - 1 > 0) and (point [1] - 1 > 0))

#barrier const for CC
CC_B = float('inf')

DIR_TO_DUMP = 'dumps/'

def SWViz(image):
    tmp = np.zeros(image.shape, dtype=np.uint8)
    tmp[:] = image[:]
    Barrier = 50
    tmp[tmp == np.inf] = Barrier
    tmp[tmp > Barrier] = Barrier
    tmp *= 10
    #res = np.zeros((image.shape[0], image.shape[1], 3), dtype=np.uint8)
    #res[tmp > 10] = (200, 0, 0)
    #res[tmp > 15] = (10, 50, 100)
    #res[tmp > 30] = (0, 100, 100)
    #res[tmp > 45] = (0, 0, 200)
    #cv2.imwrite('swimageimprove1.jpg', tmp)
    cv2.imshow('swimage', tmp)
    cv2.waitKey(100000)

def loadobj(name, ser):
    f = open('%s%s-%s.dump' % (DIR_TO_DUMP, str(ser), name), 'r')
    res = pickle.load(f)
    f.close()
    return res

def dumpobj(obj, name, ser):
    f = open('%s%s-%s.dump' % (DIR_TO_DUMP, str(ser), name) , 'w')
    pickle.dump(obj, f)
    f.close()

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

MAX_RAY_LEN = 100
#Должен давать нам 1 луч 
def Stroke(image, angles_img, point, dx, dy):
    stroke = []
    if not checkbound_sq(point, image): return 
    oldangle = angles_img[point[0], point[1]]#Получаем угол
    angle = oldangle
    if (oldangle == None) or (np.isnan(oldangle)): return 

    #Получаем шаг. Тут надо вставить брезенхейма. Ну мне так кажется
    selector = Selector(point[0], point[1], point[0]-dy[point[0], point[1]], point[1] - dx[point[0], point[1]])#(np.pi + angles_img[point[0], point[1]]) % (2*np.pi))
    #step = dirselect(angles_img[point[0], point[1]])#stepmap[point[0]][point[1]]
    #step = (step[1], step[0])
    #if not step:return 
        
    diff = anglediff(oldangle, angle) 
    new_point = selector.GetPoint()
    if point == new_point: return
    point = new_point
    #point = makestep(point, step)
    if not checkbound_sq(point, image):# or mask[point[0], point[1]] == 255:
        return 

    i = 0

    #Пока не уткнемся в градиент различающийся с нашим более чем в 30* ползем в направлении step
    #Из-за кривого шага на больших расстояниях дает нехороший результат
    while image[point[0], point[1]] == 0:
        #if (image[point[0], point[1]] != 0):
        stroke.append(point)        
        #point = makesstep(point, step)
        point = selector.GetPoint()
        i += 1
        #Если уткнулись в край картинки - считаем луч ошибочным
        if not checkbound_sq(point, image) or i > MAX_RAY_LEN:# or mask[point[0], point[1]] == 255:
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
                   1/5. < image[point[0], point[1]] / image[tmp[0], tmp[1]] < 5.):

                    q.put(tmp)
                    component.append(tmp)
                    mask[tmp[0], tmp[1]] = 255
    #if len(component) < 2:
    #    return {}
    #variance = Variance(component, image)
    
    swvalues = np.array([image[p[0], p[1]] for p in component])
    #mean = np.mean(swvalues)
    #deviation = np.std(swvalues)
    #beauty but weak
    minY = min((p[1] for p in component))
    maxY = max((p[1] for p in component))
    minX = min((p[0] for p in component))
    maxX = max((p[0] for p in component))
    #bboxvariance = VarianceFromRect((minX, minY), (maxX, maxY), original)
    #if bboxvariance:
    #    bboxvariance /= ((maxX-minX)*(maxY-minY))
    return {
            'points' : component, 
            #'variance' : variance, 
            'height' : maxY  - minY, 
            'width' : maxX - minX, 
            'X' : minX, 'Y' : minY, 'X2' : maxX, 'Y2' : maxY,
            'swvalues' : swvalues,
            ##'bboxvariance' : bboxvariance,
            #'mean' : mean,
            #'deviation' : deviation,
        }
                    

#cv2.imshow('orig', img)

def GradientCalc(original, contour):
    #Тут мы получаем градиент (точнее угол) всех (ну почти) точек
    angles_img = np.zeros(original.shape)
    angles_img[:] = float('nan')
    dx = cv2.Sobel(original, cv2.CV_32F, 1, 0, ksize=7)
    dy = cv2.Sobel(original, cv2.CV_32F, 0, 1, ksize=7)
    angles_img = np.arctan2(dy, dx)
    '''
    for j in xrange(1, original.shape[1]-1):
        for i in xrange(1, original.shape[0]-1):    
            if contour[i, j] != 0:
                edges.append((i, j))
                #angles_img[i, j] = gradient(original, (i, j))
    '''
    return angles_img, dx, dy

def Ray_Tracing(contour, angles_img, debug_rays=False, dx=None, dy=None):#return sw_image
    rays = []
    for j in xrange(1, contour.shape[1]-1):
        for i in xrange(1, contour.shape[0]-1):    
            if contour[i, j] != 0:
    #for e in edges:
        #Проверяем прошли ли мы эту точку
                res = Stroke(contour, angles_img, (i, j), dx, dy)            
                if res :#len(res) > 0:
                    #print 'Start from', (i, j)
                    #print 'Grad', dx[i, j], dy[i, j]
                    rays.append(res)
                    #print res
                    if debug_rays:
                        tmp = contour.copy()
                        for p in res:#Показываем луч
                            tmp[p[0], p[1]] = 255
                        cv2.imshow('77', tmp)
                        #Для удобства просмотра
                        cv2.waitKey(100000)
    return rays

def SWT_Operator(original, rays, debug_swimage):
    swimage = np.zeros(original.shape)
    swimage[:] = float('inf')
    for ray in rays:
        for p in ray:#Заполняем матрицу с ширинами штрихов
            if swimage[p[0], p[1]] > len(ray):
                swimage[p[0], p[1]] = len(ray)
    if debug_swimage:
        SWViz(swimage)
    return swimage

def FindComponents(gray, contour, swimage, debug_components=False, debug_components_after=False):
    mask = np.zeros(gray.shape)
    components = []
    for j in xrange(gray.shape[1]):
        for i in xrange(gray.shape[0]):
            if (mask[i, j] == 0) and (swimage[i, j] < CC_B):#CC_B = inf - "барьер"
                res = SearchComponent(swimage, (i, j), mask, contour, gray)
                if debug_components:
                    tmp = contour.copy()
                    for p in res['points']:#Показываем компонент
                        tmp[p[0], p[1]] = 255                    
                    cv2.imshow('11111', tmp)
                    cv2.waitKey(1000)
                if (
                    len(res['points']) > 7
                    and (res['height'] > 5 and res['width'] > 3)
                    #and (res['bboxvariance'] > 2.5)
                    #and ((res['width'] * res['height']) * 0.15 < (len(res['points'])))
                    and (0.1 < (float(len(res['points']))/(res['width']*res['height'])) < 1)
                    #and ((res['height'] > 9) and (res['width'] > 3)) 
                    and (1/2.5 < res['width'] / res['height'] < 2.5)

                    #and ((res['mean'] == 0) or (0 < (res['deviation']/res['mean']) < 1))
                    and (np.std(res['swvalues'])/np.mean(res['swvalues']) < 1)
                    and (VarianceFromRect((res['X'], res['Y']), (res['X2'], res['Y2']), gray) > 2000)
                    #and (0.25 < min(float(res['width'])/res['height'], float(res['height'])/res['width']) < 1)
                    ):
                    #if True:#res['variance'] < 40:
                    components.append(res)
                    if debug_components_after:
                        tmp = contour.copy()
                        for p in res['points']:#Показываем компонент
                            tmp[p[0], p[1]] = 255                    
                        cv2.imshow('11111', tmp)
                        cv2.waitKey(1000)
    return components

def PairFilter(components):
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

work_stages = {
        'no' : 0,
        'contour' : 1,
        'angles_img' : 2,
        'rays' : 3,
        'swimage' : 4,
        'Components' : 5,
        'lettercandidats' : 6,
    }

DEFAULT_DEBUG_FLAGS = {
        'debug_rays' : False,
        'debug_swimage' : False,
        'debug_components' : False,
        'debug_components_after' : False,
    }

def FindLetters(gray, stage=work_stages['no'], oldser=None, dump_stages=False, new_ser='', debug_flags=None):
    #init section. Just for simplify debug. delete this after debooooging
    if not debug_flags: debug_flags = DEFAULT_DEBUG_FLAGS
    curser = new_ser#current ser of dump files
    contour = None;  angles_img = None; rays = None; swimage = None; components = None; lettercandidats = None;
    dx = None; dy = None
    if stage < work_stages['contour']:
        print 'Finding counters...'
        contour = cv2.Canny(gray, 10, 230)
        if dump_stages:
            dumpobj(contour, 'contour', curser)
    else:
        contour = loadobj('contour', oldser)

    if stage < work_stages['angles_img']:
        print 'Calc gradient\'s angle...'
        angles_img, dx, dy = GradientCalc(gray, contour)
        if dump_stages:
            dumpobj(angles_img, 'angles_img', curser)
    else:
        angles_img = loadobj('angles_img', oldser)

    if stage < work_stages['rays']:
        print 'Tracing rays...'
        rays = Ray_Tracing(contour, angles_img, debug_rays=debug_flags['debug_rays'], dx=dx, dy=dy)#set true for show image     
        if dump_stages:
            dumpobj(rays, 'rays', curser)
    else:
        rays = loadobj('rays', oldser)
    
    if stage < work_stages['swimage']:
        print 'Calc Stroke Width...'
        swimage = SWT_Operator(gray, rays, debug_swimage=debug_flags['debug_swimage'])
        if dump_stages:
            dumpobj(swimage, 'swimage', curser)
    else:
        swimage = loadobj('swimage', oldser)

    if stage < work_stages['Components']:
        print 'Search Components'
        components = FindComponents(gray, contour, swimage, debug_components=debug_flags['debug_components'], debug_components_after=debug_flags['debug_components_after'])
        if dump_stages:
            dumpobj(components, 'components', curser)
    else:
        components = loadobj('components', oldser)

    if stage < work_stages['lettercandidats']:
        print 'filtering letter candidats...'
        lettercandidats = PairFilter(components)
        if dump_stages:
            dumpobj(lettercandidats, 'lettercandidats', curser)
    else:
        lettercandidats = loadobj('lettercandidats', oldser)

    return lettercandidats

def GetLetters(img):
    lettercandidats = FindLetters(img)
    return [CutRect(img, (c['X'], c['Y']), (c['X2'], c['Y2'])) for c in lettercandidats]


if __name__ == '__main__':
    print 'loading image....'
    img = cv2.imread('img/cars/4.jpg')
    #img = cv2.imread('img/cars/3.jpg')
    #img = cv2.imread('img/pure/2.jpg')
    #img = cv2.imread('img/numbers/1.jpg')
    gr = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    orig = gr.copy()
    #USAGE FindLetters(gray_scale, <stage>, <ser of dumps>)
    lettercandidats = FindLetters(gr, dump_stages=True, new_ser='ser_')#, work_stages['lettercandidats'], '1352903799.13')
    '''
work_stages = {
        'no' : 0,
        'contour' : 1,
        'angles_img' : 2,
        'rays' : 3,
        'swimage' : 4,
        'Components' : 5,
        'lettercandidats' : 6,
    }
    '''

    tmp = orig.copy()
    print 'writting letters'
    for i, c in enumerate(lettercandidats):
        #cv2.imwrite('result/' + str(i) + ".tif", CutRect(orig, (c['X'], c['Y']), (c['X2'], c['Y2']), 3))
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
    
