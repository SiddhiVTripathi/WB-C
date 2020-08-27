'''
Source code for CVPR 2020 paper
'Learning to Cartoonize Using White-Box Cartoon Representations'
by Xinrui Wang and Jinze yu
'''



import tensorflow as tf
import tf_slim as slim
import wandb
import utils
import os
import numpy as np
import argparse
import network 
from tqdm import tqdm
from random import sample


os.environ["CUDA_VISIBLE_DEVICES"]="0"
wandb.init(project="white-box-cartoonization", sync_tensorboard=True)

def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch_size", default = 256, type = int)
    parser.add_argument("--batch_size", default = 16, type = int)     
    parser.add_argument("--total_iter", default = 10000, type = int)
    parser.add_argument("--adv_train_lr", default = 2e-4, type = float)
    parser.add_argument("--gpu_fraction", default = 0.5, type = float)
    parser.add_argument("--save_dir", default = 'pretrain')

    args = parser.parse_args()
    
    return args



def train(args):
    

    input_photo = tf.compat.v1.placeholder(tf.float32, [args.batch_size, 
                                args.patch_size, args.patch_size, 3])
    
    output = network.unet_generator(input_photo)
    
    recon_loss = tf.reduce_mean(input_tensor=tf.compat.v1.losses.absolute_difference(input_photo, output))

    all_vars = tf.compat.v1.trainable_variables()
    gene_vars = [var for var in all_vars if 'gene' in var.name]
      
    update_ops = tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.UPDATE_OPS)
    with tf.control_dependencies(update_ops):
        
        optim = tf.compat.v1.train.AdamOptimizer(args.adv_train_lr, beta1=0.5, beta2=0.99)\
                                        .minimize(recon_loss, var_list=gene_vars)
        
        
    '''
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)
    '''
    gpu_options = tf.compat.v1.GPUOptions(per_process_gpu_memory_fraction=args.gpu_fraction)
    sess = tf.compat.v1.Session(config=tf.compat.v1.ConfigProto(gpu_options=gpu_options))
    saver = tf.compat.v1.train.Saver(var_list=gene_vars, max_to_keep=20)
   
    with tf.device('/device:GPU:0'):

        sess.run(tf.compat.v1.global_variables_initializer())
        face_photo_dir = 'dataset/face_photo'
        face_photo_list = sample(utils.load_image_list(face_photo_dir),3000)
        scenery_photo_dir = 'dataset/scenery_photo'
        scenery_photo_list = sample(utils.load_image_list(scenery_photo_dir),3000)


        for total_iter in tqdm(range(args.total_iter)):

            if np.mod(total_iter, 5) == 0: 
                photo_batch = utils.next_batch(face_photo_list, args.batch_size)
            else:
                photo_batch = utils.next_batch(scenery_photo_list, args.batch_size)
                
            _, r_loss = sess.run([optim, recon_loss], feed_dict={input_photo: photo_batch})

            if np.mod(total_iter+1, 50) == 0:

                wandb.log({"r_loss":r_loss,"iteration":total_iter})
                print('pretrain, iter: {}, recon_loss: {}'.format(total_iter, r_loss))
                if np.mod(total_iter+1, 500 ) == 0:
                    
                    saver.save(sess, args.save_dir+'save_models/model', 
                               write_meta_graph=False, global_step=total_iter)
                     
                    photo_face = utils.next_batch(face_photo_list, args.batch_size)
                    photo_scenery = utils.next_batch(scenery_photo_list, args.batch_size)

                    result_face = sess.run(output, feed_dict={input_photo: photo_face})
                   
                    result_scenery = sess.run(output, feed_dict={input_photo: photo_scenery})

                    wandb.log({"pretrain example":[wandb.Image(utils.write_batch_image(result_face, args.save_dir+'/images', 
                                            str(total_iter)+'_face_result.jpg', 4), caption=str(total_iter)+'_face_result')]})
                    wandb.log({"pretrain example":[wandb.Image(utils.write_batch_image(photo_face, args.save_dir+'/images', 
                                            str(total_iter)+'_face_photo.jpg', 4), caption=str(total_iter)+'_face_result')]})
                    wandb.log({"pretrain example":[wandb.Image(utils.write_batch_image(result_scenery, args.save_dir+'/images', 
                                            str(total_iter)+'_scenery_result.jpg', 4), caption=str(total_iter)+'_face_result')]})
                    wandb.log({"pretrain example":[wandb.Image(utils.write_batch_image(photo_scenery, args.save_dir+'/images', 
                                            str(total_iter)+'_scenery_photo.jpg', 4), caption=str(total_iter)+'_face_result')]})

        
    wandb.tensorflow.log(tf.summary.merge_all())

                    

 
            
if __name__ == '__main__':
    
    args = arg_parser()
    train(args)  
