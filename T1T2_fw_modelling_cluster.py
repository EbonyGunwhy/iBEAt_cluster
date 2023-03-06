import datetime
import time
import dbdicom as db
import os
import numpy as np
import models.iBEAt_Model_Library.single_pixel_forward_models.iBEAT_T1_FM
import models.iBEAt_Model_Library.single_pixel_forward_models.iBEAT_T2_FM
import parallel_curve_fit_T1_T2_alone_cluster as parallel_curve_fit_T1_T2
from tqdm import tqdm
import multiprocessing

def T1T2_Modelling(series_T1_T2, study=None):

    series_T1 = series_T1_T2[0]
    series_T2 = series_T1_T2[1]

    array_T1, header_T1 = series_T1.array(['SliceLocation', 'AcquisitionTime'], pixels_first=True)
    array_T2, header_T2 = series_T2.array(['SliceLocation', 'AcquisitionTime'], pixels_first=True)

    array_T1 = np.squeeze(array_T1[:,:,:,:,0])
    array_T2 = np.squeeze(array_T2[:,:,:,:,0])

    header_T1 = np.squeeze(header_T1[:,...])
    header_T2 = np.squeeze(header_T2[:,...])

    TR = 4.6                            #in ms
    FA = 12    #in degrees
    FA_rad = FA/360*(2*np.pi)           #convert to rads
    N_T1 = 66                           #number of k-space lines
    FA_Cat  = [(-FA/5)/360*(2*np.pi), (2*FA/5)/360*(2*np.pi), (-3*FA/5)/360*(2*np.pi), (4*FA/5)/360*(2*np.pi), (-5*FA/5)/360*(2*np.pi)] #cat module

    FA_Cat  = [(-FA/5)/360*(2*np.pi), (2*FA/5)/360*(2*np.pi), (-3*FA/5)/360*(2*np.pi), (4*FA/5)/360*(2*np.pi), (-5*FA/5)/360*(2*np.pi)] #cat module

    TE = [0,30,40,50,60,70,80,90,100,110,120]
    Tspoil = 1
    N_T2 = 72
    Trec = 463*2
    FA_eff = 0.6

    number_slices = np.shape(array_T1)[2]

    T1_S0_map = np.zeros(np.shape(array_T1)[0:3])
    T1_map = np.zeros(np.shape(array_T1)[0:3])
    FA_Eff_map = np.zeros(np.shape(array_T1)[0:3])
    Ref_Eff_map = np.zeros(np.shape(array_T1)[0:3])
    T2_S0_map = np.zeros(np.shape(array_T1)[0:3])
    T2_map = np.zeros(np.shape(array_T1)[0:3])
    T1_rsquare_map = np.zeros(np.shape(array_T1)[0:3])
    T2_rsquare_map = np.zeros(np.shape(array_T1)[0:3])

    for i in range(np.shape(array_T1)[2]):
        Kidney_pixel_T1 = np.squeeze(array_T1[...,i,:])
        Kidney_pixel_T2 = np.squeeze(array_T2[...,i,:])

        if np.size(np.shape(np.squeeze(header_T1)))==2:
            TI_temp =  [float(hdr['InversionTime']) for hdr in header_T1[i,:]]
        elif np.size(np.shape(np.squeeze(header_T1)))==3:
            TI_temp =  [float(hdr['InversionTime']) for hdr in header_T1[i,:,0]]

        pool = multiprocessing.Pool(processes=os.cpu_count()-1)

        arguments =[]
        pool = multiprocessing.Pool(initializer=multiprocessing.freeze_support,processes=os.cpu_count()-1)
        for (x, y), _ in np.ndenumerate(Kidney_pixel_T1[..., 0]):
            t1_value = Kidney_pixel_T1[x, y, :]
            t2_value = Kidney_pixel_T2[x, y, :]

            arguments.append((x,y,t1_value,t2_value,TI_temp,TE,FA_rad,TR,N_T1,N_T2,FA_Cat,Trec,FA_eff,Tspoil))

        results = list(tqdm(pool.imap(parallel_curve_fit_T1_T2.main, arguments), total=len(arguments), desc='Processing pixels of slice ' + str(i)))

        for result in results:
            xi = result[0]
            yi = result[1]
            T1 = result[2]
            T2 = result[3]
            S0_T1 = result[4]
            S0_T2 = result[5]
            FA_eff = result[6]
            r_squared_T1 = result[7]
            r_squared_T2 = result[8]

            r_squared_T1 = result[7]
            r_squared_T2 = result[8]
            T1_map[xi,yi,i] = T1
            T2_map[xi,yi,i] = T2
            T1_S0_map[xi,yi,i] = S0_T1
            T2_S0_map[xi,yi,i] = S0_T2
            FA_Eff_map[xi,yi,i] = FA_eff
            T1_rsquare_map[xi,yi,i] = r_squared_T1
            T2_rsquare_map[xi,yi,i] = r_squared_T2

    T1_S0_map_series = series_T1.SeriesDescription + "_T1_" + "S0_Map_v2"
    T1_S0_map_series = series_T1.new_sibling(SeriesDescription=T1_S0_map_series)
    T1_S0_map_series.set_array(np.squeeze(T1_S0_map),np.squeeze(header_T1[:,0]),pixels_first=True)

    T1_map_series = series_T1.SeriesDescription + "_T1_" + "T1_Map_v2"
    T1_map_series = series_T1.new_sibling(SeriesDescription=T1_map_series)
    T1_map_series.set_array(np.squeeze(T1_map),np.squeeze(header_T1[:,0]),pixels_first=True)

    FA_Eff_map_series = series_T1.SeriesDescription + "_T1_" + "FA_Eff_Map_v2"
    FA_Eff_map_series = series_T1.new_sibling(SeriesDescription=FA_Eff_map_series)
    FA_Eff_map_series.set_array(np.squeeze(FA_Eff_map),np.squeeze(header_T1[:,0]),pixels_first=True)

    T2_S0_map_series = series_T1.SeriesDescription + "_T2_" + "S0_Map_v2"
    T2_S0_map_series = series_T1.new_sibling(SeriesDescription=T2_S0_map_series)
    T2_S0_map_series.set_array(np.squeeze(T2_S0_map),np.squeeze(header_T2[:,0]),pixels_first=True)

    T2_map_series = series_T1.SeriesDescription + "_T2_" + "T2_Map_v2"
    T2_map_series = series_T1.new_sibling(SeriesDescription=T2_map_series)
    T2_map_series.set_array(np.squeeze(T2_map),np.squeeze(header_T2[:,0]),pixels_first=True)

    T1_rsquare_map_series = series_T1.SeriesDescription + "_T1_" + "rsquare_Map_v2"
    T1_rsquare_map_series = series_T1.new_sibling(SeriesDescription=T1_rsquare_map_series)
    T1_rsquare_map_series.set_array(np.squeeze(T1_rsquare_map),np.squeeze(header_T1[:,0]),pixels_first=True)

    T2_rsquare_map_series = series_T1.SeriesDescription + "_T2_" + "rsquare_Map_v2"
    T2_rsquare_map_series = series_T1.new_sibling(SeriesDescription=T2_rsquare_map_series)
    T2_rsquare_map_series.set_array(np.squeeze(T2_rsquare_map),np.squeeze(header_T2[:,0]),pixels_first=True)

def main(pathScan,filename_log):

    list_of_series = Folder(pathScan).open().series()

    current_study = list_of_series[0].parent
    study = list_of_series[0].new_pibling(StudyDescription=current_study.StudyDescription + '_ModellingResults')

    for i,series in enumerate(list_of_series):

        if series["SequenceName"] is not None:
            if series['SeriesDescription'] == "T1map_kidneys_cor-oblique_mbh_magnitude_mdr_moco":
                try:
                    start_time = time.time()
                    file = open(filename_log, 'a')
                    file.write("\n"+str(datetime.datetime.now())[0:19] + ": T1 and T2 mapping has started")
                    file.close()

                    T1 = series
                    for i_2,series in enumerate (list_of_series):
                        if series['SeriesDescription'] == "T2map_kidneys_cor-oblique_mbh_magnitude_mdr_moco":
                            T2 = series
                            break
                            T1T2_Modelling([T1,T2], study=study)

                    file = open(filename_log, 'a')
                    file.write("\n"+str(datetime.datetime.now())[0:19] + ": T1 and T2 mapping was not done here --- %s seconds ---" % (int(time.time() - start_time))) 
                    file.close()   

                except Exception as e: 
                    file = open(filename_log, 'a')
                    file.write("\n"+str(datetime.datetime.now())[0:19] + ": T1 and T2 mapping was NOT completed; error: "+str(e)) 
                    file.close()

    Folder(pathScan).save()
