import params

from common import *
from dataset.carvana_cars import *
from train_seg_net import evaluate, criterion, show_batch_results, predict8_in_blocks

from model.tool import *
from model.rate import *
from model.segmentation.loss import *
from model.segmentation.blocks import *

#-------------测试 itchat-----------
#import itchat
#----------------------------------

Net = params.post_model

#CSV_BLOCK_SIZE = params.npy_BLOCK_SIZE

# ------------------------------------------------------------------------------------
def run_post_train():


    out_dir = params.out_dir + params.save_path
    
    #initial_checkpoint = None
    if params.init_post is not None:
        initial_checkpoint = out_dir + '/post_train/checkpoint/' + params.init_post
    else:
        initial_checkpoint = None
        #'/root/share/project/kaggle-carvana-cars/results/single/UNet128-00-xxx/checkpoint/006.pth'


    #logging, etc --------------------
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(out_dir+'/post_train/train/results', exist_ok=True)
    os.makedirs(out_dir+'/post_train/valid/results', exist_ok=True)
    os.makedirs(out_dir+'/post_train/backup', exist_ok=True)
    os.makedirs(out_dir+'/post_train/checkpoint', exist_ok=True)
    os.makedirs(out_dir+'/post_train/snap', exist_ok=True)
    backup_project_as_zip( os.path.dirname(os.path.realpath(__file__)), out_dir +'/post_train/backup/train.code.zip')

    log = Logger()
    log.open(out_dir+'/post_train/log.post_train.txt',mode='a')
    log.write('\n--- [START %s] %s\n\n' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '-' * 64))
    log.write('** experiment for average labels channel as prior**\n\n')
    
    log.write('** some project setting **\n')
    log.write('\tSEED    = %u\n' % SEED)
    log.write('\tfile    = %s\n' % __file__)
    log.write('\tout_dir = %s\n' % out_dir)
    log.write('\n')



    ## dataset ----------------------------------------
    def train_augment(image,mask,label):
        image, mask, label = random_horizontal_flipN([image, mask, label])
        image, mask, label = random_shift_scale_rotateN([image, mask, label], shift_limit=(-0.0625,0.0625),
                  scale_limit=(0.91,1.21), rotate_limit=(-0,0))

        #image, label = random_mask_hue(image, label, hue_limit=(-1,1), u=0.5)
        #image = random_hue(image, hue_limit=(-1,1), u=0.5)

        # image = random_brightness(image, limit=(-0.5,0.5), u=0.5)
        # image = random_contrast  (image, limit=(-0.5,0.5), u=0.5)
        # image = random_saturation(image, limit=(-0.3,0.3), u=0.5)
        # image = random_gray(image, u=0.25)

        return  image, mask, label

    ## ----------------------------------------------------



    log.write('** dataset setting **\n')
    #batch_size   =  2
    batch_size = params.step_batch_size
    num_grad_acc =  params.real_batch_size//batch_size

    train_dataset = post_prosses_Dataset(  'post_train_v2_k%d'%params.post_k_folds,
                                   #'train_5088',
                                   'train',
                                   #'train128x128', ## 1024x1024 ##
                                   #'test_100064', 'test1024x1024',
                                   transform = [ lambda x,y,z:train_augment(x,y,z), ],
                                   mode='train')
    train_loader  = DataLoader(
                        train_dataset,
                        #sampler = RandomSampler(train_dataset),
                        sampler = RandomSamplerWithLength(train_dataset,4320),
                        batch_size  = batch_size,
                        drop_last   = True,
                        num_workers = 4,
                        pin_memory  = True)
    ##check_dataset(train_dataset, train_loader), exit(0)

    valid_dataset = post_prosses_Dataset('post_valid_v2_k%d'%params.post_k_folds,
                                 #'train128x128', 
                                 'train',
                                 mode='train')
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
    net = Net(in_shape=(4, params.input_h, params.input_w))
    net.cuda()

    log.write('%s\n\n'%(type(net)))
    if initial_checkpoint is None:
        log.write('%s\n\n'%(str(net)))
        log.write('%s\n\n'%(inspect.getsource(net.__init__)))
        log.write('%s\n\n'%(inspect.getsource(net.forward )))

    ## optimiser ----------------------------------
    if params.post_optimer == 'SGD':
        optimizer = optim.SGD(net.parameters(), lr=0.01, momentum=0.9, weight_decay=0.0005)
    #optimizer = optim.SGD(filter(lambda p: p.requires_grad, net.parameters()), lr=0.01, momentum=0.9, weight_decay=0.0005)
    if params.post_optimer == 'Adam':
        optimizer = optim.Adam(net.parameters(), lr=0.001, betas=(0.9, 0.999), eps=1e-8,
                 weight_decay=0)
        #optimizer = optim.Adam(net.parameters(), lr=0.001, betas=(0.9, 0.999), eps=1e-8,
        #         weight_decay=0.0005)

    num_epoches = 150  #100
    it_print    = 1    #20
    it_smooth   = 20
    epoch_valid = list(range(0,num_epoches+1))
    epoch_save  = list(range(0,num_epoches+1))
    #LR = StepLR([ (0, 0.01),  (35, 0.005),  (40,0.001),  (42, -1),(44, -1)])
    if params.post_optimer == 'SGD':
        LR = StepLR([ (0, 0.01),  (35, 0.005),  (40,0.001),  (45, 0.0002),(55, -1)])
    if params.post_optimer == 'Adam':
        LR = StepLR([ (0, 0.001),  (35, 0.0005),  (55, -1)])

    #https://github.com/EKami/carvana-challenge/blob/7d20494f40b39686c25159403e2a27a82f4096a9/src/nn/classifier.py
    lr_scheduler = ReduceLROnPlateau(optimizer, 'min', patience=4, verbose=True, min_lr=1e-7)
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
    log.write(' input_size = %d x %d\n'%(params.input_h,params.input_w) )
    log.write(' optimizer=%s\n'%str(optimizer) )
    if params.post_using_ReduceLROnPlateau is True:
        log.write(' is_ReduceLRonPlateau: %s\n'%str(params.post_using_ReduceLROnPlateau))
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

        if epoch > params.max_post_train_epochs: break
        #---learning rate schduler ------------------------------
        if params.post_using_ReduceLROnPlateau == True:
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
            torch.save(net.state_dict(),out_dir +'/post_train/snap/%03d.pth'%epoch)
            torch.save({
                'state_dict': net.state_dict(),
                'optimizer' : optimizer.state_dict(),
                'epoch'     : epoch,
            }, out_dir +'/post_train/checkpoint/%03d.pth'%epoch)
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
                                   wait=1, out_dir=out_dir+'/post_train/train/results', names=train_dataset.names, epoch=epoch, it=it)

        end  = timer()
        time = (end - start)/60
        #end of epoch --------------------------------------------------------------



    #---- end of all epoches -----
    end0  = timer()
    time0 = (end0 - start0) / 60
    log.write('\nalltime = %f min\n'%time0)
    ## save final
    torch.save(net.state_dict(),out_dir +'/post_train/snap/final.pth')

def run_post_submit1():

    is_merge_bn = 1
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-00d'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'
    out_dir = params.out_dir + params.save_path

    out_dir = out_dir + '/post_train'

    # model_file = out_dir +'/snap/040.pth'  #final
    model_file = out_dir + '/snap/' + params.post_submit_snap

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
    batch_size = 8

    test_dataset = post_prosses_Dataset( 'test_100064',  'test',#100064  #3197
                                 #'valid_v0_768',  'train1024x1024',#100064  #3197
                                     mode='test')
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
    net = Net(in_shape=(4, CARVANA_HEIGHT, CARVANA_WIDTH))
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

        ## full results ----------------
        probs  = (probs.data.float().cpu().numpy()*255).astype(np.uint8)
        for b in range(batch_size):
            name = names[indices[b]]
            prob = probs[b]

            cv2.imwrite(out_dir+'/submit/test_mask/%s.png'%(name), prob)

        print('\rit: %d, num: %d'%(it,num), end=' ', flush=True)
        if num%1000 == 0:
            log.write(' [it: %d, num: %d] \n'%(it,num))
            log.write('\t time = %0.2f min \n'%((timer() - start)/60))

    log.write(' save_masks = %f min\n'%((timer() - start) / 60))
    log.write('\n')
    assert(num == test_num)


def run_post_submit2():

    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet512-peduo-label-00c'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'
    out_dir = params.out_dir + params.save_path

    out_dir = out_dir + '/post_train'
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

    #-----------------------------------------------------
    names = [name+'.jpg' for name in names]

    dir_name = out_dir.split('/')[-1]
    gz_file  = out_dir + '/submit/results-%s.csv.gz'%dir_name
    df = pd.DataFrame({ 'img' : names, 'rle_mask' : rles})
    df.to_csv(gz_file, index=False, compression='gzip')

    log.write('\tdf.to_csv time = %f min\n'%((timer() - total_start) / 60)) #3 min
    log.write('\n')

def TTA(): #test time augmentation --post train 未完工

    is_merge_bn = 1
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-00d'
    #out_dir = '/root/share/project/kaggle-carvana-cars/results/single/UNet1024-peduo-label-01c'
    out_dir = params.out_dir + params.save_path

    out_dir = out_dir + '/post_train'

    # model_file = out_dir +'/snap/060.pth'  #final
    model_file = out_dir + '/snap/' + params.post_submit_snap

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

    test_dataset = post_prosses_Dataset( 'bad_images_split',  'test',#100064  #3197
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
    net = Net(in_shape=(4, CARVANA_HEIGHT, CARVANA_WIDTH))
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

    for it, (images0, images1, images2, indices) in enumerate(test_loader, 0):
        images0  = Variable(images0,volatile=True).cuda()
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
        probs0 = (probs0.data.float().cpu().numpy()*255).astype(np.uint8)
        probs1 = (probs1.data.float().cpu().numpy()*255).astype(np.uint8)
        probs2 = (probs2.data.float().cpu().numpy()*255).astype(np.uint8)

        probs = (probs0 + probs1 + probs2)/3
        for b in range(batch_size):
            name = names[indices[b]]
            prob = probs[b]
            
            cv2.imwrite(out_dir+'/TTA/test_mask/%s.png'%(name), prob)

        print('it: %d, num: %d'%(it,num), end=' ', flush=True)
        if num%1000 == 0:
            log.write(' [it: %d, num: %d] \n'%(it,num))
            log.write('\t time = %0.2f min \n'%((timer() - start)/60))
    
    log.write(' save_masks = %f min\n'%((timer() - start) / 60))
    log.write('\n')
    assert(num == test_num)


# ------------------------------------------------------------------------------------
if __name__ == '__main__':
    print('%s: calling main function ... ' % os.path.basename(__file__))

    #-------------测试 itchat-----------
    #itchat.auto_login()
    #----------------------------------

    opts, args = getopt.getopt(sys.argv[1:], 'ts', ['s1', 's2', 'tta'])

    for opt, val in opts:
        print(opt)

    if opt == '-t':
        run_post_train()
    elif opt == '-s':
        run_post_submit1()
        run_post_submit2()
        
    elif opt == '--s1':
        run_post_submit1()
    elif opt == '--s2':
        run_post_submit2()
    elif opt == '--tta':
        TTA()
    else:
        print('nothing,stop')
        

    print('\nsucess!')