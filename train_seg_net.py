import params

from common import *
from dataset.carvana_cars import *

from model.tool import *
from model.rate import *
from model.segmentation.loss import *
from model.segmentation.blocks import *

#from net.segmentation.my_unet_baseline import UNet512 as Net
#from model.segmentation.my_unet_baseline import UNet1024 as Net
#from net.segmentation.my_unet_baseline import UNet128 as Net
Net = params.model_factory


## ----------------------------------------------------------------------------------
#  ffmpeg -y -loglevel 0 -f image2 -r 15 -i 'xxxxx/%*.jpg' -b:v 8000k xxxxx.avi
#  ffmpeg -i results.avi -vf scale=300:100 -b:v 8000k results-small.avi

CSV_BLOCK_SIZE = 8000

## experiment setting here ----------------------------------------------------
def criterion(logits, labels, is_weight=True):
    #l = BCELoss2d()(logits, labels)
    #l = BCELoss2d()(logits, labels) + SoftDiceLoss()(logits, labels)

    #compute weights
    btach_size,H,W = labels.size()
    if   H == 128:  kernel_size =11
    elif H == 256:  kernel_size =21
    elif H == 512:  kernel_size =21
    elif H == 960:  kernel_size =39
    elif H == 1024: kernel_size =41 #41
    elif H == 1280: kernel_size =51 #41
    else: raise ValueError('exit at criterion()')

    a   = F.avg_pool2d(labels,kernel_size=kernel_size,padding=kernel_size//2,stride=1)
    ind = a.ge(0.01) * a.le(0.99)
    ind = ind.float()
    weights  = Variable(torch.tensor.torch.ones(a.size())).cuda()

    if is_weight:
        w0 = weights.sum()
        weights = weights + ind*2
        w1 = weights.sum()
        weights = weights/w1*w0

        l = WeightedBCELoss2d()(logits, labels, weights) + \
            WeightedSoftDiceLoss()(logits, labels, weights)
    else:
        l = BCELoss2d()(logits, labels) + SoftDiceLoss()(logits, labels)

    return l






#debug and show ----------------------------------------------------------
def show_batch_results(indices, images, probs, labels=None, wait=1,
                       out_dir=None, names=None, df=None, mode='both', epoch=0, it=0):

    images = (images.data.float().cpu().numpy()*255).astype(np.uint8)
    images = np.transpose(images, (0, 2, 3, 1))
    probs  = (probs.float().data.cpu().numpy()*255).astype(np.uint8)
    if labels is not None:
        labels = (labels.float().data.cpu().numpy()*255).astype(np.uint8)


    batch_size,H,W,C = images.shape
    for b in range(batch_size):
        image = images[b]
        prob  = probs[b]
        label = None
        score = -1
        if labels is not None:
            label = labels[b]
            score = one_dice_loss_py(label>127 , prob>127)

        results = make_results_image(image, label=label, prob=prob)

        if out_dir is not None:
            name = names[indices[b]]
            description = ''
            if df is not None:
                meta = df.loc[name[:-3]]
                description = '%d %s %s %s'%( int(meta['year']), meta['make'],  meta['model'], meta['trim2'])

            L=30
            draw_shadow_text  (results, '%s.jpg'%(name), (5,1*L),  0.5, (255,255,255), 1)
            draw_shadow_text  (results, '%s'%(description), (5,2*L),  0.5, (255,255,255), 1)
            draw_shadow_text  (results, '%0.5f'%(score), (5,4*L),  0.5, (255,255,255), 1)

            #os.makedirs(out_dir+'/results_by_name', exist_ok=True)
            #os.makedirs(out_dir+'/results_by_score', exist_ok=True)
            #cv2.imwrite(save_dir + '/%05d-%03d.jpg'%(it,b), results)
            if mode in['both','by_score'] : cv2.imwrite(out_dir+'/results_by_score/%0.5f-%s.png'%(score,name), results)
            if mode in['both','by_name' ] : cv2.imwrite(out_dir+'/results_by_name/%s.png'%(name), results)

        #im_show('train',  results,  resize=1)
        #cv2.waitKey(wait)



#helper ----------------------------------------------------------
#  100064/32000 =
def predict8_in_blocks(net, test_loader, block_size=CSV_BLOCK_SIZE, log=None, save_dir=None):

    test_dataset = test_loader.dataset
    test_iter    = iter(test_loader)
    test_num     = len(test_dataset)
    batch_size   = test_loader.batch_size
    assert(block_size%batch_size==0)
    assert(log!=None)

    start0 = timer()
    num  = 0
    predictions = []
    for n in range(0, test_num, block_size):
        M = block_size if n+block_size < test_num else test_num-n
        log.write('[n=%d, M=%d]  \n'%(n,M) )

        start = timer()

        ps  = None
        for m in range(0, M, batch_size):
            print('\r\t%05d/%05d'%(m,M), end='',flush=True)

            images, indices  = test_iter.next()
            if images is None:
                break


            # forward
            images = Variable(images,volatile=True).cuda()
            logits = net(images)
            probs  = F.sigmoid(logits)

            #save results
            if ps is None:
                H = images.size(2)
                W = images.size(3)
                ps  = np.zeros((M, H, W),np.uint8)
                ids = np.zeros((M),np.int64)


            batch_size = len(indices)
            indices = indices.cpu().numpy()
            probs = probs.data.cpu().numpy() *255

            ps [m : m+batch_size] = probs
            ids[m : m+batch_size] = indices
            num  += batch_size
            # im_show('probs',probs[0],1)
            # cv2.waitKey(0)
            #print('\tm=%d, m+batch_size=%d'%(m,m+batch_size) )

        pass # end of one block -----------------------------------------------------
        print('\r')
        log.write('\tpredict = %0.2f min, '%((timer() - start) / 60))


        ##if(n<64000): continue
        if save_dir is not None:
            start = timer()
            np.savetxt(save_dir+'/indices-part%02d.8.txt'%(n//block_size), ids, fmt='%d')
            np.save(save_dir+'/probs-part%02d.8.npy'%(n//block_size), ps) #  1min
            log.write('save = %0.2f min'%((timer() - start) / 60))
        log.write('\n')


    log.write('\nall time = %0.2f min\n'%((timer() - start0) / 60))
    assert(test_num == num)




def evaluate(net, test_loader):

    test_dataset = test_loader.dataset

    num = len(test_dataset)
    test_acc  = 0
    test_loss = 0
    test_num  = 0
    for it, (images, labels, indices) in enumerate(test_loader, 0):
        images = Variable(images.cuda(),volatile=True)
        labels = Variable(labels.cuda(),volatile=True)

        # forward
        logits = net(images)
        probs  = F.sigmoid(logits)
        masks  = (probs>0.5).float()

        loss = criterion(logits, labels, is_weight=True)
        acc  = dice_loss(masks, labels)

        batch_size = len(indices)
        test_num  += batch_size
        test_loss += batch_size*loss.data[0]
        test_acc  += batch_size*acc.data[0]

    assert(test_num == len(test_loader.sampler))
    test_loss = test_loss/test_num
    test_acc  = test_acc/test_num

    return test_loss, test_acc



# ------------------------------------------------------------------------------------
def run_train():

    
    out_dir = params.out_dir + params.save_path

    if params.init_checkpoint is not None:
        initial_checkpoint = out_dir + '/checkpoint/' + params.init_checkpoint 
    else:
        initial_checkpoint = None
        #'/root/share/project/kaggle-carvana-cars/results/single/UNet128-00-xxx/checkpoint/006.pth'


    #logging, etc --------------------
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(out_dir+'/train/results', exist_ok=True)
    os.makedirs(out_dir+'/valid/results', exist_ok=True)
    os.makedirs(out_dir+'/backup', exist_ok=True)
    os.makedirs(out_dir+'/checkpoint', exist_ok=True)
    os.makedirs(out_dir+'/snap', exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), out_dir +'/backup/train.code.zip')

    log = Logger()
    log.open(out_dir+'/log.train.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** experiment for average labels channel as prior**\n\n')
    
    log.write('** some project setting **\n')
    log.write('\tSEED    = %u\n' % SEED)
    log.write('\tfile    = %s\n' % __file__)
    log.write('\tout_dir = %s\n' % out_dir)
    log.write('\n')



    ## dataset ----------------------------------------
    def train_augment(image,label):
        image, label = random_horizontal_flipN([image, label])
        image, label = random_shift_scale_rotateN([image, label], shift_limit=(-0.0625,0.0625),
                  scale_limit=(0.91,1.21), rotate_limit=(-0,0))

        #image, label = random_mask_hue(image, label, hue_limit=(-1,1), u=0.5)
        #image = random_hue(image, hue_limit=(-1,1), u=0.5)

        # image = random_brightness(image, limit=(-0.5,0.5), u=0.5)
        # image = random_contrast  (image, limit=(-0.5,0.5), u=0.5)
        # image = random_saturation(image, limit=(-0.3,0.3), u=0.5)
        # image = random_gray(image, u=0.25)

        return  image, label

    ## ----------------------------------------------------



    log.write('** dataset setting **\n')
    #batch_size   =  2
    batch_size = params.step_batch_size
    num_grad_acc =  params.real_batch_size//batch_size

    train_dataset = KgCarDataset(  'train_v%d_k%d'%(params.k_version,params.k_folds),
                                   #'train_5088',
                                   'train',
                                   #'train128x128', ## 1024x1024 ##
                                   #'test_100064', 'test1024x1024',
                                transform = [ lambda x,y:train_augment(x,y), ], mode='train')
    train_loader  = DataLoader(
                        train_dataset,
                        #sampler = RandomSampler(train_dataset),
                        sampler = RandomSamplerWithLength(train_dataset,len(train_dataset)),
                        batch_size  = batch_size,
                        drop_last   = True,
                        num_workers = 4,
                        pin_memory  = True)
    ##check_dataset(train_dataset, train_loader), exit(0)

    valid_dataset = KgCarDataset('valid_v%d_k%d'%(params.k_version,params.k_folds), 
                                 #'train128x128', 
                                 'train',
                                  transform=[], mode='train')
    valid_loader  = DataLoader(
                        valid_dataset,
                        sampler = SequentialSampler(valid_dataset),
                        batch_size  = batch_size,
                        drop_last   = False,
                        num_workers = 4,
                        pin_memory  = True)


    log.write('\ttrain_dataset.split = %s\n'%train_dataset.split)
    log.write('\tvalid_dataset.split = %s\n'%valid_dataset.split)
    log.write('\tlen(train_dataset)  = %d\n'%len(train_dataset))
    log.write('\tlen(valid_dataset)  = %d\n'%len(valid_dataset))
    log.write('\n%s\n\n'%(inspect.getsource(train_augment)))


    ## net ----------------------------------------
    log.write('** net setting **\n')

    #net = Net(in_shape=(3, 128, 128))
    net = Net(in_shape=(3, params.input_h, params.input_w))
    
    if torch.cuda.device_count() > 1: 
        net = torch.nn.DataParallel(net).cuda()
    else:
        net.cuda()

    log.write('%s\n\n'%(type(net)))
    if initial_checkpoint is None:
        log.write('%s\n\n'%(str(net)))
        log.write('%s\n\n'%(inspect.getsource(net.__init__)))
        log.write('%s\n\n'%(inspect.getsource(net.forward )))

    ## optimiser ----------------------------------
    if params.optimer == 'SGD':
        optimizer = optim.SGD(net.parameters(), lr=0.01, momentum=0.9, weight_decay=0.0005)
    #optimizer = optim.SGD(filter(lambda p: p.requires_grad, net.parameters()), lr=0.01, momentum=0.9, weight_decay=0.0005)
    if params.optimer == 'Adam':
        optimizer = optim.Adam(net.parameters(), lr=0.001, betas=(0.9, 0.999), eps=1e-8,
                 weight_decay=0)
        # optimizer = optim.Adam(net.parameters(), lr=0.001, betas=(0.9, 0.999), eps=1e-8,
        #         weight_decay=0.0005)       

    num_epoches = 150  #100
    it_print    = 1    #20
    it_smooth   = 20
    epoch_valid = list(range(0,num_epoches+1))
    epoch_save  = list(range(0,num_epoches+1))
    #LR = StepLR([ (0, 0.01),  (35, 0.005),  (40,0.001),  (42, -1),(44, -1)])
    if params.optimer == 'SGD':
        # LR = StepLR([ (0, 0.01),  (35, 0.005),  (40,0.001),  (45, 0.0002),(55, -1)])
        LR = StepLR(params.LR_sgd)
    if params.optimer == 'Adam':
        LR = StepLR(params.LR_adam)

    #https://github.com/EKami/carvana-challenge/blob/7d20494f40b39686c25159403e2a27a82f4096a9/src/nn/classifier.py
    lr_scheduler = ReduceLROnPlateau(optimizer, 'min', factor=0.2, patience=4, verbose=True, min_lr=1e-7)
    #LR = StepLR([ (0, 0.01),])
    #LR = StepLR([ (0, 0.005),])


    ## resume from previous ------------------------
    log.write('\ninitial_checkpoint=%s\n\n'%initial_checkpoint)
    log.write('%s\n\n'%(type(net)))

    start_epoch=0
    if initial_checkpoint is not None:
        checkpoint  = torch.load(initial_checkpoint)
        start_epoch = checkpoint['epoch']
        net.load_state_dict(checkpoint['state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer'])


    #merge_bn_in_net(net)
    #training ####################################################################3
    log.write('** start training here! **\n')
    log.write(' num_grad_acc x batch_size = %d x %d=%d\n'%(num_grad_acc,batch_size,num_grad_acc*batch_size))
    #log.write(' input_size = %d x %d\n'%(params.input_size,params.input_size) )
    log.write(' input_size = %d x %d\n'%(params.input_h,params.input_w) )
    log.write(' optimizer=%s\n'%str(optimizer) )
    if params.using_ReduceLROnPlateau is True:
        log.write(' is_ReduceLRonPlateau: %s\n'%str(lr_scheduler))
        log.write(' ReduceLRonPlateau_factor: %0.3f\n'%lr_scheduler.factor)
    else:
        log.write(' LR=%s\n\n'%str(LR) )
    log.write('\n')


    log.write('epoch    iter      rate   | valid_loss/acc | train_loss/acc | batch_loss/acc ... \n')
    log.write('--------------------------------------------------------------------------------------------------\n')

    num_its = len(train_loader)
    smooth_loss = 0.0
    smooth_acc  = 0.0
    train_loss  = 0.0
    train_acc   = 0.0
    #valid_loss  = 0.0
    valid_loss = 100
    valid_acc   = 0.0
    batch_loss  = 0.0
    batch_acc   = 0.0
    time = 0

    start_lr = get_learning_rate(optimizer)[0]

    if initial_checkpoint is not None:
        start_lr = start_lr * num_grad_acc

    start0 = timer()
    for epoch in range(start_epoch, num_epoches+1):  # loop over the dataset multiple times

        if epoch > params.max_epochs: break
        #---learning rate schduler ------------------------------
        if params.using_ReduceLROnPlateau == True:
            adjust_learning_rate(optimizer, start_lr/num_grad_acc)
            lr_scheduler.step(valid_loss)
            rate = get_learning_rate(optimizer)[0]*num_grad_acc #check
            start_lr = rate
        else:
            lr = LR.get_rate(epoch, num_epoches)
            if lr<0 : break
            adjust_learning_rate(optimizer, lr/num_grad_acc)
            rate = get_learning_rate(optimizer)[0]*num_grad_acc #check
        #--------------------------------------------------------


        # validate at current epoch
        if epoch in epoch_valid:
            net.eval()
            valid_loss, valid_acc = evaluate(net, valid_loader)

            print('\r',end='',flush=True)
            log.write('%5.1f   %5d    %0.6f   | %0.5f  %0.6f | %0.5f  %0.5f | %0.5f  %0.5f  |  %3.1f min \n' % \
                    (epoch, num_its, rate, valid_loss, valid_acc, train_loss, train_acc, batch_loss, batch_acc, time))


        #if 1:
        if epoch in epoch_save:
            torch.save(net.state_dict(),out_dir +'/snap/%03d.pth'%epoch)
            torch.save({
                'state_dict': net.state_dict(),
                'optimizer' : optimizer.state_dict(),
                'epoch'     : epoch,
            }, out_dir +'/checkpoint/%03d.pth'%epoch)
            ## https://github.com/pytorch/examples/blob/master/imagenet/main.py

        if epoch==num_epoches: break ##########################################-


        start = timer()
        sum_train_loss = 0.0
        sum_train_acc  = 0.0
        sum = 0

        net.train()
        for it, (images, labels, indices) in enumerate(train_loader, 0):
            images  = Variable(images).cuda()
            labels  = Variable(labels).cuda()

            #forward
            logits = net(images)
            probs  = F.sigmoid(logits)
            masks  = (probs>0.5).float()

            loss = criterion(logits, labels, is_weight=True)
            acc  = dice_loss(masks, labels)

            # optimizer.zero_grad()
            # loss.backward()
            # optimizer.step()

            # accumulate gradients
            if it==0:
                optimizer.zero_grad()
            loss.backward()
            if it%num_grad_acc==0:
                optimizer.step()
                optimizer.zero_grad()  # assume no effects on bn for accumulating grad


            # print statistics
            batch_acc  = acc.data [0]
            batch_loss = loss.data[0]
            sum_train_loss += batch_loss
            sum_train_acc  += batch_acc
            sum += 1
            if it%it_smooth == 0:
                train_loss = sum_train_loss/sum
                train_acc  = sum_train_acc /sum
                sum_train_loss = 0.0
                sum_train_acc  = 0.0
                sum = 0

            if it%it_print == 0 or it==num_its-1:
                print('\r%5.1f   %5d    %0.4f   | .......  ....... | %0.5f  %0.5f | %0.5f  %0.5f ' % \
                        (epoch + (it+1)/num_its, it+1, rate, train_loss, train_acc, batch_loss, batch_acc),\
                        end='',flush=True)

            #debug show prediction results ---
            if 0:
            #if it%100==0:
                show_batch_results(indices, images, probs, labels,
                                   wait=1, out_dir=out_dir+'/train/results', names=train_dataset.names, epoch=epoch, it=it)

        end  = timer()
        time = (end - start)/60
        #end of epoch --------------------------------------------------------------



    #---- end of all epoches -----
    end0  = timer()
    time0 = (end0 - start0) / 60
    log.write('\nalltime = %f min\n'%time0)
    ## save final
    torch.save(net.state_dict(),out_dir +'/snap/final.pth')

# ------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------

def run_submit1():

    is_merge_bn = 1
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-00d'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'
    out_dir = params.out_dir + params.save_path

    # model_file = out_dir +'/snap/060.pth'  #final
    model_file = out_dir + '/snap/' + params.model_snap

    #logging, etc --------------------
    os.makedirs(out_dir+'/submit/results',  exist_ok=True)
    os.makedirs(out_dir+'/submit/test_mask',  exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), out_dir +'/backup/submit.code.zip')

    log = Logger()
    log.open(out_dir+'/log.submit.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** some project setting **\n')
    log.write('* model_file=%s\n' % model_file)



    ## dataset ----------------------------
    log.write('** dataset setting **\n')
    batch_size = 4

    test_dataset = KgCarDataset( 'test_100064',  'test',#100064  #3197
                                 #'valid_v0_768',  'train1024x1024',#100064  #3197
                                     transform= [
                                    ],mode='test')
    test_loader  = DataLoader(
                        test_dataset,
                        sampler     = SequentialSampler(test_dataset),
                        batch_size  = batch_size,
                        drop_last   = False,
                        num_workers = 12,
                        pin_memory  = True)

    log.write('\tbatch_size         = %d\n'%batch_size)
    log.write('\ttest_dataset.split = %s\n'%test_dataset.split)
    log.write('\tlen(test_dataset)  = %d\n'%len(test_dataset))
    log.write('\n')


    ## net ----------------------------------------
    net = Net(in_shape=(3, CARVANA_HEIGHT, CARVANA_WIDTH))
    net.load_state_dict(torch.load(model_file))
    net.cuda()

    #num_valid = len(test_dataset)
    names = test_dataset.names
    df = test_dataset.df.set_index('id')

    if is_merge_bn: merge_bn_in_net(net)
    ## start testing now #####
    log.write('start prediction ...\n')
    start = timer()

    net.eval()

    time_taken = 0
    end = 0
    num = 0

    test_num = len(test_loader)

    for it, (images, indices) in enumerate(test_loader, 0):
        images  = Variable(images,volatile=True).cuda()
        #labels  = Variable(labels).cuda().half()
        batch_size = len(indices)

        num = num + batch_size

        #forward
        t0 =  timer()
        logits = net(images)
        probs  = F.sigmoid(logits)

        #warm start
        #if it>10:
        #    time_taken = time_taken + timer() - t0
        #    print(time_taken)

        #a = dice_loss((probs.float()>0.5).float(), labels.float(), is_average=False)
        #accs[start:start + batch_size]=a.data.cpu().numpy()

        ## full results ----------------
        probs  = (probs.data.float().cpu().numpy()*255).astype(np.uint8)
        for b in range(batch_size):
            name = names[indices[b]]
            prob = probs[b]
            
            cv2.imwrite(out_dir+'/submit/test_mask/%s.png'%(name), prob)

        print('\r it: %d, num: %d'%(it,num), end=' ', flush=True)
        if num%8000 == 0:
            log.write(' [it: %d, num: %d] \n'%(it,num))
            log.write('\t time = %0.2f min \n'%((timer() - start)/60))
    
    log.write(' save_masks = %f min\n'%((timer() - start) / 60))
    log.write('\n')
    assert(num == test_num)




def run_submit2():

    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet512-peduo-label-00c'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'
    out_dir = params.out_dir + params.save_path

    #logging, etc --------------------
    os.makedirs(out_dir+'/submit/results',  exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), out_dir +'/backup/submit.code.zip')

    log = Logger()
    log.open(out_dir+'/log.submit.txt',mode='a')
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
        p = cv2.imread(out_dir+'/submit/test_mask/%s.png'%(names[i]),cv2.IMREAD_GRAYSCALE)
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

            #debug
            #if 0:
    '''           
            if m<10 and i==0:
                name = names[ind]
                img_file = CARVANA_DIR + '/images/test/%s.jpg'%(name)
                #img_file = CARVANA_DIR + '/images/train/%s'%(name)
                image = cv2.imread(img_file)
                results = make_results_image(image, label=None, prob=prob)
                im_show('results',results,0.33)
                im_show('prob',prob,0.33)
                im_show('p',p,0.33)
                cv2.waitKey(1)
    '''
    #-----------------------------------------------------
    names = [name+'.jpg' for name in names]

    dir_name = out_dir.split('/')[-1]
    gz_file  = out_dir + '/submit/results-%s.csv.gz'%dir_name
    df = pd.DataFrame({ 'img' : names, 'rle_mask' : rles})
    df.to_csv(gz_file, index=False, compression='gzip')

    log.write('\tdf.to_csv time = %f min\n'%((timer() - total_start) / 60)) #3 min
    log.write('\n')

def TTA(): #test time augmentation

    is_merge_bn = 1
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-00d'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'
    out_dir = params.out_dir + params.save_path

    # model_file = out_dir +'/snap/060.pth'  #final
    model_file = out_dir + '/snap/' + params.model_snap

    #logging, etc --------------------
    os.makedirs(out_dir+'/TTA/results',  exist_ok=True)
    os.makedirs(out_dir+'/TTA/test_mask',  exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), out_dir +'/backup/TTA.code.zip')

    log = Logger()
    log.open(out_dir+'/log.TTA.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** some project setting **\n')
    log.write('* model_file=%s\n' % model_file)



    ## dataset ----------------------------
    log.write('** dataset setting **\n')
    batch_size = 4

    test_dataset = KgCarDataset_TTA( 'bad_images_split',  'test',#100064  #3197
                                 #'valid_v0_768',  'train1024x1024',#100064  #3197
                                     transform= [
                                    ],mode='test')
    test_loader  = DataLoader(
                        test_dataset,
                        sampler     = SequentialSampler(test_dataset),
                        batch_size  = batch_size,
                        drop_last   = False,
                        num_workers = 12,
                        pin_memory  = True)

    log.write('\tbatch_size         = %d\n'%batch_size)
    log.write('\ttest_dataset.split = %s\n'%test_dataset.split)
    log.write('\tlen(test_dataset)  = %d\n'%len(test_dataset))
    log.write('\n')


    ## net ----------------------------------------
    net = Net(in_shape=(3, CARVANA_HEIGHT, CARVANA_WIDTH))
    net.load_state_dict(torch.load(model_file))
    net.cuda()

    #num_valid = len(test_dataset)
    names = test_dataset.names
    df = test_dataset.df.set_index('id')

    if is_merge_bn: merge_bn_in_net(net)
    ## start testing now #####
    log.write('TTA ...\n')
    start = timer()

    net.eval()

    time_taken = 0
    end = 0
    num = 0

    test_num = len(test_loader)

    for it, (images0, images1, images2, indices) in enumerate(test_loader, 0):
        images0  = Variable(images0,volatile=True).cuda()
        images1  = Variable(images1,volatile=True).cuda()
        images2  = Variable(images2,volatile=True).cuda()
        #labels  = Variable(labels).cuda().half()
        batch_size = len(indices)

        num = num + batch_size

        #forward
        t0 =  timer()

        logits0 = net(images0)
        probs0  = F.sigmoid(logits0)

        logits1 = net(images1)
        probs1  = F.sigmoid(logits1)

        logits2 = net(images2)
        probs2  = F.sigmoid(logits2)

        #warm start
        #if it>10:
        #    time_taken = time_taken + timer() - t0
        #    print(time_taken)

        #a = dice_loss((probs.float()>0.5).float(), labels.float(), is_average=False)
        #accs[start:start + batch_size]=a.data.cpu().numpy()

        ## full results ----------------
        probs = np.zeros((batch_size,CARVANA_H,CARVANA_W),np.uint16)
        probs0 = (probs0.data.float().cpu().numpy()*255).astype(np.uint8)
        probs1 = (probs1.data.float().cpu().numpy()*255).astype(np.uint8)
        probs2 = (probs2.data.float().cpu().numpy()*255).astype(np.uint8)

        probs += probs0
        probs += probs1
        probs += probs2
        probs = probs/3
        probs.astype(np.uint8)
        for b in range(batch_size):
            name = names[indices[b]]
            prob = probs[b]
            
            cv2.imwrite(out_dir+'/TTA/test_mask/%s.png'%(name), prob)
            cv2.imwrite(out_dir + '/TTA/test_mask/%s_origin.png' % (name), probs0[b])

        print('\r it: %d, num: %d'%(it,num), end=' ', flush=True)
        if num%8000 == 0:
            log.write(' [it: %d, num: %d] \n'%(it,num))
            log.write('\t time = %0.2f min \n'%((timer() - start)/60))
    
    log.write(' save_masks = %f min\n'%((timer() - start) / 60))
    log.write('\n')
    assert(num == test_num)


def save_vaild_mask_for_ensemble(): #保存预测的valid mask图片，为第二阶段ensemble生成训练集

    is_merge_bn = 1
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-00d'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'

    out_dir = params.out_dir + params.save_path

    # model_file = out_dir +'/snap/047.pth'  #final
    model_file = out_dir + '/snap/' + params.model_snap

    #logging, etc --------------------
    os.makedirs(out_dir+'/out_mask/results',  exist_ok=True)
    os.makedirs(out_dir+'/out_mask/train_mask',  exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), out_dir +'/backup/submit.code.zip')

    log = Logger()
    log.open(out_dir+'/log.make_valid_mask.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** some project setting **\n')
    log.write('* model_file=%s\n' % model_file)



    ## dataset ----------------------------
    log.write('** dataset setting **\n')
    batch_size = 4

    test_dataset = KgCarDataset( 'valid_v%d_k%d'%(params.k_version,params.k_folds),
                                'train',#100064  #3197
                                #'valid_v0_768',  'train1024x1024',#100064  #3197
                                transform= [
                                ],mode='test')
    test_loader  = DataLoader(
                            test_dataset,
                            sampler     = SequentialSampler(test_dataset),
                            batch_size  = batch_size,
                            drop_last   = False,
                            num_workers = 12,
                            pin_memory  = True)

    log.write('\tbatch_size         = %d\n'%batch_size)
    log.write('\ttest_dataset.split = %s\n'%test_dataset.split)
    log.write('\tlen(test_dataset)  = %d\n'%len(test_dataset))
    log.write('\n')


    ## net ----------------------------------------
    net = Net(in_shape=(3, CARVANA_HEIGHT, CARVANA_WIDTH))
    net.load_state_dict(torch.load(model_file))
    net.cuda()

    #num_valid = len(test_dataset)
    names = test_dataset.names
    df = test_dataset.df.set_index('id')


    if is_merge_bn: merge_bn_in_net(net)
    ## start testing now #####
    log.write('start saving masks ...\n')
    start = timer()

    net.eval()
    # probs = predict8_in_blocks( net, test_loader, block_size=CSV_BLOCK_SIZE, save_dir=out_dir+'/submit',log=log)           # 20 min

    time_taken = 0
    end = 0
    num = 0

    test_num = len(test_loader)

    for it, (images, indices) in enumerate(test_loader, 0):
        images  = Variable(images,volatile=True).cuda()
        #labels  = Variable(labels).cuda().half()
        batch_size = len(indices)

        num = num + batch_size

        #forward
        t0 =  timer()
        logits = net(images)
        probs  = F.sigmoid(logits)

        #warm start
        #if it>10:
        #    time_taken = time_taken + timer() - t0
        #    print(time_taken)

        #a = dice_loss((probs.float()>0.5).float(), labels.float(), is_average=False)
        #accs[start:start + batch_size]=a.data.cpu().numpy()

        ## full results ----------------
        probs  = (probs.data.float().cpu().numpy()*255).astype(np.uint8)
        for b in range(batch_size):
            name = names[indices[b]]
            prob = probs[b]

            cv2.imwrite(out_dir+'/out_mask/train_mask/%s.png'%(name), prob)

        pass ######################
        #start = start + batch_size
        print('\r it: %d, num: %d'%(it,num), end=' ', flush=True)
        if num%8000 == 0:
            log.write(' [it: %d, num: %d] \n'%(it,num))
            log.write('\t time = %0.2f min \n'%((timer() - start)/60))
    
    log.write(' save_masks = %f min\n'%((timer() - start) / 60))
    log.write('\n')
    assert(num == test_num)

def run_valid():

    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'
    #out_dir    = '/root/share/project/kaggle-carvana-cars/results/single/UNet512-peduo-label-00'
    #out_dir    = '/root/share/project/kaggle-carvana-cars/results/single/UNet512-peduo-label-00c'
    #out_dir    = '/root/share/project/kaggle-carvana-cars/results/__old_4__/UNet1024-shallow-01b'
    out_dir = params.out_dir + params.save_path

    # model_file = out_dir +'/snap/final.pth'  #final
    model_file = out_dir + '/snap/' + params.model_snap

    is_results      = True
    is_full_results = True  #True

    #logging, etc --------------------
    if is_results:      shutil.rmtree(out_dir+'/valid/results_by_score',ignore_errors=True)
    if is_full_results: shutil.rmtree(out_dir+'/valid/full_results_by_score',ignore_errors=True)

    os.makedirs(out_dir+'/valid/full_results_by_score',  exist_ok=True)
    os.makedirs(out_dir+'/valid/full_results_by_name',   exist_ok=True)
    os.makedirs(out_dir+'/valid/results_by_score',  exist_ok=True)
    os.makedirs(out_dir+'/valid/results_by_name',   exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), out_dir +'/backup/valid.code.zip')

    log = Logger()
    log.open(out_dir+'/log.train.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** some project setting **\n')
    log.write('\tSEED    = %u\n' % SEED)
    log.write('\tfile    = %s\n' % __file__)
    log.write('\tout_dir = %s\n' % out_dir)
    log.write(' model_file=%s\n' % model_file)
    log.write('\n')


    batch_size   =  8
    valid_dataset = KgCarDataset(
                                #'train_160', 'train512x512',
                                #'train_v0_4320', 'train512x512',
                                'valid_v%d_k%d'%(params.k_version,params.k_folds),
                                'train', #'train1024x1024',
                                transform=[
                                ])
    valid_loader  = DataLoader(
                        valid_dataset,
                        sampler = SequentialSampler(valid_dataset),
                        batch_size  = batch_size,
                        drop_last   = False,
                        num_workers = 6,
                        pin_memory  = True)
    ##check_dataset(valid_dataset, valid_loader), exit(0)

    ## net ----------------------------------------
    net = Net(in_shape=(3, CARVANA_HEIGHT, CARVANA_WIDTH))
    net.load_state_dict(torch.load(model_file))
    net.cuda()

    num_valid = len(valid_dataset)
    names = valid_dataset.names
    df = valid_dataset.df.set_index('id')

    full_indices = np.zeros(num_valid,np.float32)
    full_accs    = np.zeros(num_valid,np.float32)
    accs         = np.zeros(num_valid,np.float32)
    net.eval().half()


    time_taken =0
    start=0
    end  =0
    for it, (images, labels, indices) in enumerate(valid_loader, 0):
        images  = Variable(images,volatile=True).cuda().half()
        labels  = Variable(labels).cuda().half()
        batch_size = len(indices)

        #forward
        t0 =  timer()
        logits = net(images)
        probs  = F.sigmoid(logits)

        #warm start
        if it>10:
            time_taken = time_taken + timer() - t0
            #print(time_taken)



        a = dice_loss((probs.float()>0.5).float(), labels.float(), is_average=False)
        accs[start:start + batch_size]=a.data.cpu().numpy()

        if is_results:
            show_batch_results(indices, images, probs, labels=labels, wait=1,
                    out_dir=out_dir+'/valid', mode='both', names=names, df=df, epoch=0, it=0)


        ## full results ----------------
        probs  = (probs.data.float().cpu().numpy()*255).astype(np.uint8)
        for b in range(batch_size):
            name = names[indices[b]]
            mask_file = CARVANA_DIR + '/annotations/%s/%s_mask.png'%('train',name)
            label = cv2.imread(mask_file,cv2.IMREAD_GRAYSCALE)

            prob = probs[b]
            prob = cv2.resize(prob,dsize=(CARVANA_WIDTH,CARVANA_HEIGHT),interpolation=cv2.INTER_LINEAR)  #INTER_CUBIC  ##

            score = one_dice_loss_py(prob>127, label>127)
            full_accs   [start+b] = score
            full_indices[start+b] = indices[b]

            if is_full_results:
                meta = df.loc[name[:-3]]
                description = '%d %s %s %s'%( int(meta['year']), meta['make'],  meta['model'], meta['trim2'])
                results = draw_dice_on_image(label, prob)
                draw_shadow_text  (results, '%s.jpg'%(name), (5,30),  1, (255,255,255), 2)
                draw_shadow_text  (results, description, (5,60),  1, (255,255,255), 2)

                #print('full : %0.6f'%score)
                #im_show('results',results,0.33)
                #cv2.waitKey(1)

                cv2.imwrite(out_dir+'/valid/full_results_by_score/%0.5f-%s.png'%(score,name), results)
                cv2.imwrite(out_dir+'/valid/full_results_by_name/%s.png'%(name), results)


        pass ######################
        start = start + batch_size


    #save ----------------
    time_taken = time_taken/60
    accuracy = accs.mean()
    full_accuracy = full_accs.mean()
    print('accuracy (full) = %f (%f)'%(accuracy,full_accuracy))
    print('time_taken min = %f'%(time_taken))
    with open(out_dir+'/valid/full_results-summary.INTER_LINEAR.txt', 'w') as f:
        for n in range(num_valid):
            f.write('%s\t%f\t%f\t%d\n'%(names[n],accs[n],full_accs[n],full_indices[n]))
        f.write('\naccuracy (full) = %f (%f)\n'%(accuracy,full_accuracy))
        f.write('\ntime_taken min = %f\n'%(time_taken))


# main #################################################################
if __name__ == '__main__':
    print( '%s: calling main function ... ' % os.path.basename(__file__))

    opts, args = getopt.getopt(sys.argv[1:], 'tvms', ['s1','s2','tta'])
    
    for opt, val in opts: 
        print(opt)
    
    if opt == '-t':
        run_train()
    elif opt =='-v':  
        run_valid()
    elif opt =='-m':  
        save_vaild_mask_for_ensemble()
    elif opt =='-s':  
        run_submit1()
        run_submit2()
    elif opt =='--s1':
        run_submit1()
    elif opt =='--s2':
        run_submit2()
    elif opt =='--tta':
        TTA()
    else:
        print('nothing,stop')

    print('\nsucess!')