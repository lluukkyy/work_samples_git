import os
import sys

import numpy as np
import scipy as sp

import cv2

def compare(name1,name2):
    #a local function *************************************************************
    #returns True if matches False if not
    def refineAndOutput(m,mask,name):
        print("Analyze with",name,":")
        m = np.array(m)
        index = np.where(mask==1)
        #p1n and p2n are good matches filtered by mask
        p1n, p2n = p1[index], p2[index]
        #if not enougth points after mask
        #then returns False which means these two are not the same scene.
        l = len(index[0])
        if l<10: 
            print("     Too few matches:",l)
            print("     Not the same scene.")
            return False,0
        #compute distance for each pair of positions
        d = []
        for i in range(len(p1n)):
            line = m * np.mat([[p1n[i][0]],[p1n[i][1]],[1]])
            line = line/np.linalg.norm(line) #normalized
            d.append( (np.mat([p2n[i][0],p2n[i][1],1]) * line) [0,0]  ) #dot product as distance
        #compute confidentce and verify the matrix
        d = np.array(d)
        mean, std = np.mean(d),np.std(d)
        goodMatches = []
        for i in range(len(d)):
            if abs(d[i]-mean) <= 2 * std : 
                goodMatches.append([tuple(p1n[i]),( int( p2n[i][0]+width ), int (p2n[i][1]) ) ])
        confidence = len(goodMatches)/p1n.shape[0]   
        #if confidence of result is lower than 90%
        if confidence<0.8: 
            print("     Matrix not found.")
            return False,0
        #otherwise
        print("     Matches:",p1n.shape[0]," Good ones:",len(goodMatches))
        print("     Confidence: %.2f"%(100*confidence),"%")    
        print("     Pass.")
        #draw lines between well matched ones
        output = np.concatenate((img1,img2),axis = 1)
        for i in goodMatches:
            cv2.line(output,i[0],i[1],(0,255,0),1)
        #output
        #cv2.imwrite(name+"_"+name1[:-4]+"_"+name2[:-4]+".jpg",output)
        return True, l 
    #*********************************************************************************
    img1 = cv2.imread(name1) #read img1
    img2 = cv2.imread(name2) #read img2
    width = img1.shape[1]
    #following part of code is quoted from "https://docs.opencv.org/3.4.3/dc/dc3/tutorial_py_matcher.html"
    # Initiate SIFT detector
    sift = cv2.xfeatures2d.SIFT_create() #this line of code is modified due to cv2 update
    # find the keypoints and descriptors with SIFT
    kp1, des1 = sift.detectAndCompute(img1,None)
    kp2, des2 = sift.detectAndCompute(img2,None)
    #following 10 lines of code is quoted from 
    #******************************
    # "https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_feature2d/py_feature_homography/py_feature_homography.html"
    FLANN_INDEX_KDTREE = 0
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks = 50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1,des2,k=2)
    # store all the good matches as per Lowe's ratio test.
    good = []
    for m,n in matches:
        if m.distance < 0.8*n.distance:
            good.append(m)
    #******************************
    #corresponding positions
    p1 = np.float32([ kp1[m.queryIdx].pt for m in good ])
    p2 = np.float32([ kp2[m.trainIdx].pt for m in good ])
    #compute fundamentalMat using fm_ransac
    m, mask = cv2.findFundamentalMat(p1, p2, cv2.FM_RANSAC)
    mask = np.ravel(mask)
    pass_f,l_f = refineAndOutput(m,mask,"fund")
    #compute homography using ransac
    m, mask = cv2.findHomography(p1,p2,cv2.RANSAC)
    mask = np.ravel(mask)
    pass_h,l_h = refineAndOutput(m,mask,"homo")

    #return True if both homography and fundamental passed and ratio of good matches greater than 80%
    ratio = l_h/l_f
    print("Ratio",ratio)
    if pass_f and pass_h and ratio>=0.75:
        print("Same scene.\n")
        return True, m
    else: 
        print("Not the same scene.\n")
        return False,m
   
   
   
   
def align(name1,name2,m):
    img1 = cv2.imread(name1) #read img1
    img2 = cv2.imread(name2) #read img2
    h,w = img1.shape[0], img1.shape[1] #shape of original photo

    #calculate the size of the new canvas
    pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(4,1,2) #four corners of img2
    dst = cv2.perspectiveTransform(pts,m) #four corners of transformed img1
    dst = np.concatenate((pts,dst)) #eight corners of img2 and transformed img1
    upperLeft = np.min(dst,axis=0)[0] #upperLeft corner of new canvas
    bottomRight = np.max(dst,axis=0)[0]#bottomRight corner of new canvas
    #compute the bounding box size
    width,height = np.round(abs(upperLeft-bottomRight)+0.5).astype(int) #width and height of new canvas

    #transformation matrix
    t = np.mat([
    [ 1, 0, -upperLeft[0] ],
    [ 0, 1, -upperLeft[1] ],
    [ 0, 0,   1 ]
    ])
    #both img should be transfomed first
    if width>10000 or height>10000: 
        print("Mosaic too big.")
        return
    imgNew1 = cv2.warpPerspective(img1,t*m,(width,height))
    imgNew2 = cv2.warpPerspective(img2,t,(width,height))
    imgNew = cv2.addWeighted(imgNew1,0.5,imgNew2,0.5,0)
    cv2.imwrite(name1[:-4]+"_"+name2[:-4]+".jpg",imgNew)
    

   
    


if __name__=="__main__":
    items = os.listdir(sys.argv[1]) #get all files in designated folder
    items = [i for i in items if i.endswith(".JPG")] #keep those end with .jpg
    os.chdir(sys.argv[1]) #get inside the img folder
 
    for i in range(len(items)):
        for j in range(i+1,len(items)):
            #compare between 2 photos     
            print("Comparing %s %s"%(items[i],items[j]))
            result, matrix = compare(items[i],items[j])
            if result: align(items[i],items[j],matrix)

    

