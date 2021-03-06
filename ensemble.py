from common import *
from dataset.carvana_cars import *
from model.tool import *

import lmdb

def run_vote():

    prediction_files=[
        '/root/share/project/kaggle-carvana-cars/results/xx5-UNet512_2/submit/probs.8.npy',
        '/root/share/project/kaggle-carvana-cars/results/xx5-UNet512_2_two-loss/submit/probs.8.npy',
        '/root/share/project/kaggle-carvana-cars/results/xx5-UNet512_2_two-loss-full_1/submit/probs.8.npy',
    ]
    out_dir ='/root/share/project/kaggle-carvana-cars/results/ensemble/xxx'

    log = Logger()
    log.open(out_dir+'/log.vote.txt',mode='a')
    os.makedirs(out_dir,  exist_ok=True)

    write_list_to_file(prediction_files, out_dir+'/prediction_files.txt')

    #----------------------------------------------------------

    #read names
    split_file = CARVANA_DIR +'/split/'+ 'test%dx%d_100064'%(CARVANA_H,CARVANA_W)
    with open(split_file) as f:
        names = f.readlines()
    names = [name.strip()for name in names]
    names = [name.split('/')[-1]+'.jpg' for name in names]

    #read probs
    num_test   = len(names)
    votes = np.zeros((num_test, CARVANA_H, CARVANA_W), np.uint8)

    num_files = len(prediction_files)
    for n in range(num_files):
        prediction_file = prediction_files[n]
        print(prediction_files[n])

        probs = np.load(prediction_file)
        votes += probs >=128
        probs = None



    #prepare csv file -------------------------------------------------------
    threshold = 1  #/num_files
    probs = votes

    gz_file = out_dir+'/results-ensemble-th%05f.csv.gz'%threshold
    prob_to_csv(gz_file, names, votes, log, threshold)

def ensamble_png_custom():
    out_dir_ = []
    
    out_dir_.append(params.out_dir + '/UNet1024_ASPP_08')
    out_dir_.append(params.out_dir + '/UNet1024_ASPP_08_k3')
    out_dir_.append(params.out_dir + '/UNet1024_ASPP_08_k4')


    final_out_dir = params.out_dir + params.ensemble_dir

    #logging, etc --------------------
    os.makedirs(final_out_dir+'/submit/results',  exist_ok=True)
    os.makedirs(final_out_dir + '/submit/test_mask', exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), final_out_dir +'/backup/submit.code.zip')

    log = Logger()
    log.open(final_out_dir+'/log.submit.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** some project setting **\n')

    split_file = CARVANA_DIR +'/split/'+ 'test_100064'
    with open(split_file) as f:
        names = f.readlines()
    names = [name.strip()for name in names]
    num_test = len(names)

    rles=[]
    total_start = timer()
    start = timer()
    for i in range(len(names)): 
        p = []
        average = np.zeros((CARVANA_H,CARVANA_W),np.uint16)

        p.append(cv2.imread(out_dir_[0]+'/submit/test_mask/%s.png'%(names[i]),cv2.IMREAD_GRAYSCALE))
        p.append(cv2.imread(out_dir_[1]+'/post_train/submit/test_mask/%s.png'%(names[i]),cv2.IMREAD_GRAYSCALE))
        p.append(cv2.imread(out_dir_[2]+'/post_train/submit/test_mask/%s.png'%(names[i]),cv2.IMREAD_GRAYSCALE))
            
        for temp_ in p:
            temp_ = temp_.astype(np.uint8)
            average += temp_
        
        average = average/len(p)
        
        cv2.imwrite(final_out_dir+'/submit/test_mask/%s.png'%(names[i]), average.astype(np.uint8))

        if i%1000 == 0:
            log.write(' [num: %d] \n'%(i))
            log.write('\t time = %0.2f min \n'%((timer() - start)/60))
            start = timer()
    
    log.write(' save_masks = %f min\n'%((timer() - total_start) / 60))
    log.write('\n')

def ensamble_png():

    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet512-peduo-label-00c'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'

    out_dir_ = []
    for i in range(0,5):
    #for i in range(0,7):
        out_dir_.append(params.out_dir + params.ensemble_dir + '_k%d'%(i+1))

    #out_dir_.append(params.out_dir + params.ensemble_dir + '_single')
    
    #final_out_dir = params.out_dir + params.ensemble_dir #+ '_post_train_no_src'
    final_out_dir = params.out_dir + 'test'

    #logging, etc --------------------
    os.makedirs(final_out_dir+'/submit/results',  exist_ok=True)
    os.makedirs(final_out_dir + '/submit/test_mask', exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), final_out_dir +'/backup/submit.code.zip')

    log = Logger()
    log.open(final_out_dir+'/log.submit.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** some project setting **\n')
    for i in range(len(out_dir_)):
        log.write('*' + out_dir_[i] + '\n')

    split_file = CARVANA_DIR +'/split/'+ 'test_100064'
    with open(split_file) as f:
        names = f.readlines()
    names = [name.strip()for name in names]
    num_test = len(names)

    use_lmdb = False
    env = []
    for i in range(len(out_dir_)):
        env.append(lmdb.open(out_dir_[i]+'/submit/test_lmdb'))
    
    total_start = timer()
    start = timer()
    for i in range(len(names)): 
        p = []
        average = np.zeros((CARVANA_H,CARVANA_W),np.uint16)
        for j in range(len(out_dir_)):
            if use_lmdb:
                with env[j].begin(write=False) as txn:
                    imgbuf = txn.get(names[i].encode())
                    #buf = six.BytesIO();buf.write(imgbuf);buf.seek(0)
                    #p.append(np.array(Image.open(buf).convert('L')))
                    buf2 = np.fromstring(imgbuf, np.uint8)
                    p.append(cv2.imdecode(buf2, cv2.IMREAD_GRAYSCALE))
            else:
                p.append(cv2.imread(out_dir_[j]+'/submit/test_mask/%s.png'%(names[i]),cv2.IMREAD_GRAYSCALE))
            
            p[j] = p[j].astype(np.uint8)
            average += p[j]
        
        #average = average/5
        average = average/len(out_dir_)
        
        cv2.imwrite(final_out_dir+'/submit/test_mask/%s.png'%(names[i]), average.astype(np.uint8))

        print('\r current_num: %d'%(i), end='', flush=True)
        if i%5000 == 0:
            log.write(' [num: %d] \n'%(i))
            log.write('\t time = %0.2f min ,check dir_num = %d\n'%((timer() - start)/60, len(out_dir_)))
            start = timer()
    
    log.write(' save_masks = %f min\n'%((timer() - total_start) / 60))
    log.write('\n')

def run_submit_ensemble():

    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet512-peduo-label-00c'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'

    final_out_dir = params.out_dir + params.ensemble_dir

    #logging, etc --------------------
    os.makedirs(final_out_dir+'/submit/results',  exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), final_out_dir +'/backup/submit.code.zip')

    log = Logger()
    log.open(final_out_dir+'/log.submit.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** some project setting **\n')


    # read names
    # split_file = CARVANA_DIR +'/split/'+ 'valid_v0_768'
    # CARVANA_NUM_BLOCKS =1


    split_file = CARVANA_DIR +'/split/'+ 'test_100064'
    with open(split_file) as f:
        names = f.readlines()
    names = [name.strip()for name in names]
    num_test = len(names)


    rles=[]
    total_start = timer()
    start = timer()
    for i in range(len(names)):
        #test
        p = cv2.imread(final_out_dir+'/submit/test_mask/%s.png'%(names[i]),cv2.IMREAD_GRAYSCALE)
        if (i%1000==0):
            end  = timer()
            n = len(rles)          
            time = (end - start) / 60
            time_remain = (num_test-n-1)*time/(n+1)
            print('rle : b/num_test = %06d/%06d,  time elased (remain) = %0.1f (%0.1f) min'%(n,num_test,time,time_remain))
            start = timer()

        prob = cv2.resize(p,dsize=(CARVANA_WIDTH,CARVANA_HEIGHT),interpolation=cv2.INTER_LINEAR)
        mask = prob>127
        rle  = run_length_encode(mask)
        rles.append(rle)
    #-----------------------------------------------------
    names = [name+'.jpg' for name in names]

    dir_name = final_out_dir.split('/')[-1]
    gz_file  = final_out_dir + '/submit/results-%s.csv.gz'%dir_name
    df = pd.DataFrame({ 'img' : names, 'rle_mask' : rles})
    df.to_csv(gz_file, index=False, compression='gzip')

    log.write('\tdf.to_csv time = %f min\n'%((timer() - total_start) / 60)) #3 min
    log.write('\n')


# main #################################################################
if __name__ == '__main__':
    print( '%s: calling main function ... ' % os.path.basename(__file__))

    opts, args = getopt.getopt(sys.argv[1:], '',['vot', 'cus', 'ens'])

    for opt, val in opts: 
        print(opt)
    if opt == '--vot':
        run_vote()
    elif opt == '--cus':
        ensamble_png_custom()
    elif opt == '--ens':
        ensamble_png()
    #run_submit_ensemble()

    print('\nsucess!')
